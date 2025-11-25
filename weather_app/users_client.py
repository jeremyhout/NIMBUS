"""
ZMQ Client for the Secure Users Service
Place this in: weather_app/users_client.py
"""

import zmq
import json
from typing import Dict, Any, Optional


class UsersClient:
    """Client for communicating with the Secure Users Service."""
    
    def __init__(self, port: int = 5556, host: str = "localhost"):
        """Initialize connection to the users service."""
        self.context = zmq.Context()
        self.socket = None
        self.address = f"tcp://{host}:{port}"
        self._connect()
    
    def _connect(self):
        """Establish connection to the service."""
        if self.socket:
            self.socket.close()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        self.socket.connect(self.address)
    
    def _send_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request and receive response."""
        try:
            request_json = json.dumps(request_data)
            self.socket.send_string(request_json)
            response_json = self.socket.recv_string()
            return json.loads(response_json)
        except zmq.error.Again:
            # Timeout - reconnect and raise
            self._connect()
            raise TimeoutError("Request to users service timed out")
        except Exception as e:
            # On any socket error, try to reconnect
            self._connect()
            raise RuntimeError(f"Users service communication error: {e}")
    
    def create_user(self, username: str, email: str, password: str, 
                    full_name: str = "") -> Dict[str, Any]:
        """
        Create a new user account.
        
        Returns:
            {"status": "success", "username": "...", "email": "..."}
            or {"status": "error", "message": "..."}
        """
        request = {
            "action": "create_user",
            "user_data": {
                "username": username,
                "email": email,
                "password": password,
                "full_name": full_name
            }
        }
        return self._send_request(request)
    
    def login(self, username_or_email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user.
        
        Returns:
            {"status": "success", "session_token": "...", "user": {...}}
            or {"status": "error", "message": "..."}
        """
        request = {
            "action": "login",
            "credentials": {
                "username": username_or_email,
                "password": password
            }
        }
        return self._send_request(request)
    
    def logout(self, session_token: str) -> Dict[str, Any]:
        """Logout a user session."""
        request = {
            "action": "logout",
            "session_token": session_token
        }
        return self._send_request(request)
    
    def get_user(self, session_token: str) -> Dict[str, Any]:
        """
        Get user profile.
        
        Returns:
            {"status": "success", "user": {...}}
            or {"status": "error", "message": "..."}
        """
        request = {
            "action": "get_user",
            "session_token": session_token
        }
        return self._send_request(request)
    
    def update_user(self, session_token: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user information.
        
        update_data can include:
        - email, full_name, phone, etc.
        - metadata: dict with favorites, settings, etc.
        
        Returns:
            {"status": "success", "user": {...}}
            or {"status": "error", "message": "..."}
        """
        request = {
            "action": "update_user",
            "session_token": session_token,
            "update_data": update_data
        }
        return self._send_request(request)
    
    def update_password(self, session_token: str, current_password: str, 
                       new_password: str) -> Dict[str, Any]:
        """Update user password."""
        request = {
            "action": "update_user",
            "session_token": session_token,
            "update_data": {
                "current_password": current_password,
                "password": new_password
            }
        }
        return self._send_request(request)
    
    def delete_user(self, session_token: str, password: str) -> Dict[str, Any]:
        """Delete user account (requires password confirmation)."""
        request = {
            "action": "delete_user",
            "session_token": session_token,
            "password": password
        }
        return self._send_request(request)
    
    def close(self):
        """Close the connection."""
        if self.socket:
            self.socket.close()
        self.context.term()


# Singleton instance
_users_client: Optional[UsersClient] = None

def get_users_client() -> UsersClient:
    """Get or create the users client singleton."""
    global _users_client
    if _users_client is None:
        _users_client = UsersClient()
    return _users_client