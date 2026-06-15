from flask import Flask

from app.config import load_config
from app.db import init_db
from app.routes import api


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(load_config())

    init_db(app)
    app.register_blueprint(api)
    return app
