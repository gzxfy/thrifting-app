from flask import Flask, flash, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.utils import secure_filename
import os
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
from auth import auth_bp, create_tables, login_required
import validation_helpers
load_dotenv()

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
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
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    if request.method == "POST":
        email = session.get('email')  # Get the logged-in user's email from the session
        if not email:
            flash("You must be logged in to create an item.", "danger")
            return redirect(url_for('auth.login'))

        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        try:
            price = float(price)
        except (ValueError, TypeError):
            flash("Price must be a valid number.", "danger")
            conn.close()
            return redirect(url_for('items'))

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
            return redirect(url_for('items'))

        conn = sqlite3.connect('thrifting.db')
        c = conn.cursor()
        c.execute("INSERT INTO items (title, description, url, price, email) VALUES (?, ?, ?, ?, ?)", (title, description, url, price, email))
        conn.commit()
        conn.close()
        return redirect(url_for('items'))
    
    where_clause, order_by_clause, params = build_filter_query(request.args)
    conn = sqlite3.connect('thrifting.db')
    c = conn.cursor()
    query = f"SELECT * FROM items {where_clause} {order_by_clause}"
    c.execute(query, params)
    items_data = c.fetchall()
    conn.close()
    
    items_data = [(item[0], item[1], item[2], item[3], float(item[4]) if item[4] else 0, item[5], item[6] if len(item) > 6 else None) 
                  for item in items_data
                  ]

    return render_template('items.html', items=items_data, current_email=session.get('email'), active_filters={
        'query': request.args.get('query', ''),
        'min_price': request.args.get('min_price', ''),
        'max_price': request.args.get('max_price', ''),
        'sort_by': request.args.get('sort_by', '')
    })

def build_filter_query(args):
    where_clauses = []
    params = []
    # TEXT SEARCH
    search_query = args.get('query', '').strip()
    if search_query:
        where_clauses.append("(title LIKE ? OR description LIKE ?)")
        search_pattern = f"%{search_query}%"
        params.extend([search_pattern, search_pattern])
    # PRICE FILTERS
    min_price = args.get('min_price')
    if min_price:
        try:            
            min_price = float(min_price)
            where_clauses.append("price >= ?")
            params.append(min_price)
        except ValueError:
            pass  # Ignore invalid min_price input

    max_price = args.get('max_price')
    if max_price:
        try:
            max_price = float(max_price)
            where_clauses.append("price <= ?")
            params.append(max_price)
        except ValueError:
            pass  # Ignore invalid max_price input
    
    # SORTING
    where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    sort_by = args.get('sort_by', '').strip()
    order_by_clause = ""
    if sort_by == "price_asc":
        order_by_clause = "ORDER BY price ASC"
    elif sort_by == "price_desc":
        order_by_clause = "ORDER BY price DESC"
    elif sort_by == "newest":
        order_by_clause = "ORDER BY created_at DESC"
    return where_clause, order_by_clause, params

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
            return redirect(url_for('edit_item', item_id=item_id))

        c.execute("UPDATE items SET title = ?, description = ?, url = ?, price = ? WHERE id = ?", (title, description, url, price, item_id))
        conn.commit()
        conn.close()
        return redirect(url_for('items'))

    c.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    item_data = c.fetchone()
    conn.close()
    return render_template('edit_item.html', item=item_data)

def migrate_add_created_at_column():
    conn = sqlite3.connect('thrifting.db')
    c = conn.cursor()

    try:
        c.execute("PRAGMA table_info(items)")
        columns = [column[1] for column in c.fetchall()]

        if 'created_at' not in columns:
            c.execute("ALTER TABLE items ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            c.execute("UPDATE items SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            conn.commit()
            print("created_at column added successfully.")
        else:
            print("created_at column already exists.")
    except Exception as e:
        print(f"Error occurred while adding created_at column: {e}")
    finally:
        conn.close()

create_tables()
init_db()
migrate_add_created_at_column()
if __name__ == '__main__':
    app.run(debug=True, port=5000)
