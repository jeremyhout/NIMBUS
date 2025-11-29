"""
Timezone Microservice Client
A simple HTTP client for calling the Timezone microservice.

Usage:
    from timezone_client import get_timezone_client
    
    client = get_timezone_client()
    result = client.get_timezone(lat=40.7128, lon=-74.0060)
    # Returns: {"timezone": "America/New_York", "abbreviation": "EST", ...}
"""

import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TimezoneClient:
    """Client for the Timezone microservice."""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5555",
        timeout: float = 2.0
    ):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the timezone service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def get_timezone(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Get timezone information from coordinates.
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            {
                "timezone": "America/New_York",
                "abbreviation": "EST",
                "lat": 40.7128,
                "lon": -74.0060
            }
            or None if the service is unavailable
        """
        try:
            url = f"{self.base_url}/timezone"
            params = {"lat": lat, "lon": lon}
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        
        except httpx.TimeoutException:
            logger.warning(f"Timezone service timeout for ({lat}, {lon})")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"Timezone service HTTP error {e.response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Timezone service error: {e}")
            return None
    
    def health_check(self) -> bool:
        """
        Check if the service is healthy.
        
        Returns:
            True if service is responding
        """
        try:
            url = f"{self.base_url}/healthz"
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                return response.status_code == 200
        except:
            return False


# Singleton instance
_timezone_client: Optional[TimezoneClient] = None


def get_timezone_client(base_url: str = "http://127.0.0.1:5555") -> TimezoneClient:
    """Get or create the timezone client singleton."""
    global _timezone_client
    if _timezone_client is None:
        _timezone_client = TimezoneClient(base_url=base_url)
    return _timezone_client