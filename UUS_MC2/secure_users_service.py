"""
Secure Universal Users Service
A ZMQ-based microservice that manages users with authentication and encrypted JSON storage.
"""

import zmq
import json
import logging
from datetime import datetime, timedelta
import os
import sys
import hashlib
import secrets
from typing import Dict, List, Optional, Any
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecureUsersService:
    """
    A microservice that manages users with encrypted JSON storage and authentication.
    """
    
    def __init__(self, port: int = 5556, storage_file: str = "users_encrypted.json", 
                 master_password: str = None):
        """
        Initialize the Secure Users Service.
        
        Args:
            port: Port number for ZMQ socket
            storage_file: Path to encrypted JSON storage file
            master_password: Master password for encryption (will prompt if not provided)
        """
        self.port = port
        self.storage_file = storage_file
        
        # Initialize encryption
        if master_password is None:
            master_password = os.environ.get('USERS_SERVICE_PASSWORD', 'default_secure_password_2024')
        
        self.cipher_suite = self._initialize_encryption(master_password)
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")
        
        # Session management (in production, use Redis or similar)
        self.sessions = {}  # session_token -> {username, expires_at}
        
        # Load existing users
        self.users_db = self._load_users()
        
        # Initialize with admin user if empty
        if not self.users_db:
            self._create_default_admin()
        
        logger.info(f"Secure Users Service started on port {port}")
        logger.info(f"Storage: {os.path.abspath(storage_file)}")
    
    def _initialize_encryption(self, master_password: str) -> Fernet:
        """
        Initialize encryption using a master password.
        
        Args:
            master_password: Master password for encryption
            
        Returns:
            Fernet cipher suite for encryption/decryption
        """
        # Derive a key from the master password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'stable_salt_v1',  # In production, use a random salt stored separately
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        return Fernet(key)
    
    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Load users from encrypted JSON file.
        
        Returns:
            Dictionary of users (username -> user_data)
        """
        if not os.path.exists(self.storage_file):
            return {}
        
        try:
            with open(self.storage_file, 'rb') as f:
                encrypted_data = f.read()
            
            if encrypted_data:
                decrypted_data = self.cipher_suite.decrypt(encrypted_data)
                users = json.loads(decrypted_data.decode())
                logger.info(f"Loaded {len(users)} users from encrypted storage")
                return users
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            logger.info("Starting with empty user database")
            return {}
    
    def _save_users(self):
        """Save users to encrypted JSON file."""
        try:
            json_data = json.dumps(self.users_db, indent=2)
            encrypted_data = self.cipher_suite.encrypt(json_data.encode())
            
            # Write atomically
            temp_file = f"{self.storage_file}.tmp"
            with open(temp_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Replace old file
            os.replace(temp_file, self.storage_file)
            
            logger.info(f"Saved {len(self.users_db)} users to encrypted storage")
            
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            raise
    
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """
        Hash a password with salt.
        
        Args:
            password: Plain text password
            salt: Optional salt (generates new if not provided)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for password hashing
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000  # iterations
        )
        
        return password_hash.hex(), salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Stored password hash
            salt: Salt used for hashing
            
        Returns:
            True if password matches, False otherwise
        """
        test_hash, _ = self._hash_password(password, salt)
        return test_hash == password_hash
    
    def _generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)
    
    def _create_default_admin(self):
        """Create a default admin user if database is empty."""
        admin_password_hash, admin_salt = self._hash_password("admin123")
        
        self.users_db["admin"] = {
            "username": "admin",
            "email": "admin@localhost",
            "password_hash": admin_password_hash,
            "password_salt": admin_salt,
            "full_name": "System Administrator",
            "role": "admin",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_login": None,
            "metadata": {}
        }
        
        self._save_users()
        logger.info("Created default admin user (username: admin, password: admin123)")
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user account.
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            Response dictionary
        """
        try:
            # Required fields validation
            username = user_data.get('username', '').strip().lower()
            email = user_data.get('email', '').strip().lower()
            password = user_data.get('password', '').strip()
            
            if not username or not email or not password:
                return {
                    'status': 'error',
                    'message': 'Username, email, and password are required'
                }
            
            # Validate password strength
            if len(password) < 6:
                return {
                    'status': 'error',
                    'message': 'Password must be at least 6 characters long'
                }
            
            # Check if user already exists
            if username in self.users_db:
                return {
                    'status': 'error',
                    'message': 'Username already exists'
                }
            
            # Check if email already exists
            for user in self.users_db.values():
                if user['email'] == email:
                    return {
                        'status': 'error',
                        'message': 'Email already registered'
                    }
            
            # Hash password
            password_hash, salt = self._hash_password(password)
            
            # Create user record
            now = datetime.now().isoformat()
            self.users_db[username] = {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "password_salt": salt,
                "full_name": user_data.get('full_name', ''),
                "phone": user_data.get('phone', ''),
                "address": user_data.get('address', ''),
                "city": user_data.get('city', ''),
                "country": user_data.get('country', ''),
                "postal_code": user_data.get('postal_code', ''),
                "date_of_birth": user_data.get('date_of_birth', ''),
                "role": user_data.get('role', 'user'),
                "status": 'active',
                "created_at": now,
                "updated_at": now,
                "last_login": None,
                "notes": user_data.get('notes', ''),
                "metadata": user_data.get('metadata', {})
            }
            
            # Save to encrypted storage
            self._save_users()
            
            logger.info(f"Created user: {username}")
            
            return {
                'status': 'success',
                'message': 'User created successfully',
                'username': username,
                'email': email
            }
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def login(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Authenticate a user and create a session.
        
        Args:
            credentials: Dictionary with username/email and password
            
        Returns:
            Response with session token if successful
        """
        try:
            identifier = credentials.get('username', '').strip().lower()
            password = credentials.get('password', '')
            
            if not identifier or not password:
                return {
                    'status': 'error',
                    'message': 'Username/email and password are required'
                }
            
            # Find user by username or email
            user = None
            if identifier in self.users_db:
                user = self.users_db[identifier]
            else:
                # Try to find by email
                for u in self.users_db.values():
                    if u['email'] == identifier:
                        user = u
                        break
            
            if not user:
                return {
                    'status': 'error',
                    'message': 'Invalid username/email or password'
                }
            
            # Check if user is active
            if user['status'] != 'active':
                return {
                    'status': 'error',
                    'message': 'Account is not active'
                }
            
            # Verify password
            if not self._verify_password(password, user['password_hash'], user['password_salt']):
                return {
                    'status': 'error',
                    'message': 'Invalid username/email or password'
                }
            
            # Create session
            session_token = self._generate_session_token()
            expires_at = datetime.now() + timedelta(hours=24)
            
            self.sessions[session_token] = {
                'username': user['username'],
                'expires_at': expires_at.isoformat()
            }
            
            # Update last login
            user['last_login'] = datetime.now().isoformat()
            self._save_users()
            
            logger.info(f"User logged in: {user['username']}")
            
            # Return user info without sensitive data
            user_info = {k: v for k, v in user.items() 
                        if k not in ['password_hash', 'password_salt']}
            
            return {
                'status': 'success',
                'message': 'Login successful',
                'session_token': session_token,
                'user': user_info
            }
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return {
                'status': 'error',
                'message': 'Login failed'
            }
    
    def logout(self, session_token: str) -> Dict[str, Any]:
        """
        Log out a user by invalidating their session.
        
        Args:
            session_token: Session token to invalidate
            
        Returns:
            Response dictionary
        """
        if session_token in self.sessions:
            username = self.sessions[session_token]['username']
            del self.sessions[session_token]
            logger.info(f"User logged out: {username}")
            return {
                'status': 'success',
                'message': 'Logged out successfully'
            }
        
        return {
            'status': 'error',
            'message': 'Invalid session'
        }
    
    def verify_session(self, session_token: str) -> Optional[str]:
        """
        Verify a session token and return username if valid.
        
        Args:
            session_token: Session token to verify
            
        Returns:
            Username if valid, None otherwise
        """
        if session_token not in self.sessions:
            return None
        
        session = self.sessions[session_token]
        expires_at = datetime.fromisoformat(session['expires_at'])
        
        if datetime.now() > expires_at:
            del self.sessions[session_token]
            return None
        
        return session['username']
    
    def update_user(self, session_token: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user information (requires authentication).
        
        Args:
            session_token: Valid session token
            update_data: Fields to update
            
        Returns:
            Response dictionary
        """
        try:
            # Verify session
            username = self.verify_session(session_token)
            if not username:
                return {
                    'status': 'error',
                    'message': 'Invalid or expired session'
                }
            
            user = self.users_db[username]
            
            # Handle username change
            new_username = update_data.get('username', '').strip().lower()
            if new_username and new_username != username:
                if new_username in self.users_db:
                    return {
                        'status': 'error',
                        'message': 'Username already exists'
                    }
                
                # Move user to new username
                self.users_db[new_username] = self.users_db.pop(username)
                user = self.users_db[new_username]
                user['username'] = new_username
                
                # Update session
                self.sessions[session_token]['username'] = new_username
                username = new_username
            
            # Handle email change
            new_email = update_data.get('email', '').strip().lower()
            if new_email and new_email != user['email']:
                # Check if email already exists
                for u in self.users_db.values():
                    if u['email'] == new_email and u['username'] != username:
                        return {
                            'status': 'error',
                            'message': 'Email already registered'
                        }
                user['email'] = new_email
            
            # Handle password change
            if 'password' in update_data:
                new_password = update_data['password'].strip()
                if len(new_password) < 6:
                    return {
                        'status': 'error',
                        'message': 'Password must be at least 6 characters long'
                    }
                
                # Verify current password if provided
                if 'current_password' in update_data:
                    if not self._verify_password(
                        update_data['current_password'],
                        user['password_hash'],
                        user['password_salt']
                    ):
                        return {
                            'status': 'error',
                            'message': 'Current password is incorrect'
                        }
                
                # Hash new password
                password_hash, salt = self._hash_password(new_password)
                user['password_hash'] = password_hash
                user['password_salt'] = salt
            
            # Update metadata (favorites + settings)
            if "metadata" in update_data:
                user["metadata"] = update_data["metadata"]

            # Update other allowed fields
            allowed_fields = [
                'full_name', 'phone', 'address', 'city', 'country',
                'postal_code', 'date_of_birth', 'notes'
            ]

            for field in allowed_fields:
                if field in update_data:
                    user[field] = update_data[field]
            
            # Update timestamp
            user['updated_at'] = datetime.now().isoformat()
            
            # Save changes
            self._save_users()
            
            logger.info(f"Updated user: {username}")
            
            # Return updated user info without sensitive data
            user_info = {k: v for k, v in user.items() 
                        if k not in ['password_hash', 'password_salt']}
            
            return {
                'status': 'success',
                'message': 'User updated successfully',
                'user': user_info
            }
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_user(self, session_token: str) -> Dict[str, Any]:
        """
        Get current user information (requires authentication).
        
        Args:
            session_token: Valid session token
            
        Returns:
            User data or error response
        """
        try:
            username = self.verify_session(session_token)
            if not username:
                return {
                    'status': 'error',
                    'message': 'Invalid or expired session'
                }
            
            user = self.users_db[username]
            
            # Return user info without sensitive data
            user_info = {k: v for k, v in user.items() 
                        if k not in ['password_hash', 'password_salt']}
            
            return {
                'status': 'success',
                'user': user_info
            }
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def delete_user(self, session_token: str, password: str) -> Dict[str, Any]:
        """
        Delete user account (requires authentication and password confirmation).
        
        Args:
            session_token: Valid session token
            password: Password confirmation
            
        Returns:
            Response dictionary
        """
        try:
            username = self.verify_session(session_token)
            if not username:
                return {
                    'status': 'error',
                    'message': 'Invalid or expired session'
                }
            
            user = self.users_db[username]
            
            # Verify password
            if not self._verify_password(password, user['password_hash'], user['password_salt']):
                return {
                    'status': 'error',
                    'message': 'Incorrect password'
                }
            
            # Remove user
            del self.users_db[username]
            
            # Invalidate session
            del self.sessions[session_token]
            
            # Save changes
            self._save_users()
            
            logger.info(f"Deleted user: {username}")
            
            return {
                'status': 'success',
                'message': 'Account deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def list_users(self, session_token: str = None) -> Dict[str, Any]:
        """
        List all users (admin only or public info).
        
        Args:
            session_token: Optional session token for admin access
            
        Returns:
            List of users
        """
        # Check if admin
        is_admin = False
        if session_token:
            username = self.verify_session(session_token)
            if username and self.users_db.get(username, {}).get('role') == 'admin':
                is_admin = True
        
        users = []
        for user in self.users_db.values():
            if user['status'] == 'active':
                if is_admin:
                    # Admin sees all info except passwords
                    user_info = {k: v for k, v in user.items() 
                                if k not in ['password_hash', 'password_salt']}
                else:
                    # Public sees limited info
                    user_info = {
                        'username': user['username'],
                        'full_name': user.get('full_name', ''),
                        'role': user.get('role', 'user')
                    }
                users.append(user_info)
        
        return {
            'status': 'success',
            'users': users,
            'count': len(users)
        }
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming request and route to appropriate method.
        
        Args:
            request_data: Request dictionary
            
        Returns:
            Response dictionary
        """
        action = request_data.get('action')
        
        if action == 'create_user':
            return self.create_user(request_data.get('user_data', {}))
        
        elif action == 'login':
            return self.login(request_data.get('credentials', {}))
        
        elif action == 'logout':
            return self.logout(request_data.get('session_token', ''))
        
        elif action == 'get_user':
            return self.get_user(request_data.get('session_token', ''))
        
        elif action == 'update_user':
            return self.update_user(
                request_data.get('session_token', ''),
                request_data.get('update_data', {})
            )
        
        elif action == 'delete_user':
            return self.delete_user(
                request_data.get('session_token', ''),
                request_data.get('password', '')
            )
        
        elif action == 'list_users':
            return self.list_users(request_data.get('session_token'))
        
        elif action == 'health_check':
            return {
                'status': 'healthy',
                'service': 'Secure Universal Users Service',
                'timestamp': datetime.now().isoformat(),
                'storage': os.path.abspath(self.storage_file),
                'active_sessions': len(self.sessions)
            }
        
        else:
            return {
                'status': 'error',
                'message': f"Unknown action: {action}"
            }
    
    def run(self):
        """Run the service main loop."""
        logger.info("Secure Users Service is ready to accept requests...")
        logger.info("Default admin credentials: username=admin, password=admin123")
        
        try:
            while True:
                # Wait for request
                message = self.socket.recv_string()
                logger.info(f"Received request: {message[:100]}...")
                
                try:
                    # Parse JSON request
                    request_data = json.loads(message)
                    
                    # Process request
                    response = self.process_request(request_data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    response = {
                        'status': 'error',
                        'message': 'Invalid JSON format'
                    }
                
                # Send response
                response_json = json.dumps(response)
                self.socket.send_string(response_json)
                logger.info(f"Sent response: {response_json[:100]}...")
                
        except KeyboardInterrupt:
            logger.info("Shutting down Secure Users Service...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        # Save any pending changes
        self._save_users()
        
        self.socket.close()
        self.context.term()
        logger.info("Secure Users Service shutdown complete")


def main():
    """Main entry point."""
    port = 5556
    storage_file = "users_encrypted.json"
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        storage_file = sys.argv[2]
    
    # Create and run the service
    service = SecureUsersService(port=port, storage_file=storage_file)
    service.run()


if __name__ == "__main__":
    main()
