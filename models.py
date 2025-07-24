from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()  # uninitialized here, will be initialized in app.py

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "Renter" or "Provider"

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_location = db.Column(db.String(150), nullable=False)
    end_location = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_booked = db.Column(db.Boolean, default=False)
