from flask import Flask, request, render_template, redirect, url_for
from flask_login import (
    LoginManager, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

# Import db and models from models.py
# Make sure you have a models.py in the same directory as app.py
# and it defines 'db', 'User', and 'Ride'.
from models import db, User, Ride

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
    # This is a placeholder for your About Us page content
    return "<h1>About Us Page</h1><p>Information about TripBuddy will go here.</p>"

@app.route('/contact')
def contact():
    # This is a placeholder for your Contact Us page content
    return "<h1>Contact Us Page</h1><p>Our contact information will go here.</p>"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return 'User already exists! Please choose a different username.'

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    # Make sure 'login_signup.html' is in your 'templates' folder
    return render_template('login_signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return "Invalid username or password. Please try again."

    # Make sure 'login_signup.html' is in your 'templates' folder
    return render_template('login_signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Make sure 'dashboard.html' is in your 'templates' folder
    return render_template('dashboard.html', name=current_user.username, role=current_user.role)


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
        return "Sorry, this ride is already booked."
    ride.is_booked = True
    db.session.commit()
    return redirect(url_for('find_rides'))


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)