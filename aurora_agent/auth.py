"""
Google OAuth 2.0 authentication module for Aurora Agent.
Handles teacher authentication and token management.
"""
import os
import json
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .database import get_db, UserToken

# OAuth 2.0 Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/google/callback")

# Required scopes for Google Drive, Sheets, and Apps Script
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive', 
    'https://www.googleapis.com/auth/script.projects',
    'https://www.googleapis.com/auth/script.scriptapp',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'  # Google is adding this automatically
]

class GoogleOAuthManager:
    """Manages Google OAuth 2.0 flow for teacher authentication."""
    
    def __init__(self):
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables")
        
        self.client_config = {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        }
    
    def create_authorization_url(self, state: str) -> str:
        """
        Create Google OAuth authorization URL.
        
        Args:
            state: Random state parameter for security
            
        Returns:
            Authorization URL for redirecting user
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent screen to get refresh token
        )
        
        return auth_url
    
    def exchange_code_for_tokens(self, authorization_code: str, state: str) -> dict:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Code received from Google
            state: State parameter for verification
            
        Returns:
            Dictionary containing token information
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
            state=state
        )
        
        flow.fetch_token(code=authorization_code)
        
        credentials = flow.credentials
        
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_expiry': credentials.expiry,
            'scopes': credentials.scopes
        }
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Stored refresh token
            
        Returns:
            Dictionary with new token information
        """
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=self.client_config["web"]["token_uri"],
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )
        
        credentials.refresh(GoogleRequest())
        
        return {
            'access_token': credentials.token,
            'token_expiry': credentials.expiry
        }

# Global OAuth manager instance
oauth_manager = GoogleOAuthManager()

async def store_user_tokens(
    db: AsyncSession,
    user_id: str,
    token_data: dict
) -> None:
    """
    Store or update user tokens in database.
    
    Args:
        db: Database session
        user_id: User identifier
        token_data: Token information from OAuth flow
    """
    # Check if user already exists
    result = await db.execute(select(UserToken).where(UserToken.user_id == user_id))
    existing_token = result.scalar_one_or_none()
    
    if existing_token:
        # Update existing tokens
        await db.execute(
            update(UserToken)
            .where(UserToken.user_id == user_id)
            .values(
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token', existing_token.refresh_token),
                token_expiry=token_data.get('token_expiry'),
                scopes=json.dumps(token_data.get('scopes', [])),
                updated_at=datetime.utcnow()
            )
        )
    else:
        # Create new token record
        new_token = UserToken(
            user_id=user_id,
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            token_expiry=token_data.get('token_expiry'),
            scopes=json.dumps(token_data.get('scopes', []))
        )
        db.add(new_token)
    
    await db.commit()

async def get_user_tokens(
    db: AsyncSession,
    user_id: str
) -> Optional[UserToken]:
    """
    Retrieve user tokens from database.
    
    Args:
        db: Database session
        user_id: User identifier
        
    Returns:
        UserToken object or None if not found
    """
    result = await db.execute(select(UserToken).where(UserToken.user_id == user_id))
    return result.scalar_one_or_none()

async def get_valid_access_token(
    db: AsyncSession,
    user_id: str
) -> Optional[str]:
    """
    Get a valid access token for user, refreshing if necessary.
    
    Args:
        db: Database session
        user_id: User identifier
        
    Returns:
        Valid access token or None if user not authenticated
    """
    user_token = await get_user_tokens(db, user_id)
    if not user_token:
        return None
    
    # Check if token is expired
    if user_token.token_expiry and user_token.token_expiry <= datetime.utcnow():
        try:
            # Refresh the token
            new_token_data = oauth_manager.refresh_access_token(user_token.refresh_token)
            
            # Update database with new token
            await store_user_tokens(db, user_id, {
                'access_token': new_token_data['access_token'],
                'token_expiry': new_token_data['token_expiry']
            })
            
            return new_token_data['access_token']
        except Exception as e:
            # Refresh failed, user needs to re-authenticate
            return None
    
    return user_token.access_token
