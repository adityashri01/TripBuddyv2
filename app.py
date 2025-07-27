from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Ride #

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tripbuddy.db'
app.config['SECRET_KEY'] = 'your_super_secret_key_here_please_change_me'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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

        hashed_password = generate_password_hash(password)
        # Initialize rides_taken to 0 for a new user
        new_user = User(username=username, email=email, password=hashed_password, role=role, rides_taken=0) #
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('login_signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
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


@app.route('/dashboard')
@login_required
def dashboard():
    # Fetch rides offered by the current user
    user_rides = Ride.query.filter_by(creator_id=current_user.id).all() #
    rides_offered_count = len(user_rides)
    # Get rides taken count directly from the current user object
    rides_taken_count = current_user.rides_taken #
    return render_template('dashboard.html', name=current_user.username, role=current_user.role, user_rides=user_rides, rides_offered_count=rides_offered_count, rides_taken_count=rides_taken_count)


@app.route('/post_ride', methods=['GET', 'POST'])
@login_required
def post_ride():
    if request.method == 'POST':
        start = request.form['start_location']
        end = request.form['end_location']
        price = float(request.form['price'])
        seats = int(request.form['seats'])

        if seats <= 0:
            flash('Number of seats must be at least 1.', 'danger')
            return redirect(url_for('post_ride'))

        new_ride = Ride(
            start_location=start,
            end_location=end,
            price=price,
            seats=seats,
            creator_id=current_user.id
        ) #
        db.session.add(new_ride)
        db.session.commit()
        flash('Ride posted successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('post_ride.html')


@app.route('/find_rides')
@login_required
def find_rides():
    # Fetch rides that have at least 1 seat available and are not created by the current user
    rides = Ride.query.filter(Ride.seats > 0, Ride.creator_id != current_user.id).all() #
    return render_template('find_rides.html', rides=rides)


@app.route('/book_ride/<int:ride_id>', methods=['POST'])
@login_required
def book_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    requested_seats_str = request.form.get('seats_to_book')

    if not requested_seats_str:
        flash("Please specify the number of seats to book.", 'danger')
        return redirect(url_for('dashboard')) # Redirect to dashboard

    try:
        requested_seats = int(requested_seats_str)
    except ValueError:
        flash("Invalid number of seats. Please enter a valid number.", 'danger')
        return redirect(url_for('dashboard')) # Redirect to dashboard

    if requested_seats <= 0:
        flash("You must book at least one seat.", 'danger')
        return redirect(url_for('dashboard')) # Redirect to dashboard

    if requested_seats > ride.seats:
        flash(f"Only {ride.seats} seats are available for this ride.", 'danger')
        return redirect(url_for('dashboard')) # Redirect to dashboard

    # Prevent a user from booking their own ride
    if ride.creator_id == current_user.id:
        flash("You cannot book seats on your own offered ride.", 'danger')
        return redirect(url_for('dashboard')) # Redirect to dashboard

    ride.seats -= requested_seats # Decrement available seats #
    current_user.rides_taken += requested_seats # Increment rides_taken for the booking user #
    db.session.commit()

    flash(f'{requested_seats} seat(s) on the ride from {ride.start_location} to {ride.end_location} booked successfully!', 'success')
    return redirect(url_for('dashboard')) # Always redirect to dashboard after booking attempt


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)