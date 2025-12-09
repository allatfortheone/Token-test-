import json, os
from datetime import timedelta
from flask import Flask, jsonify, request
from flask_jwt_extended import create_access_token
from flask_jwt_extended import current_user
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import verify_jwt_in_request
from flask_migrate import Migrate
from models import db, User, Team, PitScout, Schedule, Scoring, RobotMatch
import random

app = Flask(__name__)

# Load configuration from config.json
with open('config.json', 'r+') as config:
    config = json.load(config)
    app.config.update(config)

    # Generate a random secret key
    secret_key = os.urandom(24)

    # Convert the bytes to a string (hexadecimal representation)
    secret_key_hex = secret_key.hex()

    app.config['JWT_SECRET_KEY'] = secret_key_hex
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=3)
    jwt = JWTManager(app)
app.config.from_mapping(
    JSONIFY_PRETTYPRINT_REGULAR=False,
    SQLALCHEMY_DATABASE_URI=f"mysql://{config['db_user']}:{config['db_password']}@{config['db_host']}/{config['db_database']}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

# Initialize Flask extensions
db.init_app(app)
migrate = Migrate(app, db)

# Register a callback function that takes whatever object is passed in as the
# identity when creating JWTs and converts it to a JSON serializable format.
@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id

# Register a callback function that loads a user from the database whenever
# a protected route is accessed. This should return an User object on a
# successful lookup, or None if the lookup failed for any reason (for example
# if the user has been deleted from the database).
@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.filter_by(id=identity).one_or_none()


# Routes

@app.route('/clear_tables', methods=['GET'])
@jwt_required()
def clear_tables():
    try:
        clearable_tables = ["pit_scout","robot_match","schedule","scoring"]

        for table_name in clearable_tables:
            if table_name in db.metadata.tables:
                # Get the table object
                table = db.metadata.tables[table_name]
                # Delete all rows from the tabl
                db.session.execute(table.delete())
                db.session.commit()
        return jsonify({'message': f'All rows deleted from clearable tables.'}), 200
    except Exception as e:
        return jsonify({'message': "Error clearing tables"}), 500

# Login
@app.route('/login', methods=['POST'])
def login():
    # Verify user credentials
    # Query the database to check if the user exists and the password is correct
    user = User.query.filter_by(name=request.json['username']).one_or_none()
    if user and user.check_password(request.json['password']):
        # Generate JWT access token
        access_token = create_access_token(identity=user)
        return jsonify({'access_token': access_token}), 200
    else:
        return jsonify({'message': 'Invalid username or password'}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data['username']
    password = data['password']
    scouter_id = random.randint(10**5, (10**6)-1)

    existing_user = User.query.filter_by(name=username).first()
    if existing_user:
        return jsonify({'message': 'User Exists'}), 409
    new_user = User(name=username, password=password, scouter_id=scouter_id)
    db.session.add(new_user)
    db.session.commit()

    user = User.query.filter_by(name=username).one_or_none()
    if user and user.check_password(password):
        access_token = create_access_token(identity=user)
        return jsonify({'access_token': access_token}), 200
    else:
        return jsonify({'message': 'Invalid username or password'}), 401

# Current user
@app.route("/who_am_i", methods=["GET"])
@jwt_required()
def who_am_i():
    # We can now access our User object via `current_user`.
    return jsonify(
        id=current_user.id,
        name=current_user.name,
        scouter_id=current_user.scouter_id
    ), 200

# Team routes
# Add team(s)
@app.route('/teams', methods=['POST'])
@jwt_required()
def add_teams():
    data = request.json
    if data['teams'] and len(data['teams']) > 0:
        teams = [Team(**team_data) for team_data in data['teams']]
        db.session.add_all(teams)
        db.session.commit()
        return jsonify({'message': 'Team(s) added successfully'}), 201
    return jsonify({'message': 'Invalid data'}), 400

# List teams
@app.route('/teams', methods=['GET'])
@jwt_required()
def list_teams():
    teams = Team.query.all()
    if (len(teams) == 0):
        return jsonify([])
    else:
        serialized_teams = [team.to_dict() for team in teams]
        return jsonify(serialized_teams)

# Get a team by number
@app.route('/teams/<int:team_number>', methods=['GET'])
@jwt_required()
def get_team(team_number):
    team = Team.query.get(team_number)
    if team:
        return jsonify(team.to_dict())
    return jsonify({'message': 'Team not found'}), 404

# Pit Scout Routes
# Add pit scout data
@app.route('/pit_scout', methods=['POST'])
@jwt_required()
def add_pit_scout():
    current_user_id = get_jwt_identity()
    data = request.json
    if data['pit_scout'] and len(data['pit_scout']) > 0:
        pit_scouts = [PitScout(scouter_id=current_user.scouter_id, **pit_scout) for pit_scout in data['pit_scout']]
        db.session.add_all(pit_scouts)
        db.session.commit()
        return jsonify({'message': 'Pit Scout data added successfully'}), 201
    return jsonify({'message': 'Invalid data'}), 400

# List pit scout data
@app.route('/pit_scout', methods=['GET'])
@jwt_required()
def list_pit_scout():
    pit_scouts = PitScout.query.all()
    if (len(pit_scouts) == 0):
        return jsonify([])
    else:
        serialized_data = [pit_scout.to_dict() for pit_scout in pit_scouts]
        return jsonify(serialized_data)

# Get pit scout items by a team number
@app.route('/pit_scout/<int:team_number>', methods=['GET'])
@jwt_required()
def get_pit_scout(team_number):
    pit_scouts = PitScout.query.filter_by(team_number=team_number).all()
    if pit_scouts:
        serialized_pit_scouts = [pit_scout.serialize() for pit_scout in pit_scouts]
        return jsonify(serialized_pit_scouts)
    return jsonify({'message': 'Pit Scout not found'}), 404


# Schedule Routes
# Add schedule data
@app.route('/schedule', methods=['POST'])
@jwt_required()
def add_schedule():
    data = request.json
    if data['schedule'] and len(data['schedule']) > 0:
        schedule = [Schedule(**schedule_data) for schedule_data in data['schedule']]
        db.session.add_all(schedule)
        db.session.commit()
        return jsonify({'message': 'Schedule added successfully'}), 201
    return jsonify({'message': 'Invalid data'}), 400

@app.route('/schedule', methods=['GET'])
@jwt_required()
def get_all_schedule():
    schedules = Schedule.query.all()
    if (len(schedules) == 0):
        return jsonify([])
    else:
        serialized_data = [match.to_dict() for match in schedules]
        return jsonify(serialized_data)

# Get event schedule
@app.route("/schedule/<string:eventCode>", methods=["GET"])
@app.route("/schedule/<string:eventCode>/<int:matchNumber>", methods=["GET"])
@jwt_required()
def get_schedule(eventCode, matchNumber=None):
    if matchNumber is not None:    
        matches = Schedule.query.filter_by(eventCode=eventCode, matchNumber=matchNumber).all()
    else:
        matches = Schedule.query.filter_by(eventCode=eventCode).order_by(Schedule.matchNumber).all()
    if (len(matches) == 0):
        return jsonify({'schedule': []}), 200
    else:
        serialized_schedule = [match.serialize() for match in matches]
        return jsonify({'schedule': Schedule.serialize_list(matches)}), 200

# Scoring Routes
# Add scoring
@app.route('/scoring', methods=['POST'])
@jwt_required()
def add_scoring():
    data = request.json
    current_user_id = get_jwt_identity()
    print(current_user_id)
    if data['scoring'] and len(data['scoring']) > 0:
        scoring = [Scoring(scouter_id=current_user.scouter_id, **item) for item in data['scoring']]
        db.session.add_all(scoring)
        db.session.commit()
        return jsonify({'message': 'Scoring added successfully'}), 201
    return jsonify({'message': 'Invalid data'}), 400


@app.route('/robot_match', methods=['GET'])
@jwt_required()
def get_robot_match():
    matches = RobotMatch.query.all()
    if (len(matches) == 0):
        return jsonify([])
    else:
        serialized_data = [match.to_dict() for match in matches]
        return jsonify(serialized_data)

# Add robot match
@app.route('/robot_match', methods=['POST'])
@jwt_required()
def add_robot_match():
    data = request.json
    current_user_id = get_jwt_identity()
    if data and len(data) > 0:
        robot_match = [RobotMatch(scouter_id=current_user.scouter_id, **item) for item in data['robot_match']]
        db.session.add_all(robot_match)
        db.session.commit()
        return jsonify({'message': 'Robot Match added successfully'}), 201
    return jsonify({'message': 'Invalid data'}), 400


@app.route("/match", methods=["POST"])
@jwt_required()
def add_all_match_data():
    current_user_id = get_jwt_identity()
    data = request.json
    try:
        if data['robot_data'] and len(data['robot_data']) > 0:
            robot_match = [RobotMatch(scouter_id=current_user.scouter_id, **item) for item in data['robot_data']]
            db.session.add_all(robot_match)
            db.session.commit()
            
        if data['scoring'] and len(data['scoring']) > 0:
            scoring = [Scoring(scouter_id=current_user.scouter_id, **item) for item in data['scoring']]
            db.session.add_all(scoring)
            db.session.commit()
        
        return jsonify({'message': 'Robot Match Data added successfully'}), 201
    except Exception as error:
        print(error)
        return jsonify({'message': "Error saving new match data."}), 400



# main
if __name__ == '__main__':
   app.run(host= '0.0.0.0', port=5001, debug=False);
