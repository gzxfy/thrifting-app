import pytest
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, init_db, create_tables

@pytest.fixture
def client():
    """Set up a test client and initialize the database for testing."""
    app.config['TESTING'] = True
    with app.app_context():
        create_tables()  # Ensure tables are created before tests
        yield app.test_client()       # Initialize the database with test data

        conn = sqlite3.connect('accounts.db')
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS accounts")  # Clear accounts after tests
        conn.commit()
        conn.close()

def test_register(client):
    """Test the user registration process."""
    response = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'testpassword'

    })

    assert response.status_code == 302  # Expect a redirect after successful registration
    assert 'login' in response.location  # Check if redirected to login page

def test_register_duplicate_email(client):
    """Test registration with an email that already exists."""
    # First registration should succeed
    response1 = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'testpassword'
    })

    response2 = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'anotherpassword'
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
        'password': 'testpassword'
    })
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpassword'
    })
    assert response.status_code == 302  # Expect a redirect after successful login
    assert response.location == '/'  # Check if redirected to home page

def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'wrongpassword'
    })
    assert response.status_code == 200  # Should return the login page with an error
    assert b"Invalid email or password" in response.data  # Check for error message in response

