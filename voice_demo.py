#!/usr/bin/env python3
"""
Voice-enabled demo of the cooking assistant
This version uses your microphone for input and speaks responses back to you!
"""

import sys
import os
import threading
import time
import queue
import speech_recognition as sr
import pyttsx3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Recipe, CookingSession, StepStatus
from services.cooking_service import CookingService
from data.sample_recipes import get_recipe

class VoiceCookingAssistant:
    def __init__(self):
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize text-to-speech
        self.tts = pyttsx3.init()
        self.setup_voice()
        
        # Initialize cooking service
        self.cooking_service = CookingService()
        
        # Voice input queue
        self.voice_queue = queue.Queue()
        self.listening = False
        
        print("🎤 Setting up voice recognition...")
        self.calibrate_microphone()
    
    def setup_voice(self):
        """Configure text-to-speech voice"""
        voices = self.tts.getProperty('voices')
        
        # Try to find a good voice (prefer female voices for cooking)
        preferred_voice = None
        for voice in voices:
            if 'female' in voice.name.lower() or 'samantha' in voice.name.lower():
                preferred_voice = voice.id
                break
        
        if preferred_voice:
            self.tts.setProperty('voice', preferred_voice)
        
        # Set speech rate (words per minute)
        self.tts.setProperty('rate', 180)  # Slightly slower for cooking instructions
        
        # Set volume
        self.tts.setProperty('volume', 0.9)
    
    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        print("🔧 Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print("✅ Microphone calibrated!")
    
    def speak(self, text):
        """Convert text to speech"""
        print(f"🤖 AI: {text}")
        self.tts.say(text)
        self.tts.runAndWait()
    
    def listen_for_voice(self):
        """Listen for voice input in a separate thread"""
        while self.listening:
            try:
                with self.microphone as source:
                    print("🎤 Listening... (speak now)")
                    # Listen for audio with a timeout
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                try:
                    # Use Google's speech recognition
                    text = self.recognizer.recognize_google(audio)
                    print(f"👤 You said: {text}")
                    self.voice_queue.put(text)
                except sr.UnknownValueError:
                    # Speech was unclear
                    pass
                except sr.RequestError as e:
                    print(f"❌ Speech recognition error: {e}")
                    
            except sr.WaitTimeoutError:
                # No speech detected, continue listening
                pass
            except Exception as e:
                print(f"❌ Microphone error: {e}")
                time.sleep(1)
    
    def get_voice_input(self, timeout=10):
        """Get voice input with timeout"""
        print(f"🎤 Say something (or press Enter to skip voice input)...")
        
        # Start listening thread
        self.listening = True
        listen_thread = threading.Thread(target=self.listen_for_voice)
        listen_thread.daemon = True
        listen_thread.start()
        
        # Wait for voice input or timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check for voice input
                voice_input = self.voice_queue.get_nowait()
                self.listening = False
                return voice_input
            except queue.Empty:
                # Check if user pressed Enter to skip
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    keyboard_input = input().strip()
                    self.listening = False
                    if keyboard_input:
                        return keyboard_input
                time.sleep(0.1)
        
        self.listening = False
        return None
    
    def mock_ai_response(self, user_input: str, session: CookingSession, recipe: Recipe):
        """Mock AI response with more natural speech patterns"""
        user_input = user_input.lower()
        
        if "start" in user_input or "begin" in user_input:
            return {
                "response": "Perfect! Let's start cooking together. First, we'll season the ground beef. Get your mixing bowl ready, and let me know when you're set!",
                "action": "next_step"
            }
        elif "next" in user_input or "done" in user_input or "ready" in user_input:
            return {
                "response": "Excellent work! Let's move on to the next step.",
                "action": "next_step"
            }
        elif "pause" in user_input or "wait" in user_input or "hold" in user_input:
            return {
                "response": "No problem at all! I'll pause right here. Take all the time you need, and just say 'continue' when you're ready.",
                "action": "pause"
            }
        elif "resume" in user_input or "continue" in user_input:
            return {
                "response": "Great! Welcome back. Let's pick up where we left off.",
                "action": "resume"
            }
        elif "repeat" in user_input or "again" in user_input:
            return {
                "response": "Of course! Let me repeat the current step for you.",
                "action": "repeat_step"
            }
        elif "dropped" in user_input or "fell" in user_input or "disaster" in user_input or "mess" in user_input:
            return {
                "response": "Oh no! Don't worry - kitchen accidents happen to the best of us. Take a deep breath. Do you need to start this step over, or can we work with what you have?",
                "action": "pause"
            }
        elif "help" in user_input or "stuck" in user_input or "confused" in user_input:
            return {
                "response": "I'm here to help! What's going on? Tell me what you're having trouble with and I'll guide you through it.",
                "action": "none"
            }
        elif "stop" in user_input or "quit" in user_input or "exit" in user_input:
            return {
                "response": "Thanks for cooking with me! Hope to help you again soon.",
                "action": "complete_recipe"
            }
        else:
            return {
                "response": "I understand. Let me know if you need help, want to continue, or need to pause. Just speak naturally - I'm here to help!",
                "action": "none"
            }
    
    def demo_voice_cooking(self):
        """Run the voice-enabled cooking demo"""
        
        self.speak("Welcome to Foodingo, your AI cooking assistant! I'm here to help you cook delicious meals.")
        
        # Get the burger recipe
        recipe = get_recipe("classic_beef_burger")
        if not recipe:
            self.speak("I'm sorry, I couldn't load the recipe. Please try again.")
            return
        
        self.speak(f"Today we're making {recipe.name}. It serves {recipe.servings} people and takes about {recipe.prep_time + recipe.cook_time} minutes total.")
        
        # Monkey patch the AI response for demo
        self.cooking_service.conversation_engine.generate_response = self.mock_ai_response
        
        # Start cooking session
        session = self.cooking_service.start_cooking_session(recipe)
        
        self.speak("I can understand your voice commands. Try saying things like 'start cooking', 'next step', 'pause', or 'I dropped something'. When you're ready to begin, just say 'start'!")
        
        while True:
            # Show current status
            current_step = session.get_current_step(recipe)
            if current_step:
                step_info = f"Step {session.current_step + 1} of {len(recipe.steps)}. {current_step.instruction}"
                print(f"📍 {step_info}")
                
                if current_step.tips:
                    tip = f"Here's a tip: {current_step.tips[0]}"
                    print(f"💡 {tip}")
            else:
                self.speak("Congratulations! You've completed the recipe! Your delicious burgers are ready to enjoy!")
                break
            
            # Get voice input
            try:
                user_input = self.get_voice_input(timeout=30)
                
                if not user_input:
                    self.speak("I didn't hear anything. Say 'help' if you need assistance, or 'continue' to keep going.")
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'stop cooking']:
                    self.speak("Thanks for cooking with me! Have a great meal!")
                    break
                
                # Process input
                result = self.cooking_service.process_user_input(
                    session_id=session.session_id,
                    user_input=user_input,
                    recipe=recipe
                )
                
                # Speak the response
                self.speak(result['response'])
                
                if result.get('session_update', {}).get('step_introduction'):
                    self.speak(result['session_update']['step_introduction'])
                
                # Check if recipe is complete
                if session.current_step >= len(recipe.steps):
                    self.speak("Perfect! You've successfully completed the recipe. Enjoy your delicious homemade burgers!")
                    break
                    
            except KeyboardInterrupt:
                self.speak("Cooking session ended. Thanks for using Foodingo!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                self.speak("I'm sorry, I had a technical issue. Let's try again.")

def main():
    try:
        # Check if required packages are available
        import select
        assistant = VoiceCookingAssistant()
        assistant.demo_voice_cooking()
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please install required packages:")
        print("pip install pyttsx3")
        print("On macOS, you might also need: brew install espeak")
    except Exception as e:
        print(f"❌ Error starting voice assistant: {e}")
        print("Falling back to text-based demo...")
        os.system("python test_demo.py")

if __name__ == "__main__":
    main() 