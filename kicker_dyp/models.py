from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from kicker_dyp import db


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dyp_year = db.Column(db.Integer, nullable=False)
    dyp_season = db.Column(db.Integer, nullable=False)
    dyp_start = db.Column(db.DateTime, nullable=False)
    dyp_end = db.Column(db.DateTime, nullable=False)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login_name = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)

    @classmethod
    def hash_password(cls, password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


players_scores = db.Table('players_scores',
                          db.Column('player_id', db.Integer, db.ForeignKey(
                              'player.id'), primary_key=True),
                          db.Column('score_id', db.Integer, db.ForeignKey(
                              'score.id'), primary_key=True)
                          )


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    club = db.Column(db.String(100))
    registration_nr = db.Column(db.String(8))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    scores = db.relationship(
        'Score',
        secondary=players_scores,
        backref=db.backref(
            'players',
            lazy='dynamic',
        ))


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    dyp_date = db.Column(db.DateTime, nullable=False)
    match_day = db.Column(db.Integer, nullable=False)
    score_today = db.Column(db.Integer, nullable=False)
    place_today = db.Column(db.Integer, nullable=False)
