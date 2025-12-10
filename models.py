# (top-of-file imports, keep everything you already have here)
import os
import json
import logging
from datetime import timedelta
from flask import request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

# Import the db and model classes from models.py BEFORE initializing extensions.
# This ensures the same SQLAlchemy instance is used and that migrations see all models.
from models import db, User, PitScout, Schedule, RobotMatch, Scoring, Team

# (rest of your existing app setup)
# app = Flask(__name__)  <-- keep your existing app instantiation
cfg = {}
config_path = os.getenv("APP_CONFIG_PATH", "config.json")
if os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh) or {}
            logger.info("Loaded configuration from %s", config_path)
    except Exception as e:
        logger.exception("Failed to load config.json: %s", e)

# Secret key for JWT: prefer env var -> config file -> generated (dev only)
jwt_secret = os.getenv("JWT_SECRET_KEY") or cfg.get("JWT_SECRET_KEY")
if not jwt_secret:
    # WARNING: generated secret will invalidate tokens on restart. Use env or config in production.
    jwt_secret = os.getenv("FLASK_SECRET_KEY") or os.urandom(24).hex()
    logger.warning(
        "No JWT_SECRET_KEY found in env or config.json. Using a generated secret (NOT for production)."
    )

# Database URI: environment takes precedence (useful for deployments)
default_db_user = cfg.get("db_user", "root")
default_db_password = cfg.get("db_password", "")
default_db_host = cfg.get("db_host", "127.0.0.1")
default_db_database = cfg.get("db_database", "testdb")
database_url = os.getenv(
    "DATABASE_URL",
    f"mysql://{default_db_user}:{default_db_password}@{default_db_host}/{default_db_database}",
)

# CORS origins: allow specific origins via env or config, fallback to all for dev
cors_origins = os.getenv("CORS_ORIGINS") or cfg.get("cors_origins", "*")

# Put main config into app.config
app.config.update(
    JWT_SECRET_KEY=jwt_secret,
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(days=3),
    SQLALCHEMY_DATABASE_URI=database_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    JSONIFY_PRETTYPRINT_REGULAR=False,
)

# Initialize extensions (db comes from models)
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# ---------------- JWT callbacks -----------------
@jwt.user_identity_loader
def user_identity_lookup(user):
    # When create_access_token(identity=user) is called, store the user's id as sub.
    return user.id

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    # Load user object for current_user
    identity = jwt_data.get("sub")
    if identity is None:
        return None
    return User.query.filter_by(id=identity).one_or_none()

# ... rest of app.py unchanged ...
