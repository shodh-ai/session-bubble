# in aurora_agent/app.py
import logging
import asyncio
import os
import json
from datetime import datetime
import secrets
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.events.event import Event
from google.genai.types import Content, Part
from aurora_agent.tools.sheets import get_sheets_tool_instance  # Factory function to get SheetsTool instance
from aurora_agent.ui_tools.interaction_tool import live_ui_interaction_tool # The real UI tool
# Import the brain you built
from .agent_brains.root_agent import root_agent

# Import the browser manager
from .browser_manager import browser_manager
from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import os

# Import OAuth and database components
from .auth import oauth_manager, store_user_tokens, get_user_tokens, get_valid_access_token
from .database import create_tables, get_db, AsyncSessionLocal, UserToken
from .websocket_manager import websocket_manager
from .webhook_handler import webhook_handler
from .gcp_services.deployment_service import ImprinterDeploymentService

app = FastAPI()

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    await create_tables()


logger = logging.getLogger(__name__)

# Root route to serve the frontend
@app.get("/")
async def root():
    """Serve the teacher dashboard frontend."""
    static_file = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    else:
        return HTMLResponse("""
        <html>
            <body>
                <h1>Aurora Agent - Teacher Dashboard</h1>
                <p>Frontend not found. Please ensure static/index.html exists.</p>
                <a href="/auth/google?user_id=default_teacher">Connect Your Google Account</a>
            </body>
        </html>
        """)

# --- Critical ADK Patch ---
# The google-adk library does not correctly add the user's first message to the request.
# We are patching the method responsible for calling the LLM (`_call_llm_async`)
# to ensure the user's content is added to the request payload before being sent.
from google.adk.flows.llm_flows import base_llm_flow


@app.post("/run-mission")
async def run_mission(payload: dict):
    session_id = payload.get("session_id", "default")
    return await execute_browser_mission(payload, session_id)


# --- OAuth 2.0 Endpoints ---

@app.get("/auth/google")
async def google_auth_redirect(request: Request, user_id: str = "default_teacher"):
    """
    Endpoint 1: Generate Google OAuth authorization URL and redirect teacher.
    
    Args:
        user_id: Teacher's user ID (can be passed as query parameter)
    
    Returns:
        Redirect to Google OAuth consent screen
    """
    try:
        # Generate a secure random state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state and user_id in session (in production, use proper session management)
        # For now, we'll encode user_id in the state parameter
        state_with_user = f"{state}:{user_id}"
        
        # Create authorization URL
        auth_url = oauth_manager.create_authorization_url(state_with_user)
        
        logger.info(f"Redirecting user {user_id} to Google OAuth: {auth_url}")
        
        # Redirect teacher to Google OAuth consent screen
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        logger.error(f"Error creating OAuth URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate OAuth flow")


@app.get("/auth/google/callback")
async def google_auth_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint 2: Handle OAuth callback and exchange code for tokens.
    
    Args:
        code: Authorization code from Google
        state: State parameter for verification
        error: Error parameter if OAuth failed
        db: Database session
    
    Returns:
        Success page or error response
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"OAuth error: {error}")
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing authorization code or state")
        
        # Extract user_id from state parameter
        try:
            state_parts = state.split(":")
            if len(state_parts) != 2:
                raise ValueError("Invalid state format")
            original_state, user_id = state_parts
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Exchange authorization code for tokens
        token_data = oauth_manager.exchange_code_for_tokens(code, state)
        
        # Store tokens in database
        await store_user_tokens(db, user_id, token_data)
        
        logger.info(f"Successfully stored OAuth tokens for user {user_id}")
        
        # Return success page
        success_html = f"""
        <html>
            <head>
                <title>Google Account Connected</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: #28a745; }}
                    .container {{ max-width: 500px; margin: 0 auto; }}
                    .button {{ 
                        background-color: #007bff; 
                        color: white; 
                        padding: 10px 20px; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        display: inline-block; 
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="success">✅ Google Account Connected Successfully!</h1>
                    <p>Your Google account has been connected to Aurora Agent.</p>
                    <p>You can now close this window and return to the application.</p>
                    <p><strong>User ID:</strong> {user_id}</p>
                    <a href="/" class="button">Return to App</a>
                </div>
            </body>
        </html>
        """
        
        return HTMLResponse(content=success_html)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to complete OAuth flow")


@app.get("/auth/status")
async def auth_status(user_id: str = "default_teacher", db: AsyncSession = Depends(get_db)):
    """
    Check authentication status for a user.
    
    Args:
        user_id: Teacher's user ID
        db: Database session
    
    Returns:
        Authentication status and token validity
    """
    try:
        user_token = await get_user_tokens(db, user_id)
        
        if not user_token:
            return {
                "authenticated": False,
                "message": "No valid tokens found",
                "auth_url": f"/auth/google?user_id={user_id}"
            }
        
        # Check if we can get a valid access token
        valid_token = await get_valid_access_token(db, user_id)
        
        return {
            "authenticated": bool(valid_token),
            "user_id": user_id,
            "token_expiry": user_token.token_expiry.isoformat() if user_token.token_expiry else None,
            "scopes": user_token.scopes,
            "last_updated": user_token.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking auth status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check authentication status")

    
async def patched_call_llm_async(self, invocation_context):
    llm_request = self._build_llm_request(invocation_context)
    if invocation_context.new_message and invocation_context.new_message.content:
        llm_request.contents.append(invocation_context.new_message.content)
    async for llm_response in self._llm.generate_content_async(
        llm_request=llm_request, stream=self._stream
    ):
        yield self._build_event_from_llm_response(llm_response)

# Apply the patch
base_llm_flow.BaseLlmFlow._call_llm_async = patched_call_llm_async
# --- End of Patch ---


# --- Main Executor Function ---
async def execute_browser_mission(mission_payload: dict, session_id: str) -> dict:
    logger.info(f"--- ADK MISSION STARTING (Session: {session_id}) ---")

    try:
        await browser_manager.start_browser()
        logger.info("Browser is running.")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to start browser: {e}", exc_info=True)
        return {"status": "ERROR", "result": f"Browser failed to start: {e}"}

    prompt = mission_payload.get("mission_prompt", "No prompt provided.")
    context = mission_payload.get("session_context", {})
    user_id = context.get("user_id", "default_user")
    current_url = context.get("current_url", "")

    prompt_with_context = f"Current Page URL: {current_url}\nUser's Mission: {prompt}"

    logger.info(f"Invoking root_agent with enriched prompt...")

    # Initialize the runner with a session service.
    session_service = InMemorySessionService()
    await session_service.create_session(session_id=session_id, user_id=user_id, app_name="aurora_agent")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="aurora_agent")

    # +++ THIS IS THE CRITICAL FIX +++
    # We build the structured Event object instead of passing a raw string.
    new_content = Content(parts=[Part(text=prompt_with_context)])
    new_message_event = Event(author="user", content=new_content)
    # The runner also expects a top-level 'parts' attribute, so we add it.
    new_message_event.parts = new_content.parts
    # +++ END OF FIX +++
    
    final_result = "No textual output from agent."
    try:
        # --- THIS IS THE CORRECTED LOOP ---
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message_event
        ):
            logger.info(f"[DEBUG] Raw event from runner: {event}")

            # The most robust way to check for the final response is to look for
            # an event that has content but is NOT a tool call.
            # The final textual response from the agent is a specific kind of event.
            
            is_tool_call = event.content and event.content.parts and hasattr(event.content.parts[0], 'tool_code')
            has_text = event.content and event.content.parts and hasattr(event.content.parts[0], 'text')

            if has_text and not is_tool_call:
                # This is likely the final conversational response from the agent.
                final_result = event.content.parts[0].text
                logger.info(f"Captured agent's final textual response: {final_result}")
            elif is_tool_call:
                # This is an intermediate step where the agent is using a tool.
                tool_call = event.content.parts[0].tool_code
                tool_name = tool_call.name
                tool_args = tool_call.args if hasattr(tool_call, 'args') else None
                logger.info(f"Agent is calling tool: {tool_name} with args: {tool_args}")
            
        # The loop finishes when the agent's run is complete.
        # The last captured text is our final result.
        # --- END OF CORRECTED LOOP ---
                    
        logger.info(f"ADK mission completed. Final result: {final_result}")
        return {"status": "SUCCESS", "result": final_result}

    except Exception as e:
        logger.error(f"An exception occurred during ADK agent execution: {e}", exc_info=True)
        return {"status": "ERROR", "result": f"Agent execution failed: {e}"}


# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time communication with frontend"""
    try:
        await websocket_manager.connect(user_id, websocket)
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (heartbeat, etc.)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types from client
                if message.get("type") == "heartbeat":
                    await websocket_manager.send_to_user(user_id, {
                        "type": "heartbeat_response",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif message.get("type") == "status_request":
                    await websocket_manager.send_to_user(user_id, {
                        "type": "status_response",
                        "connected_users": websocket_manager.get_active_users(),
                        "user_id": user_id
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error for user {user_id}: {e}")
                break
                
    except Exception as e:
        print(f"WebSocket connection error for user {user_id}: {e}")
    finally:
        websocket_manager.disconnect(user_id)

# ============================================================================
# WEBHOOK ENDPOINTS  
# ============================================================================

@app.post("/webhook/sheets")
async def sheets_webhook(request: Request):
    """Webhook endpoint to receive events from Google Apps Script"""
    try:
        # Parse the incoming JSON payload
        payload = await request.json()
        
        # Process the webhook event
        result = await webhook_handler.process_webhook_event(payload)
        
        return result
        
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/webhook/test")
async def test_webhook():
    """Test endpoint to simulate a webhook event."""
    test_event = {
        "type": "SHEET_CHANGE",
        "sheet_name": "Test Sheet",
        "change_type": "EDIT",
        "range": "A1:B2",
        "timestamp": datetime.now().isoformat(),
        "user_email": "test@example.com"
    }
    
    result = await webhook_handler.process_event(test_event, "default_teacher")
    return result

# ============================================================================
# PHASE 3: SPY DEPLOYMENT ENDPOINTS
# ============================================================================

@app.post("/spy/deploy")
async def deploy_spy(request: dict):
    """
    Deploy the Aurora Agent spy script to a Google Spreadsheet.
    
    Expected request body:
    {
        "user_id": "teacher_user_id",
        "spreadsheet_id": "1abc123..."
    }
    """
    try:
        user_id = request.get("user_id")
        spreadsheet_id = request.get("spreadsheet_id")
        
        if not user_id or not spreadsheet_id:
            return {"success": False, "error": "Missing user_id or spreadsheet_id"}
        
        # Get user's OAuth tokens with database session
        async with AsyncSessionLocal() as db:
            tokens = await db.get(UserToken, user_id)
            if not tokens:
                return {"success": False, "error": "User not authenticated with Google"}
        
        # Create deployment service with user's credentials
        # Parse scopes from JSON string format
        try:
            scopes = json.loads(tokens.scopes) if tokens.scopes else []
        except (json.JSONDecodeError, TypeError):
            # Fallback to split if not JSON format
            scopes = tokens.scopes.split(",") if tokens.scopes else []
        
        credentials = {
            "token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": scopes
        }
        
        deployment_service = ImprinterDeploymentService(credentials)
        result = await deployment_service.deploy_spy(spreadsheet_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in deploy_spy endpoint: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.post("/spy/remove")
async def remove_spy(request: dict):
    """
    Remove the Aurora Agent spy script from a Google Spreadsheet.
    
    Expected request body:
    {
        "user_id": "teacher_user_id",
        "spreadsheet_id": "1abc123..."
    }
    """
    try:
        user_id = request.get("user_id")
        spreadsheet_id = request.get("spreadsheet_id")
        
        if not user_id or not spreadsheet_id:
            return {"success": False, "error": "Missing user_id or spreadsheet_id"}
        
        # Get user's OAuth tokens with database session
        async with AsyncSessionLocal() as db:
            tokens = await db.get(UserToken, user_id)
            if not tokens:
                return {"success": False, "error": "User not authenticated with Google"}
        
        # Create deployment service with user's credentials
        # Parse scopes from JSON string format
        try:
            scopes = json.loads(tokens.scopes) if tokens.scopes else []
        except (json.JSONDecodeError, TypeError):
            # Fallback to split if not JSON format
            scopes = tokens.scopes.split(",") if tokens.scopes else []
        
        credentials = {
            "token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": scopes
        }
        
        deployment_service = ImprinterDeploymentService(credentials)
        result = await deployment_service.remove_spy(spreadsheet_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in remove_spy endpoint: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

@app.get("/spy/status")
async def check_spy_status(user_id: str, spreadsheet_id: str):
    """
    Check the status of the Aurora Agent spy script on a Google Spreadsheet.
    
    Query parameters:
    - user_id: teacher_user_id
    - spreadsheet_id: 1abc123...
    """
    try:
        if not user_id or not spreadsheet_id:
            return {"deployed": False, "error": "Missing user_id or spreadsheet_id"}
        
        # Get user's OAuth tokens with database session
        async with AsyncSessionLocal() as db:
            tokens = await db.get(UserToken, user_id)
            if not tokens:
                return {"deployed": False, "error": "User not authenticated with Google"}
        
        # Create deployment service with user's credentials
        # Parse scopes from JSON string format
        try:
            scopes = json.loads(tokens.scopes) if tokens.scopes else []
        except (json.JSONDecodeError, TypeError):
            # Fallback to split if not JSON format
            scopes = tokens.scopes.split(",") if tokens.scopes else []
        
        credentials = {
            "token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": scopes
        }
        
        deployment_service = ImprinterDeploymentService(credentials)
        result = await deployment_service.check_spy_status(spreadsheet_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in check_spy_status endpoint: {e}", exc_info=True)
        return {"deployed": False, "error": str(e)}

# ============================================================================
# PHASE 4: FINAL INTEGRATION ENDPOINT
# ============================================================================

class StartImprintingRequest(BaseModel):
    spreadsheet_id: str
    user_id: str

@app.post("/imprinter/start-session")
async def start_imprinting_session(request: StartImprintingRequest):
    """
    Endpoint called by the frontend when a teacher wants to start imprinting.
    It deploys the spy script to the target spreadsheet.
    
    This is the final integration endpoint that connects the UI to the backend service.
    """
    try:
        # 1. Get the teacher's stored OAuth credentials from the database
        async with get_db() as db:
            tokens = await get_user_tokens(db, request.user_id)
            
            if not tokens:
                raise HTTPException(status_code=401, detail="User not authenticated with Google")
            
            # Refresh token if needed
            valid_token = await get_valid_access_token(db, request.user_id)
            if not valid_token:
                raise HTTPException(status_code=401, detail="Unable to refresh access token")
        
        # 2. Prepare credentials for the deployment service
        credentials = {
            "token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "scopes": tokens.scopes.split(",") if tokens.scopes else []
        }
        
        # 3. Instantiate and run the deployment service
        deployment_service = ImprinterDeploymentService(credentials)
        result = await deployment_service.deploy_spy(request.spreadsheet_id)
        
        # 4. Return the result to the frontend
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        # Log successful deployment
        logger.info(f"Imprinting session started for user {request.user_id} on spreadsheet {request.spreadsheet_id}")
        
        return {"message": "Imprinting session started. The sheet is now being monitored."}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in start_imprinting_session endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start imprinting session: {str(e)}")