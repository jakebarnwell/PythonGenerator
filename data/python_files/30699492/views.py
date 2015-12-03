import datetime
from pymongo.objectid import ObjectId
from flask import Module, render_template, url_for, request, session, redirect
from flask import flash, current_app as app, abort, g

from semaphore.core.auth.decorators import login_required
from semaphore.core.auth.models import Organization, User

from semaphore.core.settings import permission_required, PERMISSION_ORGANIZATION
from semaphore.core.settings import PERMISSION_READ, PERMISSION_MODIFY, \
		PERMISSION_CREATE

from . import module
from .forms import CreateOrganizationForm, EditOrganizationForm


@module.route('/organization/create', methods=('GET','POST'))
@login_required
@permission_required(PERMISSION_ORGANIZATION, PERMISSION_CREATE)
def create():
	form = CreateOrganizationForm(request.form)
	if request.method == 'POST' and form.validate_on_submit():
		organization = Organization()
		organization.name = form.name.data
		organization.active = True

		organization.save()	
		print organization

		return redirect(url_for('auth.change_organization', id=organization.id))
	else:
		return render_template('organizations/create_organization.html', form=form)

@module.route('/organization/edit', methods=('GET','POST'))
@login_required
@permission_required(PERMISSION_ORGANIZATION, PERMISSION_MODIFY)
def edit():
	form = EditOrganizationForm(request.form)
	if request.method == 'POST' and form.validate_on_submit():
		organization = get_organization(Object(g.organization))
		organization.name = form.name.data
		organization.active = form.active.data
		organization.save()
		
		if organization.active is False:
			return render_template('organization/must_change_to_active_organization.html')
		else:
			return redirect(url_for('dashboard.index'))
	
	else:
		return render_template('organizations/edit_organization.html', form=form)
