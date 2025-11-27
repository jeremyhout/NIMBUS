"""
Location Search Service Client
A simple HTTP client for integrating the Location Search History microservice.

Usage:
    from location_search_client import LocationSearchClient
    
    client = LocationSearchClient()
    
    # Track a search
    client.track_search(
        user_id="user123",
        location_id="longbeach_ca_usa",
        display_name="Long Beach, CA, USA",
        lat=33.7701,
        lon=-118.1937
    )
    
    # Get suggestions
    suggestions = client.get_suggestions(
        user_id="user123",
        query="long"
    )
"""

import httpx
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LocationSearchClient:
    """Client for the Location Search History microservice."""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:6000",
        api_key: str = "dev-key",
        timeout: float = 2.0
    ):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the location search service
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the service."""
        url = f"{self.base_url}{endpoint}"
        headers = {"X-App-Key": self.api_key}
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method == "GET":
                    response = client.get(url, headers=headers)
                elif method == "POST":
                    response = client.post(url, headers=headers, json=json_data)
                elif method == "DELETE":
                    response = client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                return response.json()
        
        except httpx.TimeoutException:
            logger.error(f"Request timeout: {url}")
            return {"status": "error", "message": "Request timeout"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {url}")
            return {"status": "error", "message": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"status": "error", "message": str(e)}
    
    def track_search(
        self,
        user_id: str,
        location_id: str,
        display_name: str,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """
        Track a location search for a user.
        
        Args:
            user_id: User identifier
            location_id: Unique location identifier (e.g., "longbeach_ca_usa")
            display_name: Human-readable name (e.g., "Long Beach, CA, USA")
            lat: Latitude
            lon: Longitude
        
        Returns:
            {"status": "success", "message": "...", "search_count": 5}
            or {"status": "error", "message": "..."}
        """
        data = {
            "user_id": user_id,
            "location": {
                "location_id": location_id,
                "display_name": display_name,
                "lat": lat,
                "lon": lon
            }
        }
        
        return self._make_request("POST", "/track", json_data=data)
    
    def get_suggestions(
        self,
        user_id: str,
        query: str,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Get personalized location suggestions for a user.
        
        Args:
            user_id: User identifier
            query: Search query (min 3 characters)
            limit: Maximum number of suggestions (1-10)
        
        Returns:
            List of suggestions:
            [
                {
                    "location_id": "...",
                    "display_name": "...",
                    "lat": ...,
                    "lon": ...,
                    "source": "frequent" | "recent" | "standard",
                    "rank_score": ...,
                    "search_count": ...,
                    "last_searched": "..."
                },
                ...
            ]
        """
        data = {
            "user_id": user_id,
            "query": query,
            "limit": limit
        }
        
        result = self._make_request("POST", "/suggestions", json_data=data)
        
        if result.get("status") == "success":
            return result.get("suggestions", [])
        else:
            logger.warning(f"Failed to get suggestions: {result.get('message')}")
            return []
    
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all search history for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of search history entries
        """
        result = self._make_request("GET", f"/history/{user_id}")
        
        if result.get("status") == "success":
            return result.get("history", [])
        else:
            return []
    
    def clear_user_history(self, user_id: str) -> bool:
        """
        Clear all search history for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            True if successful
        """
        result = self._make_request("DELETE", f"/history/{user_id}")
        return result.get("status") == "success"
    
    def health_check(self) -> bool:
        """
        Check if the service is healthy.
        
        Returns:
            True if service is responding
        """
        try:
            result = self._make_request("GET", "/healthz")
            return result.get("status") == "healthy"
        except:
            return False


# Singleton instance
_client: Optional[LocationSearchClient] = None


def get_location_search_client(
    base_url: str = "http://127.0.0.1:6000",
    api_key: str = "dev-key"
) -> LocationSearchClient:
    """Get or create the location search client singleton."""
    global _client
    if _client is None:
        _client = LocationSearchClient(base_url=base_url, api_key=api_key)
    return _client