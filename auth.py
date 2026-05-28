from flask import Blueprint, flash, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import db, User
import validation_helpers 

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    email = ''
    password = ''

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        try:
            # validate input 
            validation_helpers.validate_email_and_password(email, password)
            if password != confirm_password:
                raise ValueError("Passwords do not match.")
            
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                raise ValueError("Email already registered. Please use a different email or log in.")
            
            password_hash = generate_password_hash(password)
            new_user = User(email=email, password_hash=password_hash)

            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('auth.login'))
        
        except ValueError as ve:
            flash(str(ve), "danger")
            password = ''  # Clear password field on error
            confirm_password = ''  # Clear confirm password field on error
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {e}", "danger")
            password = ''  # Clear password field on error
            confirm_password = ''  # Clear confirm password field on error
            
    return render_template('register.html', email=email, password='', confirm_password='', error=error, success=success)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    success = None
    email = ''
    password = ''

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            # Create a validation for login credentials.
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id  # Store user ID in session for later use   
                session['email'] = user.email  # Store email in session for display purposes
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
               flash("Invalid email or password", "danger")
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
    return render_template('login.html', email=email, password='', error=error, success=success)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)  # Remove user ID from session
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))


