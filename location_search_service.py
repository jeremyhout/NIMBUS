"""
Location Search History Microservice
A FastAPI-based microservice that provides personalized location search suggestions.

Features:
- Track location searches per user
- Rank suggestions by frequency and recency
- Sub-1-second response time
- Works standalone or integrated with any app

Usage:
    python location_search_service.py [port]
    
Default port: 6000
"""

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json
import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------- Config ---------------------------------

APP_KEY = "dev-key"  # Shared secret for authentication
ALLOWED_ORIGINS = [
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://127.0.0.1:8081",
    "http://localhost:8081"
]
STORAGE_FILE = "location_search_history.json"
MAX_HISTORY_PER_USER = 50  # Prevent unbounded growth
DEFAULT_LIMIT = 4

# Ranking weights (simple explainable model)
RECENCY_WEIGHT = 0.4
FREQUENCY_WEIGHT = 0.6

# ---------------------------- Data Models -----------------------------

class LocationData(BaseModel):
    """Location information for tracking."""
    location_id: str = Field(..., min_length=1, description="Unique location identifier")
    display_name: str = Field(..., min_length=1, description="Human-readable location name")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    
    @field_validator('location_id', 'display_name')
    @classmethod
    def strip_whitespace(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class TrackSearchRequest(BaseModel):
    """Request to track a location search."""
    user_id: str = Field(..., min_length=1, description="User identifier")
    location: LocationData


class SuggestionsRequest(BaseModel):
    """Request for location suggestions."""
    user_id: str = Field(..., min_length=1, description="User identifier")
    query: str = Field(..., min_length=3, description="Search query (min 3 chars)")
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=10, description="Max suggestions")
    
    @field_validator('query')
    @classmethod
    def strip_query(cls, v):
        return v.strip()


class LocationSuggestion(BaseModel):
    """A location suggestion with ranking info."""
    location_id: str
    display_name: str
    lat: float
    lon: float
    source: str  # "frequent", "recent", or "standard"
    rank_score: float
    search_count: int
    last_searched: str


# ---------------------------- Storage Layer ---------------------------

class SearchHistoryStore:
    """Simple JSON file storage for search history."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = self._load()
    
    def _load(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load search history from disk."""
        if not os.path.exists(self.filepath):
            logger.info(f"Creating new storage file: {self.filepath}")
            return {}
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded search history for {len(data)} users")
            return data
        except Exception as e:
            logger.error(f"Error loading storage: {e}")
            return {}
    
    def _save(self):
        """Save search history to disk."""
        try:
            # Atomic write
            temp_file = f"{self.filepath}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            os.replace(temp_file, self.filepath)
            logger.debug(f"Saved search history for {len(self.data)} users")
        except Exception as e:
            logger.error(f"Error saving storage: {e}")
            raise
    
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get search history for a user."""
        return self.data.get(user_id, [])
    
    def track_search(self, user_id: str, location: LocationData) -> Dict[str, Any]:
        """Track a location search for a user."""
        if user_id not in self.data:
            self.data[user_id] = []
        
        history = self.data[user_id]
        now = datetime.now().isoformat()
        
        # Find existing entry
        existing = None
        for entry in history:
            if entry.get('location_id') == location.location_id:
                existing = entry
                break
        
        if existing:
            # Update existing entry
            existing['search_count'] = existing.get('search_count', 0) + 1
            existing['last_searched'] = now
            existing['display_name'] = location.display_name
            existing['lat'] = location.lat
            existing['lon'] = location.lon
        else:
            # Create new entry
            history.append({
                'location_id': location.location_id,
                'display_name': location.display_name,
                'lat': location.lat,
                'lon': location.lon,
                'search_count': 1,
                'first_searched': now,
                'last_searched': now
            })
        
        # Keep only most recent entries (sorted by last_searched)
        self.data[user_id] = sorted(
            history,
            key=lambda x: x.get('last_searched', ''),
            reverse=True
        )[:MAX_HISTORY_PER_USER]
        
        self._save()
        
        return {
            'status': 'success',
            'message': 'Search tracked',
            'search_count': existing['search_count'] if existing else 1
        }
    
    def clear_user_history(self, user_id: str) -> bool:
        """Clear all search history for a user."""
        if user_id in self.data:
            del self.data[user_id]
            self._save()
            return True
        return False


# ---------------------------- Service Logic ---------------------------

class LocationSearchService:
    """Core service logic for location search suggestions."""
    
    def __init__(self, store: SearchHistoryStore):
        self.store = store
    
    def calculate_rank_score(self, entry: Dict[str, Any]) -> float:
        """
        Calculate ranking score for a search history entry.
        
        Simple explainable model:
        - Frequency score: normalized search count
        - Recency score: 1 / (days since last search + 1)
        - Combined: 60% frequency + 40% recency
        """
        search_count = entry.get('search_count', 0)
        last_searched_str = entry.get('last_searched', '')
        
        # Recency score (decays over time)
        try:
            last_searched = datetime.fromisoformat(last_searched_str)
            now = datetime.now()
            days_ago = (now - last_searched).days
            recency_score = 1.0 / (days_ago + 1)
        except:
            recency_score = 0.0
        
        # Frequency score (we'll normalize this relative to all entries)
        frequency_score = search_count
        
        # Combined score
        return (FREQUENCY_WEIGHT * frequency_score) + (RECENCY_WEIGHT * recency_score)
    
    def get_suggestions(
        self,
        user_id: str,
        query: str,
        limit: int = DEFAULT_LIMIT
    ) -> List[LocationSuggestion]:
        """
        Get personalized location suggestions for a user.
        
        Returns locations matching the query, ranked by:
        1. Frequently searched (search_count > 2)
        2. Recently searched (within last 7 days)
        3. Other matches
        """
        history = self.store.get_user_history(user_id)
        query_lower = query.lower()
        
        suggestions = []
        
        # Find matches
        for entry in history:
            display_name = entry.get('display_name', '')
            if query_lower in display_name.lower():
                # Calculate rank score
                rank_score = self.calculate_rank_score(entry)
                
                # Determine source category
                search_count = entry.get('search_count', 0)
                last_searched_str = entry.get('last_searched', '')
                
                try:
                    last_searched = datetime.fromisoformat(last_searched_str)
                    days_ago = (datetime.now() - last_searched).days
                    
                    if search_count > 2:
                        source = 'frequent'
                    elif days_ago <= 7:
                        source = 'recent'
                    else:
                        source = 'standard'
                except:
                    source = 'standard'
                
                suggestions.append(LocationSuggestion(
                    location_id=entry.get('location_id', ''),
                    display_name=display_name,
                    lat=entry.get('lat', 0.0),
                    lon=entry.get('lon', 0.0),
                    source=source,
                    rank_score=rank_score,
                    search_count=search_count,
                    last_searched=last_searched_str
                ))
        
        # Sort by rank score (descending)
        suggestions.sort(key=lambda x: x.rank_score, reverse=True)
        
        # Return top N
        return suggestions[:limit]


# ---------------------------- FastAPI App -----------------------------

# Initialize storage and service
store = SearchHistoryStore(STORAGE_FILE)
service = LocationSearchService(store)

app = FastAPI(
    title="Location Search History Service",
    description="Personalized location search suggestions microservice",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------- Authentication --------------------------

def verify_api_key(x_app_key: Optional[str] = Header(None)) -> bool:
    """Verify the API key from request header."""
    if x_app_key != APP_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-App-Key header"
        )
    return True


# ---------------------------- Endpoints -------------------------------

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Location Search History Service",
        "timestamp": datetime.now().isoformat(),
        "storage": os.path.abspath(STORAGE_FILE),
        "total_users": len(store.data)
    }


@app.post("/track")
async def track_search(
    request: TrackSearchRequest,
    x_app_key: Optional[str] = Header(None)
):
    """
    Track a location search for a user.
    
    This endpoint should be called when a user selects a location
    from search results to improve future suggestions.
    """
    verify_api_key(x_app_key)
    
    try:
        result = store.track_search(request.user_id, request.location)
        return result
    except Exception as e:
        logger.error(f"Error tracking search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/suggestions")
async def get_suggestions(
    request: SuggestionsRequest,
    x_app_key: Optional[str] = Header(None)
):
    """
    Get personalized location suggestions for a user.
    
    Returns locations matching the query, ranked by frequency and recency.
    Suggestions should appear within 1 second for typical queries.
    """
    verify_api_key(x_app_key)
    
    start_time = datetime.now()
    
    try:
        suggestions = service.get_suggestions(
            request.user_id,
            request.query,
            request.limit
        )
        
        # Calculate query time
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "status": "success",
            "query": request.query,
            "suggestions": [s.dict() for s in suggestions],
            "count": len(suggestions),
            "query_time_ms": round(elapsed_ms, 2)
        }
    
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{user_id}")
async def get_user_history(
    user_id: str,
    x_app_key: Optional[str] = Header(None)
):
    """Get all search history for a user."""
    verify_api_key(x_app_key)
    
    history = store.get_user_history(user_id)
    
    return {
        "status": "success",
        "user_id": user_id,
        "history": history,
        "count": len(history)
    }


@app.delete("/history/{user_id}")
async def clear_user_history(
    user_id: str,
    x_app_key: Optional[str] = Header(None)
):
    """Clear all search history for a user."""
    verify_api_key(x_app_key)
    
    success = store.clear_user_history(user_id)
    
    if success:
        return {
            "status": "success",
            "message": f"Cleared search history for user {user_id}"
        }
    else:
        return {
            "status": "success",
            "message": f"No history found for user {user_id}"
        }


@app.get("/stats")
async def get_stats(x_app_key: Optional[str] = Header(None)):
    """Get service statistics."""
    verify_api_key(x_app_key)
    
    total_users = len(store.data)
    total_searches = sum(
        sum(entry.get('search_count', 0) for entry in history)
        for history in store.data.values()
    )
    
    return {
        "status": "success",
        "total_users": total_users,
        "total_searches": total_searches,
        "avg_searches_per_user": round(total_searches / total_users, 2) if total_users > 0 else 0
    }


# ---------------------------- Main Entry ------------------------------

if __name__ == "__main__":
    import uvicorn
    
    port = 6000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    
    logger.info(f"Starting Location Search History Service on port {port}")
    logger.info(f"Storage file: {os.path.abspath(STORAGE_FILE)}")
    logger.info(f"API Key required: {APP_KEY}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")