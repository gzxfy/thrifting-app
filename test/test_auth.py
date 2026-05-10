from flask import session
import pytest
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from validation_helpers import validate_email_and_password
from app import app, init_db, create_tables

def register_and_login(client, email, password):
    """Helper function to register and log in a user."""
    client.post('/register', data={
        'email': email,
        'password': password,
        'confirm_password': password
    })
    return client.post('/login', data={
        'email': email,
        'password': password
    })

def create_test_item(client, title, description, price):
    """Helper function to create a test item."""
    return client.post('/items', data={
        'title': title,
        'description': description,
        'price': price,
        'image_url': 'http://example.com/image.jpg'
    })

@pytest.fixture
def client():
    """Set up a test client and initialize the database for testing."""
    app.config['TESTING'] = True
    with app.app_context():
        create_tables()  # Ensure tables are created before tests
        init_db()  # Initialize the database with test data
        yield app.test_client()         

        conn = sqlite3.connect('accounts.db')
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS accounts")  # Clear accounts after tests
        conn.commit()
        conn.close()

        conn = sqlite3.connect('thrifting.db')
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS items")  # Clear items after tests
        conn.commit()
        conn.close()

def test_register(client):
    """Test the user registration process."""
    response = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    })

    assert response.status_code == 302  # Expect a redirect after successful registration
    assert response.location == '/login'  # Check if redirected to login page after registration

def test_register_duplicate_email(client):
    """Test registration with an email that already exists."""
    # First registration should succeed
    response1 = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    })

    response2 = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Another@1234',
        'confirm_password': 'Another@1234'

        })
    
    assert response2.status_code == 200  # Should return the registration page with an error
    assert b"Email already registered" in response2.data  # Check for error message in response

def test_password_hashing():
    """Test that password hashing and verification works correctly."""
    password = "testpassword"
    password_hash = generate_password_hash(password)

    assert check_password_hash(password_hash, password)  # Should return True for correct password
    assert not check_password_hash(password_hash, "wrongpassword")  # Should return False for incorrect password

def test_login_page(client):
    """Test that the login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200  # Check if the login page loads successfully
    assert b"Login" in response.data  # Check if the login form is present in the response

def test_register_page(client):
    """Test that the registration page loads correctly."""
    response = client.get('/register')
    assert response.status_code == 200  # Check if the registration page loads successfully
    assert b"Register" in response.data  # Check if the registration form is present in the response

def test_login(client):
    """Test the user login process."""
    # First, register a user to test login
    client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    })
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'Test@1234'
    })
    assert response.status_code == 302  # Expect a redirect after successful login
    assert response.location == '/'  # Check if redirected to home page

def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    })

    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 200  # Should return the login page with an error
    assert b"Invalid email or password" in response.data  # Check for error message in response


def test_logout(client):
    """Test the user logout process."""
    # First, register and log in a user to test logout
    response = register_and_login(client, "test@example.com", "Test@1234")
    assert response.status_code == 302  # Expect a redirect after successful login
    
    # Now test logout
    response = client.get('/logout')
    assert response.status_code == 302  # Expect a redirect after logout
    assert response.location == '/'  # Check if redirected to home page after logout
    
    with client:
        response = client.get('/')
        assert 'email' not in session  

def test_login_required_decorator(client):
    """Test that the login_required decorator redirects unauthenticated users."""
    response = create_test_item(client, 'Test Item', 'This is a test item.', '10.00')  # Attempt to create an item without logging in
    assert response.status_code == 302  # Expect a redirect to login page
    assert '/login' in response.location  # Check if redirected to login page

def test_unauthorized_delete(client):
    """Test that the login_required decorator allows access to delete only for authenticated users who own the item."""
    # First, register and log in a user to test item deletion
    response = register_and_login(client, "test@example.com", "Test@1234")

    # Second, create an item to test deletion
    assert response.status_code == 302  # Expect a redirect after successful login
    response = client.get('/items')
    assert response.status_code == 200  # Expect access to items page for authenticated user
    create_test_item(client, 'Test Item', 'This is a test item.', '10.00')
    conn = sqlite3.connect('thrifting.db')
    c = conn.cursor()
    c.execute("SELECT id FROM items WHERE title = ?", ('Test Item',))
    item_id = c.fetchone()[0]
    conn.close()

    # Test unauthorized delete attempt by a different user
    client.post('/logout')  # Log out the first user
    register_and_login(client, "random@example.com", "Random@1234")

    response = client.post(f'/delete/{item_id}',follow_redirects=True)
    assert response.status_code == 200  # Should return the items page with an error

    assert b"You are not authorized to delete this item." in response.data  # Check for error message in response

def test_unauthorized_edit(client):
    """Test that the login_required decorator allows access to edit only for authenticated users who own the item."""
    # First, register and log in a user to test item deletion
    response = register_and_login(client, "test@example.com", "Test@1234")

    # Second, create an item to test editing
    assert response.status_code == 302  # Expect a redirect after successful login
    response = client.get('/items')
    assert response.status_code == 200  # Expect access to items page for authenticated user

    create_test_item(client, 'Test Item', 'This is a test item.', '10.00')
    conn = sqlite3.connect('thrifting.db')
    c = conn.cursor()
    c.execute("SELECT id FROM items WHERE title = ?", ('Test Item',))
    item_id = c.fetchone()[0]
    conn.close()

    # Test unauthorized edit attempt by a different user
    client.post('/logout')  # Log out the first user
    register_and_login(client, "random@example.com", "Random@1234")

    response = client.post(f'/edit/{item_id}',follow_redirects=True)
    assert response.status_code == 200  # Should return the items page with an error

    assert b"You are not authorized to edit this item." in response.data  # Check for error message in response

def test_validate_email_and_password():
    assert validate_email_and_password("test@example.com", "Test@1234") == True  # Valid email and password
    with pytest.raises(ValueError):
        validate_email_and_password("invalidemail", "Test@1234")  # Invalid email format
    with pytest.raises(ValueError):
        validate_email_and_password("test@example.com", "short")  # Invalid password
    with pytest.raises(ValueError):
        validate_email_and_password("", "Test@1234")  # Empty email
    with pytest.raises(ValueError):
        validate_email_and_password("test@example.com", "")  # Empty password
    with pytest.raises(ValueError):
        validate_email_and_password("test@example.com", "123328213231")  # no uppercase, lowercase, or special character