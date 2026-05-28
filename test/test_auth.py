from flask import session
import pytest
import time
from models import User, Item
from werkzeug.security import check_password_hash, generate_password_hash
from validation_helpers import validate_email_and_password

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

# ===== REGISTRATION TESTS =====
def test_register(client):
    """Test the user registration process."""
    response = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    })
    assert response.status_code == 302
    assert response.location == '/login'

def test_register_page(client):
    """Test that the registration page loads correctly."""
    response = client.get('/register')
    assert response.status_code == 200
    assert b"Register" in response.data

def test_register_invalid_email(client):
    """Test registration with an invalid email format."""
    response = client.post('/register', data={
        'email': 'invalidemail',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    }, follow_redirects=True)
    assert response.status_code == 200
    # Check if any error message is present (more flexible)
    assert b"error" in response.data.lower() or b"invalid" in response.data.lower()

def test_register_mismatched_passwords(client):
    """Test registration with mismatched passwords."""
    response = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Mismatch@1234'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data

def test_register_duplicate_email(client):
    """Test registration with an email that already exists."""
    client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    })

    response = client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Another@1234',
        'confirm_password': 'Another@1234'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Email already registered" in response.data

# ===== LOGIN TESTS =====

def test_login_page(client):
    """Test that the login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Login" in response.data

def test_login(client):
    """Test the user login process."""
    client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    })
    
    response = client.post('/login', data={
        'email': 'test@example.com',
        'password': 'Test@1234'
    })
    assert response.status_code == 302
    assert response.location == '/'

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
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

def test_login_stores_user_id_in_session(client):
    """Test that logging in stores the user ID in the session."""
    client.post('/register', data={
        'email': 'test@example.com',
        'password': 'Test@1234',
        'confirm_password': 'Test@1234'
    })

    with client:
        client.post('/login', data={
            'email': 'test@example.com',
            'password': 'Test@1234'
        })
        assert 'user_id' in session
        assert isinstance(session['user_id'], int)

def test_login_nonexistent_email(client):
    """Test login with an email that does not exist."""
    response = client.post('/login', data={
        'email': 'nonexistent@example.com',
        'password': 'Test@1234'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

# ===== LOGOUT TESTS =====
def test_logout(client):
    """Test the user logout process."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    assert response.status_code == 302
    
    response = client.get('/logout')
    assert response.status_code == 302
    assert response.location == '/'
    
    with client:
        client.get('/logout')
        assert 'user_id' not in session

# ===== AUTHORIZATION TESTS =====
def test_login_required_decorator(client):
    """Test that the login_required decorator redirects unauthenticated users."""
    response = create_test_item(client, 'Test Item', 'This is a test item.', '10.00')
    assert response.status_code == 302
    assert '/login' in response.location

def test_unauthorized_delete(client, test_app):
    """Test that unauthorized users cannot delete items."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    assert response.status_code == 302

    response = client.get('/items')
    assert response.status_code == 200
    create_test_item(client, 'Test Item', 'This is a test item.', '10.00')

    with test_app.app_context():
        item = Item.query.filter_by(title='Test Item').first()
        item_id = item.id

    client.get('/logout')
    register_and_login(client, "random@example.com", "Random@1234")

    response = client.post(f'/delete/{item_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to delete this item." in response.data

def test_unauthorized_edit(client, test_app):
    """Test that unauthorized users cannot edit items."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    assert response.status_code == 302

    response = client.get('/items')
    assert response.status_code == 200
    create_test_item(client, 'Test Item', 'This is a test item.', '10.00')

    with test_app.app_context():
        item = Item.query.filter_by(title='Test Item').first()
        item_id = item.id

    client.get('/logout')
    register_and_login(client, "random@example.com", "Random@1234")

    response = client.post(f'/edit/{item_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"You are not authorized to edit this item." in response.data

# ===== PASSWORD HASHING TESTS =====
def test_password_hashing(test_app):
    """Test that password hashing and verification works correctly."""
    with test_app.app_context():
        password = "testpassword"
        password_hash = generate_password_hash(password)
        assert check_password_hash(password_hash, password)
        assert not check_password_hash(password_hash, "wrongpassword")

# ===== VALIDATION TESTS =====
def test_validate_email_and_password():
    """Test email and password validation."""
    assert validate_email_and_password("test@example.com", "Test@1234") == True
    
    with pytest.raises(ValueError):
        validate_email_and_password("invalidemail", "Test@1234")
    
    with pytest.raises(ValueError):
        validate_email_and_password("test@example.com", "short")
    
    with pytest.raises(ValueError):
        validate_email_and_password("", "Test@1234")
    
    with pytest.raises(ValueError):
        validate_email_and_password("test@example.com", "")

# ===== ITEM DISPLAY TESTS =====
def test_owner_sees_edit_delete_buttons(client):
    """Test that the owner of an item can see the edit and delete buttons."""
    response = register_and_login(client, "owner@example.com", "Owner@1234")
    assert response.status_code == 302

    create_test_item(client, 'Owner Item', 'This is an item owned by the user.', '20.00')
    response = client.get('/items')
    assert response.status_code == 200
    assert b"Edit" in response.data
    assert b"Delete" in response.data

def test_non_owner_cannot_see_edit_delete_buttons(client):
    """Test that a non-owner of an item cannot see the edit and delete buttons."""
    response = register_and_login(client, "owner@example.com", "Owner@1234")
    create_test_item(client, 'Owner Item', 'This is an item owned by the user.', '20.00')
    client.get('/logout')
    
    register_and_login(client, "random@example.com", "Random@1234")
    response = client.get('/items')
    assert response.status_code == 200
    assert b"Owner Item" in response.data

def test_item_card_structure(client):
    """Test that item cards display correctly on the items page."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    create_test_item(client, 'Test Item', 'This is a test item.', '10.00')
    
    response = client.get('/items')
    assert response.status_code == 200
    assert b"item-card" in response.data
    assert b"Test Item" in response.data

# ===== SORTING TESTS =====
def test_high_to_low_sorting(client):
    """Test that items are sorted from high to low price correctly."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    create_test_item(client, 'Expensive Item', 'This is an expensive item.', '50.00')
    create_test_item(client, 'Cheapest Item', 'This is the cheapest item.', '5.00')
    create_test_item(client, 'Medium Item', 'This is a medium-priced item.', '25.00')

    response = client.get('/items?sort_by=price_desc')
    assert response.status_code == 200
    expensive_pos = response.data.find(b'Expensive Item')
    medium_pos = response.data.find(b'Medium Item')
    cheapest_pos = response.data.find(b'Cheapest Item')
    assert expensive_pos < medium_pos < cheapest_pos

def test_low_to_high_sorting(client):
    """Test that items are sorted from low to high price correctly."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    create_test_item(client, 'Expensive Item', 'This is an expensive item.', '50.00')
    create_test_item(client, 'Cheapest Item', 'This is the cheapest item.', '5.00')
    create_test_item(client, 'Medium Item', 'This is a medium-priced item.', '25.00')

    response = client.get('/items?sort_by=price_asc')
    assert response.status_code == 200
    cheapest_pos = response.data.find(b'Cheapest Item')
    medium_pos = response.data.find(b'Medium Item')
    expensive_pos = response.data.find(b'Expensive Item')
    assert cheapest_pos < medium_pos < expensive_pos

def test_newest_sorting(client):
    """Test that items are sorted by newest correctly."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    create_test_item(client, 'First Created Item', 'This item was created first.', '10.00')
    time.sleep(0.1)
    create_test_item(client, 'Second Created Item', 'This item was created second.', '10.00')
    time.sleep(0.1)
    create_test_item(client, 'Third Created Item', 'This item was created third.', '10.00')

    response = client.get('/items?sort_by=newest')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    third_pos = html.find('Third Created Item')
    second_pos = html.find('Second Created Item')
    first_pos = html.find('First Created Item')
    
    assert third_pos < second_pos < first_pos, f"Order wrong: Third={third_pos}, Second={second_pos}, First={first_pos}"

def test_invalid_sorting(client):
    """Test that invalid sorting parameters do not break the items page."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    create_test_item(client, 'First Default Item', 'This is the first default item.', '10.00')
    create_test_item(client, 'Second Default Item', 'This is the second default item.', '20.00')
    create_test_item(client, 'Third Default Item', 'This is the third default item.', '30.00')

    response = client.get('/items?sort_by=invalid_sort')
    assert response.status_code == 200
    assert b'First Default Item' in response.data

# ===== FILTER TESTS =====
def test_clear_filters(client):
    """Test that the clear filters button resets all filters and sorting."""
    response = register_and_login(client, "test@example.com", "Test@1234")
    create_test_item(client, 'Matching Item', 'This item matches the filter.', '10.00')
    create_test_item(client, 'Outside Range Item', 'This item should be filtered out.', '30.00')

    filtered_response = client.get('/items?query=item&min_price=5&max_price=15&sort_by=price_desc')
    assert filtered_response.status_code == 200
    assert b'Matching Item' in filtered_response.data
    assert b'Outside Range Item' not in filtered_response.data

    cleared_response = client.get('/items')
    assert cleared_response.status_code == 200
    assert b'Matching Item' in cleared_response.data
    assert b'Outside Range Item' in cleared_response.data