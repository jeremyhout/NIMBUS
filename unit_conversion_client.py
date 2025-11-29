"""
Unit Conversion Microservice Client
A simple HTTP client for calling the Unit Conversion microservice.

Usage:
    from unit_conversion_client import get_conversion_client
    
    client = get_conversion_client()
    result = client.convert(32, 'fahrenheit', 'celsius')
    # Returns: 0.0
"""

import httpx
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class UnitConversionClient:
    """Client for the Unit Conversion microservice."""
    
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:6001",
        timeout: float = 2.0
    ):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the conversion service
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def convert(self, value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """
        Convert a value from one unit to another.
        
        Args:
            value: Value to convert
            from_unit: Source unit (e.g., 'celsius', 'miles')
            to_unit: Target unit (e.g., 'fahrenheit', 'kilometers')
        
        Returns:
            Converted value, or None if service is unavailable
        """
        try:
            url = f"{self.base_url}/convert"
            params = {
                "value": value,
                "from": from_unit,
                "to": to_unit
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get('result')
        
        except httpx.TimeoutException:
            logger.warning(f"Conversion service timeout for {value} {from_unit} -> {to_unit}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"Conversion service HTTP error {e.response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"Conversion service error: {e}")
            return None
    
    def batch_convert(self, values: List[float], from_unit: str, to_unit: str) -> Optional[List[float]]:
        """
        Convert multiple values at once.
        
        Args:
            values: List of values to convert
            from_unit: Source unit
            to_unit: Target unit
        
        Returns:
            List of converted values, or None if service is unavailable
        """
        try:
            url = f"{self.base_url}/batch-convert"
            params = {
                "values": ",".join(str(v) for v in values),
                "from": from_unit,
                "to": to_unit
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                conversions = data.get('conversions', [])
                return [c['result'] for c in conversions]
        
        except Exception as e:
            logger.warning(f"Batch conversion service error: {e}")
            return None
    
    def get_supported_units(self) -> Optional[Dict[str, Any]]:
        """
        Get all supported units organized by category.
        
        Returns:
            Dictionary of categories and units, or None if unavailable
        """
        try:
            url = f"{self.base_url}/units"
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except:
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
_conversion_client: Optional[UnitConversionClient] = None


def get_conversion_client(base_url: str = "http://127.0.0.1:6001") -> UnitConversionClient:
    """Get or create the unit conversion client singleton."""
    global _conversion_client
    if _conversion_client is None:
        _conversion_client = UnitConversionClient(base_url=base_url)
    return _conversion_client