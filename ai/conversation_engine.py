import openai
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

from models import Recipe, CookingSession, CookingInterruption, StepStatus, InterruptionType
from config import Config

logger = logging.getLogger(__name__)

class ConversationEngine:
    """
    The brain of the cooking assistant. Handles all AI-powered conversation,
    context management, and intelligent responses during cooking.
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
    def generate_response(
        self, 
        user_input: str, 
        session: CookingSession, 
        recipe: Recipe
    ) -> Dict[str, Any]:
        """
        Generate an intelligent response based on user input and cooking context.
        
        Returns:
            Dict containing:
            - response: The AI's text response
            - action: Any action to take (pause, resume, next_step, etc.)
            - context_updates: Updates to session context
        """
        
        # Build context for the AI
        context = self._build_context(session, recipe)
        
        # Create the system prompt
        system_prompt = self._create_system_prompt(recipe, session)
        
        # Build conversation history
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {context}\n\nUser says: {user_input}"}
        ]
        
        # Add recent conversation history
        for msg in session.conversation_history[-5:]:  # Last 5 messages for context
            messages.append(msg)
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=messages,
                temperature=Config.AI_TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
                functions=[
                    {
                        "name": "cooking_action",
                        "description": "Take a cooking-related action",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["pause", "resume", "next_step", "repeat_step", "go_back", "complete_recipe", "none"]
                                },
                                "response": {
                                    "type": "string",
                                    "description": "The conversational response to the user"
                                },
                                "context_updates": {
                                    "type": "object",
                                    "description": "Updates to the cooking session context"
                                }
                            },
                            "required": ["action", "response"]
                        }
                    }
                ],
                function_call="auto"
            )
            
            # Parse the response
            result = self._parse_ai_response(response)
            
            # Update conversation history
            session.conversation_history.append({
                "role": "user", 
                "content": user_input
            })
            session.conversation_history.append({
                "role": "assistant", 
                "content": result["response"]
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return {
                "response": "I'm sorry, I had trouble understanding that. Could you try again?",
                "action": "none",
                "context_updates": {}
            }
    
    def _build_context(self, session: CookingSession, recipe: Recipe) -> str:
        """Build a context string for the AI about the current cooking state"""
        
        current_step = session.get_current_step(recipe)
        context_parts = []
        
        # Recipe info
        context_parts.append(f"Recipe: {recipe.name}")
        context_parts.append(f"Total steps: {len(recipe.steps)}")
        
        # Current progress
        context_parts.append(f"Current step: {session.current_step + 1}")
        context_parts.append(f"Step status: {session.step_status}")
        
        if current_step:
            context_parts.append(f"Current instruction: {current_step.instruction}")
            if current_step.estimated_time:
                context_parts.append(f"Estimated time: {current_step.estimated_time} seconds")
        
        # Recent interruptions
        recent_interruptions = [i for i in session.interruptions if not i.resolved]
        if recent_interruptions:
            context_parts.append("Active interruptions:")
            for interruption in recent_interruptions[-3:]:
                context_parts.append(f"- {interruption.type}: {interruption.reason}")
        
        # Session context
        if session.context:
            context_parts.append("Session context:")
            for key, value in session.context.items():
                context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts)
    
    def _create_system_prompt(self, recipe: Recipe, session: CookingSession) -> str:
        """Create the system prompt that defines the AI's behavior"""
        
        return f"""You are an AI cooking assistant helping someone cook {recipe.name}. 

Your personality:
- Friendly, encouraging, and patient
- Understand that cooking is messy and unpredictable
- Handle interruptions gracefully
- Adapt to the user's pace
- Provide helpful tips and encouragement

Key behaviors:
1. ALWAYS be supportive when things go wrong (spills, burns, dropped food)
2. Pause intelligently when the user needs time
3. Provide context when resuming after interruptions
4. Give clear, actionable guidance
5. Don't rush the user - let them work at their own pace
6. Offer alternatives when ingredients are missing or things go wrong

Current cooking context:
- Recipe: {recipe.name}
- Step {session.current_step + 1} of {len(recipe.steps)}
- Status: {session.step_status}

Use the cooking_action function to:
- "pause": When user needs to stop/handle something
- "resume": When user is ready to continue
- "next_step": When current step is complete
- "repeat_step": When user wants to hear instructions again
- "go_back": When user wants to return to previous step
- "complete_recipe": When all steps are done
- "none": For general conversation/questions

Always provide a warm, conversational response along with any action."""
    
    def _parse_ai_response(self, response) -> Dict[str, Any]:
        """Parse the AI response and extract action + response"""
        
        # Check if AI used function calling
        if response.choices[0].message.function_call:
            try:
                function_args = json.loads(response.choices[0].message.function_call.arguments)
                return {
                    "response": function_args.get("response", ""),
                    "action": function_args.get("action", "none"),
                    "context_updates": function_args.get("context_updates", {})
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback to regular message
        return {
            "response": response.choices[0].message.content,
            "action": "none",
            "context_updates": {}
        }
    
    def generate_step_introduction(self, session: CookingSession, recipe: Recipe) -> str:
        """Generate an introduction for a new step"""
        
        current_step = session.get_current_step(recipe)
        if not current_step:
            return "We've completed all the steps! Great job cooking!"
        
        step_num = session.current_step + 1
        total_steps = len(recipe.steps)
        
        # Build context about what we've done and what's next
        context = f"""
        We're on step {step_num} of {total_steps} for {recipe.name}.
        Current step: {current_step.instruction}
        """
        
        if current_step.estimated_time:
            context += f"\nThis should take about {current_step.estimated_time // 60} minutes."
        
        if current_step.tips:
            context += f"\nTips: {', '.join(current_step.tips)}"
        
        messages = [
            {
                "role": "system", 
                "content": "You are a cooking assistant. Introduce the next step in a friendly, encouraging way. Keep it concise but helpful."
            },
            {
                "role": "user", 
                "content": context
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating step introduction: {e}")
            return f"Step {step_num}: {current_step.instruction}" 