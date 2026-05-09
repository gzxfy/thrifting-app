import re

# Validation helper functions for email and password
def validate_email(email):
    if email is None or email.strip() == "":
        raise ValueError("Email is required.")
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError("Invalid email format.")
    
def validate_password(password):
    if password is None or password.strip() == "":
        raise ValueError("Password is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character.")
    return True

def validate_email_and_password(email, password):
    validate_email(email)
    validate_password(password)
    return True

# Will most likely be changed to use a more robust validation library in the future, and for better error handling and user feedback, but this is a simple validation function for now.
def validate_item_data(title, description, price, url):
    if not title or not description or not price or not url:
        raise ValueError("Title, description, price, and a picture are required.")
    try:
        price_float = float(price)
    except (ValueError, TypeError):
        raise ValueError("Price must be a valid number.")
    if price_float < 0:
        raise ValueError("Price must be a positive number.")
    return True
