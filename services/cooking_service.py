import uuid
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from models import Recipe, CookingSession, CookingInterruption, StepStatus, InterruptionType
from ai.conversation_engine import ConversationEngine

logger = logging.getLogger(__name__)

class CookingService:
    """
    Orchestrates cooking sessions, manages state, and coordinates between
    the AI conversation engine and the cooking session data.
    """
    
    def __init__(self):
        self.conversation_engine = ConversationEngine()
        self.active_sessions: Dict[str, CookingSession] = {}
    
    def start_cooking_session(self, recipe: Recipe, user_id: Optional[str] = None) -> CookingSession:
        """Start a new cooking session"""
        
        session_id = str(uuid.uuid4())
        session = CookingSession(
            session_id=session_id,
            recipe_id=recipe.id,
            user_id=user_id,
            current_step=0,
            step_status=StepStatus.PENDING
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Started cooking session {session_id} for recipe {recipe.name}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[CookingSession]:
        """Get an active cooking session"""
        return self.active_sessions.get(session_id)
    
    def process_user_input(
        self, 
        session_id: str, 
        user_input: str, 
        recipe: Recipe
    ) -> Dict[str, Any]:
        """
        Process user input and return AI response with any actions to take.
        
        This is the main entry point for handling user interactions during cooking.
        """
        
        session = self.get_session(session_id)
        if not session:
            return {
                "error": "Session not found",
                "response": "I'm sorry, I can't find your cooking session. Let's start over.",
                "action": "restart"
            }
        
        # Let the AI generate a response
        ai_result = self.conversation_engine.generate_response(
            user_input=user_input,
            session=session,
            recipe=recipe
        )
        
        # Execute any actions the AI requested
        action_result = self._execute_action(
            action=ai_result["action"],
            session=session,
            recipe=recipe,
            context_updates=ai_result.get("context_updates", {})
        )
        
        # Combine AI response with action results
        result = {
            "response": ai_result["response"],
            "action": ai_result["action"],
            "session_update": action_result,
            "current_step": session.current_step,
            "step_status": session.step_status.value,
            "total_steps": len(recipe.steps)
        }
        
        # Add step information if we're in a step
        current_step = session.get_current_step(recipe)
        if current_step:
            result["current_step_info"] = {
                "instruction": current_step.instruction,
                "estimated_time": current_step.estimated_time,
                "tips": current_step.tips
            }
        
        return result
    
    def _execute_action(
        self, 
        action: str, 
        session: CookingSession, 
        recipe: Recipe,
        context_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an action requested by the AI"""
        
        result = {"action_executed": action}
        
        # Update session context
        if context_updates:
            session.context.update(context_updates)
        
        if action == "pause":
            session.pause_step("User requested pause")
            result["message"] = "Cooking paused"
            
        elif action == "resume":
            session.resume_step()
            result["message"] = "Cooking resumed"
            
        elif action == "next_step":
            if session.current_step < len(recipe.steps) - 1:
                session.step_status = StepStatus.COMPLETED
                session.advance_step()
                session.step_status = StepStatus.IN_PROGRESS
                result["message"] = f"Advanced to step {session.current_step + 1}"
                
                # Generate introduction for new step
                intro = self.conversation_engine.generate_step_introduction(session, recipe)
                result["step_introduction"] = intro
            else:
                session.step_status = StepStatus.COMPLETED
                result["message"] = "Recipe completed!"
                
        elif action == "repeat_step":
            # Just keep current step, maybe mark as in progress
            session.step_status = StepStatus.IN_PROGRESS
            result["message"] = "Repeating current step"
            
        elif action == "go_back":
            if session.current_step > 0:
                session.current_step -= 1
                session.step_status = StepStatus.IN_PROGRESS
                result["message"] = f"Went back to step {session.current_step + 1}"
            else:
                result["message"] = "Already at the first step"
                
        elif action == "complete_recipe":
            session.step_status = StepStatus.COMPLETED
            result["message"] = "Recipe completed! Great job!"
            
        # Log the action
        logger.info(f"Executed action '{action}' for session {session.session_id}")
        
        return result
    
    def get_cooking_status(self, session_id: str, recipe: Recipe) -> Dict[str, Any]:
        """Get current status of a cooking session"""
        
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        current_step = session.get_current_step(recipe)
        
        return {
            "session_id": session_id,
            "recipe_name": recipe.name,
            "current_step": session.current_step + 1,
            "total_steps": len(recipe.steps),
            "step_status": session.step_status.value,
            "current_instruction": current_step.instruction if current_step else None,
            "estimated_time": current_step.estimated_time if current_step else None,
            "active_interruptions": [
                {
                    "type": i.type.value,
                    "reason": i.reason,
                    "timestamp": i.timestamp.isoformat()
                }
                for i in session.interruptions if not i.resolved
            ],
            "session_context": session.context
        }
    
    def handle_interruption(
        self, 
        session_id: str, 
        interruption_type: InterruptionType, 
        reason: str,
        user_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle a specific interruption (like disasters, timing issues, etc.)"""
        
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Create interruption record
        interruption = CookingInterruption(
            type=interruption_type,
            reason=reason,
            timestamp=datetime.now(),
            step_number=session.current_step,
            user_message=user_message
        )
        
        session.add_interruption(interruption)
        
        # Pause the session if it's a disaster or timing issue
        if interruption_type in [InterruptionType.DISASTER, InterruptionType.TIMING_ISSUE]:
            session.step_status = StepStatus.PAUSED
        
        logger.info(f"Handled interruption: {interruption_type.value} - {reason}")
        
        return {
            "interruption_handled": True,
            "type": interruption_type.value,
            "reason": reason,
            "session_paused": session.step_status == StepStatus.PAUSED
        }
    
    def end_session(self, session_id: str) -> bool:
        """End a cooking session"""
        
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Ended cooking session {session_id}")
            return True
        return False 