"""Student Verifier Tool for LangGraph Integration - Real-time AI Coaching."""
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class StudentActionSubscriber:
    """Event subscription system for student action verification."""
    
    def __init__(self):
        self.subscribers: Dict[str, Dict[str, Any]] = {}
        self.action_queues: Dict[str, asyncio.Queue] = {}
    
    def subscribe(self, user_id: str, callback: Optional[Callable] = None) -> asyncio.Queue:
        """Subscribe to VERIFIED_ACTION events for a specific user."""
        if user_id not in self.action_queues:
            self.action_queues[user_id] = asyncio.Queue()
        
        self.subscribers[user_id] = {
            'callback': callback,
            'subscribed_at': datetime.utcnow(),
            'active': True
        }
        
        logger.info(f"Subscribed to student actions for user: {user_id}")
        return self.action_queues[user_id]
    
    def unsubscribe(self, user_id: str):
        """Unsubscribe from events for a specific user."""
        if user_id in self.subscribers:
            self.subscribers[user_id]['active'] = False
            del self.subscribers[user_id]
        
        if user_id in self.action_queues:
            # Clear the queue
            while not self.action_queues[user_id].empty():
                try:
                    self.action_queues[user_id].get_nowait()
                except asyncio.QueueEmpty:
                    break
            del self.action_queues[user_id]
        
        logger.info(f"Unsubscribed from student actions for user: {user_id}")
    
    async def publish_action(self, user_id: str, action_data: Dict[str, Any]):
        """Publish a verified action to subscribers."""
        if user_id in self.subscribers and self.subscribers[user_id]['active']:
            if user_id in self.action_queues:
                await self.action_queues[user_id].put(action_data)
                logger.info(f"Published action to subscriber for user {user_id}: {action_data.get('tool_name', 'unknown')}")
            
            # Call callback if provided
            callback = self.subscribers[user_id].get('callback')
            if callback:
                try:
                    await callback(user_id, action_data)
                except Exception as e:
                    logger.error(f"Callback error for user {user_id}: {e}")

# Global subscriber instance
student_subscriber = StudentActionSubscriber()

class ActionComparator:
    """Compare expected vs actual student actions."""
    
    @staticmethod
    def compare_actions(expected_action: Dict[str, Any], actual_action: Dict[str, Any]) -> Dict[str, Any]:
        """Compare expected action with actual verified action."""
        try:
            logger.info(f"Comparing actions - Expected: {expected_action.get('tool_name')}, Actual: {actual_action.get('tool_name')}")
            
            # Extract key components for comparison
            expected_tool = expected_action.get('tool_name', '').lower()
            actual_tool = actual_action.get('tool_name', '').lower()
            
            expected_params = expected_action.get('parameters', {})
            actual_params = actual_action.get('parameters', {})
            
            # Basic tool name matching
            tool_match = expected_tool == actual_tool
            
            # Parameter matching (flexible)
            param_matches = ActionComparator._compare_parameters(expected_params, actual_params)
            
            # Overall match determination
            overall_match = tool_match and param_matches['match']
            
            # Calculate confidence score
            confidence = ActionComparator._calculate_confidence(tool_match, param_matches, actual_action)
            
            result = {
                "match": overall_match,
                "confidence": confidence,
                "tool_match": tool_match,
                "parameter_match": param_matches['match'],
                "expected_action": expected_action,
                "actual_action": actual_action,
                "comparison_details": {
                    "tool_comparison": {
                        "expected": expected_tool,
                        "actual": actual_tool,
                        "match": tool_match
                    },
                    "parameter_comparison": param_matches,
                    "verification_status": actual_action.get('status', 'unknown'),
                    "verification_confidence": actual_action.get('confidence', 0.0)
                },
                "timestamp": datetime.utcnow().isoformat(),
                "feedback_suggestion": ActionComparator._generate_feedback_suggestion(
                    overall_match, tool_match, param_matches, expected_action, actual_action
                )
            }
            
            logger.info(f"Action comparison result: {overall_match} (confidence: {confidence})")
            return result
            
        except Exception as e:
            logger.error(f"Action comparison failed: {e}", exc_info=True)
            return {
                "match": False,
                "confidence": 0.0,
                "error": str(e),
                "expected_action": expected_action,
                "actual_action": actual_action,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def _compare_parameters(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
        """Compare parameter dictionaries with flexible matching."""
        if not expected and not actual:
            return {"match": True, "details": "Both parameter sets empty"}
        
        if not expected:
            return {"match": True, "details": "No expected parameters to match"}
        
        matches = {}
        mismatches = {}
        
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            
            if actual_value is None:
                mismatches[key] = {"expected": expected_value, "actual": None, "reason": "missing"}
            elif ActionComparator._values_match(expected_value, actual_value):
                matches[key] = {"expected": expected_value, "actual": actual_value}
            else:
                mismatches[key] = {"expected": expected_value, "actual": actual_value, "reason": "value_mismatch"}
        
        match_ratio = len(matches) / len(expected) if expected else 1.0
        overall_match = match_ratio >= 0.8  # 80% of parameters must match
        
        return {
            "match": overall_match,
            "match_ratio": match_ratio,
            "matches": matches,
            "mismatches": mismatches,
            "details": f"Matched {len(matches)}/{len(expected)} parameters"
        }
    
    @staticmethod
    def _values_match(expected: Any, actual: Any) -> bool:
        """Check if two values match with flexible comparison."""
        # Exact match
        if expected == actual:
            return True
        
        # String comparison (case-insensitive, stripped)
        if isinstance(expected, str) and isinstance(actual, str):
            return expected.strip().lower() == actual.strip().lower()
        
        # Numeric comparison with tolerance
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return abs(expected - actual) < 0.01
        
        # List/array comparison
        if isinstance(expected, list) and isinstance(actual, list):
            return len(expected) == len(actual) and all(
                ActionComparator._values_match(e, a) for e, a in zip(expected, actual)
            )
        
        return False
    
    @staticmethod
    def _calculate_confidence(tool_match: bool, param_matches: Dict[str, Any], actual_action: Dict[str, Any]) -> float:
        """Calculate confidence score for the action match."""
        base_confidence = 0.0
        
        # Tool match contributes 50% to confidence
        if tool_match:
            base_confidence += 0.5
        
        # Parameter match contributes 30% to confidence
        if param_matches.get('match', False):
            base_confidence += 0.3 * param_matches.get('match_ratio', 0.0)
        
        # Verification confidence contributes 20% to confidence
        verification_confidence = actual_action.get('confidence', 0.0)
        base_confidence += 0.2 * verification_confidence
        
        return min(1.0, max(0.0, base_confidence))
    
    @staticmethod
    def _generate_feedback_suggestion(overall_match: bool, tool_match: bool, param_matches: Dict[str, Any], 
                                    expected: Dict[str, Any], actual: Dict[str, Any]) -> str:
        """Generate feedback suggestion for the AI coach."""
        if overall_match:
            return "Great job! You performed the correct action."
        
        if not tool_match:
            expected_tool = expected.get('tool_name', 'unknown')
            actual_tool = actual.get('tool_name', 'unknown')
            return f"You performed '{actual_tool}' but I expected '{expected_tool}'. Let me show you the correct action."
        
        if not param_matches.get('match', False):
            mismatches = param_matches.get('mismatches', {})
            if mismatches:
                key = list(mismatches.keys())[0]
                mismatch = mismatches[key]
                return f"Close! You got the action right, but the {key} should be '{mismatch['expected']}' instead of '{mismatch['actual']}'."
        
        return "Not quite right. Let me demonstrate the correct action for you."

async def await_and_verify_student_action(user_id: str, expected_action: Dict[str, Any], 
                                        timeout_seconds: int = 60) -> Dict[str, Any]:
    """
    Main function for LangGraph integration - waits for and verifies student action.
    
    Args:
        user_id: The student's user ID
        expected_action: The expected action structure from the lesson plan
        timeout_seconds: How long to wait for student action (default: 60 seconds)
    
    Returns:
        Dict containing match result, confidence, and feedback suggestions
    """
    logger.info(f"Starting student action verification for user {user_id}")
    logger.info(f"Expected action: {expected_action.get('tool_name', 'unknown')}")
    
    # Subscribe to student actions
    action_queue = student_subscriber.subscribe(user_id)
    
    try:
        # Wait for student action with timeout
        timeout_time = datetime.utcnow() + timedelta(seconds=timeout_seconds)
        
        while datetime.utcnow() < timeout_time:
            try:
                # Wait for action with short timeout to allow checking overall timeout
                actual_action = await asyncio.wait_for(action_queue.get(), timeout=5.0)
                
                logger.info(f"Received student action: {actual_action.get('tool_name', 'unknown')}")
                
                # Compare actions
                comparison_result = ActionComparator.compare_actions(expected_action, actual_action)
                
                # Unsubscribe and return result
                student_subscriber.unsubscribe(user_id)
                
                logger.info(f"Student verification complete - Match: {comparison_result['match']}")
                return comparison_result
                
            except asyncio.TimeoutError:
                # Continue waiting until overall timeout
                continue
        
        # Timeout reached
        logger.warning(f"Student action verification timed out for user {user_id}")
        student_subscriber.unsubscribe(user_id)
        
        return {
            "match": False,
            "confidence": 0.0,
            "timeout": True,
            "expected_action": expected_action,
            "actual_action": None,
            "timestamp": datetime.utcnow().isoformat(),
            "feedback_suggestion": f"I'm waiting for you to perform the action. Take your time and try: {expected_action.get('description', 'the expected action')}",
            "timeout_seconds": timeout_seconds
        }
        
    except Exception as e:
        logger.error(f"Student verification error for user {user_id}: {e}", exc_info=True)
        student_subscriber.unsubscribe(user_id)
        
        return {
            "match": False,
            "confidence": 0.0,
            "error": str(e),
            "expected_action": expected_action,
            "actual_action": None,
            "timestamp": datetime.utcnow().isoformat(),
            "feedback_suggestion": "There was an issue with the verification system. Let me try to help you in a different way."
        }

# Helper function to integrate with SessionCore
async def publish_student_action(user_id: str, action_data: Dict[str, Any]):
    """Publish a verified action from SessionCore to student subscribers."""
    await student_subscriber.publish_action(user_id, action_data)
