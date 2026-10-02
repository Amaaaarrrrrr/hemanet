"""Flask extension instances, initialised in ``create_app`` (blueprint §P.1)."""

from flask_cors import CORS
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy

from app.core.db import Base

db = SQLAlchemy(model_class=Base)
migrate = Migrate(render_as_batch=False)  # PostgreSQL only; batch mode is for SQLite
api = Api()
cors = CORS()
