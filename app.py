import os
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from flask_login import (
        LoginManager, login_user, login_required,
        logout_user, current_user
    )
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload
import uuid
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit, join_room, leave_room # Import SocketIO, emit, join_room, leave_room

from models import db, User, Ride, Notification

app = Flask(__name__)
db_user = os.getenv('MYSQL_USER')
db_password = os.getenv('MYSQL_PASSWORD')
db_host = os.getenv('MYSQL_HOST')
db_port = os.getenv('MYSQL_PORT', '3306')  # default to 3306 if not set
db_name = os.getenv('MYSQL_DATABASE')

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')


# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize SocketIO
socketio = SocketIO(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# SocketIO event handlers
@socketio.on('connect')
@login_required # Ensure only logged-in users can connect to their room
def handle_connect():
    # Join a room specific to the user's ID for targeted notifications
    room = str(current_user.id)
    join_room(room)
    print(f"Socket.IO: Client {current_user.username} (ID: {current_user.id}) connected and joined room {room}")

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        room = str(current_user.id)
        leave_room(room)
        print(f"Socket.IO: Client {current_user.username} (ID: {current_user.id}) disconnected and left room {room}")


def create_tables():
        """Create database tables if they don't exist."""
        with app.app_context():
            db.create_all()

@app.route('/')
def home():
    return render_template('frontpage.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone_number = request.form['phone_number'] # Get the phone number from the form
        role = request.form['role']

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('register'))

        existing_user_username = User.query.filter_by(username=username).first()
        if existing_user_username:
            flash('Username already exists! Please choose a different username.', 'danger')
            return redirect(url_for('register'))

        existing_user_email = User.query.filter_by(email=email).first()
        if existing_user_email:
            flash('Email address is already registered. Please use a different one or login.', 'danger')
            return redirect(url_for('register'))
            
        existing_user_phone = User.query.filter_by(phone_number=phone_number).first()
        if existing_user_phone:
            flash('Phone number is already registered. Please use a different one or login.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        verification_token = str(uuid.uuid4())
        token_expiration = datetime.utcnow() + timedelta(minutes=5)

        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            phone_number=phone_number, # Pass the phone number to the new user object
            role=role,
            rides_taken=0,
            is_email_verified=False,
            email_verification_token=verification_token,
            email_verification_token_expiration=token_expiration
        )
        if role == 'Renter':
            new_user.can_find_rides = True
            new_user.can_offer_rides = False
        elif role == 'Provider':
            new_user.can_find_rides = False
            new_user.can_offer_rides = True

        db.session.add(new_user)
        db.session.commit()

        verification_link = url_for('verify_email', token=verification_token, _external=True)
        msg = Message("Verify your TripBuddy account",
                      recipients=[new_user.email])
        msg.body = f"""
        Hi {new_user.username},

        Thank you for registering with TripBuddy!
        Please click the following link to verify your email address and activate your account.
        This link will expire in 5 minutes.

        {verification_link}

        If you did not register for a TripBuddy account, please ignore this email.

        Best regards,
        The TripBuddy Team
        """
        try:
            mail.send(msg)
            flash('Registration successful! Please check your email to verify your account before logging in.', 'success')
        except Exception as e:
            flash(f'Registration successful, but failed to send verification email. Error: {e}', 'danger')
            print(f"Error sending email: {e}")

        return redirect(url_for('login'))
    return render_template('login_signup.html')

@app.route('/verify_email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()
    if user:
        if user.is_email_verified:
            flash('Your email is already verified. Please log in.', 'info')
        elif user.email_verification_token_expiration and datetime.utcnow() > user.email_verification_token_expiration:
            # Token has expired
            flash('Your verification link has expired. Please register again to receive a new link.', 'danger')
            # Optionally, you might want to clear the expired token and allow re-registration with the same email
            user.email_verification_token = None
            user.email_verification_token_expiration = None
            db.session.commit()
        else:
            # Token is valid and not expired
            user.is_email_verified = True
            user.email_verification_token = None # Clear the token after verification
            user.email_verification_token_expiration = None # Clear expiration after verification
            db.session.commit()
            flash('Your email has been successfully verified! You can now log in.', 'success')
    else:
        flash('Invalid verification link.', 'danger') # General message for security
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if not user.is_email_verified:
                flash('Please verify your email address before logging in. Check your inbox for a verification link.', 'warning')
                return render_template('login_signup.html')

            login_user(user)
            # --- Update last_login_date on successful login ---
            user.last_login_date = datetime.utcnow()
            db.session.commit()

            # --- Create login notification ---
            new_notification = Notification(
                user_id=user.id,
                message=f"Welcome back, {user.username}! You have successfully logged in.",
                type='login_success',
                timestamp=datetime.utcnow()
            )
            db.session.add(new_notification)
            db.session.commit()
            print(f"DEBUG: Login notification created for user {user.username} (ID: {user.id})")
            # Emit SocketIO event for login notification
            socketio.emit('new_notification', new_notification.to_dict(), room=str(user.id))
            # --- END NEW ---

            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", 'danger')
            return render_template('login_signup.html')
    return render_template('login_signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

# API to get current user's notifications
@app.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications():
    # Fetch notifications for the current user, ordered by timestamp descending
    # and then by read status (unread first)
    notifications = Notification.query.filter_by(user_id=current_user.id)\
                                  .order_by(Notification.is_read.asc(), Notification.timestamp.desc())\
                                  .all()
    # Convert notifications to a list of dictionaries using the to_dict method
    notifications_data = [notif.to_dict() for notif in notifications]
    return jsonify(notifications_data)

# API to mark a notification as read (using URL parameter)
@app.route('/api/notifications/<int:notification_id>/mark_read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get(notification_id)
    if not notification:
        return jsonify({'message': 'Notification not found'}), 404
    # Ensure the current user owns this notification
    if notification.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    notification.is_read = True
    db.session.commit()
    return jsonify({'message': 'Notification marked as read', 'notification_id': notification_id})

# API to mark all notifications as read for the current user
@app.route('/api/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    return jsonify({'message': 'All notifications marked as read'})

@app.route('/dashboard')
@login_required
def dashboard():
    user_rides = Ride.query.filter_by(creator_id=current_user.id).all()
    rides_offered_count = len(user_rides)
    rides_taken_count = current_user.rides_taken
    # Assuming average_rating and wallet_balance are placeholders or fetched elsewhere
    average_rating = "4.5"
    wallet_balance = "1200.00"

    return render_template('dashboard.html',
                           name=current_user.username,
                           role=current_user.role,
                           user_rides=user_rides,
                           rides_offered_count=rides_offered_count,
                           rides_taken_count=rides_taken_count,
                           average_rating=average_rating, # Pass these placeholders
                           wallet_balance=wallet_balance, # Pass these placeholders
                           can_offer_rides=current_user.can_offer_rides,
                           can_find_rides=current_user.can_find_rides,
                           is_email_verified=current_user.is_email_verified,
                           # --- NEW: Pass last_login_date to the template ---
                           last_login_date=current_user.last_login_date
                           )

@app.route('/activate_offer_rides', methods=['POST'])
@login_required
def activate_offer_rides():
    if current_user.role == 'Renter': # Only a Renter can activate Provider features
        current_user.can_offer_rides = True
        if current_user.can_find_rides: # If user can already find rides (i.e., was a Renter)
            current_user.role = 'Renter, Provider' # Update role to both
            flash('You have activated "Offer a Ride" and your role is now "Renter, Provider"!', 'success')
        else:
            flash('You have activated "Offer a Ride"!', 'success')
        db.session.commit()
    else:
        flash('Only Renter roles can activate offering rides.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/activate_find_rides', methods=['POST'])
@login_required
def activate_find_rides():
    if current_user.role == 'Provider': # Only a Provider can activate Renter features
        current_user.can_find_rides = True
        if current_user.can_offer_rides: # If user can already offer rides (i.e., was a Provider)
            current_user.role = 'Renter, Provider' # Update role to both
            flash('You have activated "Find a Ride" and your role is now "Renter, Provider"!', 'success')
        else:
            flash('You have activated "Find a Ride"!', 'success')
        db.session.commit()
    else:
        flash('Only Provider roles can activate finding rides.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/post_ride', methods=['GET', 'POST'])
@login_required
def post_ride():
    if not current_user.can_offer_rides:
        flash('You need to activate "Offer a Ride" from your dashboard to post a ride.', 'warning')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        start = request.form['start_location']
        end = request.form['end_location']
        price = float(request.form['price'])
        seats = int(request.form['seats'])
        # You need to add these lines to get date and time from the form
        ride_date_str = request.form['date']
        ride_time_str = request.form['time']
        description = request.form.get('description', '') # Assuming description might be optional
        from datetime import datetime
        try:
            # Convert date string to a date object
            ride_date = datetime.strptime(ride_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('post_ride'))
        if seats <= 0:
            flash('Number of seats must be at least 1.', 'danger')
            return redirect(url_for('post_ride'))
        new_ride = Ride(
            start_location=start,
            end_location=end,
            price=price,
            seats=seats,
            date=ride_date, # Add date here
            time=ride_time_str, # Add time here
            description=description, # Add description here
            creator_id=current_user.id
        )
        db.session.add(new_ride)
        db.session.commit()

        # --- Create post ride notification for the creator ---
        post_ride_notification = Notification(
            user_id=current_user.id,
            message=f"You have successfully posted a ride from {start} to {end}.",
            type='ride_posted',
            ride_id=new_ride.id,
            timestamp=datetime.utcnow()
        )
        db.session.add(post_ride_notification)
        db.session.commit()
        print(f"DEBUG: Ride posted notification created for user {current_user.username} (ID: {current_user.id})")
        # Emit SocketIO event for ride posted notification
        socketio.emit('new_notification', post_ride_notification.to_dict(), room=str(current_user.id))
        # --- END NEW ---

        flash('Ride posted successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('post_ride.html')

@app.route('/find_rides', methods=['GET'])
@login_required
def find_rides():
    if not current_user.can_find_rides:
        flash('You need to activate "Find a Ride" from your dashboard to view and book rides.', 'warning')
        return redirect(url_for('dashboard'))
    # Start with all available rides not created by the current user
    rides_query = Ride.query.filter(Ride.seats > 0, Ride.creator_id != current_user.id)
    # Get search parameters from the request
    start_location = request.args.get('start_location')
    end_location = request.args.get('end_location')
    # Apply filters if search parameters are provided
    if start_location:
        rides_query = rides_query.filter(Ride.start_location.ilike(f'%{start_location}%'))
    if end_location:
        rides_query = rides_query.filter(Ride.end_location.ilike(f'%{end_location}%'))
    rides = rides_query.all()
    return render_template('find_rides.html', rides=rides)

@app.route('/book_ride/<int:ride_id>', methods=['POST'])
@login_required
def book_ride(ride_id):
    if not current_user.can_find_rides:
        flash('You need to activate "Find a Ride" from your dashboard to book rides.', 'warning')
        return redirect(url_for('dashboard'))
    ride = Ride.query.get_or_404(ride_id)
    requested_seats_str = request.form.get('seats_to_book')
    if not requested_seats_str:
        flash("Please specify the number of seats to book.", 'danger')
        return redirect(url_for('dashboard'))
    try:
        requested_seats = int(requested_seats_str)
    except ValueError:
        flash("Invalid number of seats. Please enter a valid number.", 'danger')
        return redirect(url_for('dashboard'))
    if requested_seats <= 0:
        flash("You must book at least one seat.", 'danger')
        return redirect(url_for('dashboard'))
    if requested_seats > ride.seats:
        flash(f"Only {ride.seats} seats are available for this ride.", 'danger')
        return redirect(url_for('dashboard'))
    # Prevent a user from booking their own ride
    if ride.creator_id == current_user.id:
        flash("You cannot book seats on your own offered ride.", 'danger')
        return redirect(url_for('dashboard'))
    ride.seats -= requested_seats
    current_user.rides_taken += requested_seats
    db.session.commit() # Commit the changes to the ride and user first
    # --- NEW: Create a notification for the ride creator ---
    ride_creator = User.query.get(ride.creator_id)
    if ride_creator:
        notification_message = f"Your ride from {ride.start_location} to {ride.end_location} has been booked by {current_user.username} for {requested_seats} seat(s)."
        new_notification = Notification(
            user_id=ride_creator.id,
            sender_id=current_user.id,
            message=notification_message,
            type='ride_booked',
            ride_id=ride.id,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_notification)
        db.session.commit() # Commit the new notification
    flash(f'{requested_seats} seat(s) on the ride from {ride.start_location} to {ride.end_location} booked successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/my_rides', methods=['GET'])
@login_required
def my_rides():
    filter_type = request.args.get('filter', 'all')
    offered_rides = []
    rented_bookings = [] # Renamed to better reflect it's a list of Notification objects
    # Fetch rides offered by the current user
    offered_rides_query = Ride.query.filter_by(creator_id=current_user.id).order_by(Ride.date.desc(), Ride.time.asc())
    # Fetch notifications where the current user is the sender (booker) and the type is 'ride_booked'
    # Use joinedload to eager-load the associated Ride object to avoid N+1 queries in the template
    rented_bookings_query = Notification.query.options(joinedload(Notification.ride)).filter(
        Notification.sender_id == current_user.id,
        Notification.type == 'ride_booked',
        Notification.ride_id.isnot(None) # Ensure there's an associated ride
    ).order_by(Notification.timestamp.desc())
    if filter_type == 'offered':
        offered_rides = offered_rides_query.all()
    elif filter_type == 'rented':
        rented_bookings = rented_bookings_query.all()
    else: # 'all' or no filter
        offered_rides = offered_rides_query.all()
        rented_bookings = rented_bookings_query.all()
    return render_template('my_rides.html',
                           offered_rides=offered_rides,
                           rented_bookings=rented_bookings, # Pass the list of notifications
                           filter_type=filter_type)


@app.route('/send_contact_message', methods=['POST'])
def send_contact_message():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message_body = request.form['message']

        msg_subject = f"TripBuddy Contact Form: {subject} from {name}"
        msg_body = f"""
        Name: {name}
        Email: {email}
        Subject: {subject}

        Message:
        {message_body}
        """

        msg = Message(msg_subject,
                      sender=app.config['MAIL_DEFAULT_SENDER'],
                      recipients=['tripbuddy898@gmail.com']) # Send to your specified email
        msg.body = msg_body

        try:
            mail.send(msg)
            flash('Your message has been sent successfully! Our team will reach you soon.', 'success')

            # --- Create notification for successful contact form submission ---
            if current_user.is_authenticated:
                contact_notification = Notification(
                    user_id=current_user.id,
                    message=f"Your contact message '{subject}' has been successfully submitted. We will get back to you soon!",
                    type='contact_submission',
                    timestamp=datetime.utcnow()
                )
                db.session.add(contact_notification)
                db.session.commit()
                print(f"DEBUG: Contact form notification created for user {current_user.username} (ID: {current_user.id})")
                # Emit SocketIO event for contact submission notification
                socketio.emit('new_notification', contact_notification.to_dict(), room=str(current_user.id))
            else:
                print("DEBUG: Contact form submitted by an unauthenticated user. No notification created for user.")
            # --- END NEW ---

        except Exception as e:
            flash(f'Failed to send your message. Please try again later. Error: {e}', 'danger')
            print(f"Error sending contact message: {e}") # Log the error for debugging

        return redirect(url_for('contact')) # Redirect back to the contact page

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user_to_delete = User.query.get(current_user.id)
    if user_to_delete:
        # Before deleting the user, you might want to handle associated data, e.g.:
        # 1. Delete all rides created by this user
        Ride.query.filter_by(creator_id=user_to_delete.id).delete()
        # 2. Delete all notifications associated with this user (as sender or recipient)
        Notification.query.filter(
            (Notification.user_id == user_to_delete.id) |
            (Notification.sender_id == user_to_delete.id)
        ).delete()
        
        db.session.delete(user_to_delete)
        db.session.commit()
        logout_user() # Log the user out after deletion
        flash('Your account has been permanently deleted.', 'success')
        return redirect(url_for('home'))
    else:
        flash('Error: Account not found.', 'danger')
        return redirect(url_for('settings')) # Redirect back to settings or dashboard

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)