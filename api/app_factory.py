"""Flask application factory."""

import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from blueprints import register_blueprints
from config import TEMPLATES_DIR
from db import close_db
from extensions import limiter


def create_app(test_config=None):
    app = Flask(__name__, template_folder=TEMPLATES_DIR)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_production')
    app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:5700')

    if test_config:
        app.config.update(test_config)

    try:
        from flask_cors import CORS
        CORS(app, resources={r'/api/*': {'origins': '*'}})
    except ImportError:
        pass

    limiter.init_app(app)
    app.teardown_appcontext(close_db)
    register_blueprints(app)
    return app
