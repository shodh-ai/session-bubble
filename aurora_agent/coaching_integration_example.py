"""Complete Integration Example: Aurora Agent AI Coaching System."""
import asyncio
import logging
from typing import Dict, Any
from langgraph_coaching_nodes import create_coaching_graph, start_coaching_session, CoachingState

logger = logging.getLogger(__name__)

async def run_coaching_session_example():
    """
    Example of how to use the complete Aurora Agent coaching system.
    This demonstrates the integration between:
    - Real-time verification (SessionCore + student_verifier)
    - AI coaching logic (LangGraph nodes)
    - Lesson plan data (from lesson builder)
    """
    
    # Example lesson data (this would come from your lesson API)
    example_lesson = {
        "id": "lesson_001",
        "title": "Basic Google Sheets Operations",
        "creator_id": "teacher_123",
        "steps": [
            {
                "id": "step_001",
                "step_number": 1,
                "narration": "Click on cell A1 to select it",
                "action_json": {
                    "tool_name": "click_cell",
                    "parameters": {
                        "cell": "A1",
                        "sheet": "Sheet1"
                    },
                    "description": "Select cell A1"
                }
            },
            {
                "id": "step_002", 
                "step_number": 2,
                "narration": "Type 'Hello World' in the selected cell",
                "action_json": {
                    "tool_name": "write_cell",
                    "parameters": {
                        "cell": "A1",
                        "value": "Hello World",
                        "sheet": "Sheet1"
                    },
                    "description": "Write 'Hello World' to cell A1"
                }
            },
            {
                "id": "step_003",
                "step_number": 3, 
                "narration": "Press Enter to confirm the entry",
                "action_json": {
                    "tool_name": "press_key",
                    "parameters": {
                        "key": "Enter"
                    },
                    "description": "Press Enter key"
                }
            }
        ]
    }
    
    # Student user ID (this would come from authentication)
    student_user_id = "student_456"
    
    logger.info("=== Aurora Agent Coaching Session Example ===")
    
    # Step 1: Create the coaching graph
    coaching_graph = create_coaching_graph()
    logger.info("✅ Coaching graph created")
    
    # Step 2: Initialize coaching session
    initial_state = await start_coaching_session(student_user_id, example_lesson)
    logger.info(f"✅ Coaching session initialized for lesson: {example_lesson['title']}")
    
    # Step 3: Run the coaching workflow
    logger.info("🚀 Starting AI coaching workflow...")
    
    try:
        # Convert state to dict for LangGraph
        state_dict = initial_state.to_dict()
        
        # Run the graph (this will execute the coaching logic)
        final_state = await coaching_graph.ainvoke(state_dict)
        
        logger.info("✅ Coaching session completed")
        
        # Display session results
        conversation_history = final_state.get("conversation_history", [])
        logger.info(f"📊 Session Summary:")
        logger.info(f"   - Total interactions: {len(conversation_history)}")
        logger.info(f"   - Final step index: {final_state.get('step_index', 0)}")
        logger.info(f"   - Session completed: {not final_state.get('session_active', True)}")
        
        # Show conversation flow
        logger.info("💬 Conversation Flow:")
        for i, interaction in enumerate(conversation_history):
            interaction_type = interaction.get("type", "unknown")
            message = interaction.get("message", "")[:100] + "..." if len(interaction.get("message", "")) > 100 else interaction.get("message", "")
            logger.info(f"   {i+1}. [{interaction_type}] {message}")
        
        return final_state
        
    except Exception as e:
        logger.error(f"❌ Coaching session failed: {e}", exc_info=True)
        return None

class CoachingSessionManager:
    """
    Production-ready coaching session manager.
    This would be integrated into your main FastAPI application.
    """
    
    def __init__(self):
        self.active_coaching_sessions: Dict[str, Dict[str, Any]] = {}
        self.coaching_graph = create_coaching_graph()
    
    async def start_student_coaching(self, user_id: str, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new coaching session for a student."""
        try:
            logger.info(f"Starting coaching session for student {user_id}")
            
            # Initialize session state
            initial_state = await start_coaching_session(user_id, lesson_data)
            
            # Store active session
            self.active_coaching_sessions[user_id] = {
                "state": initial_state.to_dict(),
                "lesson_data": lesson_data,
                "started_at": "now",  # Use actual timestamp
                "status": "active"
            }
            
            # Start the coaching workflow
            state_dict = initial_state.to_dict()
            updated_state = await self.coaching_graph.ainvoke(state_dict)
            
            # Update stored session
            self.active_coaching_sessions[user_id]["state"] = updated_state
            
            return {
                "success": True,
                "session_id": user_id,
                "current_step": updated_state.get("current_step"),
                "conversation_history": updated_state.get("conversation_history", [])
            }
            
        except Exception as e:
            logger.error(f"Failed to start coaching session for {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def continue_coaching_session(self, user_id: str) -> Dict[str, Any]:
        """Continue an existing coaching session after student action."""
        try:
            if user_id not in self.active_coaching_sessions:
                return {"success": False, "error": "No active session found"}
            
            session = self.active_coaching_sessions[user_id]
            current_state = session["state"]
            
            # Continue the workflow
            updated_state = await self.coaching_graph.ainvoke(current_state)
            
            # Update stored session
            session["state"] = updated_state
            
            # Check if session is complete
            if not updated_state.get("session_active", True):
                session["status"] = "completed"
                logger.info(f"Coaching session completed for student {user_id}")
            
            return {
                "success": True,
                "session_active": updated_state.get("session_active", True),
                "current_step": updated_state.get("current_step"),
                "conversation_history": updated_state.get("conversation_history", []),
                "verification_result": updated_state.get("verification_result")
            }
            
        except Exception as e:
            logger.error(f"Failed to continue coaching session for {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_session_status(self, user_id: str) -> Dict[str, Any]:
        """Get current status of a coaching session."""
        if user_id not in self.active_coaching_sessions:
            return {"active": False, "error": "No session found"}
        
        session = self.active_coaching_sessions[user_id]
        state = session["state"]
        
        return {
            "active": state.get("session_active", False),
            "lesson_title": session["lesson_data"].get("title", "Unknown"),
            "current_step_index": state.get("step_index", 0),
            "total_steps": len(session["lesson_data"].get("steps", [])),
            "last_action": state.get("coaching_context", {}).get("last_action", "unknown"),
            "conversation_count": len(state.get("conversation_history", []))
        }
    
    async def end_coaching_session(self, user_id: str) -> Dict[str, Any]:
        """End a coaching session."""
        if user_id in self.active_coaching_sessions:
            session = self.active_coaching_sessions[user_id]
            session["status"] = "ended"
            session["state"]["session_active"] = False
            
            logger.info(f"Coaching session ended for student {user_id}")
            return {"success": True, "message": "Session ended"}
        
        return {"success": False, "error": "No active session found"}

# Global coaching manager instance
coaching_manager = CoachingSessionManager()

if __name__ == "__main__":
    # Run the example
    asyncio.run(run_coaching_session_example())
