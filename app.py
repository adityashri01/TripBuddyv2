from flask import Flask, request, render_template, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# Import db and models from models.py
# Make sure you have a models.py in the same directory as app.py
# and it defines 'db', 'User', and 'Ride'.
from models import db, User, Ride # Assuming User model now includes 'email' field

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tripbuddy.db'
# IMPORTANT: Change this secret key in a production environment
app.config['SECRET_KEY'] = 'your_super_secret_key_here_please_change_me'

# Initialize extensions with the app
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

# --- Routes defined for frontpage.html links ---

@app.route('/')
def home():
    # Make sure 'frontpage.html' is in your 'templates' folder
    return render_template('frontpage.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    # This route now renders the contact.html template
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email'] # Added email field
        password = request.form['password']
        confirm_password = request.form['confirm_password'] # Added confirm_password field
        role = request.form['role']

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return redirect(url_for('register')) # Redirect back to register route

        existing_user_username = User.query.filter_by(username=username).first()
        if existing_user_username:
            flash('Username already exists! Please choose a different username.', 'danger')
            return redirect(url_for('register')) # Redirect back to register route

        existing_user_email = User.query.filter_by(email=email).first() # Assuming 'email' field in User model
        if existing_user_email:
            flash('Email address is already registered. Please use a different one or login.', 'danger')
            return redirect(url_for('register')) # Redirect back to register route

        # MODIFIED: Removed 'method='sha256'' to use Werkzeug's default secure hashing method
        hashed_password = generate_password_hash(password)
        # Updated User creation to include email
        new_user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    # Make sure 'login_signup.html' is in your 'templates' folder
    return render_template('login_signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'] # Changed from 'username' to 'email'
        password = request.form['password']

        user = User.query.filter_by(email=email).first() # Changed to query by email
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success') # Flash success message
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", 'danger') # Flash error message
            # Re-render the login_signup.html template on failure
            return render_template('login_signup.html')

    # Make sure 'login_signup.html' is in your 'templates' folder
    return render_template('login_signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success') # Flash logout message
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Fetch rides offered by the current user
    user_rides = Ride.query.filter_by(creator_id=current_user.id).all()
    rides_offered_count = len(user_rides) # Calculate the count of rides offered
    # Make sure 'dashboard.html' is in your 'templates' folder
    return render_template('dashboard.html', name=current_user.username, role=current_user.role, user_rides=user_rides, rides_offered_count=rides_offered_count) # Pass the count


@app.route('/post_ride', methods=['GET', 'POST'])
@login_required
def post_ride():
    if request.method == 'POST':
        start = request.form['start_location']
        end = request.form['end_location']
        price = float(request.form['price'])
        seats = int(request.form['seats'])

        new_ride = Ride(
            start_location=start,
            end_location=end,
            price=price,
            seats=seats,
            creator_id=current_user.id
        )
        db.session.add(new_ride)
        db.session.commit()
        flash('Ride posted successfully!', 'success') # Flash success message
        return redirect(url_for('dashboard'))

    # Make sure 'post_ride.html' is in your 'templates' folder
    return render_template('post_ride.html')


@app.route('/find_rides')
@login_required
def find_rides():
    rides = Ride.query.filter_by(is_booked=False).all()
    # Make sure 'find_rides.html' is in your 'templates' folder
    return render_template('find_rides.html', rides=rides)


@app.route('/book_ride/<int:ride_id>')
@login_required
def book_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    if ride.is_booked:
        flash("Sorry, this ride is already booked.", 'danger') # Flash error message
        return redirect(url_for('find_rides')) # Redirect back to find rides
    ride.is_booked = True
    db.session.commit()
    flash(f'Ride from {ride.start_location} to {ride.end_location} booked successfully!', 'success') # Flash success message
    return redirect(url_for('find_rides'))


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)