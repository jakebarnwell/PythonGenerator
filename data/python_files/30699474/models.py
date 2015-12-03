import datetime
from flask import current_app as app
from flaskext.mongoengine import Document

from pymongo.objectid import ObjectId
from mongoengine import EmbeddedDocument
from mongoengine import StringField, ReferenceField, BooleanField,\
		DateTimeField, EmbeddedDocumentField, FileField, ListField,\
		DictField, IntField, signals
from mongoengine.base import BaseList

from semaphore.core.auth.models import User
from semaphore.core.organizations.models import Organization
import config

STATUSES = ["New", "Opened", "Assigned", "Reopened", "Closed", "Pending",\
		"WONT FIX"]
PRIORITIES = ["Undetermined", "Trivial", "Minor", "Major", "Critical",\
		"Blocker"]

class Product(Document):
	"""
	Represents a product/project in Semaphore
	"""
	name = StringField(required=True)
	organization = ReferenceField(Organization, required=True)
	active = BooleanField(required=True)

	def __repr__(self):
		return '<Product:' + str([str(x) + ':' + str(getattr(self,x)) for x in
				self._fields]) + '>'
	
	def __str__(self):
		return self.__repr__()
	
	@classmethod
	def get_product(cls, product_id):
		"""
		Returns a product with a given ID that's active.
		"""
		return cls.objects(__raw__={'_id': ObjectId(product_id), 'active':
			True}).first()

	@classmethod
	def get_all_products(cls, org_id):
		return cls.objects(__raw__={'organization.$id':ObjectId(org_id), 'active': True})


class Comment(EmbeddedDocument):
	"""
	A comment on a ticket from a user
	"""

	def __hash__(self):
		return self.owner.__hash__() * (31 * self.body.__hash__()) * (31 *
				self.timestamp.__hash__())

	def __eq__(self, other):
		return self.__hash__() == other.__hash__()

	owner = ReferenceField(User, required=True)
	timestamp = DateTimeField(required=True, default=datetime.datetime.utcnow)
	body = StringField(required=True)
	active = BooleanField(required=True, default=True)

	def __repr__(self):
		return '<Comment:' + str([str(x) + ':' + str(getattr(self,x)) for x in
				self._fields]) + '>'

	def __str__(self):
		return self.__repr__()


class Changeset(EmbeddedDocument):
	"""
	A set of changes on a ticket
	"""
	owner = ReferenceField(User, required=True)
	timestamp = DateTimeField(required=True, default=datetime.datetime.utcnow)
	types = ListField(StringField())
	involves = ListField(ReferenceField(User))
	fields = DictField()

	def __repr__(self):
		return '<Changeset:' + str([str(x) + ':' + str(getattr(self,x)) for x in
				self._fields]) + '>'
	
	def __str__(self):
		return self.__repr__()

class Attachment(EmbeddedDocument):
	"""
	An attachment (file) on a ticket
	"""
	
	def __hash__(self):
		return self.owner.__hash__() * (31 * self.title.__hash__())
	
	owner = ReferenceField(User, required=True)
	files = ListField(FileField())
	title = StringField()


class Ticket(Document):
	"""
	Represents a ticket in Semaphore
	"""
	organization = ReferenceField(Organization, required=True)
	active = BooleanField(required=True, default=True)
	owner = ReferenceField(User, required=True)
	title = StringField(required=True)
	title_keywords = ListField(StringField())
	body = StringField()
	priority = IntField()
	status = IntField()
	tags = ListField(StringField())
	product = ReferenceField(Product, required=True)
	dynamic_fields = DictField()

	last_modified = DateTimeField(required=True,
			default=datetime.datetime.utcnow)

	comments = ListField(EmbeddedDocumentField(Comment))
	attachments = ListField(EmbeddedDocumentField(Attachment))
	changesets = ListField(EmbeddedDocumentField(Changeset))
	watchers = ListField(User)

	UNDIFFABLE_FIELDS = [changesets, title_keywords]

	@classmethod
	def handle_migrations(cls, sender, document, **kwargs):
		"""
		Handles running any migration hooks.
		"""
		#if document.id:
			#if (len(document.title_keywords) == 0 and len(document.title) > 0):
				#print "Migrating ticket %s" % document.id
				#document.title_keywords.extend(document.title.lower().split())
				#document.save()
			#elif len(document.title_keywords) > 0:
				#document.title_keywords = [x.lower() for x in
						#document.title_keywords]
				#document.save()
		pass

	def __repr__(self):
		return '<Ticket:' + str([str(x) + ':' + str(getattr(self,x)) for x in
				self._fields]) + '>'
	
	def __str__(self):
		return self.__repr__()

	@classmethod
	def pre_save(cls, sender, document, **kwargs):
		"""
		Handles creating a changeset and updating title_keywords
		"""
		document.title_keywords = document.title.lower().split(" ")

		# Build a new changeset
		if len(document._delta()) > 0 and document.save_owner:
			changeset = Changeset(owner=document.save_owner)
			fields = document._delta()[0]
		
			# Get the old ticket so we can diff collections
			old_ticket = Ticket.get_ticket(document.id)

			for field in fields.keys():
				if field not in document._fields or field in document.UNDIFFABLE_FIELDS:
					pass
				elif isinstance(getattr(document, field), (BaseList,)):
					# TODO: Diff the collection
					if old_ticket is None:
						changeset.fields[field] = (getattr(document, field), [])
					else:
						added = set(getattr(document,
							field)) - (set(getattr(old_ticket, field)))
						removed = set(getattr(old_ticket, field)) -\
								set(getattr(document, field))
						if len(added) > 0 or len(removed) > 0:
							changeset.fields[field] = (list(added), list(removed))
							changeset.types.append(field)
				else:
					# Just add the field
					if old_ticket is None:
						changeset.fields[field] = (getattr(document, field),
								None)
					else:
						v = getattr(old_ticket, field)
						nv = getattr(document, field)
						if v != nv:
							changeset.fields[field] = (getattr(document, field),
									getattr(old_ticket, field))
							changeset.types.append(field)

			if old_ticket is None:
				changeset.types = ['new',]

			changeset.involves = list(set(document.watchers +
				[document.save_owner, document.owner]))

			if len(changeset.types) > 0:
				document.changesets.append(changeset)
				# Update last modified 
				document.last_modified = datetime.datetime.utcnow()


	@classmethod
	def get_ticket(cls, ticket_id):
		"""
		Finds a ticket in the database.
		"""
		return cls.objects(__raw__={"_id": ObjectId(ticket_id), "active":
			True}).first()

	@classmethod
	def get_tickets_of_org(cls, org_id):
		"""
		Gets all active tickets of an organization ; filter by user if specified
		"""
		return cls.objects(__raw__={"organization.$id": ObjectId(org_id),
			"active": True}).order_by('-last_modified')
	
	@classmethod
	def get_tickets_involving(cls, org_id , user):
		"""
		Gets all active tickets an user is involved in 
		"""
		return cls.objects(__raw__ ={"organization.$id": ObjectId(org_id), 
			"changesets.involves.$id": user.id,
			"active": True}).order_by('-last_modified')
	
	@classmethod
	def search_tickets(cls, org_id, terms):
		"""
		Searches for a ticket that has some of the terms
		"""
		results = set()
		for term in terms:
			results.update(set(cls.objects(__raw__={"organization.$id":
				ObjectId(org_id), "active": True, "tags":
				term.lower()})));
			results.update(set(cls.objects(__raw__={"organization.$id":
				ObjectId(org_id), "active": True, "title_keywords":
				term.lower()})));
		return results;

	@classmethod
	def search_by_tag(cls, org_id, tag):
		return cls.objects(__raw__={'organization.$id': ObjectId(org_id),
			'tags': tag, 'active': True})

	def add_comment(self, owner, body):
		"""
		Adds a comment to the ticket
		"""
		comment = Comment(owner=owner, body=body)
		self.comments.append(comment)

	## HACK HACK HACK HACK HACK
	## God murders kittens every time this function is called
	def save(self, *args, **kwargs):
		self.save_owner = kwargs['owner'] if 'owner' in kwargs else None
		if 'owner' in kwargs: del kwargs['owner']
		r = super(Ticket, self).save(*args, **kwargs)
		self.kwargs = {}
		return r

signals.pre_save.connect(Ticket.pre_save, sender=Ticket)
signals.post_init.connect(Ticket.handle_migrations, sender=Ticket)
