from flask import Flask, flash, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename
from models import db, User, Item
from auth import auth_bp, login_required
import validation_helpers
import os
from dotenv import load_dotenv

load_dotenv()

my_sql_password = os.getenv('MySQL_PASSWORD')
my_sql_host = os.getenv('MySQL_HOST')
my_sql_db = os.getenv('MySQL_DB')
my_sql_user = os.getenv('MySQL_USER', 'root')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)

# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{my_sql_user}:{my_sql_password}@{my_sql_host}/{my_sql_db}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    secret_key = 'dev-secret-key-change-me'
    app.logger.warning(
        "SECRET_KEY environment variable is not set. Using an insecure development fallback key."
    )
app.secret_key = secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  
app.register_blueprint(auth_bp)

# Set security headers to prevent caching, made with the help of ChatGPT
@app.after_request
def set_response_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def init_db():
    with app.app_context():
        db.create_all()

#Home route, will most likely be changed to a landing page in the future, but for now it just redirects to the items page.
@app.route('/')
def home():
    return render_template('home.html')

# Items route
@app.route("/items", methods=["GET", "POST"])
def items():
    if request.method == "POST":
        user = User.query.get(session.get('user_id'))
        if not user:
            flash("You must be logged in to add an item.", "danger")
            return redirect(url_for('auth.login'))

        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        try:
            price = float(price)
        except (ValueError, TypeError):
            flash("Price must be a valid number.", "danger")
            return redirect(url_for('items'))

        image_filename = request.form.get('image_url')  # Get the image URL from the form, if provided
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_filename = f'/static/uploads/{filename}'

        try:
            validation_helpers.validate_item_data(title, description, price, image_filename)
        except ValueError as ve:
            flash(str(ve), "danger")
            return redirect(url_for('items'))

        new_item = Item(title=title, description=description, price=price, image_filename=image_filename, user_id=user.id)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('items'))
    
    # Build the base query and apply filters based on query parameters
    query = Item.query

    # TEXT SEARCH
    search_query = request.args.get('query', '').strip()
    if search_query:
        query = query.filter((Item.title.contains(search_query)) | (Item.description.contains(search_query)))

    # PRICE FILTERS
    min_price = request.args.get('min_price')
    if min_price:
        try:            
            min_price = float(min_price)
            query = query.filter(Item.price >= min_price)
        except ValueError:
            pass  # Ignore invalid min_price input

    max_price = request.args.get('max_price')
    if max_price:
        try:
            max_price = float(max_price)
            query = query.filter(Item.price <= max_price)
        except ValueError:
            pass  # Ignore invalid max_price input

    # SORTING
    sort_by = request.args.get('sort_by', '').strip()
    if sort_by == "price_asc":
        query = query.order_by(Item.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Item.price.desc())
    elif sort_by == "newest":
        query = query.order_by(Item.created_at.desc(), Item.id.desc())
    
    items_data = query.all()

    # get the current user's email for display in the template, if logged in
    current_email = None
    if session.get('user_id'):
        user = User.query.get(session.get('user_id'))
        if user:
            current_email = user.email

    return render_template('items.html', items=items_data, current_email=current_email, active_filters={
        'query': request.args.get('query', ''),
        'min_price': request.args.get('min_price', ''),
        'max_price': request.args.get('max_price', ''),
        'sort_by': request.args.get('sort_by', '')
    })

# Delete and Edit routes, with authorization checks to ensure only the user who created the item can edit or delete it.
@app.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    user = User.query.get(session.get('user_id'))
    if not user:
        flash("You are not authorized to delete this item.", "danger")
        return redirect(url_for('items'))

    item = Item.query.get(item_id)
    if not item or item.user_id != user.id:
        flash("You are not authorized to delete this item.", "danger")
        return redirect(url_for('items'))

    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('items'))

@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_item(item_id):
    user = User.query.get(session.get('user_id'))
    if not user:
        flash("You are not authorized to edit this item.", "danger")
        return redirect(url_for('items'))
    
    item = Item.query.get(item_id)
    if not item or item.user_id != user.id:
        flash("You are not authorized to edit this item.", "danger")
        return redirect(url_for('items'))

    if request.method == "POST":
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price')
        image_filename = item.image_filename

        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_filename = f'/static/uploads/{filename}'

        try:
            validation_helpers.validate_item_data(title, description, price, image_filename)
        except ValueError as ve:
            flash(str(ve), "danger")
            return redirect(url_for('edit_item', item_id=item_id))

        item.title = title
        item.description = description
        item.image_filename = image_filename
        item.price = price
        db.session.commit()
        return redirect(url_for('items'))

    item_data = Item.query.get(item_id)
    return render_template('edit_item.html', item=item_data)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
