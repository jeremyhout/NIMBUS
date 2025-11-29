"""
Timezone Microservice
A simple HTTP-based microservice that provides timezone information from coordinates.

Usage:
    python timezone_service.py [port]
    
Default port: 5555

Endpoints:
    GET /timezone?lat=X&lon=Y  - Get timezone info from coordinates
    GET /healthz               - Health check
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import sys
import logging
from typing import Optional
from datetime import datetime
from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Timezone Microservice", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy load timezonefinder (only import when needed)
_tf = None

def get_timezone_finder():
    """Lazy load TimezoneFinder to speed up startup."""
    global _tf
    if _tf is None:
        try:
            from timezonefinder import TimezoneFinder
            _tf = TimezoneFinder()
            logger.info("TimezoneFinder initialized")
        except ImportError:
            logger.error("timezonefinder not installed. Run: pip install timezonefinder")
            raise
    return _tf


def get_timezone_abbreviation(timezone_name: str) -> str:
    """
    Get timezone abbreviation (e.g., 'EST', 'PST') from timezone name.
    Returns the current abbreviation based on whether DST is active.
    """
    try:
        tz = ZoneInfo(timezone_name)
        # Get current time in that timezone
        now = datetime.now(tz)
        # Get the abbreviation (e.g., 'EST' or 'EDT')
        abbr = now.strftime('%Z')
        return abbr
    except Exception as e:
        logger.warning(f"Could not get abbreviation for {timezone_name}: {e}")
        # Fallback: extract last part of timezone name
        return timezone_name.split('/')[-1]


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Timezone Microservice",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/timezone")
async def get_timezone(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
):
    """
    Get timezone information from coordinates.
    
    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)
    
    Returns:
        {
            "timezone": "America/New_York",
            "abbreviation": "EST",
            "lat": 40.7128,
            "lon": -74.0060
        }
    """
    try:
        tf = get_timezone_finder()
        
        # Get timezone name from coordinates
        timezone_name = tf.timezone_at(lat=lat, lng=lon)
        
        if not timezone_name:
            raise HTTPException(
                status_code=404,
                detail=f"Could not determine timezone for coordinates: {lat}, {lon}"
            )
        
        # Get abbreviation
        abbreviation = get_timezone_abbreviation(timezone_name)
        
        logger.info(f"Timezone lookup: ({lat}, {lon}) -> {timezone_name} ({abbreviation})")
        
        return {
            "timezone": timezone_name,
            "abbreviation": abbreviation,
            "lat": lat,
            "lon": lon
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in timezone lookup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Timezone lookup failed: {str(e)}"
        )


def main():
    """Main entry point."""
    import uvicorn
    
    port = 5555
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    
    logger.info(f"Starting Timezone Microservice on port {port}")
    logger.info("Make sure timezonefinder is installed: pip install timezonefinder")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()