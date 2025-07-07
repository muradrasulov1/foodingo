#!/usr/bin/env python3
"""
Final voice demo - fixes audio glitches and gives more microphone time
"""

import sys
import os
import threading
import time
import speech_recognition as sr
import pyttsx3
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Recipe, CookingSession, StepStatus
from services.cooking_service import CookingService
from data.sample_recipes import get_recipe

class VoiceCookingAssistant:
    def __init__(self):
        print("🎤 Initializing voice cooking assistant...")
        
        # Initialize text-to-speech (single-threaded to avoid glitches)
        try:
            self.tts = pyttsx3.init()
            self.setup_voice()
            print("✅ Text-to-speech initialized")
        except Exception as e:
            print(f"❌ TTS error: {e}")
            self.tts = None
        
        # Initialize speech recognition with longer timeouts
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.setup_microphone()
            print("✅ Speech recognition initialized")
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            self.microphone = None
        
        # Initialize cooking service
        self.cooking_service = CookingService()
        
        # Speech control (simplified to avoid threading issues)
        self.currently_speaking = False
    
    def setup_voice(self):
        """Configure text-to-speech with best voice"""
        if not self.tts:
            return
            
        try:
            voices = self.tts.getProperty('voices')
            
            # Look for good voices
            preferred_voices = ['samantha', 'alex', 'victoria', 'allison', 'ava', 'karen', 'moira']
            best_voice = None
            
            if voices:
                print("🎭 Finding best voice...")
                for voice in voices:
                    voice_name = voice.name.lower()
                    
                    # Check for preferred voices
                    for preferred in preferred_voices:
                        if preferred in voice_name and 'english' in voice_name:
                            best_voice = voice.id
                            print(f"✅ Selected voice: {voice.name}")
                            break
                    if best_voice:
                        break
                
                # Fallback to first English voice
                if not best_voice:
                    for voice in voices:
                        if 'english' in voice.name.lower():
                            best_voice = voice.id
                            print(f"✅ Using voice: {voice.name}")
                            break
                
                if best_voice:
                    self.tts.setProperty('voice', best_voice)
            
            # Optimize speech settings to avoid glitches
            self.tts.setProperty('rate', 190)  # Good speed
            self.tts.setProperty('volume', 0.8)  # Slightly lower to avoid distortion
            
        except Exception as e:
            print(f"⚠️  Voice setup warning: {e}")
    
    def setup_microphone(self):
        """Configure microphone with longer timeouts"""
        if not self.microphone:
            return
            
        try:
            print("🔧 Setting up microphone...")
            
            # Quick calibration
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Better recognition settings
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8  # Wait longer for pauses
            
            print("✅ Microphone ready!")
        except Exception as e:
            print(f"⚠️  Microphone setup warning: {e}")
    
    def speak_simple(self, text):
        """Simple speech without threading to avoid glitches"""
        print(f"🤖 AI: {text}")
        
        if not self.tts:
            print("🔇 (Text-to-speech not available)")
            return
        
        try:
            self.currently_speaking = True
            
            # Stop any previous speech first
            self.tts.stop()
            time.sleep(0.1)  # Small pause to clear audio buffer
            
            # Speak in main thread to avoid conflicts
            self.tts.say(text)
            self.tts.runAndWait()
            
        except Exception as e:
            print(f"⚠️  TTS error: {e}")
        finally:
            self.currently_speaking = False
    
    def listen_with_longer_timeout(self):
        """Listen with much longer timeout"""
        if not self.microphone:
            return None
            
        try:
            print("🎤 Listening... (you have 10 seconds to speak)")
            
            with self.microphone as source:
                # Much longer timeout - 10 seconds to start speaking
                # 10 seconds max phrase length
                audio = self.recognizer.listen(
                    source, 
                    timeout=10,  # 10 seconds to start speaking
                    phrase_time_limit=10  # 10 seconds max phrase
                )
            
            print("🔄 Processing your speech...")
            
            # Recognize speech
            text = self.recognizer.recognize_google(audio)
            print(f"👤 You said: '{text}'")
            return text
            
        except sr.WaitTimeoutError:
            print("⏱️  No speech detected in 10 seconds")
            return None
        except sr.UnknownValueError:
            print("🤔 Could not understand - please speak more clearly")
            return None
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
            return None
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            return None
    
    def get_input_patient(self):
        """Get input with patient waiting"""
        print("\n" + "="*50)
        print("💬 Your turn to speak!")
        print("🎤 You have 10 seconds to start speaking")
        print("⌨️  Or just press Enter to type instead")
        print("="*50)
        
        # Try voice input with long timeout
        if self.microphone:
            voice_input = self.listen_with_longer_timeout()
            if voice_input:
                return voice_input
        
        # Fallback to keyboard
        print("\n⌨️  Voice timeout - please type your response:")
        try:
            return input("You: ").strip()
        except KeyboardInterrupt:
            return "quit"
    
    def mock_ai_response(self, user_input: str, session: CookingSession, recipe: Recipe):
        """Mock AI response with concise responses"""
        user_input = user_input.lower()
        
        if "start" in user_input or "begin" in user_input:
            return {
                "response": "Perfect! Let's start cooking. First, season the ground beef in a large bowl.",
                "action": "next_step"
            }
        elif "next" in user_input or "done" in user_input or "ready" in user_input:
            return {
                "response": "Great! Moving to the next step.",
                "action": "next_step"
            }
        elif "pause" in user_input or "wait" in user_input:
            return {
                "response": "Paused. Say continue when ready.",
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
                "response": "Got it. Say help, next, or pause as needed.",
                "action": "none"
            }
    
    def demo_voice_cooking(self):
        """Run the voice cooking demo"""
        
        self.speak_simple("Welcome to Foodingo! Your AI cooking assistant.")
        time.sleep(0.5)  # Pause between speeches
        
        # Get the burger recipe
        recipe = get_recipe("classic_beef_burger")
        if not recipe:
            self.speak_simple("Sorry, couldn't load the recipe.")
            return
        
        self.speak_simple(f"Today we're making {recipe.name}. Ready to start?")
        
        # Monkey patch the AI response for demo
        self.cooking_service.conversation_engine.generate_response = self.mock_ai_response
        
        # Start cooking session
        session = self.cooking_service.start_cooking_session(recipe)
        
        print("\n🎯 Voice Commands:")
        print("   • 'start' - Begin cooking")
        print("   • 'next' - Next step") 
        print("   • 'pause' - Pause cooking")
        print("   • 'I dropped something' - Handle disasters")
        print("   • 'help' - Get assistance")
        print("   • 'quit' - Exit")
        
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
                self.speak_simple("Recipe complete! Enjoy your burgers!")
                break
            
            # Get user input with patience
            try:
                user_input = self.get_input_patient()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'stop']:
                    self.speak_simple("Thanks for cooking!")
                    break
                
                # Process input
                result = self.cooking_service.process_user_input(
                    session_id=session.session_id,
                    user_input=user_input,
                    recipe=recipe
                )
                
                # Speak response with pause
                time.sleep(0.3)  # Small pause before responding
                self.speak_simple(result['response'])
                
                if result.get('session_update', {}).get('step_introduction'):
                    time.sleep(0.5)
                    self.speak_simple(result['session_update']['step_introduction'])
                
                # Check completion
                if session.current_step >= len(recipe.steps):
                    time.sleep(0.5)
                    self.speak_simple("Perfect! Recipe completed!")
                    break
                    
            except KeyboardInterrupt:
                self.speak_simple("Cooking ended. Thanks!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                self.speak_simple("Technical issue. Let's continue.")

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