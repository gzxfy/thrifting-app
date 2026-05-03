from flask import Blueprint, flash, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def create_tables():
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            password_hash = generate_password_hash(password)
            c.execute("INSERT INTO accounts (email, password_hash) VALUES (?, ?)", (email, password_hash))
            conn.commit()
            conn.close()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            flash("Email already registered. Please use a different email or log in.", "danger")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "danger")
        finally:
            conn.close()
    return render_template('register.html', error=error, success=success)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    success = None
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            c.execute("SELECT password_hash FROM accounts WHERE email = ?", (email,))
            result = c.fetchone()
            if result and check_password_hash(result[0], password):
                session['email'] = email  # Store email in session for later use   
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
               flash("Invalid email or password", "danger")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "danger")
    conn.close()
    return render_template('login.html', error=error, success=success)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash("You must be logged in.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/logout')
@login_required
def logout():
    session.pop('email', None)  # Remove email from session
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)

