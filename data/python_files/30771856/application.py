import os

from flask import Flask, Response, request, g, \
        jsonify, redirect, url_for, flash, Blueprint, abort, render_template

from jinja2 import TemplateNotFound

from amdsales import helpers
from amdsales import views
from amdsales import filters
from amdsales.config import DefaultConfig
from amdsales.extensions import db


__all__ = ['create_app']

DEFAULT_APP_NAME = 'amdsales'

DEFAULT_MODULES = (
    (views.frontend, ""),
    (views.api, "/api"),
    (views.admin, "/admin"),
    (views.events, "/events"),
)

def create_app(config=None, app_name=None, blueprints=None):

    if app_name is None:
        app_name = DEFAULT_APP_NAME

    if blueprints is None:
        blueprints = DEFAULT_MODULES

    app = Flask(app_name)

    configure_app(app, config)

    configure_errorhandlers(app)
    configure_blueprints(app, blueprints)
    configure_extensions(app)

    filters.create_filters(app);

    return app


def configure_app(app, config):
    
    app.config.from_object(DefaultConfig())

    if config is not None:
        app.config.from_object(config)

    app.config.from_envvar('APP_CONFIG', silent=True)


def configure_blueprints(app, blueprints):
    
    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)


def configure_errorhandlers(app):

    if app.testing:
        return

    @app.errorhandler(404)
    def page_not_found(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, page not found'))
        return render_template("errors/404.html", error=error)

    @app.errorhandler(403)
    def forbidden(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, not allowed'))
        return render_template("errors/403.html", error=error)

    @app.errorhandler(500)
    def server_error(error):
        if request.is_xhr:
            return jsonify(error=_('Sorry, an error has occurred'))
        return render_template("errors/500.html", error=error)

def configure_extensions(app):
    db.init_app(app)
