#!/usr/bin/env python3
"""
Improved voice-enabled demo with better voice, message skipping, and faster response
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
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Recipe, CookingSession, StepStatus
from services.cooking_service import CookingService
from data.sample_recipes import get_recipe

class VoiceCookingAssistant:
    def __init__(self):
        print("🎤 Initializing improved voice cooking assistant...")
        
        # Initialize text-to-speech with better voice
        try:
            self.tts = pyttsx3.init()
            self.setup_better_voice()
            print("✅ Text-to-speech initialized")
        except Exception as e:
            print(f"❌ TTS error: {e}")
            self.tts = None
        
        # Initialize speech recognition with faster settings
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.setup_fast_recognition()
            print("✅ Speech recognition initialized")
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            self.microphone = None
        
        # Initialize cooking service
        self.cooking_service = CookingService()
        
        # Speech control
        self.speaking = False
        self.should_stop_speaking = False
        self.speech_thread = None
    
    def setup_better_voice(self):
        """Configure text-to-speech with the best available voice"""
        if not self.tts:
            return
            
        try:
            voices = self.tts.getProperty('voices')
            
            # Look for better voices (prefer female, natural-sounding ones)
            preferred_voices = ['samantha', 'alex', 'victoria', 'allison', 'ava']
            best_voice = None
            
            if voices:
                for voice in voices:
                    voice_name = voice.name.lower()
                    print(f"🎭 Available voice: {voice.name}")
                    
                    # Check for preferred voices
                    for preferred in preferred_voices:
                        if preferred in voice_name:
                            best_voice = voice.id
                            print(f"✅ Selected voice: {voice.name}")
                            break
                    if best_voice:
                        break
                
                # If no preferred voice found, use the first one
                if not best_voice and voices:
                    best_voice = voices[0].id
                    print(f"✅ Using default voice: {voices[0].name}")
                
                if best_voice:
                    self.tts.setProperty('voice', best_voice)
            
            # Optimize speech settings
            self.tts.setProperty('rate', 200)  # Slightly faster
            self.tts.setProperty('volume', 0.9)
            
        except Exception as e:
            print(f"⚠️  Voice setup warning: {e}")
    
    def setup_fast_recognition(self):
        """Configure speech recognition for faster response"""
        if not self.microphone:
            return
            
        try:
            print("🔧 Calibrating microphone for fast response...")
            
            # Faster calibration
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Optimize recognition settings
            self.recognizer.energy_threshold = 300  # Lower threshold for faster detection
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.5  # Shorter pause detection
            
            print("✅ Microphone optimized for speed!")
        except Exception as e:
            print(f"⚠️  Microphone setup warning: {e}")
    
    def speak_interruptible(self, text):
        """Speak text but allow interruption"""
        print(f"🤖 AI: {text}")
        
        if not self.tts:
            print("🔇 (Text-to-speech not available)")
            return
        
        self.speaking = True
        self.should_stop_speaking = False
        
        def speak_in_thread():
            try:
                # Split text into chunks for interruptibility
                sentences = text.split('. ')
                
                for i, sentence in enumerate(sentences):
                    if self.should_stop_speaking:
                        print("⏸️  Speech interrupted")
                        break
                    
                    # Add period back if not last sentence
                    if i < len(sentences) - 1:
                        sentence += '.'
                    
                    self.tts.say(sentence)
                    self.tts.runAndWait()
                    
                    # Small pause between sentences to check for interruption
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"⚠️  TTS error: {e}")
            finally:
                self.speaking = False
        
        # Start speaking in background thread
        self.speech_thread = threading.Thread(target=speak_in_thread)
        self.speech_thread.daemon = True
        self.speech_thread.start()
    
    def stop_speaking(self):
        """Stop current speech"""
        if self.speaking:
            self.should_stop_speaking = True
            if self.tts:
                try:
                    self.tts.stop()
                except:
                    pass
            print("🤫 Speech stopped")
    
    def listen_fast(self):
        """Fast voice recognition with reduced timeouts"""
        if not self.microphone:
            return None
            
        try:
            print("🎤 Listening... (speak now)")
            
            with self.microphone as source:
                # Much faster listening - reduced timeouts
                audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=5)
            
            print("🔄 Processing speech...")
            
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
    
    def get_input_fast(self):
        """Get input with interrupt capability"""
        print("\n💬 Say something (or type):")
        print("💡 Say 'skip' to interrupt speech, 'next' to continue")
        
        # If currently speaking, listen for interruption
        if self.speaking:
            print("🎤 Listening for interruption...")
            voice_input = self.listen_fast()
            
            if voice_input:
                voice_lower = voice_input.lower()
                if any(word in voice_lower for word in ['skip', 'stop', 'next', 'continue']):
                    self.stop_speaking()
                    return voice_input
        
        # Wait for speech to finish if not interrupted
        if self.speaking:
            print("⏳ Waiting for speech to finish...")
            while self.speaking:
                time.sleep(0.1)
        
        # Now listen for main input
        if self.microphone:
            voice_input = self.listen_fast()
            if voice_input:
                return voice_input
        
        # Fallback to keyboard
        print("⌨️  Type your response:")
        try:
            return input("You: ").strip()
        except KeyboardInterrupt:
            return "quit"
    
    def mock_ai_response(self, user_input: str, session: CookingSession, recipe: Recipe):
        """Mock AI response with shorter, more natural responses"""
        user_input = user_input.lower()
        
        if "start" in user_input or "begin" in user_input:
            return {
                "response": "Perfect! Let's start cooking. First, season the ground beef in a large bowl.",
                "action": "next_step"
            }
        elif "next" in user_input or "done" in user_input or "ready" in user_input:
            return {
                "response": "Great job! Moving to the next step.",
                "action": "next_step"
            }
        elif "skip" in user_input:
            return {
                "response": "Skipped. What would you like to do?",
                "action": "none"
            }
        elif "pause" in user_input or "wait" in user_input:
            return {
                "response": "Paused. Say 'continue' when ready.",
                "action": "pause"
            }
        elif "resume" in user_input or "continue" in user_input:
            return {
                "response": "Continuing where we left off.",
                "action": "resume"
            }
        elif "repeat" in user_input or "again" in user_input:
            return {
                "response": "Repeating current step.",
                "action": "repeat_step"
            }
        elif "dropped" in user_input or "fell" in user_input or "disaster" in user_input:
            return {
                "response": "No worries! Kitchen accidents happen. Need to restart this step?",
                "action": "pause"
            }
        elif "help" in user_input or "stuck" in user_input:
            return {
                "response": "I'm here to help! What's the problem?",
                "action": "none"
            }
        elif "stop" in user_input or "quit" in user_input or "exit" in user_input:
            return {
                "response": "Thanks for cooking with me!",
                "action": "complete_recipe"
            }
        else:
            return {
                "response": "Got it. Say 'help', 'next', or 'pause' as needed.",
                "action": "none"
            }
    
    def demo_voice_cooking(self):
        """Run the improved voice cooking demo"""
        
        self.speak_interruptible("Welcome to Foodingo! Your AI cooking assistant.")
        
        # Get the burger recipe
        recipe = get_recipe("classic_beef_burger")
        if not recipe:
            self.speak_interruptible("Sorry, couldn't load the recipe.")
            return
        
        self.speak_interruptible(f"Today we're making {recipe.name}. Ready to start?")
        
        # Monkey patch the AI response for demo
        self.cooking_service.conversation_engine.generate_response = self.mock_ai_response
        
        # Start cooking session
        session = self.cooking_service.start_cooking_session(recipe)
        
        print("\n🎯 Voice Commands:")
        print("   • 'start' - Begin cooking")
        print("   • 'next' - Next step")
        print("   • 'skip' - Skip current speech")
        print("   • 'pause' - Pause cooking")
        print("   • 'I dropped something' - Handle disasters")
        print("   • 'help' - Get assistance")
        
        while True:
            # Show current status
            current_step = session.get_current_step(recipe)
            if current_step:
                step_info = f"Step {session.current_step + 1}/{len(recipe.steps)}"
                print(f"\n📍 {step_info}")
                print(f"📝 {current_step.instruction}")
                
                if current_step.tips:
                    print(f"💡 {current_step.tips[0]}")
            else:
                self.speak_interruptible("Recipe complete! Enjoy your burgers!")
                break
            
            # Get user input with fast response
            try:
                user_input = self.get_input_fast()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'stop']:
                    self.speak_interruptible("Thanks for cooking!")
                    break
                
                # Process input
                result = self.cooking_service.process_user_input(
                    session_id=session.session_id,
                    user_input=user_input,
                    recipe=recipe
                )
                
                # Speak the response (interruptible)
                self.speak_interruptible(result['response'])
                
                if result.get('session_update', {}).get('step_introduction'):
                    self.speak_interruptible(result['session_update']['step_introduction'])
                
                # Check completion
                if session.current_step >= len(recipe.steps):
                    self.speak_interruptible("Perfect! Recipe completed!")
                    break
                    
            except KeyboardInterrupt:
                self.stop_speaking()
                self.speak_interruptible("Cooking ended. Thanks!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                self.speak_interruptible("Technical issue. Let's continue.")

def main():
    """Main function"""
    try:
        assistant = VoiceCookingAssistant()
        assistant.demo_voice_cooking()
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Install: pip install pyttsx3 pyaudio")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Falling back to text demo...")
        try:
            subprocess.run([sys.executable, "test_demo.py"])
        except:
            print("Run: python test_demo.py")

if __name__ == "__main__":
    main() 