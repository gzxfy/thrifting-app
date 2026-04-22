from flask import Blueprint, app, flash, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
auth_bp = Blueprint('auth', __name__)


#IMPLEMENT A NAV BAR WITH LOGIN AND REGISTER LINKS IN THE BASE TEMPLATE, THEN EXTEND IT IN ALL OTHER TEMPLATES TO PROVIDE EASY NAVIGATION FOR USERS.

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
            flash("Registration successful! Please log in.")
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            error = "Email already registered"
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
                flash("Login successful!")
                return redirect(url_for('home'))
            else:
                error = "Invalid email or password"
        except sqlite3.Error as e:
            error = f"Database error: {e}"
    conn.close()
    return render_template('login.html', error=error, success=success)

@auth_bp.route('/logout')
def logout():
    session.pop('email', None)  # Remove email from session
    flash("You have been logged out.")
    return redirect(url_for('home'))


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)

