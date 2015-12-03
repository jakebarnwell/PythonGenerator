import string

from pymongo.objectid import ObjectId
from flask.ext.mongoengine import Document
from wtforms import widgets, ValidationError
from flaskext.wtf import Form, HiddenField, SubmitField, TextField, \
		TextAreaField, SelectField

from flaskext.wtf import Required, Length

from semaphore.core.tickets.models import Product, Ticket, PRIORITIES, STATUSES
from semaphore.core.auth.models import User

# Inspired by bitbucket.org/maratfm/wtforms/
class QSSelectField(SelectField):
	widget = widgets.Select()
	def __init__(self, label=u'', validators=None, queryset=None,
			label_attr=u'', allow_blank=False, blank_text=u'---',
			none_value=u'__None', **kwargs):
		super(QSSelectField, self).__init__(label, validators, **kwargs)
		self.label_attr = label_attr
		self.allow_blank = allow_blank
		self.blank_text = blank_text
		self.none_value = none_value
		self.queryset = queryset or []

	def iter_choices(self):
		if self.allow_blank:
			yield(self.none_value, self.blank_text, self.data is None)

		if not self.queryset:
			return

		self.queryset.rewind()
		for q in self.queryset:
			if not self.label_attr:
				label = unicode(q)
			else:
				if hasattr(self.label_attr, '__iter__'):
					def get_complexattr(q, x):
						o = q
						for seg in x.split('.'):
							o = getattr(o, seg)
						return o

					label = " ".join([get_complexattr(q, x) for x in self.label_attr])
				else:
					label = getattr(q, self.label_attr)
			c = (q.id == self.data.id) if hasattr(self.data, 'id') else unicode(q.id) == unicode(self.data)
			yield (q.id, label, c)

	def process_formdata(self, valuelist):
		self.data = None
		if valuelist:
			print valuelist
			if (self.allow_blank and valuelist[0] == self.none_value) or not self.queryset:
				pass
			else:
				q = self.queryset.clone()
				q.filter(id=ObjectId(valuelist[0]))
				self.data = q.first()

	def process_data(self, value):
		print type(value)
		if hasattr(value, 'id'):
			self.data = unicode(value.id)
		else:
			self.data = unicode(value)

		return self.data

	def filter_id(self, id):
		return filter(lambda x: x in string.hexdigits, id)

	def pre_validate(self, form):
		q = self.queryset.clone()
		if len(self.raw_data) > 0:
			key = self.filter_id(self.raw_data[0])
			if len(key) == 24:
				if q.filter(id=ObjectId(key)).count() == 0:
					raise ValidationError('Not a valid choice')
			else:
				raise ValidationError('Invalid Object ID')
		else:
			raise ValidationError('Invalid Object ID')


class TagsField(TextField):
	"""
	A field that automatically splits items based on a delimiter
	"""

	widget = widgets.TextInput()
	
	def process_formdata(self, valuelist):
		self.data = []
		if len(valuelist) > 0:
			self.data = filter(lambda x: len(x) > 0, [x.strip() for x in
				valuelist[0].strip().split(",")])
	
	def process_data(self, value):
		self.data = u",".join(value) if value else u''

class TicketForm(Form):

	def bind_runtime_fields(self, g, ticket=None):
		self.product.queryset = Product.get_all_products(g.organization._id)
		self.owner.queryset = User.get_all_users(g.organization._id)
		if ticket is not None:
			self.tid.data = ticket.id
		else:
			self.owner.default = unicode(g.user.id)

	tid = HiddenField('id', validators=[Length(max=24)])
	title = TextField('Title')
	body = TextAreaField('Body')
	priority = SelectField('Priority', choices=[(x, PRIORITIES[x]) for x in\
		xrange(len(PRIORITIES))], coerce=int)
	product = QSSelectField('Product', label_attr='name')
	tags = TagsField('Tags', description='Comma separated (e.g., auth,crash,login)')
	owner = QSSelectField('Owner', label_attr=('name.first', 'name.last'))
	new_comment = TextAreaField('Comment')
	status = SelectField('Status', choices=[(x, STATUSES[x]) for x in
		xrange(len(STATUSES))], coerce=int, default=0)
	submit = SubmitField('Submit')

