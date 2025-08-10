from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    rides_created = db.relationship('Ride', backref='creator', lazy=True)
    rides_taken = db.Column(db.Integer, default=0, nullable=False)
    can_offer_rides = db.Column(db.Boolean, default=False, nullable=False)
    can_find_rides = db.Column(db.Boolean, default=False, nullable=False)
    received_notifications = db.relationship('Notification', backref='recipient', lazy=True, foreign_keys='Notification.user_id')
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(36), unique=True, nullable=True)
    email_verification_token_expiration = db.Column(db.DateTime, nullable=True)
    last_login_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_location = db.Column(db.String(100), nullable=False)
    end_location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(20), nullable=False)  # e.g., "10:00 AM"
    description = db.Column(db.Text, nullable=True)
    notifications = db.relationship('Notification', backref='ride', lazy=True)

    def __repr__(self):
        return f'<Ride {self.id} from {self.start_location} to {self.end_location}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)   # recipient
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # who triggered
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50), nullable=True)  # e.g., 'ride_booked', 'contact_submission'
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=True)

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}: {self.message[:30]}...>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sender_id': self.sender_id,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'ride_id': self.ride_id
        }
