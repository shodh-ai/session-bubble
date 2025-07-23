"""LangGraph Coaching Nodes for Aurora Agent - Real-time Student Verification Integration."""
import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph
from student_verifier import await_and_verify_student_action

logger = logging.getLogger(__name__)

class CoachingState:
    """State structure for LangGraph coaching workflow."""
    
    def __init__(self):
        self.user_id: Optional[str] = None
        self.current_lesson: Optional[Dict[str, Any]] = None
        self.current_step: Optional[Dict[str, Any]] = None
        self.step_index: int = 0
        self.verification_result: Optional[Dict[str, Any]] = None
        self.conversation_history: list = []
        self.coaching_context: Dict[str, Any] = {}
        self.session_active: bool = False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for LangGraph."""
        return {
            "user_id": self.user_id,
            "current_lesson": self.current_lesson,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "verification_result": self.verification_result,
            "conversation_history": self.conversation_history,
            "coaching_context": self.coaching_context,
            "session_active": self.session_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoachingState':
        """Create state from dictionary for LangGraph."""
        state = cls()
        state.user_id = data.get("user_id")
        state.current_lesson = data.get("current_lesson")
        state.current_step = data.get("current_step")
        state.step_index = data.get("step_index", 0)
        state.verification_result = data.get("verification_result")
        state.conversation_history = data.get("conversation_history", [])
        state.coaching_context = data.get("coaching_context", {})
        state.session_active = data.get("session_active", False)
        return state

async def modeling_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Demonstrate the current step to the student.
    This node shows the AI performing the action that the student should learn.
    """
    logger.info(f"Modeling node - demonstrating step {state.get('step_index', 0)}")
    
    current_step = state.get("current_step")
    if not current_step:
        logger.error("No current step found for modeling")
        return {**state, "error": "No step to model"}
    
    # Generate demonstration message
    step_description = current_step.get("narration", "Perform this action")
    action_details = current_step.get("action_json", {})
    
    demonstration_message = f"""
    Let me show you how to do this step:
    
    **Step {state.get('step_index', 0) + 1}**: {step_description}
    
    I'll demonstrate the action: {action_details.get('tool_name', 'unknown action')}
    
    Watch carefully, then try to do the same thing yourself!
    """
    
    # Add to conversation history
    conversation_history = state.get("conversation_history", [])
    conversation_history.append({
        "type": "demonstration",
        "message": demonstration_message,
        "step_index": state.get("step_index", 0),
        "timestamp": "now"  # You might want to use actual timestamp
    })
    
    logger.info(f"Modeling complete for step {state.get('step_index', 0)}")
    
    return {
        **state,
        "conversation_history": conversation_history,
        "coaching_context": {
            **state.get("coaching_context", {}),
            "last_action": "modeling",
            "demonstration_given": True
        }
    }

async def verify_student_work_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wait for and verify student's attempt at the current step.
    This is the core integration point with the verification system.
    """
    logger.info(f"Verify student work node - waiting for student action on step {state.get('step_index', 0)}")
    
    user_id = state.get("user_id")
    current_step = state.get("current_step")
    
    if not user_id:
        logger.error("No user_id found for verification")
        return {**state, "error": "No user_id for verification"}
    
    if not current_step:
        logger.error("No current step found for verification")
        return {**state, "error": "No step to verify"}
    
    # Extract expected action from lesson step
    expected_action = current_step.get("action_json", {})
    
    if not expected_action:
        logger.error("No expected action found in step")
        return {**state, "error": "No expected action in step"}
    
    try:
        # This is the key integration - wait for student action
        logger.info(f"Waiting for student {user_id} to perform: {expected_action.get('tool_name', 'unknown')}")
        
        verification_result = await await_and_verify_student_action(
            user_id=user_id,
            expected_action=expected_action,
            timeout_seconds=120  # 2 minutes timeout for student action
        )
        
        logger.info(f"Student verification complete - Match: {verification_result.get('match', False)}")
        
        # Add verification to conversation history
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "type": "verification_attempt",
            "verification_result": verification_result,
            "step_index": state.get("step_index", 0),
            "timestamp": verification_result.get("timestamp", "now")
        })
        
        return {
            **state,
            "verification_result": verification_result,
            "conversation_history": conversation_history,
            "coaching_context": {
                **state.get("coaching_context", {}),
                "last_action": "verification",
                "verification_complete": True,
                "student_succeeded": verification_result.get("match", False)
            }
        }
        
    except Exception as e:
        logger.error(f"Student verification failed: {e}", exc_info=True)
        
        return {
            **state,
            "verification_result": {
                "match": False,
                "error": str(e),
                "feedback_suggestion": "There was an issue with the verification system. Let me try to help you in a different way."
            },
            "coaching_context": {
                **state.get("coaching_context", {}),
                "last_action": "verification_error",
                "verification_complete": False
            }
        }

async def plan_advancer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advance to the next step when student succeeds.
    Provides positive feedback and moves the lesson forward.
    """
    logger.info(f"Plan advancer node - student succeeded on step {state.get('step_index', 0)}")
    
    verification_result = state.get("verification_result", {})
    current_lesson = state.get("current_lesson", {})
    current_step_index = state.get("step_index", 0)
    
    # Generate success message
    success_message = f"""
    Excellent work! ✅ You completed that step correctly.
    
    {verification_result.get('feedback_suggestion', 'Great job!')}
    
    Confidence: {verification_result.get('confidence', 0.0):.1%}
    """
    
    # Check if there are more steps
    lesson_steps = current_lesson.get("steps", [])
    next_step_index = current_step_index + 1
    
    if next_step_index < len(lesson_steps):
        # Move to next step
        next_step = lesson_steps[next_step_index]
        success_message += f"\n\nLet's move on to the next step: {next_step.get('narration', 'Next action')}"
        
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "type": "success_feedback",
            "message": success_message,
            "step_completed": current_step_index,
            "timestamp": "now"
        })
        
        return {
            **state,
            "step_index": next_step_index,
            "current_step": next_step,
            "conversation_history": conversation_history,
            "verification_result": None,  # Clear for next step
            "coaching_context": {
                **state.get("coaching_context", {}),
                "last_action": "advance",
                "step_completed": current_step_index,
                "demonstration_given": False  # Need new demonstration for next step
            }
        }
    else:
        # Lesson complete!
        success_message += f"\n\n🎉 Congratulations! You've completed the entire lesson: '{current_lesson.get('title', 'Lesson')}'"
        
        conversation_history = state.get("conversation_history", [])
        conversation_history.append({
            "type": "lesson_complete",
            "message": success_message,
            "lesson_completed": current_lesson.get("id"),
            "timestamp": "now"
        })
        
        return {
            **state,
            "conversation_history": conversation_history,
            "session_active": False,  # End the coaching session
            "coaching_context": {
                **state.get("coaching_context", {}),
                "last_action": "lesson_complete",
                "lesson_completed": True
            }
        }

async def feedback_flow_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provide helpful feedback when student makes a mistake.
    Generates hints and guidance to help student succeed.
    """
    logger.info(f"Feedback flow node - providing guidance for step {state.get('step_index', 0)}")
    
    verification_result = state.get("verification_result", {})
    current_step = state.get("current_step", {})
    
    # Generate helpful feedback message
    feedback_message = verification_result.get("feedback_suggestion", "Not quite right. Let me help you.")
    
    # Add more detailed guidance based on the error
    if verification_result.get("timeout"):
        feedback_message = f"""
        I'm still waiting for you to try the action. Take your time!
        
        Remember, you need to: {current_step.get('narration', 'perform the expected action')}
        
        Would you like me to demonstrate it again?
        """
    elif not verification_result.get("tool_match", True):
        expected_tool = verification_result.get("expected_action", {}).get("tool_name", "unknown")
        actual_tool = verification_result.get("actual_action", {}).get("tool_name", "unknown")
        feedback_message = f"""
        I see you tried to {actual_tool}, but for this step we need to {expected_tool}.
        
        Let me show you the correct action again.
        """
    
    # Add to conversation history
    conversation_history = state.get("conversation_history", [])
    conversation_history.append({
        "type": "feedback",
        "message": feedback_message,
        "verification_result": verification_result,
        "step_index": state.get("step_index", 0),
        "timestamp": "now"
    })
    
    return {
        **state,
        "conversation_history": conversation_history,
        "verification_result": None,  # Clear for retry
        "coaching_context": {
            **state.get("coaching_context", {}),
            "last_action": "feedback",
            "feedback_given": True,
            "demonstration_given": False  # May need to demonstrate again
        }
    }

def create_coaching_router(state: Dict[str, Any]) -> str:
    """
    Smart router that determines next action based on verification results.
    This is the decision-making logic for the coaching flow.
    """
    logger.info("Coaching router - determining next action")
    
    coaching_context = state.get("coaching_context", {})
    last_action = coaching_context.get("last_action")
    verification_result = state.get("verification_result")
    
    # If lesson is complete, end the session
    if not state.get("session_active", True):
        logger.info("Router: Session inactive, ending")
        return "END"
    
    # If we just completed modeling, move to verification
    if last_action == "modeling":
        logger.info("Router: After modeling -> verify student work")
        return "verify_student_work"
    
    # If we have verification results, route based on success/failure
    if verification_result:
        if verification_result.get("match", False):
            logger.info("Router: Student succeeded -> advance plan")
            return "advance_plan"
        else:
            logger.info("Router: Student needs help -> provide feedback")
            return "provide_feedback"
    
    # If we just gave feedback, demonstrate again
    if last_action == "feedback":
        logger.info("Router: After feedback -> model again")
        return "model_step"
    
    # If we just advanced, model the new step
    if last_action == "advance":
        logger.info("Router: After advance -> model new step")
        return "model_step"
    
    # Default: start with modeling
    logger.info("Router: Default -> model step")
    return "model_step"

def create_coaching_graph() -> StateGraph:
    """
    Create the complete LangGraph coaching workflow.
    This integrates all nodes and routing logic.
    """
    logger.info("Creating coaching graph")
    
    # Create the graph
    workflow = StateGraph(CoachingState)
    
    # Add nodes
    workflow.add_node("model_step", modeling_node)
    workflow.add_node("verify_student_work", verify_student_work_node)
    workflow.add_node("advance_plan", plan_advancer_node)
    workflow.add_node("provide_feedback", feedback_flow_node)
    
    # Add conditional routing
    workflow.add_conditional_edges(
        "model_step",
        create_coaching_router,
        {
            "verify_student_work": "verify_student_work",
            "END": "__end__"
        }
    )
    
    workflow.add_conditional_edges(
        "verify_student_work",
        create_coaching_router,
        {
            "advance_plan": "advance_plan",
            "provide_feedback": "provide_feedback",
            "END": "__end__"
        }
    )
    
    workflow.add_conditional_edges(
        "advance_plan",
        create_coaching_router,
        {
            "model_step": "model_step",
            "END": "__end__"
        }
    )
    
    workflow.add_conditional_edges(
        "provide_feedback",
        create_coaching_router,
        {
            "model_step": "model_step",
            "verify_student_work": "verify_student_work",
            "END": "__end__"
        }
    )
    
    # Set entry point
    workflow.set_entry_point("model_step")
    
    logger.info("Coaching graph created successfully")
    return workflow.compile()

# Helper function to start a coaching session
async def start_coaching_session(user_id: str, lesson_data: Dict[str, Any]) -> CoachingState:
    """
    Initialize a coaching session with a student and lesson.
    """
    logger.info(f"Starting coaching session for user {user_id} with lesson: {lesson_data.get('title', 'Unknown')}")
    
    state = CoachingState()
    state.user_id = user_id
    state.current_lesson = lesson_data
    state.session_active = True
    
    # Set up first step
    lesson_steps = lesson_data.get("steps", [])
    if lesson_steps:
        state.current_step = lesson_steps[0]
        state.step_index = 0
        logger.info(f"First step loaded: {state.current_step.get('narration', 'Unknown step')}")
    else:
        logger.error("No steps found in lesson data")
        state.session_active = False
    
    return state
