"""
Authentication endpoints for the weather app.
Add these to your app.py or import them.

Place this in: weather_app/auth.py
"""

from fastapi import APIRouter, HTTPException, Cookie, Response
from pydantic import BaseModel
from typing import Optional
from .users_client import get_users_client


router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = ""


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class UpdateProfileRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdatePreferencesRequest(BaseModel):
    """Update user preferences (favorites, settings)."""
    favorites: Optional[list] = None
    settings: Optional[dict] = None


@router.post("/register")
async def register(req: RegisterRequest):
    """Register a new user."""
    client = get_users_client()
    
    try:
        result = client.create_user(
            username=req.username,
            email=req.email,
            password=req.password,
            full_name=req.full_name
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return {"status": "success", "message": "Account created successfully"}
    
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=f"User service error: {str(e)}")


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    """Login and receive session token."""
    client = get_users_client()
    
    try:
        result = client.login(
            username_or_email=req.username_or_email,
            password=req.password
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=401, detail=result["message"])
        
        # Set session token as HTTP-only cookie for security
        session_token = result["session_token"]
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=86400,  # 24 hours
            samesite="lax"
        )
        
        return {
            "status": "success",
            "user": result["user"],
            "session_token": session_token  # Also return for client-side storage if needed
        }
    
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=f"User service error: {str(e)}")


@router.post("/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Logout current user."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    client = get_users_client()
    
    try:
        result = client.logout(session_token)
        
        # Clear the cookie
        response.delete_cookie(key="session_token")
        
        return {"status": "success", "message": "Logged out successfully"}
    
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=f"User service error: {str(e)}")


@router.get("/me")
async def get_current_user(session_token: Optional[str] = Cookie(None)):
    """Get current logged-in user profile."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    client = get_users_client()
    
    try:
        result = client.get_user(session_token)
        
        if result["status"] == "error":
            raise HTTPException(status_code=401, detail=result["message"])
        
        return {"status": "success", "user": result["user"]}
    
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=f"User service error: {str(e)}")


@router.put("/profile")
async def update_profile(
    req: UpdateProfileRequest,
    session_token: Optional[str] = Cookie(None)
):
    """Update user profile information."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    client = get_users_client()
    
    # Build update data from non-None fields
    update_data = {}
    if req.email is not None:
        update_data["email"] = req.email
    if req.full_name is not None:
        update_data["full_name"] = req.full_name
    if req.phone is not None:
        update_data["phone"] = req.phone
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    try:
        result = client.update_user(session_token, update_data)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return {"status": "success", "user": result["user"]}
    
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=f"User service error: {str(e)}")


@router.put("/password")
async def update_password(
    req: UpdatePasswordRequest,
    session_token: Optional[str] = Cookie(None)
):
    """Update user password."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    client = get_users_client()
    
    try:
        result = client.update_password(
            session_token,
            req.current_password,
            req.new_password
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return {"status": "success", "message": "Password updated successfully"}
    
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=f"User service error: {str(e)}")


@router.put("/preferences")
async def update_preferences(
    req: UpdatePreferencesRequest,
    session_token: Optional[str] = Cookie(None)
):
    """
    Update user preferences (favorites and settings).
    This stores data in the user's metadata field.
    """
    if not session_token:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    client = get_users_client()
    
    # First, get current user to retrieve existing metadata
    try:
        user_result = client.get_user(session_token)
        if user_result["status"] == "error":
            raise HTTPException(status_code=401, detail=user_result["message"])
        
        # Get existing metadata or create new
        metadata = user_result["user"].get("metadata", {})
        
        # Update only provided fields
        if req.favorites is not None:
            metadata["favorites"] = req.favorites
        if req.settings is not None:
            metadata["settings"] = req.settings
        
        # Save back to user
        result = client.update_user(session_token, {"metadata": metadata})
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])
        
        return {"status": "success", "metadata": metadata}
    
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=f"User service error: {str(e)}")


@router.get("/preferences")
async def get_preferences(session_token: Optional[str] = Cookie(None)):
    """Get user preferences (favorites and settings)."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    client = get_users_client()
    
    try:
        result = client.get_user(session_token)
        
        if result["status"] == "error":
            raise HTTPException(status_code=401, detail=result["message"])
        
        metadata = result["user"].get("metadata", {})
        
        return {
            "status": "success",
            "favorites": metadata.get("favorites", []),
            "settings": metadata.get("settings", {})
        }
    
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=f"User service error: {str(e)}")