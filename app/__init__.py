# app/__init__.py
import os
from flask import Flask
from config import config_map
from app.extensions import db, login_manager, migrate, oauth


def create_app(config_override=None):
    app = Flask(__name__, template_folder='../templates')

    env = os.environ.get('FLASK_ENV', 'local')
    app.config.from_object(config_map.get(env, config_map['local']))
    if config_override:
        app.config.update(config_override)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    oauth.init_app(app)

    login_manager.login_view = 'auth.login'

    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    from app.auth import auth_bp
    from app.home import home_bp
    from app.stores import stores_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(stores_bp)

    return app
