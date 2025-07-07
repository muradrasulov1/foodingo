#!/usr/bin/env python3
"""
Kitchen-ready voice assistant with proper interruption handling
Fixes: spacebar spam, terminal issues, voice recognition restart
"""

import os
import sys
import time
import threading
import queue
import subprocess
import signal
import atexit
import select
import termios
import tty

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import speech_recognition as sr
    from services.cooking_service import CookingService
    from data.sample_recipes import get_recipe
    from models.recipe import CookingSession
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install: pip install SpeechRecognition pyaudio")
    sys.exit(1)

class KitchenVoiceAssistant:
    def __init__(self):
        """Initialize kitchen voice assistant"""
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.cooking_service = CookingService()
        
        # Voice and listening state
        self.listening_active = False
        self.listen_thread = None
        self.voice_queue = queue.Queue()
        
        # Speech interruption (simplified)
        self.currently_speaking = False
        self.speech_interrupted = False
        
        # Setup
        self.setup_cleanup_handlers()
        self.setup_kitchen_voice()
        self.setup_kitchen_microphone()
        
        print("✅ Kitchen-ready voice assistant initialized")
    
    def setup_cleanup_handlers(self):
        """Setup cleanup handlers"""
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle system signals"""
        print(f"\n🛑 Received signal {signum}, cleaning up...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Clean up resources"""
        print("🧹 Cleaning up...")
        self.listening_active = False
        self.currently_speaking = False
        
        # Kill any remaining speech processes
        subprocess.run(['killall', 'say'], check=False)
        
        # Join listening thread
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        
        print("✅ Cleanup complete")
    
    def setup_kitchen_voice(self):
        """Setup voice for kitchen environment"""
        print("🎭 Configuring voice for kitchen...")
        
        # Test available voices
        result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True)
        voices = result.stdout.strip().split('\n')
        
        # Find Samantha voice (high quality)
        samantha_found = False
        for voice in voices:
            if 'Samantha' in voice:
                samantha_found = True
                break
        
        if samantha_found:
            print("✅ Selected: Samantha (high quality)")
            self.voice_name = 'Samantha'
        else:
            print("⚠️  Using default voice (Samantha not found)")
            self.voice_name = None
        
        # Test voice
        print("🎵 Testing voice...")
        self.speak_simple("Voice test")
        print("✅ Voice test complete")
    
    def setup_kitchen_microphone(self):
        """Setup microphone for kitchen environment"""
        print("🔧 Setting up kitchen microphone...")
        
        try:
            # Find microphone
            for i, mic_name in enumerate(sr.Microphone.list_microphone_names()):
                if i == 0:  # Use default microphone
                    self.microphone = sr.Microphone(device_index=i)
                    break
            
            if not self.microphone:
                print("❌ No microphone found!")
                return False
            
            # Calibrate for kitchen noise
            print("🔧 Calibrating for kitchen noise...")
            print("   (Let kitchen run normally for 3 seconds)")
            
            with self.microphone as source:
                # Higher energy threshold for noisy kitchens
                self.recognizer.energy_threshold = 400
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.adjust_for_ambient_noise(source, duration=3)
            
            print("✅ Kitchen microphone ready")
            return True
            
        except Exception as e:
            print(f"❌ Microphone setup failed: {e}")
            return False
    
    def speak_simple(self, text):
        """Simple speech without interruption"""
        try:
            if self.voice_name:
                subprocess.run(['say', '-v', self.voice_name, text], check=False)
            else:
                subprocess.run(['say', text], check=False)
        except Exception as e:
            print(f"⚠️  Speech error: {e}")
    
    def speak_interruptible(self, text):
        """Speak with simple interruption via Enter key"""
        print(f"\n🤖 AI: {text}")
        print("⏸️  Press ENTER to interrupt speech")
        print("─" * 50)
        
        try:
            self.currently_speaking = True
            self.speech_interrupted = False
            
            # Stop voice listening during speech
            listening_was_active = self.listening_active
            if listening_was_active:
                self.listening_active = False
                time.sleep(0.5)
            
            # Start speech in background
            def speak_background():
                try:
                    if self.voice_name:
                        subprocess.run(['say', '-v', self.voice_name, text], timeout=30, check=False)
                    else:
                        subprocess.run(['say', text], timeout=30, check=False)
                except Exception as e:
                    print(f"⚠️  Speech error: {e}")
            
            speech_thread = threading.Thread(target=speak_background)
            speech_thread.daemon = True
            speech_thread.start()
            
            # Simple interruption check
            while speech_thread.is_alive():
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    # User pressed Enter
                    sys.stdin.readline()  # Clear the input
                    print("🛑 Speech interrupted by Enter key")
                    subprocess.run(['killall', 'say'], check=False)
                    self.speech_interrupted = True
                    break
                time.sleep(0.1)
            
            # Wait for speech to complete
            speech_thread.join(timeout=2)
            
            # Resume listening after pause
            if listening_was_active:
                print("🔇 Clearing audio buffer...")
                time.sleep(1.5)
                self.listening_active = True
                print("🎧 Voice listening resumed")
            
        except Exception as e:
            print(f"⚠️  Speech error: {e}")
        finally:
            self.currently_speaking = False
            print("─" * 50)
    
    def is_valid_command(self, text):
        """Check if text is a valid command (not background noise)"""
        if not text or len(text.strip()) < 2:
            return False
        
        # Kitchen command keywords
        valid_keywords = [
            'start', 'begin', 'next', 'done', 'ready', 'continue',
            'pause', 'wait', 'stop', 'help', 'repeat', 'again',
            'dropped', 'fell', 'disaster', 'mess', 'quit', 'exit',
            'hey', 'foodingo', 'assistant', 'kitchen', 'cooking'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in valid_keywords)
    
    def continuous_listen(self):
        """Continuous listening loop"""
        while self.listening_active:
            try:
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                try:
                    # Recognize speech
                    text = self.recognizer.recognize_google(audio, show_all=False)
                    
                    if self.is_valid_command(text):
                        print(f"👤 Heard: '{text}'")
                        self.voice_queue.put(text)
                    
                except sr.UnknownValueError:
                    # Normal - unclear audio
                    pass
                except sr.RequestError as e:
                    print(f"⚠️  Recognition error: {e}")
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
            print("🎧 Voice listening started")
    
    def stop_continuous_listening(self):
        """Stop background listening"""
        self.listening_active = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        print("🔇 Voice listening stopped")
    
    def get_voice_command(self, timeout=15):
        """Get voice command with timeout"""
        print(f"\n💬 Listening for your command... (or type below)")
        print("🎤 Say: 'start', 'next', 'pause', 'help', 'I dropped something'")
        print("⏸️  Press ENTER to interrupt AI speech")
        
        # Ensure listening is active
        if not self.listening_active:
            print("🔄 Restarting voice recognition...")
            self.start_continuous_listening()
            time.sleep(0.5)
        
        start_time = time.time()
        last_timer_update = 0
        
        while time.time() - start_time < timeout:
            try:
                # Check for voice command
                command = self.voice_queue.get_nowait()
                return command
            except queue.Empty:
                # Check for typed input
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    typed_input = input("\n⌨️  Type: ").strip()
                    if typed_input:
                        return typed_input
                
                # Show cooking timer
                elapsed = time.time() - start_time
                if elapsed - last_timer_update >= 10:
                    remaining = int(timeout - elapsed)
                    if remaining > 0:
                        print(f"⏲️  Cooking time remaining: {remaining}s (say 'next' when ready)")
                    last_timer_update = elapsed
                
                time.sleep(0.1)
        
        print("⏱️  Cooking time complete! Continuing...")
        return None
    
    def mock_ai_response(self, user_input: str, session: CookingSession, recipe):
        """Kitchen-optimized AI responses"""
        user_input = user_input.lower()
        
        if "start" in user_input or "begin" in user_input:
            return {
                "response": "Perfect! Let's start cooking. First, season the ground beef.",
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
        elif "dropped" in user_input or "disaster" in user_input:
            return {
                "response": "No worries! Kitchen accidents happen. Need to restart?",
                "action": "pause"
            }
        elif "help" in user_input or "stuck" in user_input:
            return {
                "response": "I'm here to help! What's the problem?",
                "action": "none"
            }
        elif "quit" in user_input or "exit" in user_input:
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
        """Run kitchen cooking demo"""
        print("🍳 Starting kitchen cooking demo...")
        
        # Start listening
        self.start_continuous_listening()
        
        # Welcome
        self.speak_interruptible("Welcome to Foodingo! Your kitchen AI assistant.")
        
        # Get recipe
        recipe = get_recipe("classic_beef_burger")
        if not recipe:
            self.speak_interruptible("Sorry, couldn't load the recipe.")
            return
        
        self.speak_interruptible(f"Today we're making {recipe.name}. Say 'start' to begin!")
        
        # Setup cooking service
        self.cooking_service.conversation_engine.generate_response = self.mock_ai_response
        session = self.cooking_service.start_cooking_session(recipe)
        
        print("\n🍳 Kitchen Voice Commands:")
        print("   • 'start' - Begin cooking")
        print("   • 'next' - Next step")
        print("   • 'pause' - Pause cooking")
        print("   • 'help' - Get assistance")
        print("   • 'quit' - Exit")
        print("\n⏸️  ENTER = Interrupt AI speech")
        print("🎧 Voice recognition active!")
        
        try:
            loop_count = 0
            while loop_count < 20:  # Safety limit
                loop_count += 1
                
                # Show current step
                current_step = session.get_current_step(recipe)
                if current_step:
                    step_info = f"Step {session.current_step + 1} of {len(recipe.steps)}"
                    print(f"\n📍 {step_info}")
                    print(f"📝 {current_step.instruction}")
                    
                    if current_step.tips:
                        print(f"💡 Tip: {current_step.tips[0]}")
                    
                    estimated_minutes = current_step.estimated_time // 60
                    print(f"⏱️  Estimated time: {estimated_minutes} minutes")
                else:
                    self.speak_interruptible("Recipe complete! Enjoy your burgers!")
                    break
                
                # Get user input with realistic timeout
                cooking_time = max(30, current_step.estimated_time // 4)
                print(f"🍳 Take your time cooking... (listening for {cooking_time}s)")
                
                user_input = self.get_voice_command(timeout=cooking_time)
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit']:
                    self.speak_interruptible("Thanks for cooking!")
                    break
                
                # Process command
                result = self.cooking_service.process_user_input(
                    session_id=session.session_id,
                    user_input=user_input,
                    recipe=recipe
                )
                
                # Respond
                time.sleep(0.5)
                self.speak_interruptible(result['response'])
                
                # Check if recipe is complete
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
            self.cleanup()

def main():
    """Main function"""
    try:
        assistant = KitchenVoiceAssistant()
        assistant.demo_kitchen_cooking()
    except ImportError as e:
        print(f"❌ Missing package: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 