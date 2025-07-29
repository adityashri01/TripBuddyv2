# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime # Import datetime for timestamps

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False) # e.g., 'Renter', 'Provider'
    rides_created = db.relationship('Ride', backref='creator', lazy=True)
    rides_taken = db.Column(db.Integer, default=0, nullable=False)
    # New fields for activation
    can_offer_rides = db.Column(db.Boolean, default=False, nullable=False)
    can_find_rides = db.Column(db.Boolean, default=False, nullable=False)
    # Add relationship to notifications received by this user
    received_notifications = db.relationship('Notification', backref='recipient', lazy=True, foreign_keys='Notification.user_id')
    # Add relationship for bookings made by this user
    bookings_made = db.relationship('Booking', backref='booker', lazy=True, foreign_keys='Booking.user_id')


    def __repr__(self):
        return f'<User {self.username}>'

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_location = db.Column(db.String(100), nullable=False)
    end_location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False) # Make sure this is present and nullable=False
    time = db.Column(db.String(20), nullable=False) # Make sure this is present and nullable=False
    description = db.Column(db.Text, nullable=True)
    # Add relationship to bookings associated with this ride
    bookings = db.relationship('Booking', backref='ride', lazy=True)
    status = db.Column(db.String(20), default='active', nullable=False) # e.g., 'active', 'completed', 'cancelled'
    # Add a relationship to the driver (User) who created this ride
    driver = db.relationship('User', foreign_keys=[creator_id], backref='offered_rides', lazy=True)

    def __repr__(self):
        return f'<Ride {self.id} from {self.start_location} to {self.end_location}>'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # The user who booked the ride (renter)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)  # The ride being booked
    seats_booked = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default='confirmed', nullable=False) # e.g., 'confirmed', 'completed', 'cancelled'

    def __repr__(self):
        return f'<Booking {self.id} by User {self.user_id} for Ride {self.ride_id}>'


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # The user who receives the notification
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Optional: User who triggered the notification
    message = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50), nullable=True) # e.g., 'ride_booked', 'message', 'ride_cancelled'
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=True)
    ride = db.relationship('Ride', backref='notifications', lazy=True)

    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}: {self.message[:30]}...>'

    def to_dict(self):
        """Converts the notification object to a dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sender_id': self.sender_id,
            'message': self.message,
            'type': self.type,
            'is_read': self.is_read,
            'timestamp': self.timestamp.isoformat() + 'Z', # ISO format for JS compatibility
            'ride_id': self.ride_id
        }