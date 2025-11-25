"""
Example Client for Secure Users Service
Demonstrates authentication and account management operations.
"""

import zmq
import json
import time
from typing import Dict, Any, Optional


class SecureUsersClient:
    """Client for the Secure Users Service with authentication."""

    def __init__(self, port: int = 5556):
        """Initialize the client."""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://localhost:{port}")
        self.session_token = None
        print(f"Connected to Secure Users Service on port {port}")

    def _send_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send request and receive response."""
        request_json = json.dumps(request_data)
        print(f"\n📤 Request: {request_json[:100]}...")
        self.socket.send_string(request_json)

        response_json = self.socket.recv_string()
        response_data = json.loads(response_json)
        print(f"📥 Response: {json.dumps(response_data, indent=2)[:300]}...")

        return response_data

    def create_account(self, username: str, email: str, password: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new user account.

        Args:
            username: Unique username
            email: Email address
            password: Account password
            **kwargs: Additional fields (full_name, phone, etc.)

        Returns:
            Response from service
        """
        user_data = {
            'username': username,
            'email': email,
            'password': password,
            **kwargs
        }

        request = {
            'action': 'create_user',
            'user_data': user_data
        }

        return self._send_request(request)

    def login(self, username_or_email: str, password: str) -> bool:
        """
        Login to the service.

        Args:
            username_or_email: Username or email
            password: Account password

        Returns:
            True if login successful, False otherwise
        """
        request = {
            'action': 'login',
            'credentials': {
                'username': username_or_email,
                'password': password
            }
        }

        response = self._send_request(request)

        if response['status'] == 'success':
            self.session_token = response['session_token']
            print(f"✅ Logged in as: {response['user']['username']}")
            return True
        else:
            print(f"❌ Login failed: {response.get('message')}")
            return False

    def logout(self) -> bool:
        """Logout from the service."""
        if not self.session_token:
            print("Not logged in")
            return False

        request = {
            'action': 'logout',
            'session_token': self.session_token
        }

        response = self._send_request(request)

        if response['status'] == 'success':
            self.session_token = None
            print("✅ Logged out successfully")
            return True

        return False

    def get_profile(self) -> Optional[Dict[str, Any]]:
        """Get current user profile."""
        if not self.session_token:
            print("❌ Not logged in")
            return None

        request = {
            'action': 'get_user',
            'session_token': self.session_token
        }

        response = self._send_request(request)

        if response['status'] == 'success':
            return response['user']

        return None

    def update_username(self, new_username: str) -> bool:
        """Update username."""
        if not self.session_token:
            print("❌ Not logged in")
            return False

        request = {
            'action': 'update_user',
            'session_token': self.session_token,
            'update_data': {'username': new_username}
        }

        response = self._send_request(request)
        return response['status'] == 'success'

    def update_email(self, new_email: str) -> bool:
        """Update email."""
        if not self.session_token:
            print("❌ Not logged in")
            return False

        request = {
            'action': 'update_user',
            'session_token': self.session_token,
            'update_data': {'email': new_email}
        }

        response = self._send_request(request)
        return response['status'] == 'success'

    def update_password(self, current_password: str, new_password: str) -> bool:
        """Update password."""
        if not self.session_token:
            print("❌ Not logged in")
            return False

        request = {
            'action': 'update_user',
            'session_token': self.session_token,
            'update_data': {
                'current_password': current_password,
                'password': new_password
            }
        }

        response = self._send_request(request)
        return response['status'] == 'success'

    def update_profile(self, **fields) -> bool:
        """Update profile fields."""
        if not self.session_token:
            print("❌ Not logged in")
            return False

        request = {
            'action': 'update_user',
            'session_token': self.session_token,
            'update_data': fields
        }

        response = self._send_request(request)
        return response['status'] == 'success'

    def delete_account(self, password: str) -> bool:
        """Delete account (requires password confirmation)."""
        if not self.session_token:
            print("❌ Not logged in")
            return False

        request = {
            'action': 'delete_user',
            'session_token': self.session_token,
            'password': password
        }

        response = self._send_request(request)

        if response['status'] == 'success':
            self.session_token = None
            print("✅ Account deleted successfully")
            return True

        return False

    def list_users(self) -> Optional[list]:
        """List all users (limited info without admin rights)."""
        request = {
            'action': 'list_users',
            'session_token': self.session_token
        }

        response = self._send_request(request)

        if response['status'] == 'success':
            return response['users']

        return None

    def close(self):
        """Close the client connection."""
        if self.session_token:
            self.logout()

        self.socket.close()
        self.context.term()
        print("Client connection closed")


def main():
    """Demonstrate Secure Users Service operations."""
    print("=" * 70)
    print("Secure Users Service - Example Client")
    print("=" * 70)

    client = SecureUsersClient(port=5556)

    try:
        # 1. Create a new account
        print("\n1. CREATE NEW ACCOUNT")
        print("-" * 40)

        result = client.create_account(
            username="testuser",
            email="testuser@example.com",
            password="Test123!",
            full_name="Test User",
            phone="+1-555-0123",
            city="Test City",
            country="Test Country"
        )

        if result['status'] == 'success':
            print(f"✅ Account created: {result['username']}")
        else:
            print(f"⚠️ {result.get('message')}")

        time.sleep(1)

        # 2. Login with the new account
        print("\n2. LOGIN")
        print("-" * 40)

        if client.login("testuser", "Test123!"):
            print("✅ Login successful")

        time.sleep(1)

        # 3. Get profile information
        print("\n3. GET PROFILE")
        print("-" * 40)

        profile = client.get_profile()
        if profile:
            print("Profile Information:")
            print(f"  Username: {profile['username']}")
            print(f"  Email: {profile['email']}")
            print(f"  Full Name: {profile.get('full_name', 'N/A')}")
            print(f"  Role: {profile.get('role', 'user')}")
            print(f"  Status: {profile.get('status', 'unknown')}")

        time.sleep(1)

        # 4. Update username
        print("\n4. UPDATE USERNAME")
        print("-" * 40)

        if client.update_username("testuser_updated"):
            print("✅ Username updated successfully")

        time.sleep(1)

        # 5. Update email
        print("\n5. UPDATE EMAIL")
        print("-" * 40)

        if client.update_email("newemail@example.com"):
            print("✅ Email updated successfully")

        time.sleep(1)

        # 6. Update password
        print("\n6. UPDATE PASSWORD")
        print("-" * 40)

        if client.update_password("Test123!", "NewPass456!"):
            print("✅ Password updated successfully")

        time.sleep(1)

        # 7. Update profile fields
        print("\n7. UPDATE PROFILE")
        print("-" * 40)

        if client.update_profile(
                full_name="Updated Test User",
                phone="+1-555-9999",
                city="New City",
                notes="Account updated via API"
        ):
            print("✅ Profile updated successfully")

        time.sleep(1)

        # 8. Get updated profile
        print("\n8. GET UPDATED PROFILE")
        print("-" * 40)

        profile = client.get_profile()
        if profile:
            print("Updated Profile:")
            print(f"  Username: {profile['username']}")
            print(f"  Email: {profile['email']}")
            print(f"  Full Name: {profile.get('full_name', 'N/A')}")
            print(f"  Phone: {profile.get('phone', 'N/A')}")
            print(f"  City: {profile.get('city', 'N/A')}")

        time.sleep(1)

        # 9. List users
        print("\n9. LIST USERS")
        print("-" * 40)

        users = client.list_users()
        if users:
            print(f"Found {len(users)} user(s):")
            for user in users[:5]:  # Show first 5
                print(f"  - {user.get('username')} ({user.get('role', 'user')})")

        time.sleep(1)

        # 10. Logout
        print("\n10. LOGOUT")
        print("-" * 40)

        if client.logout():
            print("✅ Logged out")

        # 11. Try to access profile after logout (should fail)
        print("\n11. TRY ACCESS AFTER LOGOUT")
        print("-" * 40)

        profile = client.get_profile()
        if not profile:
            print("✅ Correctly denied access after logout")

        # 12. Login again with admin account
        print("\n12. LOGIN AS ADMIN")
        print("-" * 40)

        if client.login("admin", "admin123"):
            print("✅ Logged in as admin")

            # List users as admin (gets more info)
            users = client.list_users()
            if users and len(users) > 0:
                print(f"\nAdmin view - {len(users)} users:")
                for user in users[:3]:
                    print(f"  Username: {user['username']}")
                    print(f"    Email: {user.get('email', 'N/A')}")
                    print(f"    Status: {user.get('status', 'N/A')}")

        # Summary
        print("\n" + "=" * 70)
        print("DEMONSTRATION COMPLETED")
        print("=" * 70)
        print("\n✅ Demonstrated operations:")
        print("  • Account creation")
        print("  • Login/Logout")
        print("  • Get profile")
        print("  • Update username")
        print("  • Update email")
        print("  • Update password")
        print("  • Update profile fields")
        print("  • List users")
        print("  • Session management")
        print("  • Admin access")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

    finally:
        client.close()


if __name__ == "__main__":
    main()
