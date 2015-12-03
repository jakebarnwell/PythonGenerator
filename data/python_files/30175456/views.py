import datetime, time
from flashburrito.flashapp.models import Game, Vote, Comment, Hits, \
      UserProfile, Feedback, Tag, TagVote, GameTag
from Setup import tag5min
from django.forms.util import ErrorList
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, logout, login
from forms import SubmitGame, SubmitGameNoCaptcha, LoginUser, \
      RegisterUser, PostComment, ChangePassword, UserDescription, \
      UserFeedback
from django.http import Http404
from django.db.models import Q
from captcha import makeCaptchaImage
from paging import paging
import flashburrito.settings, sha
from flashburrito.settings import minNumVotes, minNumHits
from django.core.exceptions import ObjectDoesNotExist
from urllib import quote_plus
from django.core.mail import send_mail


def initialVars(request):
   WEB_FILES = flashburrito.settings.WEB_FILES
   LIVE_SITE = flashburrito.settings.LIVE_SITE
   totalNumberOfGames = Game.objects.count()

   sendBackUrl = request.META.get("PATH_INFO", "/")
   qString = request.META.get("QUERY_STRING", "")
   if qString:
      sendBackUrl = sendBackUrl + qString

   #sendBackUrl = quote_plus(sendBackUrl)

   startOffset = 0
   user = getUserInfo(request)
   userId = getUserId(user)
   message = request.session.get('message', None)
   request.session['message'] = None

   # topHits is a big performance Hit!!
   topHits = getTopHits()
   # topRated is pretty big too, but aprox 10% of topHits
   topRated = getTopRated()

   return WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, \
         startOffset, user, userId, message, topHits, topRated

class GameInfo:
   def __init__(self, game, userId, userPageId):
      self.id = game.id
      self.name = game.name
      self.url = game.url
      self.urlEncode = game.urlEncode()
      self.rating = "%1.1f" % game.rating
      self.usersVote = game.usersVote(userId)
      self.usersPageVote = game.usersPageVote(userPageId)
      self.numVotes = game.numVotes
      self.numHits = game.numHits
      self.numHitsUser = game.numHitsUser(userPageId)
      self.numComments = game.numComments()
      self.whenSubmitted = game.whenSubmitted
      self.whoSubmitted = game.whoSubmitted
      self.description = game.description
      self.descriptionLeader = game.descriptionLeader()
      self.nameLeader = game.nameLeader()
      self.timeSinceSubmitted = game.timeSinceSubmitted()

      try:
         tagVote = TagVote.objects.get(tag__exact=tag5min, game__exact=game, user__exact=userId)
         self.yea5min = tagVote.yea
         self.nay5min = not tagVote.yea
      except ObjectDoesNotExist:
         self.yea5min = False
         self.nay5min = False

      self.tags = []
      try:
         gameTag = GameTag.objects.get(tag__exact=tag5min, game__exact=game)
         self.yea5minVotes = gameTag.votesYea
         self.nay5minVotes = gameTag.votesNay

         # TODO: HACK!
         if self.yea5minVotes > 0 and self.yea5minVotes >= self.nay5minVotes:
            self.tags.append({ 'name': '5min', 'url': '/5min' })
      except ObjectDoesNotExist:
         self.yea5minVotes = 0
         self.nay5minVotes = 0


def gamesOnPage(userId, start, end):
   return [ GameInfo(g, userId, None)
         for g in Game.objects.order_by("-whenSubmitted","name")[start-1:end]
   ]


def index(request):
   return viewGames(request, 1, 20)


def redirectHome(request):
   return HttpResponseRedirect('/')


def getUserId(user):
   if user:
      userId = user.id
   else:
      userId = None
   return userId


def getTopHits(minHits=minNumHits, numGames=5):
   return Game.objects.order_by('-numHits').filter(numHits__gte=minHits)[0:numGames]


def getTopRated(minVotes=minNumVotes, numGames=5): #TODO make minVotes global var settings
   return \
   Game.objects.order_by('-rating').filter(numVotes__gte=minVotes)[0:numGames]


def allTopRated(request, minVotes=minNumVotes): #TODO make minVotes global var settings
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   title = "Top 100 Games by Rating"
   titleTagCopy = "Top 100 Games by Rating"

   # TODO how many numGames do we want?
   games = [ GameInfo(g, userId, None)
         for g in getTopRated(minVotes=minVotes, numGames=100) 
   ]


   return render_to_response('allTopGames.html', locals())
   

def allTopHits(request, minHits=minNumHits): #TODO make minVotes global var settings
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   title = "Top 100 Games by Hits"
   titleTagCopy = "Top 100 Games by Hits"

   # TODO how many numGames do we want?
   games = [ GameInfo(g, userId, None)
         for g in getTopHits(minHits=minNumHits, numGames=100)
   ]

   return render_to_response('allTopGames.html', locals())


def ratingCompare(x, y):
   ratingCompare = y.rating - x.rating

   if ratingCompare > 0:
      return 1
   elif ratingCompare < 0:
      return -1
   elif ratingCompare == 0:
      if y.whenSubmitted > x.whenSubmitted:
         return 1
      elif y.whenSubmitted < x.whenSubmitted:
         return -1
      else:
         return 0

def viewGames(request, start, end):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   start = int(start)
   if (start < 1):
      start = 1
   end = int(end)
   startOffset = start -1

   games = gamesOnPage(userId, start, end)


   # this tests whether you're on first page or not. When submitting game
   # this is needed to redirect to correct page
   if start == 1:
      sendBackUrl = "/"
   else:
      sendBackUrl = "/games/" + str(start) + "-" + str(end) 

   #log(request, 'VIEWGAMES', "Just Landed", sendBackUrl)

   prevUrl, nextUrl, firstUrl, lastUrl = paging(
      start=start,
      end=end,
      totalNumberOfGames=totalNumberOfGames
   )

   return render_to_response('index.html', locals())

def getUserInfo(request):
   userId = request.session.get('_auth_user_id', None)
   if userId:
      user = User.objects.get(id=userId)
   else:
      user = None
   return user

def submitGame(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   sendBackUrl ="/submit/"

   if request.method == "GET":
      captchaImageURL, captchaHash, submitgameform = \
         captchaVarsForSubmit(request)

      return render_to_response('submitgame.html', locals())
   elif request.method == "POST":
      # TODO ideally do SubmitGame or SubmitGameNoCatcha, depending
      # on what was actually on the page
      submitgameform = SubmitGame(request.POST)

      if submitgameform.is_valid():
         gamename = submitgameform.cleaned_data['name']
         gameurl = submitgameform.cleaned_data['url']
         gamedescription = submitgameform.cleaned_data['description']

         if user is None:
            #User is logged in, need to check captcha
            captchaHash = submitgameform.cleaned_data['captchaHash']
            captchaEntry = submitgameform.cleaned_data['captchaEntry']
            captchaEntry  = captchaEntry.lower()

            SALT = flashburrito.settings.SECRET_KEY[:20]
            hashEntry = sha.new(SALT+captchaEntry).hexdigest()

            if captchaHash == hashEntry:
               gameId = addNewGame(gamename, gameurl, gamedescription, userId)
               
               #log(request, 'SUBMITGAME', gamename, gameurl)

               request.session['message'] = \
                  "Thank you for submitting a game."
               return HttpResponseRedirect(gamePageUrl(gameId))
            else:
               request.session['message'] = "Invalid Captcha Code."
               return HttpResponseRedirect(sendBackUrl)

         gameId = addNewGame(gamename, gameurl, gamedescription, userId)

         #log(request, 'SUBMITGAME', gamename, gameurl)

         #Set Thank you Message
         request.session['message'] = "Thank you for submitting a game."
         return HttpResponseRedirect(gamePageUrl(gameId))
      else:
         #form is not valid
         submitgameformerrors = submitgameform.errors

         if 'name' in submitgameform.errors:
            submitgameform.errors['name'] = ErrorList(["Type a name, dangit!\
              It must be unique."])
         if 'url' in submitgameform.errors:
            submitgameform.errors['url'] = ErrorList(["What's the URL, man?\
            It must start with http://"])

         captchaImageURL, captchaHash, submitgameform = \
            captchaVarsForSubmit(request)
            
         # Why does the next line have a DEBUG? It's mission critical, I think.
         #return HttpResponseRedirect(sendBackUrl) #DEBUG
         return render_to_response('submitgame.html', locals()) #DEBUG


def addNewGame(gamename, gameurl, gamedescription, userId):
      whenSubmitted=datetime.datetime.utcnow()

      # TODO refactor these lines of code with getUserInfo
      if userId:
         user = User.objects.get(id=userId)
      else:
         user = None


      game = Game(
         name=gamename, 
         url=gameurl, 
         rating=0, 
         numHits=0,
         numVotes=0,
         whenSubmitted=whenSubmitted,
         whoSubmitted=user,
         description=gamedescription
      )

      game.save()

      return game.id

def register(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   #Need this in the event that they don't process the form and nav to login
   sendBackUrl = '/'

   if request.method == 'GET':
      # Form has no data yet.

      request.session['sendBackUrl'] = request.GET.get('sendBack', '/')

      captchaImageURL, captchaHash = makeCaptchaImage(
         request.META['REMOTE_ADDR']
      )
      form = RegisterUser(initial={'captchaHash': captchaHash})
      return render_to_response('register.html', locals())
   elif request.method == 'POST':
      # Form has data.
      form = RegisterUser(request.POST)
      if form.is_valid():
         name = form.cleaned_data['name']
         password1 = form.cleaned_data['password1']
         password2 = form.cleaned_data['password2']
         captchaHash = form.cleaned_data['captchaHash']
         captchaEntry = form.cleaned_data['captchaEntry']
         captchaEntry  = captchaEntry.lower()
         description = form.cleaned_data['description']

         if password1 != password2:
            captchaImageURL, captchaHash = makeCaptchaImage(
               request.META['REMOTE_ADDR']
            )
            form = RegisterUser(initial={'captchaHash': captchaHash,
            'name': name})
            error = 'Passwords do not match. Please re-enter.'

            #log(request, 'REGISTERUSERERROR', name, "Password don\'t match")

            return render_to_response('register.html', locals())

         SALT = flashburrito.settings.SECRET_KEY[:20]
         hashEntry = sha.new(SALT+captchaEntry).hexdigest()

         if captchaHash == hashEntry:
            # User entered valid Captcha code
            User.objects.create_user(name, '', password1)
            user = authenticate(username=name, password=password1)
            
            if description != "":
               userProfile = UserProfile(
               user=user,
               description=description
               )
               userProfile.save()

            #log(request, 'REGISTERUSER', name, 'Valid Registration')

            login(request, user)
         else:
            # User entered invalid Captcha code
            captchaImageURL, captchaHash = makeCaptchaImage(
               request.META['REMOTE_ADDR']
            )
            form = RegisterUser(initial={'captchaHash': captchaHash,
            'name': name})
            error = 'Invalid Captcha Code. Please Enter again.'
            
            #log(request, 'REGISTERUSERERROR', name, "Invalid Captcha Code")

            return render_to_response('register.html', locals())

      else:
         # Form is not valid
         captchaImageURL, captchaHash = makeCaptchaImage(
            request.META['REMOTE_ADDR']
         )

         #TODO should parse through form and log exact error
         #log(request, 'REGISTERUSERERROR', "Bad Form", "Other: Form is Not Valid")

         return render_to_response('register.html', locals())

      sendBackUrl = request.session.get('sendBackUrl', '/')
      request.session['sendBackUrl'] = None
      return HttpResponseRedirect(sendBackUrl)

def loginUser(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   #the sendbackUrl will be root if they don't process the form.
   sendBackUrl = '/'

   if request.method == "GET":
      loginForm = LoginUser()
      request.session['sendBackUrl'] = request.GET.get('sendBack', '/')
      return render_to_response('login.html', locals())
   elif request.method == "POST":
      loginForm = LoginUser(request.POST)
      sendBackUrl = request.session.get('sendBackUrl', '/')

      if loginForm.is_valid():
         name = loginForm.cleaned_data['name']
         password = loginForm.cleaned_data['password']

         user = authenticate(username=name, password=password)
         if user is not None:
            login(request, user)

            #log(request, 'LOGINUSER', name, 'Successful Log In')

            return HttpResponseRedirect(sendBackUrl)
         else:
            #log(request, 'LOGINUSERERROR', name, 'Invalid Log In')

            message = "Come on, you can try harder. Invalid login."
            return render_to_response('login.html', locals())
      else:
         # form is not valid
         #TODO should display exactly what the error was.
         #log(request, 'LOGINUSERERROR', name, 'Form not Valid')
         return render_to_response('login.html', locals())

def logoutUser(request):
   user = getUserInfo(request)

   logout(request)
   
   #log(request, 'LOGOUT', user, 'Successfully Logged Out')

   request.session['message'] = "Successfully Logged Out."

   sendBackUrl = request.GET['sendBack']

   return HttpResponseRedirect(sendBackUrl)

def sucks(request, gameId):
   game = Game.objects.get(id__exact=gameId)
   #log(request, 'VOTE', 'SUCKS', gameId + ':\"' + game.name + '\"') 
   return vote(request, gameId, 1)

def ok(request, gameId):
   user = getUserInfo(request)
   game = Game.objects.get(id__exact=gameId)
   #log(request, 'VOTE', 'OK', gameId + ':\"' + game.name + '\"')
   return vote(request, gameId, 2)

def rules(request, gameId):
   user = getUserInfo(request)
   game = Game.objects.get(id__exact=gameId)
   #log(request, 'VOTE', 'RULES', gameId + ':\"' + game.name + '\"')
   return vote(request, gameId, 3)

def vote(request, gameId, voteCode):
   userId = request.session.get('_auth_user_id', None)

   if userId is not None:
      gameId= int(gameId)
      userId= int(userId)

      game = Game.objects.get(id__exact=gameId)
      user = User.objects.get(id__exact=userId)
      votelist = Vote.objects.filter(user=user).filter(game=gameId)

      game.incrementNumVotes(user)

      if len(votelist) == 0:
         v = Vote(game=game, user=user, vote=voteCode)
      else:
         v = votelist[0]
         v.vote = voteCode

      v.save()
      game.updateRating()

   sendBackUrl = request.GET.get('sendBack', '/')

   return HttpResponseRedirect(sendBackUrl)

def yea(request, gameId, tagName):
   game = Game.objects.get(id__exact=gameId)
   #log(request, 'VOTETAG', 'Yea', tagName )
   return voteForTag(request, gameId, tagName, True)

def nay(request, gameId, tagName):
   game = Game.objects.get(id__exact=gameId)
   #log(request, 'VOTETAG', 'Nay', tagName )
   return voteForTag(request, gameId, tagName, False)

def voteForTag(request, gameId, tagName, isYea):
   # TODO use common method to get UID
   userId = request.session.get('_auth_user_id', None)

   if userId is not None:
      gameId= int(gameId)
      userId= int(userId)

      #TODO What if they gave us a bad game, user, or tag name?
      game = Game.objects.get(id__exact=gameId)
      user = User.objects.get(id__exact=userId)
      tag = Tag.objects.get(name__exact=tagName)
      numYea = 0
      numNay = 0 
      for tagVote in TagVote.objects.filter(tag__exact=tag, game__exact=tag):
         if tagVote.yea:
            numYea += 1
         else:
            numNay += 1

      try:
         existingVote = TagVote.objects.get(
            tag__exact=tag,
            game__exact=game,
            user__exact=userId
         )
         existingVote.yea = isYea
      except ObjectDoesNotExist:
         existingVote = TagVote(tag=tag, game=game, user=user, yea=isYea)

      existingVote.save()

      game.updateTagVotes(tag)

   sendBackUrl = request.GET.get('sendBack', '/')

   return HttpResponseRedirect(sendBackUrl)
   

def searchGames(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   query = request.GET.get('q', '')
   
   sendBackUrl = "/search/?q=" + query 
   
   #log(request, 'SEARCH', query, sendBackUrl)
   if query:
      qset = (
         Q(name__icontains=query) |
         Q(description__icontains=query)
      )
      gameObjects = Game.objects.filter(qset).distinct()

      userId = getUserId(user)

      games = [ GameInfo(g, userId, None) for g in gameObjects ]

   else:
      games = []

   return render_to_response("search.html", locals() )

class CommentInfo:
   def __init__(self, user, whenPosted, text):
      self.user = user
      self.whenPosted = whenPosted
      self.text = text

def captchaVarsForSubmit(request):
   captchaImageURL, captchaHash = makeCaptchaImage(
      request.META['REMOTE_ADDR']
   )

   user = getUserInfo(request)

   fromUrl = request.META.get("PATH_INFO", "/")

   if user is None:
      submitgameform = SubmitGame(initial={
         'captchaHash': captchaHash,
         })
   else:
      submitgameform = SubmitGameNoCaptcha()

   return captchaImageURL, captchaHash, submitgameform
   
def gamePage(request, gameId):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   sendBackUrl = "/game/" + str(gameId)

   gameId= int(gameId)

   try:
      g = Game.objects.get(id__exact=gameId)
   except ObjectDoesNotExist:
      request.session['message'] = "The Game you requested doesn't exist!"
      return HttpResponseRedirect('/')

   game = GameInfo(g, userId, None)

   #log(request, 'GAMEPAGE', game.name, sendBackUrl)

   comments = [
      CommentInfo(comment.user, comment.whenPosted, comment.text)
         for comment in
            Comment.objects.filter(game=gameId, approved=1).order_by("whenPosted")
   ]

   if request.method == 'GET':
      # comment form is not posted
      commentForm = PostComment(initial={'gameId': gameId})
      loginForm = LoginUser()

   elif request.method == 'POST':
      # Comment form is submitted, POST

      commentForm = PostComment(request.POST)
      if commentForm.is_valid():
         comment = commentForm.cleaned_data['comment']
         gameId = commentForm.cleaned_data['gameId']
      else:
         # need to reload to Game Page with all variables
         return render_to_response('gamepage.html' , locals())

      try:
         #gameId = int(request.POST['gameId'])
         game = Game.objects.get(id__exact=gameId)
         if game:
            comment = Comment(
               game=game,
               user=user,
               text=comment,
               approved=True,
               whenPosted=datetime.datetime.utcnow()
            )
            comment.save()

            request.session['message'] = \
               "Thank you for posting such a brilliant message.  You are really good."
            
            return HttpResponseRedirect(gamePageUrl(gameId))

         else: # No game id?!  Just return the user to the home page.
            return HttpResponseRedirect('/')
      
      except:
         # TODO log that there was an invalid POST
         return HttpResponseRedirect('/')

   # I don't think we get down here 
   return render_to_response('gamepage.html', locals())

def gamePageUrl(gameId):
   return '/game/' + str(gameId) + '/'

def go(request):
   # functions for when user clicked on game and is leaving the site
   # includes logging and counting game hits
   gameId = request.GET.get('gameid', '')
   url = request.GET.get('url', '/')

   game = Game.objects.get(id=gameId)
   user = getUserInfo(request)
   name = game.name
   game.incrementNumHits()

   try:
      hit = Hits.objects.get(game=game, user=user)
      hit.hits += 1
   except ObjectDoesNotExist:
      hit = Hits(game=game, user=user, hits=1)
   hit.save()

   log(request, 'GO', name, url)

   return HttpResponseRedirect(url)

def log (request, action, arg1, arg2):
   LOGFILE = flashburrito.settings.LOGFILE

   try:
      user = getUserInfo(request)

      logFile = file(LOGFILE, "a")
  
      logFile.write (
         "%s %s %s %s %s %s\n"
         %
         (
            time.strftime("%a %d-%b-%Y %H:%M:%S"),
            '"' + str(user) + '"',
            action,
            arg1,
            arg2,
            request.META.get("HTTP_REFERER", "?")
         )
      )
   except Exception:
      print (
         "%s %s %s %s %s %s\n" 
         %
         (
            time.strftime("%a %d-%b-%Y %H:%M:%S"),
            '"' + str(user) + '"',
            action,
            arg1,
            arg2,
            request.META.get("HTTP_REFERER", "?")
         )
      )

def gameHitsCompare(x, y):
   hitCompare = y.numHits - x.numHits

   if hitCompare == 0:
      if y.whenSubmitted > x.whenSubmitted:
         return 1
      elif y.whenSubmitted < x.whenSubmitted:
         return -1
      else:
         return 0

   else:
      return int(hitCompare)

def gameInfoHitsCompare(x, y):

   hitCompare = y.numHitsUser - x.numHitsUser

   if hitCompare == 0:
      if y.whenSubmitted > x.whenSubmitted:
         return 1
      elif y.whenSubmitted < x.whenSubmitted:
         return -1
      else:
         return 0

   else:
      return hitCompare


def mostPlayedGames(userPageId):
   userPage = User.objects.get(id=userPageId)
   gamesHit = Hits.objects.filter(user=userPage).order_by('hits')


def gamesOfInterestTo(userPageId):
   hits = Hits.objects.filter(user=userPageId)
   gamesHit = set([ hit.game.id for hit in hits ])

   gamesSubmitted = set([
      game.id for game in Game.objects.filter(whoSubmitted=userPageId)
   ])

   comments = Comment.objects.filter(user=userPageId, approved=1)
   gamesCommentedOn = set([ comment.game.id for comment in comments ])

   votes = Vote.objects.filter(user=userPageId)
   gamesVotedOn = set([ vote.game.id for vote in votes ])

   gameSet = gamesHit | gamesSubmitted | gamesCommentedOn | gamesVotedOn

   return [ Game.objects.get(id__exact=id) for id in gameSet ]

def userPage(request, userPageId):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   sendBackUrl = "/user/" + str(userPageId)

   #check if user is on their own home page. If so, display link to admin
   if int(userPageId) == userId:
      usersHomePage = True
   else:
      usersHomePage = False
   
   # This will see if the user who's page is querried exists. It's the
   # user's page that we're on.
   try:
      userPage = User.objects.get(id__exact=userPageId)
   except ObjectDoesNotExist:
      return HttpResponseRedirect('/')

   #log(request, 'USERPAGE', userPage, sendBackUrl)

   try:
      userDescription = UserProfile.objects.get(user=userPage)
   except ObjectDoesNotExist:
      userDescription = None

   # If description is set but blank reset to None
   if userDescription == None:
      pass
   elif userDescription.description == "":
      userDescription = None

   # old games list
   gameObjects = gamesOfInterestTo(userPageId)
   gamesUnordered = [ GameInfo(g, userId, userPageId) for g in gameObjects ]

   games = sorted( gamesUnordered, gameInfoHitsCompare )

   '''
   mostPlayedGames = mostPlayedGames(userPageId)
   recentlyPlayedGames = recentlyPlayedGames(userPageId)
   votedOnGames = votedOnGames(userPageId)
   commentedOnGames = commentedOnGames(userPageId)
   '''
      
   return render_to_response('userpage.html', locals())

def userAdmin(request, userId2):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   #log(request, 'USERADMINPAGE', 'just landed', sendBackUrl)

   # need to convert to strings otherwise methods are unhappy.
   # (should look into why this is.... TODO)
   userId = str(userId)
   userId2 = str(userId2)

   # set sendBackUrl to their userPage if they logout
   sendBackUrl = "/user/" + userId

   # This will see if the user who's page is queried exists.
   try:
      userAdmin = User.objects.get(id__exact=userId)
   except ObjectDoesNotExist:
      request.session['message'] = "Something is amiss with your session.\
      Please log in again!"
      return HttpResponseRedirect('/')

   if user == None:
      request.session['message'] = "Something is amiss with your session.\
      Please log in again."
      return HttpResponseRedirect('/')
   elif user != userAdmin:
      request.session['message'] = "You aren't allowed on that page!"
      return HttpResponseRedirect('/')
   elif int(userId) != int(userId2):
      # just another paranoid check
      request.session['message'] = "You aren't allowed on that page!"
      return HttpResponseRedirect('/')

   if request.method == 'GET':
      # forms to change password and description
      try:
         userDescription = UserProfile.objects.get(user=user)
      except ObjectDoesNotExist:
         userDescription = None

      passwordForm = ChangePassword(initial={'username': user.username})
      descriptionForm = UserDescription(initial={
      'userId': userId, 
      'description': userDescription
      })

   elif request.method == 'POST':
      whichform = request.POST.get('descriptionName', '')

      if whichform: 
         # Form is description form
         descriptionForm = UserDescription(request.POST)
         if descriptionForm.is_valid():
            userFromProfile = descriptionForm.cleaned_data['userId']
            description = descriptionForm.cleaned_data['description']

            try:
               userDescription = UserProfile.objects.get(user=user)
            except ObjectDoesNotExist:
               userDescription = None

            if userDescription == None:
               userDescription = UserProfile(user=user, description=description)
            else:
               userDescription.description = description

            userDescription.save()

            #log(request, 'USERADMINPAGE', 'modified description', sendBackUrl)

            message = "The description has been changed. Perhaps to something\
            more meaningful. Perhaps to less. Tough to say."
         else:
            # need to reload to User Admin Page with all variables
            message = "Dude, something went wrong. Why you trying to hack our\
            system?"
            #log(request, 'USERADMINPAGEERROR', 'failed to modify description', sendBackUrl)
            # passwordForm = ChangePassword(initial={'username': user.username})
            # return render_to_response('useradmin.html' , locals())

         passwordForm = ChangePassword(initial={'username': user.username})
         return render_to_response('useradmin.html' , locals())

      else:
         # Password form is submitted, POST
         # First reinitialize the description form.
         try:
            userDescription = UserProfile.objects.get(user=user)
         except ObjectDoesNotExist:
            userDescription = None

         descriptionForm = UserDescription(initial={
         'userId': userId, 
         'description': userDescription
         })

         passwordForm = ChangePassword(request.POST)
         if passwordForm.is_valid():
            username = passwordForm.cleaned_data['username']
            passwordOld = passwordForm.cleaned_data['passwordOld']
            passwordNew1 = passwordForm.cleaned_data['passwordNew1']
            passwordNew2 = passwordForm.cleaned_data['passwordNew2']
         else:
            # need to reload to User Admin Page with all variables
            #log(request, 'USERADMINPAGEERROR', 'Password Form not valid', sendBackUrl)
            return render_to_response('useradmin.html' , locals())

         if passwordNew1 != passwordNew2:
            #log(request, 'USERADMINPAGEERROR', 'Passwords do not match', sendBackUrl)
            message = "Passwords do not match!"
            return render_to_response('useradmin.html' , locals())

         try:
            #Check username from hidden field against user.username from session
            if user.username != username:
               message = "User Names don't match. Something Funny's going on."
               return render_to_response('useradmin.html' , locals())

            # get user again based upon username just to be sure.
            u = User.objects.get(username__exact=username)
            if u:
               verifyOldPassword = u.check_password(passwordOld)
               if verifyOldPassword:
                  u.set_password(passwordNew1)
                  u.save()
                  #log(request, 'USERADMINPAGE', 'Successfully Changed passwords', sendBackUrl)
               else:
                  message = "Old Password did not match!"
                  #log(request, 'USERADMINPAGEERROR', 'Old Password did not match', sendBackUrl)
                  return render_to_response('useradmin.html' , locals())

               request.session['message'] = "Password has been changed. Now go do something productive!"
               return HttpResponseRedirect("/useradmin/" + userId)
               #return render_to_response('useradmin.html' , locals())

            else: # No user id?!  Just return the user to the home page.
               return HttpResponseRedirect('/')
         
         except:
            # TODO log that there was an invalid POST
            #log(request, 'USERADMINPAGEERROR', 'invalid form POST', sendBackUrl)
            return HttpResponseRedirect('/')

   return render_to_response('useradmin.html', locals())

def terms(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   sendBackUrl = "/terms/"

   #log(request, 'TERMS', "Just Landed", sendBackUrl)
   return render_to_response('terms.html', locals())

def guacamole(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   sendBackUrl = "/guacamole/"

   #log(request, 'GUACAMOLE', "Just Landed", sendBackUrl)
   return render_to_response('guacamole.html', locals())

def aboutUs(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   sendBackUrl = "/aboutus/"

   #log(request, 'ABOUTUS', "Just Landed", sendBackUrl)
   return render_to_response('aboutus.html', locals())

def overview(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   sendBackUrl = "/overview/"

   #log(request, 'OVERVIEW', "Just Landed", sendBackUrl)
   return render_to_response('overview.html', locals())

def feedback(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   #log(request, 'FEEDBACK', "Just Landed", sendBackUrl)

   sendBackUrl = "/feedback/"

   if request.method == 'GET':
      #Form not posted yet
      feedbackForm = UserFeedback()
   elif request.method == 'POST':
      # form is submitted, POST

      feedbackForm = UserFeedback(request.POST)
      if feedbackForm.is_valid():
         email = feedbackForm.cleaned_data['email']
         feedback = feedbackForm.cleaned_data['feedback']
      else:
         # need to reload to Feedback page with all variables
         #log(request, 'FEEDBACKERROR', "Feedback FORM ERRORS", sendBackUrl)
         return render_to_response('feedback.html' , locals())

      try:
         whenSubmitted=datetime.datetime.utcnow()
         f = Feedback(
            email=email, 
            feedback=feedback,
            whenSubmitted=whenSubmitted
         )
         f.save()
         message = "Thank you for your feedback!"
         #log(request, 'FEEDBACK', "Feedback Submited", sendBackUrl)
         feedbackForm = UserFeedback()

         fromEmail = 'steve@flashburrito.com'
         emailMessage1 = feedback + '\n\n' + str(whenSubmitted) + '\n\n' + email

         # send email to admins
         send_mail(
            'Flashburrito: Feedback',
            emailMessage1,
            fromEmail,
            [fromEmail]
         )

         # Send user email if they left their email address
         if email is not None:
            subject = "Flash Burrito!: Thank you for your feedback" 
            emailMessage2 = '''We appreciate your comments and will consider them as we make improvements to the site. We hope you enjoy the games on Flash Burrito!

Cheers,

-Steve
steve@flashburrito.com

If you received this email without visiting flashburrito.com we apologize.
Someone entered your email address on our site. Let me know if you want to opt
out of any future emails notifications.
'''
            toEmail = email

            send_mail(subject, emailMessage2, fromEmail, [toEmail])


      
      except:
         #log(request, 'FEEDBACKERROR', "Feedback error submitting form", sendBackUrl)
         return render_to_response('feedback.html', locals())

   return render_to_response('feedback.html', locals())

def view5min(request):
   WEB_FILES, LIVE_SITE, totalNumberOfGames, sendBackUrl, startOffset, \
   user, userId, message, topHits, topRated = initialVars(request)

   sendBackUrl = "/5min/"

   gameTags = GameTag.objects.filter(tag=tag5min)
   
   taggedGames = [
      gameTag.game for gameTag in gameTags
         if gameTag.hasTag()
   ]

   gameObjects = sorted(
      taggedGames,
      gameDateCompare
   )
   
   games = [ GameInfo(g, userId, None)
         for g in gameObjects
   ]

   #log(request, 'VIEW5MIN', "Just Landed", sendBackUrl)

   return render_to_response('5min.html', locals())

def gameDateCompare(x, y):
   return cmp(y.whenSubmitted, x.whenSubmitted)

