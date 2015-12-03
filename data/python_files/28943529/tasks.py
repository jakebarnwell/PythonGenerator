import os
import sys
import logging

import sqlite3

from pyramid.events import NewRequest
from pyramid.events import subscriber
from pyramid.events import ApplicationCreated

from pyramid.config import Configurator
from pyramid.session import UnencryptedCookieSessionFactoryConfig

from pyramid.exceptions import NotFound
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from paste.httpserver import serve


logging.basicConfig()
logger = logging.getLogger(__file__)

app_root = os.path.dirname(__file__)


################
# Subscribers
################

@subscriber(ApplicationCreated)
def application_created_subscriber(event):
    """
    Initializes the sqlite database
    """
    logger.info('Initializing database')
    sql_file = open(os.path.join(app_root, 'schema.sql'),
                    'r')
    settings = event.app.registry.settings
    db = sqlite3.connect(settings['db'])
    db.executescript(sql_file.read())
    db.commit()
    sql_file.close()
# end def application_created_subscriber

@subscriber(NewRequest)
def newRequestSubscriber(event):
    """
    This function sets up a database connection for the duration of the request
    """
    request = event.request
    settings = request.registry.settings
    request.db = sqlite3.connect(settings['db'])
    request.add_finished_callback(closeDBConnection)
# end def new_request_subscriber

def closeDBConnection(request):
    """
    a callback to ensure our connection to the database is closed
    """
    request.db.close()
# end def close_db_connection


################
# List View
################

@view_config(route_name='list', renderer='list.mako')
def listView(request):
    """
    Presents a list of any tasks present in the database
    """
    cursor = request.db.execute("select id, name from tasks where closed = 0")
    tasks = [{'id':row[0], 'name':row[1]} for row in cursor.fetchall()]
    return {'tasks':tasks}
# end def listView

################
# New View
################

@view_config(route_name='new', renderer='new.mako')
def newView(request):
    """
    Presents a form which allows you to create a new task
    """
    if request.method == 'POST':
        if request.POST.get('name'):
            request.db.execute(
                # The ? are critical here to prevent SQL injection.
                'insert into tasks (name, closed) values (?,?)',
                [request.POST['name'], 0]
            )
            request.db.commit()
            request.session.flash('New task was successfully added!')
            return HTTPFound(location=request.route_url('list'))
        else:
            request.session.flash('Please enter a name for the new task!')
    return {}
# end def newView


################
# Close View
################

@view_config(route_name='close')
def closeView(request):
    """
    Mark a task closed, present a message, and return to the listView
    """
    task_id = int(request.matchdict['id'])
    request.db.execute(
        # Again, notice the '?'
        "update tasks set closed = ? where id = ?",
        (1, task_id)
    )
    request.db.commit()
    request.session.flash('Task was successfully closed!')
    return HTTPFound(location=request.route_url('list'))
# end def closeView


################
# NotFound View
################

@view_config(context=NotFound, renderer='notfound.mako')
def notFoundView(self):
    """
    Customize the 404 page
    """
    return {}
# end def notFoundView


################
# Service
################

def main():
    """
    Starts an http server process.
    """
    settings = {
        'reload_all':True,
        'debug_all':True,
        'db':os.path.join(app_root, 'tasks.db'),
        'mako.directories':os.path.join(app_root, 'templates')
    }
    session_factory = UnencryptedCookieSessionFactoryConfig('sekret')
    config = Configurator(
        settings=settings,
        session_factory=session_factory
    )

    # route setup
    config.add_route('list', '/')
    config.add_route('new', '/new')
    config.add_route('close', '/close/{id}')
    config.add_static_view('static', os.path.join(app_root, 'static'))

    # this comes after any other setup?
    config.scan()

    app = config.make_wsgi_app()
    serve(app, host='0.0.0.0')
# end def main


if __name__ == "__main__":
    sys.exit(main())