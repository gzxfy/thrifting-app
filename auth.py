from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
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
            success = "Registration successful! Please log in."
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            error = "Email already registered"
    conn.close()
    return render_template('register.html', error=error, success=success)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)

