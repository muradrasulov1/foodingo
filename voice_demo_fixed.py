#!/usr/bin/env python3
"""
Fixed voice-enabled demo of the cooking assistant
This version properly handles microphone access and threading
"""

import sys
import os
import threading
import time
import queue
import select
import speech_recognition as sr
import pyttsx3
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Recipe, CookingSession, StepStatus
from services.cooking_service import CookingService
from data.sample_recipes import get_recipe

class VoiceCookingAssistant:
    def __init__(self):
        print("🎤 Initializing voice cooking assistant...")
        
        # Initialize text-to-speech first
        try:
            self.tts = pyttsx3.init()
            self.setup_voice()
            print("✅ Text-to-speech initialized")
        except Exception as e:
            print(f"❌ TTS error: {e}")
            self.tts = None
        
        # Initialize speech recognition
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.calibrate_microphone()
            print("✅ Speech recognition initialized")
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            self.microphone = None
        
        # Initialize cooking service
        self.cooking_service = CookingService()
        
        # Voice input queue
        self.voice_queue = queue.Queue()
        self.listening = False
        self.listen_thread = None
    
    def setup_voice(self):
        """Configure text-to-speech voice"""
        if not self.tts:
            return
            
        try:
            voices = self.tts.getProperty('voices')
            
            # Try to find a good voice
            if voices:
                # Use the first available voice
                self.tts.setProperty('voice', voices[0].id)
            
            # Set speech rate (words per minute)
            self.tts.setProperty('rate', 180)
            
            # Set volume
            self.tts.setProperty('volume', 0.9)
        except Exception as e:
            print(f"⚠️  Voice setup warning: {e}")
    
    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        if not self.microphone:
            return
            
        try:
            print("🔧 Calibrating microphone...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Microphone calibrated!")
        except Exception as e:
            print(f"⚠️  Microphone calibration warning: {e}")
    
    def speak(self, text):
        """Convert text to speech"""
        print(f"🤖 AI: {text}")
        
        if self.tts:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception as e:
                print(f"⚠️  TTS error: {e}")
        else:
            print("🔇 (Text-to-speech not available)")
    
    def listen_once(self):
        """Listen for a single voice input"""
        if not self.microphone:
            return None
            
        try:
            print("🎤 Listening... (speak now)")
            with self.microphone as source:
                # Listen for audio with timeout
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=8)
            
            # Recognize speech
            text = self.recognizer.recognize_google(audio)
            print(f"👤 You said: {text}")
            return text
            
        except sr.WaitTimeoutError:
            print("⏱️  No speech detected")
            return None
        except sr.UnknownValueError:
            print("🤔 Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
            return None
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            return None
    
    def get_input(self):
        """Get input from voice or keyboard"""
        print("\n💬 Say something or type your response:")
        
        # Try voice input first
        if self.microphone:
            voice_input = self.listen_once()
            if voice_input:
                return voice_input
        
        # Fallback to keyboard input
        print("⌨️  Voice not detected. Type your response:")
        try:
            return input("You: ").strip()
        except KeyboardInterrupt:
            return "quit"
    
    def mock_ai_response(self, user_input: str, session: CookingSession, recipe: Recipe):
        """Mock AI response with natural speech patterns"""
        user_input = user_input.lower()
        
        if "start" in user_input or "begin" in user_input:
            return {
                "response": "Perfect! Let's start cooking together. First, we'll season the ground beef. Get your mixing bowl ready!",
                "action": "next_step"
            }
        elif "next" in user_input or "done" in user_input or "ready" in user_input:
            return {
                "response": "Excellent work! Let's move on to the next step.",
                "action": "next_step"
            }
        elif "pause" in user_input or "wait" in user_input or "hold" in user_input:
            return {
                "response": "No problem! I'll pause right here. Take your time, and say 'continue' when you're ready.",
                "action": "pause"
            }
        elif "resume" in user_input or "continue" in user_input:
            return {
                "response": "Great! Welcome back. Let's pick up where we left off.",
                "action": "resume"
            }
        elif "repeat" in user_input or "again" in user_input:
            return {
                "response": "Of course! Let me repeat the current step.",
                "action": "repeat_step"
            }
        elif "dropped" in user_input or "fell" in user_input or "disaster" in user_input:
            return {
                "response": "Oh no! Don't worry - kitchen accidents happen. Take a deep breath. Do you need to start this step over?",
                "action": "pause"
            }
        elif "help" in user_input or "stuck" in user_input:
            return {
                "response": "I'm here to help! What's going on? Tell me what you're having trouble with.",
                "action": "none"
            }
        elif "stop" in user_input or "quit" in user_input or "exit" in user_input:
            return {
                "response": "Thanks for cooking with me! Hope to help you again soon.",
                "action": "complete_recipe"
            }
        else:
            return {
                "response": "I understand. Let me know if you need help, want to continue, or need to pause.",
                "action": "none"
            }
    
    def demo_voice_cooking(self):
        """Run the voice-enabled cooking demo"""
        
        self.speak("Welcome to Foodingo, your AI cooking assistant!")
        
        # Get the burger recipe
        recipe = get_recipe("classic_beef_burger")
        if not recipe:
            self.speak("I'm sorry, I couldn't load the recipe.")
            return
        
        self.speak(f"Today we're making {recipe.name}. It serves {recipe.servings} people and takes about {recipe.prep_time + recipe.cook_time} minutes total.")
        
        # Monkey patch the AI response for demo
        self.cooking_service.conversation_engine.generate_response = self.mock_ai_response
        
        # Start cooking session
        session = self.cooking_service.start_cooking_session(recipe)
        
        self.speak("I can understand voice commands or text input. Try saying 'start cooking', 'next step', 'pause', or 'I dropped something'. When you're ready to begin, just say 'start'!")
        
        while True:
            # Show current status
            current_step = session.get_current_step(recipe)
            if current_step:
                step_info = f"Step {session.current_step + 1} of {len(recipe.steps)}"
                print(f"\n📍 {step_info}")
                print(f"📝 {current_step.instruction}")
                
                if current_step.tips:
                    print(f"💡 Tip: {current_step.tips[0]}")
            else:
                self.speak("Congratulations! You've completed the recipe!")
                break
            
            # Get user input
            try:
                user_input = self.get_input()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'stop']:
                    self.speak("Thanks for cooking with me!")
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
                    self.speak("Perfect! You've completed the recipe. Enjoy your delicious burgers!")
                    break
                    
            except KeyboardInterrupt:
                self.speak("Cooking session ended. Thanks for using Foodingo!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                self.speak("I had a technical issue. Let's try again.")

def main():
    """Main function with proper error handling"""
    try:
        assistant = VoiceCookingAssistant()
        assistant.demo_voice_cooking()
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("\nTo install voice packages:")
        print("pip install pyttsx3")
        print("pip install pyaudio")
        print("\nOn macOS, you might need:")
        print("brew install portaudio")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nFalling back to text-only demo...")
        try:
            import subprocess
            subprocess.run([sys.executable, "test_demo.py"])
        except:
            print("Please run: python test_demo.py")

if __name__ == "__main__":
    main() 