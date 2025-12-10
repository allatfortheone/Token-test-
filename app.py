import json
import os
import logging
import random
from datetime import timedelta
from flask import Flask, jsonify, request, send_from_directory, current_app
from flask_jwt_extended import (
    create_access_token,
    current_user,
    jwt_required,
    JWTManager,
    get_jwt_identity,
)
from flask_migrate import Migrate
from flask_cors import CORS
from models import db, User, Team, PitScout, Schedule, Scoring, RobotMatch

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=os.getenv("FRONTEND_DIST", "frontend/dist"))

# -------- Configuration loading ----------------
# Preferred order:
# 1) Environment variables
# 2) config.json (if present)
# 3) sensible defaults for local dev
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

# Enable CORS for frontend integration (Vue / Nuxt)
# If you need to allow cookies/auth in cross-origin requests, set supports_credentials=True
CORS(app, resources={r"/api/*": {"origins": cors_origins}, r"/*": {"origins": cors_origins}}, supports_credentials=False)

# Initialize extensions
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

# ---------------- Helpers ------------------------
def json_request():
    """Safely get JSON body (returns empty dict if none)."""
    data = request.get_json(silent=True)
    return data or {}

# Optional: serve built frontend (Vue / Nuxt static build) if requested
ENABLE_STATIC = os.getenv("SERVE_FRONTEND_STATIC", "false").lower() in ("1", "true", "yes")
FRONTEND_DIST = os.getenv("FRONTEND_DIST", "frontend/dist")

if ENABLE_STATIC:
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        # Serve files from the built frontend directory. Useful for simple deployments.
        frontend_dir = FRONTEND_DIST
        if path != "" and os.path.exists(os.path.join(frontend_dir, path)):
            return send_from_directory(frontend_dir, path)
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(frontend_dir, "index.html")
        return jsonify({"message": "Frontend not built or not found."}), 404

# ---------------- Routes -------------------------

@app.route("/clear_tables", methods=["GET"])
@jwt_required()
def clear_tables():
    try:
        clearable_tables = ["pit_scout", "robot_match", "schedule", "scoring"]

        # commit once after deleting all tables
        for table_name in clearable_tables:
            if table_name in db.metadata.tables:
                table = db.metadata.tables[table_name]
                db.session.execute(table.delete())
        db.session.commit()
        return jsonify({"message": "All rows deleted from clearable tables."}), 200
    except Exception as e:
        logger.exception("Error clearing tables: %s", e)
        db.session.rollback()
        return jsonify({"message": "Error clearing tables"}), 500

# Login
@app.route("/login", methods=["POST"])
def login():
    data = json_request()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"message": "username and password required"}), 400

    user = User.query.filter_by(name=username).one_or_none()
    if user and user.check_password(password):
        access_token = create_access_token(identity=user)
        return jsonify({"access_token": access_token}), 200
    return jsonify({"message": "Invalid username or password"}), 401

@app.route("/register", methods=["POST"])
def register():
    data = json_request()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"message": "username and password required"}), 400

    existing_user = User.query.filter_by(name=username).first()
    if existing_user:
        return jsonify({"message": "User Exists"}), 409

    scouter_id = random.randint(10**5, (10**6) - 1)
    # It's assumed User model hashes password on set or via check_password implementation
    new_user = User(name=username, password=password, scouter_id=scouter_id)
    db.session.add(new_user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to create user")
        return jsonify({"message": "Failed to create user"}), 500

    user = User.query.filter_by(name=username).one_or_none()
    if user and user.check_password(password):
        access_token = create_access_token(identity=user)
        return jsonify({"access_token": access_token}), 201
    return jsonify({"message": "Invalid username or password"}), 401

@app.route("/who_am_i", methods=["GET"])
@jwt_required()
def who_am_i():
    # current_user is provided by user_lookup_loader
    if not current_user:
        return jsonify({"message": "User not found"}), 404
    return jsonify(id=current_user.id, name=current_user.name, scouter_id=current_user.scouter_id), 200

# Team routes
@app.route("/teams", methods=["POST"])
@jwt_required()
def add_teams():
    data = json_request()
    teams_data = data.get("teams")
    if teams_data and isinstance(teams_data, list) and len(teams_data) > 0:
        try:
            teams = [Team(**team_data) for team_data in teams_data]
            db.session.add_all(teams)
            db.session.commit()
            return jsonify({"message": "Team(s) added successfully"}), 201
        except Exception as e:
            logger.exception("Failed to add teams: %s", e)
            db.session.rollback()
            return jsonify({"message": "Failed to add teams"}), 500
    return jsonify({"message": "Invalid data"}), 400

@app.route("/teams", methods=["GET"])
@jwt_required()
def list_teams():
    teams = Team.query.all()
    serialized = [team.to_dict() for team in teams] if teams else []
    return jsonify(serialized), 200

@app.route("/teams/<int:team_number>", methods=["GET"])
@jwt_required()
def get_team(team_number):
    team = Team.query.get(team_number)
    if team:
        return jsonify(team.to_dict()), 200
    return jsonify({"message": "Team not found"}), 404

# Pit Scout Routes
@app.route("/pit_scout", methods=["POST"])
@jwt_required()
def add_pit_scout():
    data = json_request()
    pit_scout_list = data.get("pit_scout")
    if pit_scout_list and isinstance(pit_scout_list, list) and len(pit_scout_list) > 0:
        try:
            scouter_id = getattr(current_user, "scouter_id", None)
            pit_scouts = [PitScout(scouter_id=scouter_id, **pit_scout) for pit_scout in pit_scout_list]
            db.session.add_all(pit_scouts)
            db.session.commit()
            return jsonify({"message": "Pit Scout data added successfully"}), 201
        except Exception as e:
            logger.exception("Failed to add pit scout data: %s", e)
            db.session.rollback()
            return jsonify({"message": "Error saving pit scout data"}), 500
    return jsonify({"message": "Invalid data"}), 400

@app.route("/pit_scout", methods=["GET"])
@jwt_required()
def list_pit_scout():
    pit_scouts = PitScout.query.all()
    serialized = [ps.to_dict() for ps in pit_scouts] if pit_scouts else []
    return jsonify(serialized), 200

@app.route("/pit_scout/<int:team_number>", methods=["GET"])
@jwt_required()
def get_pit_scout(team_number):
    pit_scouts = PitScout.query.filter_by(team_number=team_number).all()
    if pit_scouts:
        serialized = [ps.serialize() for ps in pit_scouts]
        return jsonify(serialized), 200
    return jsonify({"message": "Pit Scout not found"}), 404

# Schedule Routes
@app.route("/schedule", methods=["POST"])
@jwt_required()
def add_schedule():
    data = json_request()
    schedule_data = data.get("schedule")
    if schedule_data and isinstance(schedule_data, list) and len(schedule_data) > 0:
        try:
            schedule_objs = [Schedule(**sd) for sd in schedule_data]
            db.session.add_all(schedule_objs)
            db.session.commit()
            return jsonify({"message": "Schedule added successfully"}), 201
        except Exception as e:
            logger.exception("Failed to add schedule: %s", e)
            db.session.rollback()
            return jsonify({"message": "Error saving schedule"}), 500
    return jsonify({"message": "Invalid data"}), 400

@app.route("/schedule", methods=["GET"])
@jwt_required()
def get_all_schedule():
    schedules = Schedule.query.all()
    serialized = [s.to_dict() for s in schedules] if schedules else []
    return jsonify(serialized), 200

@app.route("/schedule/<string:eventCode>", methods=["GET"])
@app.route("/schedule/<string:eventCode>/<int:matchNumber>", methods=["GET"])
@jwt_required()
def get_schedule(eventCode, matchNumber=None):
    if matchNumber is not None:
        matches = Schedule.query.filter_by(eventCode=eventCode, matchNumber=matchNumber).all()
    else:
        matches = Schedule.query.filter_by(eventCode=eventCode).order_by(Schedule.matchNumber).all()
    if not matches:
        return jsonify({"schedule": []}), 200
    return jsonify({"schedule": Schedule.serialize_list(matches)}), 200

# Scoring Routes
@app.route("/scoring", methods=["POST"])
@jwt_required()
def add_scoring():
    data = json_request()
    scoring_list = data.get("scoring")
    if scoring_list and isinstance(scoring_list, list) and len(scoring_list) > 0:
        try:
            scouter_id = getattr(current_user, "scouter_id", None)
            scoring_objs = [Scoring(scouter_id=scouter_id, **item) for item in scoring_list]
            db.session.add_all(scoring_objs)
            db.session.commit()
            return jsonify({"message": "Scoring added successfully"}), 201
        except Exception as e:
            logger.exception("Failed to add scoring: %s", e)
            db.session.rollback()
            return jsonify({"message": "Error saving scoring"}), 500
    return jsonify({"message": "Invalid data"}), 400

@app.route("/robot_match", methods=["GET"])
@jwt_required()
def get_robot_match():
    matches = RobotMatch.query.all()
    serialized = [m.to_dict() for m in matches] if matches else []
    return jsonify(serialized), 200

@app.route("/robot_match", methods=["POST"])
@jwt_required()
def add_robot_match():
    data = json_request()
    robot_list = data.get("robot_match")
    if robot_list and isinstance(robot_list, list) and len(robot_list) > 0:
        try:
            scouter_id = getattr(current_user, "scouter_id", None)
            robot_objs = [RobotMatch(scouter_id=scouter_id, **item) for item in robot_list]
            db.session.add_all(robot_objs)
            db.session.commit()
            return jsonify({"message": "Robot Match added successfully"}), 201
        except Exception as e:
            logger.exception("Failed to add robot matches: %s", e)
            db.session.rollback()
            return jsonify({"message": "Error saving robot matches"}), 500
    return jsonify({"message": "Invalid data"}), 400

@app.route("/match", methods=["POST"])
@jwt_required()
def add_all_match_data():
    data = json_request()
    try:
        scouter_id = getattr(current_user, "scouter_id", None)

        # Robot data
        robot_data = data.get("robot_data")
        if robot_data and isinstance(robot_data, list) and len(robot_data) > 0:
            robot_objs = [RobotMatch(scouter_id=scouter_id, **item) for item in robot_data]
            db.session.add_all(robot_objs)

        # Scoring data
        scoring_data = data.get("scoring")
        if scoring_data and isinstance(scoring_data, list) and len(scoring_data) > 0:
            scoring_objs = [Scoring(scouter_id=scouter_id, **item) for item in scoring_data]
            db.session.add_all(scoring_objs)

        if db.session.new:
            db.session.commit()
            return jsonify({"message": "Match data added successfully"}), 201
        else:
            return jsonify({"message": "No data to add"}), 400
    except Exception as error:
        logger.exception("Error saving new match data: %s", error)
        db.session.rollback()
        return jsonify({"message": "Error saving new match data."}), 400


# ---------------- Run server ---------------------
if __name__ == "__main__":
    # For development only. In production use gunicorn/uwsgi.
    port = int(os.getenv("PORT", 5001))
    host = os.getenv("HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true"))
