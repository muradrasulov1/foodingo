#!/usr/bin/env python3
"""
Demo script to test the core cooking assistant functionality
This demonstrates the conversation flow without requiring OpenAI API calls
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Recipe, CookingSession, StepStatus
from services.cooking_service import CookingService
from data.sample_recipes import get_recipe

def mock_ai_response(user_input: str, session: CookingSession, recipe: Recipe):
    """Mock AI response for demo purposes"""
    user_input = user_input.lower()
    
    # Simple pattern matching for demo
    if "start" in user_input or "begin" in user_input:
        return {
            "response": "Perfect! Let's start cooking. First, we'll season the ground beef. Get your mixing bowl ready!",
            "action": "next_step"
        }
    elif "next" in user_input or "done" in user_input:
        return {
            "response": "Great job! Moving to the next step.",
            "action": "next_step"
        }
    elif "pause" in user_input or "wait" in user_input:
        return {
            "response": "No problem! I'll pause here. Take your time, and let me know when you're ready to continue.",
            "action": "pause"
        }
    elif "resume" in user_input or "continue" in user_input or "ready" in user_input:
        return {
            "response": "Welcome back! Let's continue where we left off.",
            "action": "resume"
        }
    elif "repeat" in user_input or "again" in user_input:
        return {
            "response": "Sure! Let me repeat the current step for you.",
            "action": "repeat_step"
        }
    elif "dropped" in user_input or "fell" in user_input or "disaster" in user_input:
        return {
            "response": "Oh no! Kitchen accidents happen to everyone. No worries at all! Do you need to start this step over, or can you continue?",
            "action": "pause"
        }
    elif "help" in user_input or "stuck" in user_input:
        return {
            "response": "I'm here to help! What's going on? Are you having trouble with the current step?",
            "action": "none"
        }
    else:
        return {
            "response": "I understand! Let me know if you need help, want to continue, or need to pause.",
            "action": "none"
        }

def demo_cooking_session():
    """Demonstrate a cooking session with the burger recipe"""
    
    print("🍔 Welcome to Foodingo - AI Cooking Assistant Demo!")
    print("=" * 50)
    
    # Get the burger recipe
    recipe = get_recipe("classic_beef_burger")
    if not recipe:
        print("❌ Could not load recipe!")
        return
    
    print(f"📋 Recipe: {recipe.name}")
    print(f"📝 Description: {recipe.description}")
    print(f"👥 Serves: {recipe.servings}")
    print(f"⏱️  Total time: {recipe.prep_time + recipe.cook_time} minutes")
    print(f"🔧 Difficulty: {recipe.difficulty}")
    print()
    
    # Initialize cooking service
    cooking_service = CookingService()
    
    # Monkey patch the AI response for demo
    cooking_service.conversation_engine.generate_response = mock_ai_response
    
    # Start cooking session
    session = cooking_service.start_cooking_session(recipe)
    print(f"🎯 Started cooking session: {session.session_id}")
    print()
    
    # Interactive demo loop
    print("💬 Chat with your AI cooking assistant!")
    print("   Try saying: 'start', 'next', 'pause', 'resume', 'repeat', 'help'")
    print("   Or simulate disasters: 'I dropped the patty'")
    print("   Type 'quit' to exit")
    print()
    
    while True:
        # Show current status
        current_step = session.get_current_step(recipe)
        if current_step:
            print(f"📍 Step {session.current_step + 1}/{len(recipe.steps)}: {session.step_status.value}")
            print(f"   {current_step.instruction}")
            if current_step.tips:
                print(f"💡 Tips: {', '.join(current_step.tips)}")
        else:
            print("🎉 Recipe completed!")
        
        print()
        
        # Get user input
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'stop']:
            break
        
        if not user_input:
            continue
        
        # Process input
        try:
            result = cooking_service.process_user_input(
                session_id=session.session_id,
                user_input=user_input,
                recipe=recipe
            )
            
            print(f"🤖 AI: {result['response']}")
            
            if result.get('session_update', {}).get('step_introduction'):
                print(f"📝 {result['session_update']['step_introduction']}")
            
            print()
            
            # Check if recipe is complete
            if session.current_step >= len(recipe.steps):
                print("🎉 Congratulations! You've completed the recipe!")
                print("   Your delicious burgers are ready to enjoy!")
                break
                
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
    
    print("👋 Thanks for using Foodingo! Happy cooking!")

if __name__ == "__main__":
    demo_cooking_session() 