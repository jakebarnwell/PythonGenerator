import transaction

from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import create_engine, desc
from sqlalchemy import Integer, Unicode, String, SmallInteger, Boolean
from sqlalchemy import Column, DateTime, UnicodeText, ForeignKey, Float
from pyramid.traversal import resource_path
from pyramid.security import Allow, Everyone, has_permission, authenticated_userid
GROUPS = {'root': ('edit', 'view', 'super'), 'teacher': ('edit', 'view')}
from zope.sqlalchemy import ZopeTransactionExtension
from pyramid.security import Allow, Everyone


import re, os
from hashlib import sha1

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class Repository(object):
	__parent__ = __name__ = None
	__acl__ = [(Allow, Everyone, 'view'),
			   (Allow, 'group:teachers', 'edit'),
			   (Allow, 'admin', 'super')]
			
			
	def __getitem__(self, key):
		session = DBSession()
		try:
			id = int(key)
		except (ValueError, TypeError):
			item = session.query(Owner).get(key)
		else: 
			item = session.query(Question).get(id)
		if not item: raise KeyError(key)
		#item.__parent__ = self
		#item.__name__ = key
		return item
					
	@property
	def questions(self):
		session = DBSession()
		return	session.query(Question).all()
			
	@property
	def users(self):
		session = DBSession()
		return session.query(Owner).all()
		
	#def newQuestionName(self):
	#	return `len(self.questions)` Not needed
				
	def addUser(self,userid,fullname,password):
		session = DBSession()
		#if session.query(Owner).filter_by(name=userid).count() >0:
		#	raise RuntimeError, "Exisiting user '%s'" % userid
		user = Owner(userid,fullname,password)
		session.add(user)
		#self.__name__ = userid
		#user.__parent__ = self
		return user
		
	def deleteUser(self,userid):
		assert userid != 'admin', "Cannot delete root user"
		session = DBSession()
		user = session.query(Owner).get(userid)
		session.delete(user)
		
		
	def addQuestion(self,content):
		session = DBSession()
		question = Question(content)
		#question.__name__ = `question.id`
		#question.__parent__ = self
		session.add(question)
		session.flush()
		return question
		
	def delQuestion(self,id):
		session = DBSession()
		qtn = session.query(Question).get(id)
		if qtn.issues:
			ei = qtn.issues[0].issue
			raise RuntimeError, "Question used in " + resource_path(ei)
		session.delete(qtn)
		
class Owner(Base):
	__tablename__ = 'users'
	name = Column(String(25),primary_key=True)
	fullname = Column(Unicode(255))
	_password = Column(String(50),nullable=False)
	exams = relationship("Exam", backref="owner")

	def __init__(self,userid,fullname,password):
		self.name = userid
		self._set_password(password)
		self.fullname = fullname
		
	@property
	def __name__(self):
		return self.name
		
	@property
	def __parent__(self):
		return root
		
		
	def _set_password(self, password):
		salt = sha1()
		salt.update(os.urandom(60))
		hash = sha1()
		hash.update(password + salt.hexdigest())
		self._password = salt.hexdigest() + hash.hexdigest()
	
	def _get_password(self):
		return self._password		
		
	password = property(_get_password, _set_password)
	
	def validate_password(self, password):
		hashed_pass = sha1()
		hashed_pass.update(password + self.password[:40])
		return self.password[40:] == hashed_pass.hexdigest()
		
	#@property
	#def permissions(self):
	#	perms = set()
	#	for g in self.groups:
	#		perms |= set(GROUPS[g])
	#	return perms
			
			
	@property
	def groups(self):
		return ['teachers']

		
	def __getitem__(self,id):
		session = DBSession()
		exam = session.query(Exam).get(id)
		if not exam: raise KeyError(id)
		assert exam in self.exams
		return exam
			
		
	def newExam(self):
		session = DBSession()
		exam = Exam(self.name)
		session.add(exam)
		self.exams.append(exam)
		#exam.__parent__ = self
		#exam.__name__ = `exam.id`
		return exam
		
			
class Exam(Base):
	__tablename__ = 'exams'
	id = Column(Integer, primary_key=True)
	userid = Column(Integer, ForeignKey('users.name'))
	title = Column(String(50))
	subtitle = Column(String(50))
	guard = Column(SmallInteger)
	issues = relationship("ExamIssue", backref="exam")
	
	def __init__(self,ownerid):
		self.title = self.subtitle = ''
		self.userid = ownerid
		self.guard = 7
		
	def __getitem__(self,id):
		session = DBSession()
		item = session.query(ExamIssue).get(id)
		if not item: raise KeyError(id)
		assert item in self.issues
		return item
			
			
	@property
	def __parent__(self):
		session = DBSession()
		return session.query(Owner).get(self.userid)

	@property
	def __name__(self):
		return `self.id`
	
		
	def can_edit(self,request):
		userid = authenticated_userid(request)
		if self.userid == userid or has_permission('super',self,request):
			return userid

	def rmIssue(self,id):
		session = DBSession()
		issue = session.query(ExamIssue).get(id)
		assert issue in self.issues
		issue.delete()
		
	def newIssue(self,onDate=10,lapse=30):
		import datetime
		session = DBSession()
		ei = ExamIssue(self)
		now = datetime.datetime.now()
		start = now + datetime.timedelta(onDate)
		end = start + datetime.timedelta(lapse)
		ei.set_active(start,end)
		session.add(ei)
		self.issues.append(ei)
		return ei
		
class ExamIssue(Base):
	__tablename__ = 'exam_issues'
	id = Column(Integer, primary_key=True)
	exam_id = Column(Integer, ForeignKey('exams.id'))
	start = Column(DateTime)
	end = Column(DateTime)
	questions = relationship("QuestionIssue", backref='issue')
	archived = Column(Boolean)
	editable = Column(Boolean)
	results = relationship("Result", backref='issue')
	xml = Column(UnicodeText)
	knst_bound = 9
	
	def set_active(self,start,end):
		self.start = start
		self.end = end
		
	@property
	def __parent__(self):
		exam = DBSession().query(Exam).get(self.exam_id)
		assert self in exam.issues
		return exam
		
	@property
	def __name__(self):
		return `self.id`
		
		
	def __getitem__(self,id):
		"""Contains questions with its proper id"""
		session = DBSession()
		qi = session.query(QuestionIssue).get((id,self.id))
		if not qi: raise KeyError(id)
		assert qi in self.questions
		return qi.question

	
	@property
	def guard(self):
		return self.exam.guard
		
	def __init__(self,exam):
		from datetime import datetime
		self.editable = True
		self.set_active(datetime.max,datetime.min) # Never 
		self.archived = False
		
	def delete(self):
		session = DBSession()
		for qi in self.questions:
			session.delete(qi)
		session.delete(self)
		
	def can_edit(self,request):
		userid = authenticated_userid(request)
		if self.owner == userid or has_permission('super',self,request):
			return userid
			
	def add_student(self,pid,name):
		session = DBSession()
		st = session.query(Student).get(pid)
		if not st: # Not in 'students' table. Add it
			st = Student(pid,name)
		result = Result(self,pid)
		session.add(result)
		
	def isEnroled(self,pid):
		"""Is this student enroled in this exam issue?"""
		session = DBSession()
		return bool(session.query(Result).get((self.id,pid)))

	def add_result(self,studentId,grade,info,force=False):
		"""
		'force' disregard previous updates
		"""
		import logging
		session = DBSession()
		result = session.query(Result).get((self.id,studentId))
		log_prefix = resource_path(self) + ': '
		if not result:
			logging.warning(log_prefix + "not enroled '%s'.", resource_path(self),studentId)
			return
		if result.when and not force:
			logging.warning(log_prefix + "'%s' already submitted.", resource_path(self),studentId)
			return
		result.update(grade,info)
		return result
		
	@property
	def owner(self):
		return self.exam.userid
	
	@property
	def active(self):
		import datetime, logging
		logging.debug("Active from %s to %s",`self.start`,`self.end`)
		return self.start < datetime.datetime.now() < self.end
					
	def activate_now(self):
		from datetime import datetime
		now = datetime.now()
		assert now < self.end, "Cannot activate: past due."
		self.set_active(now,self.end)
			
	def deactivate_now(self):
		from datetime import datetime
		now = datetime.now()
		assert now > self.start, "Cannot deactivate: before scheduled time."
		self.set_active(self.start,now)
		
	def active_instant(self):
		import datetime
		now = datetime.datetime.now()
		if now <= self.start:
			return -1
		elif now >= self.end:
			return 1
		else:
			return 0
						
	def topdf_plain(self,settings):
		from knst.knstdoc import makePlain
		from knst.utils import xml2pdf
		self.normalize(settings)
		return xml2pdf(settings,self.xml,makePlain)
		
	def topdf_scramble(self,settings,copies):
		from knst.knstdoc import makeScrambled
		from knst.utils import xml2pdf
		self.normalize(settings)
		xml_data = self.scramble(settings,copies)
		return xml2pdf(settings, xml_data, makeScrambled)
		
	def topdf_mark(self,settings,studentId):
		from knst.utils import xml2pdf
		from knst.knstdoc import makePlain
		session = DBSession()
		result = session.query(Result).get((self.id,studentId))
		if not result: return None
		version, tallies = result.info
		xml_data = self.mark(settings,version,tallies)
		return xml2pdf(settings, unicode(xml_data,'utf8'), makePlain)
		
	def normalize(self,settings):
		import tempfile, knst.utils
		#from os import unlink
		import hashlib
		sKey = self.secret(settings)
		seed = hashlib.sha224(sKey).hexdigest()
		bound = 10**self.knst_bound/self.guard
		normParams = (bound,seed)
		f = tempfile.NamedTemporaryFile(suffix='.xml') # delete=False)
		self.xml = ''
		w = knst.utils.Writer(f)
		self.toxml(w)
		w.stream.flush()
		data = knst.utils.knst_normalize(settings,f.name,normParams)
		##assert False
		self.xml = unicode(data,'utf8')
		self._p_changed = 1
		w.close()
		
	def scramble(self,settings,copies):
		import tempfile, knst.utils
		from knst.knstdoc import makeScrambled
		f = tempfile.NamedTemporaryFile(suffix='.xml')
		f.write(self.xml.encode('utf8'))
		f.flush()
		xml_data = knst.utils.knst_scramble(settings,
			f.name,copies,guard=self.guard)
		f.close()
		return unicode(xml_data,'utf8')
		
	def reMarkAll(self,settings):
		"""
		For all results, remark them using the xml field
		"""
		import logging
		log_prefix = resource_path(self) + ': '
		results,_,_ = self.listResults()
		for r in results:
			version,tallies = r.info
			mark = self.grade(settings,r.student_id,version,tallies,force=True)
			print r.grade, "->", mark
			r.grade = mark
		logging.info(log_prefix + "%d results remarked" % results.count())
		
		
	def mark(self,settings,version,tallies):
		import knst.utils, tempfile
		assert self.xml, "Must be normalized at this stage."
		f = tempfile.NamedTemporaryFile(suffix='.xml')
		f.write(self.xml.encode('utf8'))
		f.flush()
		xml_data = knst.utils.knst_mark(settings,
			f.name,version,tallies)
		f.close()
		return xml_data
		
	def grade(self,settings,studentId,version,tallies,force=False):
		from knst.knstdoc import parseString
		import logging
		xml_data = unicode(self.mark(settings,version,tallies),'utf8')
		mark = 0.0
		marked = {}
		for n,page in enumerate(parseString(xml_data).pages):
			for q in page.questions:
				ans = q.marked()
				if ans:
					mark += ans.value
					marked[n] = ans.id
		
		if not self.add_result(studentId,mark, (version,tallies),force):
			raise ValueError, "Already submmitted or unknow student."
		logging.info("%s: Submitting for '%s' grade %5.3f. Data: %d:%s answers: %s",
						resource_path(self), studentId, mark,
						version,`tallies`, `marked`)
		return mark	 
		
	def isIn(self,qtn):
		return qtn.__name__ in self.questions
		
	@property
	def pages(self):
		from knst.knstdoc import parseString
		if not self.xml:
			raise RuntimeError, "Normalize first"
		return len(parseString(self.xml).pages)
		
						
	def add(self,qtn):
		"""Add a question/issue"""
		if qtn.id not in [qi.question_id for qi in self.questions]:
			qi = QuestionIssue(qtn,self)
			self.questions.append(qi)
		
	def remove(self,id):
		"Remove a question"
		session = DBSession()
		qi = session.query(QuestionIssue).get((id,self.id))
		assert qi in self.questions
		session.delete(qi)

	#def url(self):
	#	return self.__parent__.__name__ + '/' + self.__name__
	
	def listResults(self):
		"List the results of this issue"
		query = self.gradedResults()
		count = query.count()
		if count==0:
			return
		last = query.order_by(desc(Result.when))[0].when
		percent = 100*float(count)/len(self.results)
		results = query.order_by(Result.student)
		return (results,percent,last)
		
	def gradedResults(self):
		session = DBSession()
		return session.query(Result).filter(Result.when!=None).filter_by(issue_id=self.id)
		
	def change_values(self,newvalues):
		import knstdoc, utils, StringIO
		w = utils.Writer(StringIO.StringIO())
		doc = knstdoc.parseString(self.xml)
		for pg in doc.pages:
			for qt in pg.questions:
				for an in qt.answers:
					label = int(an.label)
					new = newvalues.get(label,None)
					an.setValue(new)
		doc.toxml(w)
		xml_data = w().getvalue()
		self.xml = unicode(xml_data,'utf8')
		#print self.xml
					
		
		
	def from_xml(self):
		import knstdoc
		doc = knstdoc.parseString(self.xml)
		assert doc.is_normal(), "Stored XML for knst is not normal"
		questions = []
		for pg in doc.pages:
			for qt in pg.questions:
				answers = []
				for an in qt.answers:
					answers.append(dict(text=an.content,value=an.value,label=an.label))
				questions.append(dict(text=qt.content,
					 				  answers=answers))
		return questions
		
		
	def toxml(self,writer):
		#writer.emit('<?xml version="1.0" encoding="UTF-8"?>\n')
		writer.openTag(u'kns')
		writer.openTag(u'title')
		writer.text(self.__parent__.title)
		writer.closeTag(u'title')
		if self.__parent__.subtitle:
			writer.openTag(u'subtitle')
			writer.text(self.__parent__.subtitle)
			writer.closeTag(u'subtitle')
		nQtn = len(self.questions)
		for q in self.questions:
			q.question.toxml(writer,nQtn)
		writer.closeTag(u'kns')
		return writer
		
	def secret(self,settings):
		return settings['secret'] + resource_path(self)
		
	def check(self,settings,issue,tally,control):
		#return silly_check(tally,control)
		return hash_check(self.secret(settings),issue,tally,control)
		
	def generate_control(self,settings):
		return lambda i,t,sec=self.secret(settings): get_control(sec,i,t)

# Security
		
def get_control(secret,issue,tally):
		import hashlib
		m = hashlib.md5(secret)
		m.update(`tally%100` + `issue%10`)
		return int(m.hexdigest(),16)%1000
		
def hash_check(secret,issue,tally,control):
		ctrl = get_control(secret,issue,tally)
		return (control-ctrl)%1000 == 0
		
def silly_check(tally,control):
		"""Use only for debugging"""
		return (tally + control)%10 == 9
		

class QuestionIssue(Base):
	__tablename__ = 'question_issues'
	question_id = Column(Integer,ForeignKey('questions.id'),primary_key=True)		
	issue_id = Column(Integer,ForeignKey('exam_issues.id'),primary_key=True)
	
	def __init__(self,question,issue):
		self.question_id = question.id
		self.issue_id = issue.id



class Question(Base):
	__tablename__ = 'questions'
	id = Column(Integer,primary_key=True)
	content = Column(UnicodeText)
	issues = relationship("QuestionIssue", backref="question")
	answers = relationship("Answer", backref="question")
	
	def __init__(self,content):
		self.content = content
		
	@property
	def __name__(self):
		return `self.id`
		
	@property
	def __parent__(self):
		return root
		
	def __getitem__(self,id):
		session = DBSession()
		item = session.query(Answer).get(id)
		if not item: raise KeyError
		assert item in self.answers
		return item

	def addAnswer(self,content):
		ans = Answer(content)
		session = DBSession()
		session.add(ans)
		self.answers.append(ans)
		ans.__parent__ = self
		ans.__name__ = `ans.id`
		return ans
		
	def remove(self,id):
		session = DBSession()
		item = session.query(Answer).get(id)
		assert item in self.answers
		session.delete(item)
		
	def isValid(self):
		r = len([a for a in self.answers if a.right])
		if r>1:
			raise ValueError, "More than one right answer"
		return r==1 and len(self.answers)>1
		
	def toxml(self,writer,nQtn):
		writer.openTag('qtn')
		writer.text(self.content)
		nAns = len(self.answers)
		rMark = 10.0/nQtn
		wMark = rMark/(1.-nAns)
		for a in self.answers:
			a.toxml(writer, (rMark,wMark))
		writer.closeTag('qtn')
			
			
			
class Answer(Base):
	__tablename__ = 'answers'
	id = Column(Integer,primary_key=True)
	q = Column(Integer, ForeignKey('questions.id'))
	content = Column(UnicodeText)
	right = Column(Boolean,default=False)
	fixed = Column(Boolean,default=False)
	
	def __init__(self,content):
		self.content = content
		
	def toxml(self,writer,vals):
		value = self.right and vals[0] or vals[1]
		fixed = self.fixed and ' fixed="1"' or ''
		atts = {'value': '%f'%value}
		if fixed: atts['fixed'] = '1'
		writer.openTag('ans',**atts)
		writer.text(self.content)
		writer.closeTag('ans')
		
class Student(Base):
	__tablename__ = 'students'
	pid = Column(String(25),primary_key=True)
	name = Column(Unicode(60))
	results = relationship("Result", backref="student")
	
	def __init__(self,pid,name):
		self.pid = pid
		self.name = name
	
	
class Result(Base):
	"""Student grades.
	   Must be inserted prior activation to authenticate students for marking.
	   On marking update the record."""
	__tablename__ = 'results'
	issue_id = Column(Integer,ForeignKey('exam_issues.id'),primary_key=True)
	student_id = Column(String(25),ForeignKey('students.pid'),primary_key=True)
	knst_info = Column(String)
	grade = Column(Float)
	when = Column(DateTime)
	
	def __init__(self,issue,student_pid):
		self.issue_id = issue.id
		self.student_id = student_pid

	def update(self,grade,info):
		import datetime
		self.when = datetime.datetime.now()
		self.grade = grade
		self.knst_info = repr(info)
		
	@property
	def info(self):
		info =  eval(self.knst_info)
		assert len(info)==2
		return info
		

root = Repository()

def default_get_root(request):
	return root

def populate():
	session = DBSession()
	admin = Owner(userid='admin',fullname='Foo Bar',password='root')
	session.add(admin)
	session.flush()
	transaction.commit()

def initialize_sql(engine):
	DBSession.configure(bind=engine)
	Base.metadata.bind = engine
	Base.metadata.create_all(engine)
	try:
		populate()
	except IntegrityError:
		DBSession.rollback()

def appmaker(engine):
	initialize_sql(engine)
	return default_get_root


