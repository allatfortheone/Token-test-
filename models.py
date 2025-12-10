from sqlalchemy import Index
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
import enum

db = SQLAlchemy()

class User(db.Model, SerializerMixin, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    scouter_id = db.Column(db.Integer, nullable=False, index=True, unique=True)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __init__(self, name, password, scouter_id):
        self.name = name
        self.password = generate_password_hash(password)
        self.scouter_id = scouter_id


class PitScout(db.Model, SerializerMixin):
    __tablename__ = 'pit_scout'

    id = db.Column(db.Integer, primary_key=True, index=True)
    team_number = db.Column(db.Integer) #, db.ForeignKey('team.team_number'))
    robot_height = db.Column(db.Integer)
    robot_dimensions = db.Column(db.String(20))  # Changed to String
    focus_amp = db.Column(db.Boolean)
    can_speaker = db.Column(db.Boolean)
    can_amp = db.Column(db.Boolean)
    ground_pickup = db.Column(db.Boolean)
    source_pickup = db.Column(db.Boolean)
    drive_train = db.Column(db.String(20))
    can_climb = db.Column(db.Boolean)
    can_harmony = db.Column(db.Boolean)
    driver_experience = db.Column(db.Integer)
    can_trap = db.Column(db.Boolean)
    event_code = db.Column(db.String(20))
    scouter_id = db.Column(db.Integer, db.ForeignKey('user.scouter_id'))

    # team = db.relationship('Team')
    scouter = db.relationship('User')

    # Define composite unique index
    __table_args__ = (
        Index('idx_unique_scoring', 'team_number', 'scouter_id', unique=True),
    )


class Schedule(db.Model, SerializerMixin):
    __tablename__ = 'schedule'

    id = db.Column(db.Integer, primary_key=True)
    team_number = db.Column(db.Integer) #, db.ForeignKey('team.team_number'))
    match_number = db.Column(db.Integer)
    drive_station = db.Column(db.Integer, nullable=True)
    alliance_color = db.Column(db.Enum('red', 'blue'), nullable=True)
    event_code = db.Column(db.String(20))
    date = db.Column(db.DateTime)  # Consider including the date mm-dd-yy or dates of the competition

    # team = db.relationship('Team')

    # Define composite unique index
    __table_args__ = (
        Index('idx_unique_scoring', 'team_number', 'match_number', unique=True),
    )


class RobotMatch(db.Model, SerializerMixin):
    __tablename__ = 'robot_match'

    id = db.Column(db.Integer, primary_key=True)
    team_number = db.Column(db.Integer) #, db.ForeignKey('team.team_number'))
    match_number = db.Column(db.Integer)
    # left_alliance_zone = db.Column(db.Boolean, nullable=True)
    # auto_ground_pickups = db.Column(db.Integer, nullable=True)
    # teleop_
    ground_pickups = db.Column(db.Integer, nullable=True)
    source_pickups = db.Column(db.Integer, nullable=True)
    endgame_park = db.Column(db.Boolean, nullable=True)
    endgame_climb = db.Column(db.Boolean, nullable=True)
    endgame_harmony = db.Column(db.Boolean, nullable=True)
    endgame_trap = db.Column(db.Boolean, nullable=True)
    coopertition_bonus = db.Column(db.Boolean, nullable=True)
    robot_type = db.Column(db.String(20))
    match_start_time = db.Column(db.DateTime)
    scouter_id = db.Column(db.Integer, db.ForeignKey('user.scouter_id'))

    # team = db.relationship('Team')
    scouter = db.relationship('User')

    # Define composite unique index
    __table_args__ = (
        Index('idx_unique_scoring', 'team_number', 'match_number', 'scouter_id', 'match_start_time', unique=True),
    )


class Scoring(db.Model, SerializerMixin):
    __tablename__ = 'scoring'

    id = db.Column(db.Integer, primary_key=True)
    team_number = db.Column(db.Integer)
    match_number = db.Column(db.Integer)
    game_phase = db.Column(db.Boolean, nullable=True)
    success_fail = db.Column(db.Integer, nullable=True)
    shot_in_speaker = db.Column(db.Boolean, nullable=True)
    # shot_in_wing = db.Column(db.Boolean, nullable=True)
    shot_x_position = db.Column(db.Float, nullable=True) 
    shot_y_position = db.Column(db.Float, nullable=True)
    is_amplified = db.Column(db.Boolean, nullable=True)
    score_occurence_time = db.Column(db.DateTime, nullable=False)
    scouter_id = db.Column(db.Integer, db.ForeignKey('user.scouter_id'))

    # team = db.relationship('Team')
    scouter = db.relationship('User')

    # Define composite unique index
    __table_args__ = (
        Index('idx_unique_scoring', 'team_number', 'match_number', 'shot_x_position', 'score_occurence_time', unique=True),
    )


class Team(db.Model, SerializerMixin):
    __tablename__ = 'team'

    team_number = db.Column(db.Integer, primary_key=True)
    name_full = db.Column(db.String(511))
    name_short = db.Column(db.String(100))
    city = db.Column(db.String(100))
    state_prov = db.Column(db.String(50))
    country = db.Column(db.String(50))
    rookie_year = db.Column(db.Integer)
    robot_name = db.Column(db.String(100))
    district_code = db.Column(db.String(20))
    school_name = db.Column(db.String(255))
    website = db.Column(db.String(255))
