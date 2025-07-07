#!/usr/bin/env python3
"""
Kitchen-optimized voice demo with continuous listening and noise filtering
"""

import sys
import os
import threading
import time
import queue
import select
import signal
import atexit
import termios
import tty
import speech_recognition as sr
import pyttsx3
import subprocess
from collections import deque

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Recipe, CookingSession, StepStatus
from services.cooking_service import CookingService
from data.sample_recipes import get_recipe

class KitchenVoiceAssistant:
    def __init__(self):
        print("🍳 Initializing kitchen-ready voice assistant...")
        
        # Initialize TTS with proper cleanup
        try:
            self.tts = pyttsx3.init()
            self.setup_kitchen_voice()
            print("✅ Kitchen-optimized voice ready")
        except Exception as e:
            print(f"❌ TTS error: {e}")
            self.tts = None
        
        # Initialize speech recognition for noisy environments
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            self.setup_kitchen_microphone()
            print("✅ Kitchen microphone ready")
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            self.microphone = None
        
        # Initialize cooking service
        self.cooking_service = CookingService()
        
        # Continuous listening control
        self.listening_active = False
        self.listen_thread = None
        self.voice_queue = queue.Queue()
        
        # Speech control with proper interruption
        self.currently_speaking = False
        self.speech_interrupted = False
        self.speech_thread = None
        
        # Spacebar interrupt system
        self.spacebar_monitoring = False
        self.spacebar_thread = None
        
        # Kitchen-specific settings
        self.wake_words = ['hey', 'foodingo', 'assistant', 'kitchen', 'cooking']
        self.command_words = ['start', 'next', 'pause', 'continue', 'help', 'repeat', 'stop', 'skip', 'done', 'ready', 'begin']
        
        # Recent speech buffer to avoid duplicates
        self.recent_speech = deque(maxlen=3)
        
        # Register cleanup handlers
        self.setup_cleanup_handlers()
    
    def setup_cleanup_handlers(self):
        """Setup cleanup handlers for proper process termination"""
        # Register cleanup function to run on exit
        atexit.register(self.cleanup)
        
        # Handle Ctrl+C and other signals
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        print(f"\n🛑 Received signal {signum}, cleaning up...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up all resources and threads"""
        print("🧹 Cleaning up voice assistant...")
        
        try:
            # Stop continuous listening
            self.stop_continuous_listening()
            
            # Stop spacebar monitoring
            self.stop_spacebar_monitoring()
            
            # Stop any ongoing speech
            if self.tts:
                self.tts.stop()
                time.sleep(0.2)
            
            # Kill any running say processes
            subprocess.run(['killall', 'say'], check=False)
            
            # Clear speech queue
            while not self.voice_queue.empty():
                try:
                    self.voice_queue.get_nowait()
                except queue.Empty:
                    break
            
            print("✅ Cleanup complete")
            
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    def setup_kitchen_voice(self):
        """Setup the best possible voice"""
        if not self.tts:
            return
            
        try:
            voices = self.tts.getProperty('voices')
            
            if voices:
                print("🎭 Available voices:")
                for i, voice in enumerate(voices[:10]):  # Show first 10
                    print(f"   {i}: {voice.name}")
                
                # Look for the best voices in order of preference
                best_voices = [
                    'Samantha',  # macOS high-quality female voice
                    'Alex',      # macOS high-quality male voice  
                    'Victoria',  # Good female voice
                    'Karen',     # Clear female voice
                    'Moira'      # Irish female voice
                ]
                
                selected_voice = None
                for preferred in best_voices:
                    for voice in voices:
                        if preferred.lower() in voice.name.lower():
                            selected_voice = voice.id
                            print(f"✅ Selected: {voice.name}")
                            break
                    if selected_voice:
                        break
                
                # If no preferred voice, force use of Alex (always works)
                if not selected_voice:
                    for voice in voices:
                        if 'alex' in voice.name.lower():
                            selected_voice = voice.id
                            print(f"✅ Using fallback: {voice.name}")
                            break
                
                # Last resort - use first available voice
                if not selected_voice and voices:
                    selected_voice = voices[0].id
                    print(f"✅ Using first available: {voices[0].name}")
                
                if selected_voice:
                    self.tts.setProperty('voice', selected_voice)
            
            # Optimized speech settings to reduce barking
            self.tts.setProperty('rate', 180)    # Good pace
            self.tts.setProperty('volume', 0.9)  # Higher volume to ensure it's heard
            
            print("🔧 Voice configured for clarity")
            
            # Test the voice to make sure it works
            print("🎵 Testing voice...")
            try:
                self.tts.say("Voice test")
                self.tts.runAndWait()
                print("✅ Voice test complete - you should have heard 'Voice test'")
            except Exception as e:
                print(f"❌ Voice test failed: {e}")
                print("🔧 Trying alternative voice setup...")
                # Try using system 'say' command as backup
                import subprocess
                try:
                    subprocess.run(['say', 'Voice test backup'], check=True)
                    print("✅ Backup voice working")
                except:
                    print("❌ No voice output available")
            
        except Exception as e:
            print(f"⚠️  Voice setup: {e}")
    
    def setup_kitchen_microphone(self):
        """Setup microphone for noisy kitchen environment"""
        if not self.microphone:
            return
            
        try:
            print("🔧 Calibrating for kitchen noise...")
            
            # Extended calibration for kitchen environment
            with self.microphone as source:
                print("   (Calibrating for background noise - let kitchen run normally)")
                self.recognizer.adjust_for_ambient_noise(source, duration=3)
            
            # Kitchen-optimized settings
            self.recognizer.energy_threshold = 400  # Higher threshold for noisy kitchen
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 1.0  # Longer pause for kitchen speech
            self.recognizer.phrase_time_limit = 8  # Reasonable phrase length
            
            print("✅ Kitchen microphone calibrated!")
            
        except Exception as e:
            print(f"⚠️  Microphone setup: {e}")
    
    def speak_interruptible(self, text):
        """Speak with spacebar interrupt capability"""
        print(f"\n🤖 AI: {text}")
        print("⏸️  Press SPACEBAR once to interrupt speech")
        print("─" * 50)
        
        try:
            self.currently_speaking = True
            self.speech_interrupted = False
            
            # COMPLETELY stop voice listening to prevent ANY feedback
            listening_was_active = self.listening_active
            if listening_was_active:
                self.listening_active = False
                time.sleep(1.0)  # Longer pause to ensure complete stop
            
            # Start spacebar monitoring ONLY during speech
            self.start_spacebar_monitoring()
            
            # Start speech in background
            import threading
            def speak_background():
                try:
                    subprocess.run(['say', text], timeout=20, check=False)
                except Exception as e:
                    print(f"⚠️  Say command error: {e}")
            
            speech_thread = threading.Thread(target=speak_background)
            speech_thread.daemon = True
            speech_thread.start()
            
            # Monitor for completion or interruption
            while speech_thread.is_alive() and not self.speech_interrupted:
                time.sleep(0.1)
            
            # If interrupted, make sure speech stops
            if self.speech_interrupted:
                subprocess.run(['killall', 'say'], check=False)
                print("🛑 Speech interrupted by spacebar")
            
            # Wait for speech thread to finish
            speech_thread.join(timeout=2)
            
        except Exception as e:
            print(f"⚠️  Speech error: {e}")
        finally:
            self.currently_speaking = False
            # ALWAYS stop spacebar monitoring after speech
            self.stop_spacebar_monitoring()
            
            # EXTENDED pause before resuming listening to prevent feedback
            if listening_was_active:
                print("🔇 Clearing audio buffer...")
                time.sleep(2.0)  # Much longer pause
                self.listening_active = True
                print("🎧 Voice listening resumed")
            
            print("─" * 50)
    
    def interrupt_speech(self):
        """Interrupt current speech"""
        if self.currently_speaking:
            self.speech_interrupted = True
            if self.tts:
                try:
                    self.tts.stop()
                except:
                    pass
            print("\n🤫 Speech interrupted!")
    
    def start_spacebar_monitoring(self):
        """Start monitoring spacebar for interruptions"""
        if not self.spacebar_monitoring:
            self.spacebar_monitoring = True
            self.spacebar_thread = threading.Thread(target=self.monitor_spacebar)
            self.spacebar_thread.daemon = True
            self.spacebar_thread.start()
    
    def stop_spacebar_monitoring(self):
        """Stop spacebar monitoring"""
        self.spacebar_monitoring = False
        if self.spacebar_thread:
            self.spacebar_thread.join(timeout=1)
    
    def monitor_spacebar(self):
        """Monitor for spacebar presses to interrupt speech"""
        # Save terminal settings
        old_settings = None
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            
            spacebar_pressed = False  # Prevent spam
            
            while self.spacebar_monitoring:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    char = sys.stdin.read(1)
                    if char == ' ' and not spacebar_pressed:  # Spacebar pressed (prevent spam)
                        spacebar_pressed = True
                        if self.currently_speaking:
                            print("\n⏸️  SPACEBAR INTERRUPT!")
                            self.interrupt_speech()
                            # Kill the say process immediately
                            subprocess.run(['killall', 'say'], check=False)
                            break  # Exit monitoring after interrupt
                        else:
                            print("\n🔘 Spacebar pressed (no speech to interrupt)")
                    elif char == '\x03':  # Ctrl+C
                        break
                else:
                    spacebar_pressed = False  # Reset when no input
                        
        except Exception as e:
            print(f"⚠️  Spacebar monitoring error: {e}")
        finally:
            # Restore terminal settings
            if old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except:
                    pass
    

    
    def is_valid_command(self, text):
        """Check if speech contains valid commands (filter kitchen noise and self-speech)"""
        text_lower = text.lower()
        
        # Must contain a wake word or command word
        has_wake_word = any(wake in text_lower for wake in self.wake_words)
        has_command = any(cmd in text_lower for cmd in self.command_words)
        
        print(f"🔍 Debug: Validating '{text}'")
        print(f"🔍 Debug: Has wake word: {has_wake_word}")
        print(f"🔍 Debug: Has command: {has_command}")
        print(f"🔍 Debug: Word count: {len(text.split())}")
        
        # Note: Self-speech filtering is now handled by muting during speech
        
        # ALWAYS allow interruption commands, even during AI speech
        interrupt_words = ['stop', 'skip', 'quiet', 'silence', 'hey', 'foodingo', 'assistant', 'help']
        emergency_words = ['dropped', 'fell', 'disaster', 'mess', 'fire', 'burn', 'emergency']
        
        if any(word in text_lower for word in interrupt_words + emergency_words):
            print(f"🔍 Debug: Approved - Interruption/emergency command detected")
            return True
        
        # Filter out very short or gibberish
        if len(text.split()) < 1:
            print(f"🔍 Debug: Rejected - too short")
            return False
        
        # Filter out repeated recent speech
        if text in self.recent_speech:
            print(f"🔍 Debug: Rejected - duplicate recent speech")
            return False
        
        result = has_wake_word or has_command or len(text.split()) >= 2
        print(f"🔍 Debug: Final validation result: {result}")
        return result
    

    
    def continuous_listen(self):
        """Continuously listen for voice commands in kitchen environment"""
        print("🎤 Starting continuous kitchen listening...")
        
        while self.listening_active:
            try:
                if not self.microphone:
                    time.sleep(1)
                    continue
                
                with self.microphone as source:
                    # Short listen cycles to avoid blocking
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=6)
                
                try:
                    # Quick recognition
                    text = self.recognizer.recognize_google(audio, show_all=False)
                    
                    if self.is_valid_command(text):
                        print(f"👤 Heard: '{text}'")
                        print(f"🔍 Debug: Command validated as valid")
                        self.recent_speech.append(text)
                        
                        # Check for interruption commands first
                        text_lower = text.lower()
                        # Wake words or explicit stop commands interrupt speech
                        interrupt_words = ['stop', 'skip', 'quiet', 'silence', 'hey', 'foodingo', 'assistant']
                        if any(word in text_lower for word in interrupt_words):
                            print(f"🔍 Debug: Interruption word detected in '{text}'")
                            self.interrupt_speech()
                        
                        # Queue the command
                        print(f"🔍 Debug: Adding '{text}' to voice queue")
                        self.voice_queue.put(text)
                        print(f"🔍 Debug: Voice queue size now: {self.voice_queue.qsize()}")
                    else:
                        # Filtered out as noise
                        pass
                        
                except sr.UnknownValueError:
                    # Normal - lots of unclear audio in kitchen
                    pass
                except sr.RequestError as e:
                    print(f"⚠️  Recognition service error: {e}")
                    time.sleep(2)
                    
            except sr.WaitTimeoutError:
                # Normal - no speech detected
                pass
            except Exception as e:
                print(f"⚠️  Listening error: {e}")
                time.sleep(1)
    
    def start_continuous_listening(self):
        """Start background listening"""
        if self.microphone and not self.listening_active:
            self.listening_active = True
            self.listen_thread = threading.Thread(target=self.continuous_listen)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            print("🎧 Continuous listening started")
    
    def stop_continuous_listening(self):
        """Stop background listening"""
        self.listening_active = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        print("🔇 Continuous listening stopped")
    
    def get_voice_command(self, timeout=15):
        """Get voice command with timeout and cooking timer"""
        print(f"\n💬 Listening for your command... (or type below)")
        print("🎤 Say: 'start', 'next', 'pause', 'help', 'I dropped something'")
        print("⏸️  Say: 'hey', 'stop', or 'skip' to interrupt speech")
        
        # Ensure voice listening is active
        if not self.listening_active:
            print("🔄 Restarting voice recognition...")
            self.start_continuous_listening()
            time.sleep(0.5)  # Give it time to initialize
        
        start_time = time.time()
        last_timer_update = 0
        
        while time.time() - start_time < timeout:
            try:
                # Check for voice command
                command = self.voice_queue.get_nowait()
                return command
            except queue.Empty:
                # Check if user wants to type instead
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    typed_input = input("\n⌨️  Type: ").strip()
                    if typed_input:
                        return typed_input
                
                # Show cooking timer every 10 seconds
                elapsed = time.time() - start_time
                if elapsed - last_timer_update >= 10:
                    remaining = int(timeout - elapsed)
                    if remaining > 0:
                        print(f"⏲️  Cooking time remaining: {remaining}s (say 'next' when ready)")
                    last_timer_update = elapsed
                
                time.sleep(0.1)
        
        print("⏱️  Cooking time complete! Continuing to next step...")
        return None
    
    def mock_ai_response(self, user_input: str, session: CookingSession, recipe: Recipe):
        """Kitchen-optimized AI responses"""
        user_input = user_input.lower()
        
        # Handle interruption commands
        if any(word in user_input for word in ['stop', 'skip', 'quiet', 'silence']):
            return {
                "response": "Okay, stopped talking.",
                "action": "none"
            }
        
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
        elif "dropped" in user_input or "fell" in user_input or "disaster" in user_input or "mess" in user_input:
            return {
                "response": "No worries! Kitchen accidents happen. Need to restart this step?",
                "action": "pause"
            }
        elif "help" in user_input or "stuck" in user_input:
            return {
                "response": "I'm here to help! What's the problem?",
                "action": "none"
            }
        elif "quit" in user_input or "exit" in user_input or "goodbye" in user_input:
            return {
                "response": "Thanks for cooking with me!",
                "action": "complete_recipe"
            }
        else:
            return {
                "response": "Got it. Say help, next, or pause as needed.",
                "action": "none"
            }
    
    def demo_kitchen_cooking(self):
        """Run kitchen-optimized cooking demo"""
        
        print("🔍 Debug: Starting demo_kitchen_cooking")
        
        # Start continuous listening
        print("🔍 Debug: Starting continuous listening")
        self.start_continuous_listening()
        
        print("🔍 Debug: Speaking welcome message")
        self.speak_interruptible("Welcome to Foodingo! Your kitchen AI assistant.")
        time.sleep(1)
        
        # Get recipe
        print("🔍 Debug: Getting recipe")
        recipe = get_recipe("classic_beef_burger")
        if not recipe:
            print("🔍 Debug: No recipe found!")
            self.speak_interruptible("Sorry, couldn't load the recipe.")
            return
        
        print(f"🔍 Debug: Recipe loaded: {recipe.name}")
        self.speak_interruptible(f"Today we're making {recipe.name}. Say 'start' to begin cooking!")
        time.sleep(1)
        
        # Setup
        print("🔍 Debug: Setting up cooking service")
        self.cooking_service.conversation_engine.generate_response = self.mock_ai_response
        print("🔍 Debug: Starting cooking session")
        session = self.cooking_service.start_cooking_session(recipe)
        print(f"🔍 Debug: Session started with ID: {session.session_id}")
        
        print("\n🍳 Kitchen Voice Commands:")
        print("   • 'start' - Begin cooking")
        print("   • 'next' - Next step")
        print("   • 'pause' - Pause cooking")
        print("   • 'I dropped something' - Handle disasters")
        print("   • 'help' - Get assistance")
        print("   • 'quit' - Exit")
        print("\n⏸️  SPACEBAR = Interrupt AI speech instantly")
        print("🎧 I'm listening continuously - just speak naturally!")
        
        print("🔍 Debug: About to enter main cooking loop")
        
        try:
            loop_count = 0
            while True:
                loop_count += 1
                print(f"🔍 Debug: Main loop iteration {loop_count}")
                # Show current step
                current_step = session.get_current_step(recipe)
                if current_step:
                    step_info = f"Step {session.current_step + 1} of {len(recipe.steps)}"
                    print(f"\n📍 {step_info}")
                    print(f"📝 {current_step.instruction}")
                    
                    if current_step.tips:
                        print(f"💡 Tip: {current_step.tips[0]}")
                    
                    # Show estimated time for this step
                    estimated_minutes = current_step.estimated_time // 60
                    print(f"⏱️  Estimated time: {estimated_minutes} minutes")
                else:
                    self.speak_interruptible("Recipe complete! Enjoy your burgers!")
                    break
                
                # Give user time to actually cook - realistic timing
                if current_step:
                    cooking_time = max(30, current_step.estimated_time // 4)  # At least 30 seconds, up to 1/4 of estimated time
                    print(f"🍳 Take your time cooking... (listening for {cooking_time}s)")
                else:
                    cooking_time = 30
                
                # Get voice command with realistic timeout
                user_input = self.get_voice_command(timeout=cooking_time)
                
                if not user_input:
                    print("🔍 Debug: No user input received, continuing loop")
                    continue
                
                print(f"🔍 Debug: Processing user input: '{user_input}'")
                
                if user_input.lower() in ['quit', 'exit', 'goodbye']:
                    print("🔍 Debug: Exit command detected")
                    self.speak_interruptible("Thanks for cooking!")
                    break
                
                # Process command
                print(f"🔍 Debug: Sending to cooking service: '{user_input}'")
                result = self.cooking_service.process_user_input(
                    session_id=session.session_id,
                    user_input=user_input,
                    recipe=recipe
                )
                
                print(f"🔍 Debug: Cooking service result: {result}")
                
                # Respond
                time.sleep(0.5)  # Brief pause
                print(f"🔍 Debug: About to speak response: '{result['response']}'")
                self.speak_interruptible(result['response'])
                
                if result.get('session_update', {}).get('step_introduction'):
                    time.sleep(0.8)
                    self.speak_interruptible(result['session_update']['step_introduction'])
                
                # Check completion
                if session.current_step >= len(recipe.steps):
                    time.sleep(0.5)
                    self.speak_interruptible("Perfect! Recipe completed!")
                    break
                    
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            self.speak_interruptible("Cooking ended. Thanks!")
        except Exception as e:
            print(f"❌ Demo error: {e}")
        finally:
            print("🧹 Cleaning up demo...")
            self.cleanup()

def main():
    """Main function"""
    try:
        import select  # Check if select is available
        assistant = KitchenVoiceAssistant()
        assistant.demo_kitchen_cooking()
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Install: pip install pyttsx3 pyaudio")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Falling back to text demo...")

if __name__ == "__main__":
    main() 