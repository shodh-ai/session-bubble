# aurora_agent/app_simple.py
# Simplified FastAPI app for UAT testing of the verification system

import logging
import asyncio
import os
import json
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Core FastAPI imports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import logging
import asyncio
from typing import Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine('sqlite:///database.db')

# Create configured "Session" class
Session = sessionmaker(bind=engine)

# Create FastAPI app
app = FastAPI(title="Aurora Agent - Verification System", version="1.0.0")

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Import our session core
from session_core import get_or_create_session, cleanup_session

# Pydantic models
class VerificationSessionRequest(BaseModel):
    user_id: str
    spreadsheet_url: str

# Root route
@app.get("/")
async def root():
    """Serve the live log frontend."""
    return HTMLResponse("""
    <html>
        <body>
            <h1>🎯 Aurora Agent - UAT Testing</h1>
            <p>Verification System Ready for Testing</p>
            <ul>
                <li><a href="/static/live-log.html">Live Log UI (Phase 3)</a></li>
                <li><a href="/static/verification.html">Basic Verification UI</a></li>
            </ul>
        </body>
    </html>
    """)

# ============================================================================
# VERIFICATION SESSION ENDPOINTS (Playwright + VLM + API)
# ============================================================================

@app.post("/verification/start")
async def start_verification_session(request: VerificationSessionRequest):
    """
    Start a new verification session using Playwright + VLM + API approach.
    
    This replaces the complex Apps Script method with a simpler, more reliable approach:
    1. Capture all user interactions with Playwright
    2. Translate raw events to meaningful actions with VLM
    3. Verify actions with Google Sheets API
    4. Present verified actions in real-time via WebSocket
    """
    try:
        logger.info(f"Starting verification session for user {request.user_id}")
        
        # Note: Session will be created when WebSocket connects
        # This endpoint just validates the request and returns success
        
        return {
            "success": True,
            "message": "Verification session ready. Connect via WebSocket to begin.",
            "user_id": request.user_id,
            "spreadsheet_url": request.spreadsheet_url
        }
        
    except Exception as e:
        logger.error(f"Error starting verification session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/session/{user_id}")
async def verification_websocket(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time verification session communication.
    
    Handles:
    - Session start/stop commands
    - Real-time interaction capture and verification
    - Status updates and verified action delivery
    """
    await websocket.accept()
    session = None
    
    try:
        logger.info(f"WebSocket connected for verification session: {user_id}")
        
        # Get or create session
        session = await get_or_create_session(user_id, websocket)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Verification session WebSocket connected",
            "user_id": user_id
        })
        
        # Listen for commands
        while True:
            try:
                data = await websocket.receive_json()
                logger.info(f"🔍 DEBUG: Received WebSocket message: {data}")
                # Accept both 'command' and 'type' for backwards compatibility
                command = data.get("command") or data.get("type")
                logger.info(f"🔍 DEBUG: Extracted command: {command}")
                
                if command == "START_SESSION":
                    spreadsheet_url = data.get("spreadsheet_url")
                    if not spreadsheet_url:
                        await websocket.send_json({
                            "type": "ERROR",
                            "message": "Missing spreadsheet_url"
                        })
                        continue
                    
                    result = await session.start_session(spreadsheet_url)
                    await websocket.send_json({
                        "type": "SESSION_START_RESULT",
                        "result": result
                    })
                    
                elif command == "STOP_SESSION":
                    await session.stop_session()
                    await websocket.send_json({
                        "type": "SESSION_STOPPED",
                        "message": "Verification session stopped"
                    })
                    
                elif command == "GET_STATUS":
                    status = await session.get_session_status()
                    await websocket.send_json({
                        "type": "SESSION_STATUS",
                        "status": status
                    })
                    
                else:
                    await websocket.send_json({
                        "type": "ERROR",
                        "message": f"Unknown command: {command}"
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in verification WebSocket: {e}")
                await websocket.send_json({
                    "type": "ERROR",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"Error in verification WebSocket: {e}")
    finally:
        # Cleanup session when WebSocket disconnects
        if session:
            await cleanup_session(user_id)

@app.get("/verification/status/{user_id}")
async def get_verification_status(user_id: str):
    """
    Get the current status of a user's verification session.
    """
    try:
        from .session_core import active_sessions
        
        if user_id not in active_sessions:
            return {
                "active": False,
                "message": "No active verification session"
            }
        
        session = active_sessions[user_id]
        status = await session.get_session_status()
        return status
        
    except Exception as e:
        logger.error(f"Error getting verification status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for UAT testing."""
    return {
        "status": "healthy",
        "message": "Aurora Agent Verification System is running",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
