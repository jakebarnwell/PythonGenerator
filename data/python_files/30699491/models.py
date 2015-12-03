import datetime
from flask import current_app as app
from flaskext.mongoengine import Document
from mongoengine import StringField, EmbeddedDocumentField, DictField,\
		BooleanField
from pymongo.objectid import ObjectId

from semaphore.core.settings.models import Settings, Permissions

import config


class Organization(Document):
	"""
	Represents an organization in Semaphore
	"""

	name = StringField(required=True)
	settings = Settings(required=True)
	permissions = Permissions(required=True)
	active = BooleanField()

	def __repr__(self):
		return u'<Organization: %s (id: %s)>' % (self.name, self.id)

	def __str__(self):
		return self.__repr__()

	@classmethod
	def get_organization(cls, id):
		"""
		Returns an organization by ID
		"""
		return cls.objects(__raw__={'_id': ObjectId(id), 'active': True}).first()

MODELS = [Organization]
			
