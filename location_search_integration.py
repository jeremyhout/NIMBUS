# weather_app/location_search_integration.py
"""
Integration endpoints for Location Search History microservice.
Add these routes to your app.
"""

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from location_search_client import get_location_search_client
from weather_app.users_client import get_users_client 


router = APIRouter(prefix="/api/location-search", tags=["location-search"])


class TrackLocationRequest(BaseModel):
    """Request to track a location selection."""
    location_id: str
    display_name: str
    lat: float
    lon: float


class SuggestionsQuery(BaseModel):
    """Request for location suggestions."""
    query: str
    limit: int = 4


def get_user_id_from_session(session_token: Optional[str]) -> Optional[str]:
    """
    Extract user_id from session token by querying the Users Service.
    """
    if not session_token:
        return None
    
    try:
        client = get_users_client()
        result = client.get_user(session_token)
        
        if result.get("status") == "success" and result.get("user"):
            return result["user"].get("username")
            
    # Handle general client exceptions raised by the UsersClient
    except Exception as e:
        # This will catch TimeoutError, RuntimeError, or any other issue 
        # talking to the ZMQ service.
        if "timeout" in str(e).lower():
            print("Warning: UUS timed out during session verification.")
        else:
            print(f"Error communicating with UUS: {e}")
        
    return None


@router.post("/track")
async def track_location(
    request: TrackLocationRequest,
    session_token: Optional[str] = Cookie(None)
):
    """
    Track a location selection for personalized suggestions.
    """
    user_id = get_user_id_from_session(session_token)
    
    if not user_id:
        return {
            "status": "skipped",
            "message": "Not authenticated - tracking skipped"
        }
    
    client = get_location_search_client()
    
    result = client.track_search(
        user_id=user_id,
        location_id=request.location_id,
        display_name=request.display_name,
        lat=request.lat,
        lon=request.lon
    )
    
    return result


@router.post("/suggestions")
async def get_suggestions(
    request: SuggestionsQuery,
    session_token: Optional[str] = Cookie(None)
):
    """
    Get personalized location suggestions as user types.
    """
    if len(request.query) < 3:
        raise HTTPException(
            status_code=400,
            detail="Query must be at least 3 characters"
        )
    
    user_id = get_user_id_from_session(session_token)
    
    if not user_id:
        return {
            "status": "success",
            "suggestions": [],
            "message": "Login for personalized suggestions"
        }
    
    client = get_location_search_client()
    
    suggestions = client.get_suggestions(
        user_id=user_id,
        query=request.query,
        limit=request.limit
    )
    
    return {
        "status": "success",
        "suggestions": suggestions,
        "count": len(suggestions)
    }


@router.get("/history")
async def get_my_history(session_token: Optional[str] = Cookie(None)):
    """Get the current user's search history."""
    user_id = get_user_id_from_session(session_token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    client = get_location_search_client()
    history = client.get_user_history(user_id)
    
    return {
        "status": "success",
        "history": history,
        "count": len(history)
    }


@router.delete("/history")
async def clear_my_history(session_token: Optional[str] = Cookie(None)):
    """Clear the current user's search history."""
    user_id = get_user_id_from_session(session_token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    client = get_location_search_client()
    success = client.clear_user_history(user_id)
    
    if success:
        return {"status": "success", "message": "Search history cleared"}
    else:
        return {"status": "success", "message": "No history to clear"}


@router.get("/health")
async def check_service_health():
    """Check if the Location Search service is available."""
    client = get_location_search_client()
    is_healthy = client.health_check()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "Location Search History",
        "available": is_healthy
    }