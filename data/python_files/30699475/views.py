import datetime
from pymongo.objectid import ObjectId
from flask import Module, render_template, url_for, request, session, redirect
from flask import flash, current_app as app, abort, g

from semaphore.core.auth.decorators import login_required
from semaphore.core.settings.decorators import permission_required
from semaphore.core.settings.permissions import resolve_permission

from semaphore.core.settings import permissions

from . import module
from .models import Ticket
from .forms import TicketForm

@module.route('/ticket/<id>', methods=('GET', 'POST'))
@login_required
@permission_required(permissions.TICKET, permissions.READ)
def view(id):
	# Check that the ticket requested belongs to the organization
	# that the user belongs to.
	ticket = Ticket.get_ticket(id)
	if ticket is None:
		abort(404)

	form = TicketForm(request.form, ticket)
	form.bind_runtime_fields(g, ticket)
	
	if request.method == 'POST' and form.validate_on_submit():
		# Check for the permission
		if resolve_permission(permissions.TICKET, permissions.MODIFY):
			# DO SOMETHING
			pass
		elif resolve_permission(permissions.COMMENT, permissions.CREATE):
			# They only have the permission to add a comment, so just add their
			# comment. 
			ticket.add_comment(g.user, form.body.data)
		else:
			flash(_('You do not have permission to modify tickets'))
		return redirect(url_for('tickets.view', id=id))

	return render_template('tickets/ticket_view.html', form=form,
			ticket=ticket, modifable=resolve_permission(permissions.TICKET,
				permissions.MODIFY),
			commentable=resolve_permission(permissions.COMMENT,
				permissions.CREATE))


@module.route('/ticket/search')
@login_required
@permission_required(permissions.TICKET, permissions.READ)
def search():
	q = request.args.get('q', '')
	results = Ticket.search_tickets(g.organization._id,
			q.split(" "))
	return render_template('tickets/search_tickets.html', tickets=results, q=q)

@module.route('/ticket/tags/<tag>')
@login_required
@permission_required(permissions.TICKET, permissions.READ)
def tag_view(tag):
	results = Ticket.search_by_tag(g.organization._id, tag)
	return render_template('tickets/search_tickets.html', tickets=results,
			q=tag)

@module.route('/ticket/browse')
@login_required
@permission_required(permissions.TICKET, permissions.READ)
def browse():
	tickets = Ticket.get_tickets_of_org(g.organization._id)
	return render_template('tickets/browse_tickets.html', tickets=tickets)


@module.route('/ticket/create', methods=('GET','POST'))
@login_required
@permission_required(permissions.TICKET, permissions.CREATE)
def create():
	form = TicketForm(request.form)
	# Bind the product options to the form
	form.bind_runtime_fields(g)
	return render_template('tickets/create_ticket.html', form=form)


@module.route('/ticket/delete/<id>')
@login_required
@permission_required(permissions.TICKET, permissions.DELETE)
def delete(id):
	ticket = Ticket.get_ticket(id)
	if ticket is not None:
		ticket.active = False
		ticket.save()

	return redirect(url_for('tickets.browse'))

@module.route('/ticket/save', methods=('POST',))
@login_required
def save():
	# Bind the ticket form and validate
	form = TicketForm()
	form.bind_runtime_fields(g)
	form.process(request.form)

	print form.tid.data
	
	if form.validate():
		print form.tid.data
		if form.tid.data is not u"":
			# Modified ticket, grab the original ticket and check that we can
			# modify it
			ticket = Ticket.get_ticket(form.tid.data)
			if ticket.organization in g.user.organizations\
					and resolve_permission(permissions.TICKET,
							permissions.MODIFY):
				pass
			else:
				flash(_("You do not have permission to modify tickets."))
				return redirect(url_for('dashboard.index'))
		else:
			ticket = Ticket()
			ticket.status = 0
			ticket.organization = g.organization
			# New ticket. Check permissions
			if not resolve_permission(permissions.TICKET, permissions.CREATE):
				flash(_("You do not have permission to create new tickets."))
				return redirect(url_for('dashboard.index'))

		# Populate the ticket object
		form.populate_obj(ticket)
		# Populate the comments (since it isn't populated by populate_obj)
		if len(form.new_comment.data) > 0:
			ticket.add_comment(g.user, form.new_comment.data)
		
		# Save!
		ticket.save(owner=g.user)
		# Redirect to new/saved ticket
		return redirect(url_for('tickets.view', id=ticket.id))
	else:
		if len(form.tid.raw_data) == 0 or form.tid.raw_data[0] == u'':
			return render_template('tickets/create_ticket.html', form=form)
		else:
			return render_template('tickets/ticket_view.html', form=form,
					ticket=Ticket.get_ticket(form.tid.raw_data[0]))
