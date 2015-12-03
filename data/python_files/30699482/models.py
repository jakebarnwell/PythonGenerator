import datetime

from hashlib import md5, sha1, sha256
from flask import current_app as app
from flaskext.mongoengine import Document
from mongoengine import EmbeddedDocument
from mongoengine import StringField, DateTimeField, EmbeddedDocumentField, \
		ReferenceField, BooleanField, EmailField, ListField
from pymongo.objectid import ObjectId

from random import choice

from semaphore.core.organizations.models import Organization
from semaphore.core.settings.models import Permissions, Settings

import config

AVAILABLE_ALGOS = {
		'SHA1': sha1,
		'SHA-2-256': sha256,
		'MD5': md5,
}


def generate_salt():
	"""
	Generates a random salt
	"""
	return unicode("".join([choice(config.SALT_CHARSET)
		for x in xrange(config.SALT_LENGTH)]))


class AuthenticationTokenOutOfDate(Exception):
	"""
	Thrown when the user's password is expired.
	"""
	pass


class AuthenticationToken(Document):
	"""
	Represents a generic way for a user to login. Should be extended
	by other actual authentication methods.
	"""

	def check(self, password, ignore_expired=False):
		"""
		Checks whether the password matches. If the password is expired and
		ignore_expired is False (default), then self will throw
		AuthenticationTokenOutOfDate.
		"""
		return False

	def change(self, oldPassword, newPassword):
		"""
		Returns True if the old password matches and the password
		was successfully changed.
		"""
		if (check(password, ignore_expired=True)):
			# Set the password using the underlying authentication
			# method's set_password.
			if (self.set_password(newPassword)):
				return True
			return False
		else:
			return False
	
	def set_password(self, newPassword):
		"""
		Sets a new password without confirming the old password. Returns
		True if it was successfully updated
		"""
		return False


class Password(AuthenticationToken):
	"""
	Represents an password authentication token.
	"""

	hashed = StringField(required=True)
	salt = StringField(required=True)
	algo = StringField(required=True)
	changed = DateTimeField(default=datetime.datetime.utcnow)

	def hash_pass(self, salt, password, algo):
		"""
		Hashs a password based on a given salt and algo.
		"""
		return unicode(AVAILABLE_ALGOS[algo](salt + password).hexdigest())

	def check(self, password, ignore_expired=False):
		# TODO: Actually check for expiration!
		return self.hash_pass(self.salt, password, self.algo) == self.hashed

	def set_password(self, newPassword):
		""" WARNING: Doesn't check the old password! """
		self.salt = generate_salt()
		self.algo = unicode(config.DEFAULT_HASH)
		self.hashed = self.hash_pass(self.salt, newPassword, self.algo)
		self.changed = datetime.datetime.utcnow()


class LoginHistory(Document):
	"""
	Stores the login history of a user.
	"""

	user = ReferenceField('User')
	successful = BooleanField(required=True)
	ipaddr = StringField(required=True)
	timestamp = DateTimeField(default=datetime.datetime.utcnow)

	@classmethod
	def create_history(cls, user, ipaddr, success):
		"""
		Creates and saves a new history object
		"""
		hist = cls()
		hist.user = user
		hist.ipaddr = unicode(ipaddr)
		hist.successful = success
		hist.save()

		return hist


class NameToken(EmbeddedDocument):
	"""
	A simple document representing a user's name
	"""
	first = StringField(required=True)
	last = StringField(required=True)

	@classmethod
	def create_name(cls, first, last):
		"""
		Creates a new name
		"""
		name = cls()
		name.first = first
		name.last = last
		return name

class User(Document):
	"""
	Represents a user in Semaphore
	"""
	username = EmailField(required=True, unique=True)
	organizations = ListField(ReferenceField(Organization))
	password = ReferenceField(AuthenticationToken)
	active = BooleanField(required=True, default=True)
	name = EmbeddedDocumentField(NameToken, required=True)
	permissions = Permissions(required=True)
	settings = Settings(required=True)

	meta = {
			'indexes': ['username'],
			'allow_inheritance': True,
	}

	def __repr__(self):
		return u'<User: %s (id: %s)>' % (self.username, self.id)

	@property
	def active_organizations(self):
		"""
		Returns a filtered list of active organizations for a user
		"""
		return filter(lambda o: o.active == True, self.organizations)

	@classmethod
	def login_user(cls, username, ipaddr, password):
		"""
		Finds a user and logs them in with the given password. Returns True
		if the user was found and logged in, False otherwise.
		"""
		user = User.get_user(username)
		if user is not None and user.handle_login(ipaddr, password):
			return user
		return None

	@classmethod 
	def get_all_users(cls, org_id):
		return cls.objects(__raw__={"organizations.$id": ObjectId(org_id),
			"active": True})
	
	@classmethod
	def get_user(cls, username):
		"""
		Returns a user (without authentication)
		"""
		return cls.objects(__raw__={'username': username, 'active':
			True}).first()
			
	@classmethod
	def get_user_id(cls, user_id):
		"""
		Returns a user (without authentication)
		"""
		return cls.objects(__raw__={'_id': ObjectId(user_id) , 'active':
			True}).first()

	def handle_login(self, ipaddr, password):
		"""
		Tries to login in the user. If the login is successful, then it
		returns True. Otherwise, it returns false. Logs the attempt in the
		database
		"""
	
		status = self.password.check(password, ignore_expired=False)
		LoginHistory.create_history(self, ipaddr, status)
		return status

