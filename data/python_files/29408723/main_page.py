import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import channel
from django.utils import simplejson

from src.board import Board
from src import create_channel
from src import get_other_player_channel_key
from src import get_user_dump

class MainPage(webapp.RequestHandler):

    @login_required
    def get(self):
        board_id = self.request.get('board')
        token = ''
        other_player = ''
        user = users.get_current_user()
        logout_url = users.create_logout_url("/")
        board_dimention = ''
        if board_id:
            board = Board.get_by_id(int(board_id))
            if board:
                board_dimention = board.dimension
                if board.may_join(user):
                    token = create_channel(str(board.key().id()) + user.user_id())
                    other_player = board.player1
                    key = get_other_player_channel_key(board, user)
                    channel.send_message(key, simplejson.dumps({'type':'join', 'user':get_user_dump(user, format='dict')}))
                else:
                    self.redirect('/')
            else:
                self.redirect('/')
        path = os.path.join('templates', 'pvk.html')
        self.response.out.write(template.render(path, {'token': token, 'board_id': board_id, 'me_user': get_user_dump(user),
                                                       'board_dimention': board_dimention, 'logout_url': logout_url,
                                                       'other_player': get_user_dump(other_player)}))
