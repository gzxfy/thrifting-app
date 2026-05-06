from flask import Flask, flash, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.utils import secure_filename
import os
from auth import auth_bp, create_tables, login_required
import validation_helpers

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.secret_key = 'super-secret-key-12345'  
app.register_blueprint(auth_bp)

# Set security headers to prevent caching, made with the help of ChatGPT
@app.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def init_db():
    conn = sqlite3.connect('thrifting.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            url TEXT,
            price REAL NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

#Home route, will most likely be changed to a landing page in the future, but for now it just redirects to the items page.
@app.route('/')
def home():
    return render_template('home.html')

# Items route
@app.route("/items", methods=["GET", "POST"])
def items():
    conn = sqlite3.connect('thrifting.db')
    c = conn.cursor()

    if request.method == "POST":
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        email = session.get('email')  # Get the logged-in user's email from the session
        if not email:
            flash("You must be logged in to create an item.", "danger")
            return redirect(url_for('auth.login'))
        
        url = request.form.get('image_url')  # Get the image URL from the form, if provided
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                url = f'/static/uploads/{filename}'

        try:
            validation_helpers.validate_item_data(title, description, price, url)
        except ValueError as ve:
            flash(str(ve), "danger")
            conn.close()
            return redirect(url_for('items'))

        c.execute("INSERT INTO items (title, description, url, price, email) VALUES (?, ?, ?, ?, ?)", (title, description, url, price, email))
        conn.commit()
        conn.close()
        return redirect(url_for('items'))

    c.execute("SELECT * FROM items")
    items_data = c.fetchall()
    conn.close()
    return render_template('items.html', items=items_data)


# Delete and Edit routes, with authorization checks to ensure only the user who created the item can edit or delete it.
@app.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    conn = sqlite3.connect('thrifting.db')
    c = conn.cursor()
    
    c.execute("SELECT email FROM items WHERE id = ?", (item_id,))
    item = c.fetchone()
    if not item or item[0] != session.get('email'):
        flash("You are not authorized to delete this item.", "danger")
        conn.close()
        return redirect(url_for('items'))

    c.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('items'))

@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    conn = sqlite3.connect('thrifting.db')
    c = conn.cursor()

    c.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    item = c.fetchone()

    if not item or item[5] != session.get('email'):
        flash("You are not authorized to edit this item.", "danger")
        conn.close()
        return redirect(url_for('items'))

    if request.method == "POST":
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        url = item[3]
        try:
            validation_helpers.validate_item_data(title, description, price, url)
        except ValueError as ve:
            flash(str(ve), "danger")
            conn.close()
            return redirect(url_for('edit_item', item_id=item_id))
        
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                url = f'/static/uploads/{filename}'
            else:
                url = item[3]  # Keep the existing image URL if no new file is uploaded

        c.execute("UPDATE items SET title = ?, description = ?, url = ?, price = ? WHERE id = ?", (title, description, url, price, item_id))
        conn.commit()
        conn.close()
        return redirect(url_for('items'))

    c.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    item_data = c.fetchone()
    conn.close()
    return render_template('edit_item.html', item=item_data)




if __name__ == '__main__':
    create_tables()
    init_db()
    app.run(debug=True, port=5000)
