import os
import datetime
from datetime import date
from dotenv import load_dotenv
import click
from flask import Flask
from flask.cli import with_appcontext
from kicker_dyp.config import config
from kicker_dyp.extensions import db, csrf, login_manager
from kicker_dyp.models import User
from kicker_dyp.views.home import home_bp
from kicker_dyp.views.auth import auth_bp
from kicker_dyp.views.admin import admin_bp
from kicker_dyp.database import save_settings

# Necessary for production: explicitely get environment variables
load_dotenv()


def create_app(config_name: str = 'dev') -> Flask:
    app = Flask(__name__.split('.')[0], static_folder=None)
    app.static_folder = 'static'
    app.config.from_object(config[config_name])

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # workaround: fixes static folder for subdomain
    app.add_url_rule('/static/<path:filename>',
                     endpoint='static',
                     subdomain='dyp',
                     view_func=app.send_static_file)

    # app extensions initialization
    db.init_app(app)
    csrf.init_app(app)  # form tokens
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = u"Bitte einloggen um die Profilseite aufzurufen oder DYP-Ergebnisse einzutragen!"

    # register blueprints here
    app.register_blueprint(home_bp, subdomain='dyp')
    app.register_blueprint(auth_bp, url_prefix='/auth', subdomain='dyp')
    app.register_blueprint(admin_bp, url_prefix='/admin', subdomain='dyp')

    app.cli.add_command(init_db_command)
    app.cli.add_command(create_standard_user_command)

    # to test if development server works
    @app.route('/test/', subdomain='dyp')
    def subdomain_test(subdomain='dyp'):
        return f'<p>Hello, World from {subdomain}-subdomain!</p>'

    # jinja2 template filters
    @app.template_filter('strftime_date')
    def format_date(value):
        if not value:
            value = date.today()
        format = '%d.%m.%Y'
        my_date = date.strftime(value, format)
        return my_date

    @app.template_filter('strftime_timestamp')
    def format_timestamp(value):
        if not value:
            value = date.today()
        format = '%d.%m.%y %H:%M:%S'
        my_time_stamp = date.strftime(value, format)
        return my_time_stamp
    return app


# login manager callback
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# flask click commands
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    db.drop_all()
    db.create_all()
    # this can be changed in the settings
    dyp_year, dyp_season = date.today().year, 32
    delta = datetime.timedelta(days=25*7)
    dyp_start, dyp_end = datetime.datetime.now(), datetime.datetime.now() + delta
    save_settings(dyp_year, dyp_season, dyp_start, dyp_end)
    click.echo('Initialized the database.')


@click.command('create-standard-user')
@with_appcontext
def create_standard_user_command():
    """Create standard user 'info@mitkickzentrale.de'."""
    while True:
        password = input(
            'Enter password for user "info@mitkickzentrale.de", please: ')
        if password:
            break
    new_user = User(login_name='info@mitkickzentrale.de',
                    password=User.hash_password(password))
    db.session.add(new_user)
    db.session.commit()
    click.echo('Created standard user info@mitkickzentrale.de')
