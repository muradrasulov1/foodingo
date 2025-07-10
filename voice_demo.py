#!/usr/bin/env python3
"""
Voice-enabled demo of the cooking assistant (macOS optimized)
This version uses your microphone for input and the native 'say' command for speech.
"""

import sys
import os
import queue
import speech_recognition as sr
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Recipe, CookingSession
from services.cooking_service import CookingService
from data.sample_recipes import get_recipe

class VoiceCookingAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.cooking_service = CookingService()
        self.voice_queue = queue.Queue()
        self.tts_process = None

        # Set a static, higher energy threshold to avoid picking up bot speech
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = False

        print("🎤 Setting up voice recognition...")
        self.calibrate_microphone()

    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise."""
        print("🔧 Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✅ Microphone calibrated!")

    def speak(self, text):
        """Convert text to speech using the non-blocking 'say' command."""
        # Stop any currently running speech
        if self.tts_process and self.tts_process.poll() is None:
            self.tts_process.terminate()
            self.tts_process.wait()

        print(f"🤖 AI: {text}")
        # Use non-blocking Popen for the 'say' command
        self.tts_process = subprocess.Popen(["say", text])

    def _audio_callback(self, recognizer, audio):
        """Callback function for background listening."""
        try:
            text = recognizer.recognize_google(audio)
            print(f"👤 You said: {text}")
            self.voice_queue.put(text)
        except sr.UnknownValueError:
            pass # Ignore unclear speech
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")

    

    def run(self):
        """Run the main loop of the voice assistant."""
        self.speak("Welcome to Foodingo! Today, we're making a Classic Beef Burger.")
        self.speak("Just say 'start cooking' when you are ready.")

        recipe = get_recipe("classic_beef_burger")
        # self.cooking_service.conversation_engine.generate_response = self.mock_ai_response
        session = self.cooking_service.start_cooking_session(recipe)

        stop_listening = self.recognizer.listen_in_background(self.microphone, self._audio_callback)

        try:
            while True:
                try:
                    user_input = self.voice_queue.get(timeout=60) # Wait for user input

                    if user_input.lower() in ['quit', 'exit', 'stop cooking']:
                        self.speak("Thanks for cooking with me! Goodbye.")
                        break

                    result = self.cooking_service.process_user_input(
                        session_id=session.session_id,
                        user_input=user_input,
                        recipe=recipe
                    )

                    self.speak(result['response'])

                    if result.get('session_update', {}).get('step_introduction'):
                        self.speak(result['session_update']['step_introduction'])

                    current_step = session.get_current_step(recipe)
                    if current_step:
                        print(f"📍 Step {session.current_step + 1}/{len(recipe.steps)}: {current_step.instruction}")
                    else:
                        self.speak("Congratulations, you've finished the recipe!")
                        break

                except queue.Empty:
                    # If no input for a while, just continue listening
                    pass

        except KeyboardInterrupt:
            self.speak("Cooking session ended. Goodbye!")
        finally:
            print("🛑 Stopping background listener...")
            stop_listening(wait_for_stop=False)
            if self.tts_process:
                self.tts_process.terminate()

def main():
    try:
        assistant = VoiceCookingAssistant()
        assistant.run()
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        print("Please ensure you have 'portaudio' installed (`brew install portaudio`).")
        print("Then run: pip install pyaudio speechrecognition")

if __name__ == "__main__":
    main()