import sys
import logging
from logging import Formatter, FileHandler

from flask import Flask, render_template, flash, g, session, current_app

from flaskext.cache import Cache
from flaskext.markdown import Markdown
from flaskext.uploads import configure_uploads, UploadSet, IMAGES
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.mail import Mail

from btnfemcol.settings import *

uploaded_avatars = UploadSet('avatars', IMAGES)
uploaded_images = UploadSet('images', IMAGES)

db = SQLAlchemy()
cache = Cache()
mail = Mail()

def create_app(debug=False):
    # Change static path based on whether we're debugging.
    if debug:
        print "Debug mode."
        app = Flask('btnfemcol', static_path='/static')

    else:
        app = Flask('btnfemcol', static_path='')

    # Handle configuration
    app.config.from_object('btnfemcol.settings')
    app.config.from_envvar('BTNFEMCOL_SETTINGS', silent=True)
    app.config['DEBUG'] = debug

    # Initialise uploads
    configure_uploads(app, uploaded_avatars)
    configure_uploads(app, uploaded_images)

    # Initialise database
    db.app = app
    db.init_app(app)

    # Initialise cache
    cache.init_app(app)

    # Initialise Markdown
    Markdown(app,
        extensions=[
            'extra',
            'wikilinks',
            'toc'
        ],
        output_format='html5',
        safe_mode=True
    )
    if not debug:
        configure_logging(app)

    # Initialise Mail
    mail.init_app(app)

    # Sub applications
    from btnfemcol.frontend import frontend
    app.register_blueprint(frontend, url_prefix='')
    from btnfemcol.admin import admin
    app.register_blueprint(admin, url_prefix='/admin')

    configure_base_views(app)

    configure_pre_post_request(app)
    
    if app.config['SECRET_KEY'] == '':
        print 'Please setup a secret key in local_settings.py!!!'

    return app

def configure_logging(app):
    file_handler = FileHandler(app.config['LOG_LOCATION'],
        encoding="UTF-8")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(funcName)s:%(lineno)d]'
    ))
    app.logger.addHandler(file_handler)
    for logger in app.config['LOGGERS']:
        app.logger.addHandler(logger)

def configure_base_views(app):
    
    @app.errorhandler(401)
    def unauthorized(error):
        return _status(error), 401

    @app.errorhandler(404)
    def not_found(error):
        return _status(error), 404

    @app.errorhandler(500)
    def fuckup(error):
        return _status("500: Internal Server Error"), 500

def configure_pre_post_request(app):
    from btnfemcol.models import User

    @app.before_request
    def before_request():
        g.logged_in = False
        try:
            if session['logged_in']:
                g.logged_in = True
                key = 'user:id:%s' % session['logged_in']
                user = cache.get(key)
                if user:
                    user = db.session.merge(user, load=False)
                else:
                    user = User.query.filter_by(id=session['logged_in']).first()
                    cache.set(key, user, 5)
                g.user = user
        except KeyError:
            pass



    @app.after_request
    def after_request(response):
        """Closes the database again at the end of the request."""
        return response
        

def _status(error):
    status = [x.strip() for x in str(error).split(":")]
    try:
        return render_template('status.html',
            _status=status[0],
            _message=status[1]
            )
    except:
        return """<h1>%s</h1><p>%s</p>""" % (status[0], status[1])