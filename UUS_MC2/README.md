# Secure Universal Users Service

A Python-based microservice that manages user accounts with authentication, password hashing, and encrypted JSON storage. Provides secure user registration, login, and profile management via ZMQ messaging.

## Table of Contents
- [Features](#features)
- [Security Features](#security-features)
- [Architecture](#architecture) 
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [UML Sequence Diagram](#uml-sequence-diagram)
- [Examples](#examples)
- [Testing](#testing)

## Features

### Account Management
- **User Registration**: Create accounts with username, email, and password
- **Authentication**: Secure login with session tokens
- **Profile Management**: Update username, email, password, and profile information
- **Account Deletion**: Secure account deletion with password confirmation
- **Session Management**: Token-based sessions with expiration

### Security
- **Password Hashing**: PBKDF2-HMAC-SHA256 with salt (100,000 iterations)
- **Encrypted Storage**: AES encryption (Fernet) for JSON data file
- **Session Tokens**: Cryptographically secure random tokens
- **Password Requirements**: Minimum 6 characters (configurable)

### User Interface
- **GUI Client**: Full-featured Tkinter interface with login/register screens
- **Dashboard**: User profile management with tabbed interface
- **Admin Panel**: User list viewing for administrators
- **Real-time Updates**: Live profile editing and credential management

## Security Features

### Password Security
- Passwords are never stored in plain text
- Each password is hashed with a unique salt
- Uses PBKDF2 with 100,000 iterations for key stretching
- Passwords are required for sensitive operations (account deletion)

### Data Encryption
- All user data is stored in an encrypted JSON file
- Uses Fernet symmetric encryption (AES-128)
- Master password protects the encryption key
- Data is encrypted at rest

### Session Security
- Sessions expire after 24 hours
- Secure random tokens (URL-safe base64)
- Sessions validated on each request
- Automatic cleanup of expired sessions

## Architecture

The system consists of three main components:

1. **Secure Users Service** (`secure_users_service.py`): Core service with authentication and encrypted storage
2. **GUI Client** (`secure_users_gui.py`): Full-featured graphical interface with login system
3. **Example Client** (`secure_users_example.py`): Demonstrates programmatic usage

### Data Storage

User data is stored in `users_encrypted.json` with the following structure (encrypted):
```json
{
  "username": {
    "username": "string",
    "email": "string", 
    "password_hash": "hex_string",
    "password_salt": "hex_string",
    "full_name": "string",
    "phone": "string",
    "address": "string",
    "city": "string",
    "country": "string",
    "postal_code": "string",
    "date_of_birth": "string",
    "role": "user|admin|moderator",
    "status": "active|inactive|suspended",
    "created_at": "ISO_datetime",
    "updated_at": "ISO_datetime",
    "last_login": "ISO_datetime",
    "notes": "string",
    "metadata": {}
  }
}
```

## Installation

### Prerequisites

```bash
# Python 3.7 or higher
python --version

# Install required packages
pip install pyzmq cryptography
```

### Setup

1. Clone or download the project files
2. Make scripts executable:
```bash
chmod +x secure_users_service.py
chmod +x secure_users_gui.py
chmod +x secure_users_example.py
```

## Usage

### Starting the Service

```bash
# Default port (5556) and storage
python secure_users_service.py

# Custom port
python secure_users_service.py 5557

# Custom port and storage file
python secure_users_service.py 5557 my_users.json

# With custom master password (environment variable)
USERS_SERVICE_PASSWORD="my_secure_password" python secure_users_service.py
```

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`

### Running the GUI Client

```bash
python secure_users_gui.py
```

The GUI provides:
- Login/Register tabs
- User dashboard with profile management
- Credential update (username, email, password)
- Admin panel for user listing (admin only)
- Account deletion with password confirmation

### Running the Example Client

```bash
python secure_users_example.py
```

## API Documentation

### 1. How to Programmatically REQUEST Data from the Microservice

All requests follow this pattern:

1. Create a ZMQ REQ socket
2. Connect to port 5556 (default)
3. Send JSON request with action and parameters
4. Receive JSON response

#### Request Format

```json
{
    "action": "action_name",
    "parameter1": "value1",
    "parameter2": "value2"
}
```

#### Available Actions

- **create_user**: Register new account
- **login**: Authenticate and get session token
- **logout**: Invalidate session
- **get_user**: Get profile (requires session)
- **update_user**: Update account (requires session)
- **delete_user**: Delete account (requires session + password)
- **list_users**: List users (public or admin view)
- **health_check**: Check service status

#### Example: Create Account and Login

```python
import zmq
import json

# Setup
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5556")

# 1. Create account
request = {
    "action": "create_user",
    "user_data": {
        "username": "alice",
        "email": "alice@example.com",
        "password": "SecurePass123!",
        "full_name": "Alice Smith"
    }
}

socket.send_string(json.dumps(request))
response = json.loads(socket.recv_string())

if response["status"] == "success":
    print(f"Account created: {response['username']}")

# 2. Login
request = {
    "action": "login",
    "credentials": {
        "username": "alice",  # or use email
        "password": "SecurePass123!"
    }
}

socket.send_string(json.dumps(request))
response = json.loads(socket.recv_string())

if response["status"] == "success":
    session_token = response["session_token"]
    print(f"Logged in! Session: {session_token}")
```

### 2. How to Programmatically RECEIVE Data from the Microservice

#### Response Format

All responses include:
```json
{
    "status": "success|error",
    "message": "Description",
    ... additional data ...
}
```

#### Example: Update Profile with Authentication

```python
# Continuing from login example...

# 3. Update username (requires session)
request = {
    "action": "update_user",
    "session_token": session_token,
    "update_data": {
        "username": "alice_updated"
    }
}

socket.send_string(json.dumps(request))
response = json.loads(socket.recv_string())

if response["status"] == "success":
    updated_user = response["user"]
    print(f"New username: {updated_user['username']}")

# 4. Update password (requires current password)
request = {
    "action": "update_user", 
    "session_token": session_token,
    "update_data": {
        "current_password": "SecurePass123!",
        "password": "NewSecurePass456!"
    }
}

socket.send_string(json.dumps(request))
response = json.loads(socket.recv_string())

if response["status"] == "success":
    print("Password updated successfully")

# 5. Logout
request = {
    "action": "logout",
    "session_token": session_token
}

socket.send_string(json.dumps(request))
socket.close()
context.term()
```

## UML Sequence Diagram

```
┌──────────┐                                          ┌───────────────────┐
│  Client  │                                          │Secure Users Service│
└─────┬────┘                                          └─────────┬─────────┘
      │                                                         │
      │  1. Initialize ZMQ Context & Socket                     │
      │──────────────────────────────┐                        │
      │                              │                        │
      │◄─────────────────────────────┘                        │
      │                                                         │
      │  2. Connect to tcp://localhost:5556                    │
      │─────────────────────────────────────────────────────────►
      │                                                         │
      │                              3. Load Encrypted Storage  │
      │                              ┌─────────────────────────┤
      │                              │ Decrypt JSON file       │
      │                              │ Load user database      │
      │                              ◄─────────────────────────┤
      │                                                         │
      │  4. Register: Create Account                           │
      │  {                                                     │
      │    "action": "create_user",                           │
      │    "user_data": {                                     │
      │      "username": "alice",                             │
      │      "email": "alice@ex..",                          │
      │      "password": "Pass123"                            │
      │    }                                                  │
      │  }                                                    │
      │─────────────────────────────────────────────────────────►
      │                                                         │
      │                              5. Process Registration    │
      │                              ┌─────────────────────────┤
      │                              │ Validate inputs         │
      │                              │ Hash password + salt    │
      │                              │ Create user record      │
      │                              │ Encrypt & save JSON     │
      │                              ◄─────────────────────────┤
      │                                                         │
      │  6. Response: Account Created                          │
      │◄─────────────────────────────────────────────────────────
      │                                                         │
      │  7. Login: Authenticate                                │
      │  {                                                     │
      │    "action": "login",                                 │
      │    "credentials": {                                   │
      │      "username": "alice",                             │
      │      "password": "Pass123"                            │
      │    }                                                  │
      │  }                                                    │
      │─────────────────────────────────────────────────────────►
      │                                                         │
      │                              8. Authenticate User       │
      │                              ┌─────────────────────────┤
      │                              │ Find user               │
      │                              │ Verify password hash    │
      │                              │ Generate session token  │
      │                              │ Store session           │
      │                              │ Update last_login       │
      │                              ◄─────────────────────────┤
      │                                                         │
      │  9. Response: Session Token                            │
      │  {                                                     │
      │    "status": "success",                               │
      │    "session_token": "abc..xyz",                       │
      │    "user": {...}                                      │
      │  }                                                    │
      │◄─────────────────────────────────────────────────────────
      │                                                         │
      │  10. Update: Change Username                           │
      │  {                                                     │
      │    "action": "update_user",                           │
      │    "session_token": "abc..xyz",                       │
      │    "update_data": {                                   │
      │      "username": "alice_new"                          │
      │    }                                                  │
      │  }                                                    │
      │─────────────────────────────────────────────────────────►
      │                                                         │
      │                              11. Validate & Update      │
      │                              ┌─────────────────────────┤
      │                              │ Verify session token    │
      │                              │ Check username unique   │
      │                              │ Update user record      │
      │                              │ Update session          │
      │                              │ Encrypt & save JSON     │
      │                              ◄─────────────────────────┤
      │                                                         │
      │  12. Response: Updated User                            │
      │◄─────────────────────────────────────────────────────────
      │                                                         │
      │  13. Update: Change Password                           │
      │  {                                                     │
      │    "action": "update_user",                           │
      │    "session_token": "abc..xyz",                       │
      │    "update_data": {                                   │
      │      "current_password": "Pass123",                   │
      │      "password": "NewPass456"                         │
      │    }                                                  │
      │  }                                                    │
      │─────────────────────────────────────────────────────────►
      │                                                         │
      │                              14. Update Password        │
      │                              ┌─────────────────────────┤
      │                              │ Verify session          │
      │                              │ Verify current password │
      │                              │ Hash new password       │
      │                              │ Update user record      │
      │                              │ Encrypt & save JSON     │
      │                              ◄─────────────────────────┤
      │                                                         │
      │  15. Response: Password Updated                        │
      │◄─────────────────────────────────────────────────────────
      │                                                         │
      │  16. Logout                                            │
      │  {                                                     │
      │    "action": "logout",                                │
      │    "session_token": "abc..xyz"                        │
      │  }                                                    │
      │─────────────────────────────────────────────────────────►
      │                                                         │
      │                              17. Invalidate Session     │
      │                              ┌─────────────────────────┤
      │                              │ Remove session token    │
      │                              ◄─────────────────────────┤
      │                                                         │
      │  18. Response: Logged Out                              │
      │◄─────────────────────────────────────────────────────────
      │                                                         │
┌─────▼────┐                                          ┌─────────▼─────────┐
│  Client  │                                          │  Service Continues │
│  (End)   │                                          │   Awaiting Requests│
└──────────┘                                          └───────────────────┘
```

## Testing

### Test Script

```python
# test_secure_service.py
import zmq
import json

def test_secure_service():
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5556")
    
    # Test 1: Create account
    request = {
        "action": "create_user",
        "user_data": {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123"
        }
    }
    socket.send_string(json.dumps(request))
    response = json.loads(socket.recv_string())
    assert response["status"] == "success"
    print("✓ Account creation")
    
    # Test 2: Login
    request = {
        "action": "login",
        "credentials": {
            "username": "testuser",
            "password": "TestPass123"
        }
    }
    socket.send_string(json.dumps(request))
    response = json.loads(socket.recv_string())
    assert response["status"] == "success"
    session = response["session_token"]
    print("✓ Login successful")
    
    # Test 3: Update email
    request = {
        "action": "update_user",
        "session_token": session,
        "update_data": {"email": "newemail@example.com"}
    }
    socket.send_string(json.dumps(request))
    response = json.loads(socket.recv_string())
    assert response["status"] == "success"
    print("✓ Email update")
    
    print("\nAll tests passed!")
    socket.close()
    context.term()

if __name__ == "__main__":
    test_secure_service()
```

## Security Considerations

1. **Change default admin password** immediately after first setup
2. **Use strong master password** for encryption (via environment variable)
3. **Regular backups** of encrypted user data file
4. **HTTPS/TLS** recommended for production deployments
5. **Rate limiting** should be implemented for production
6. **Session timeout** can be configured (default 24 hours)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Ensure service is running on correct port |
| Invalid session | Session may have expired, login again |
| Password incorrect | Check caps lock and password requirements |
| Username exists | Choose a different username |
| Decryption failed | Check master password is correct |

## Requirements File

Create `requirements.txt`:
```
pyzmq>=25.0.0
cryptography>=41.0.0
```

## License

Educational material for learning secure microservice architecture with authentication.
