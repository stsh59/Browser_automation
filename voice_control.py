import speech_recognition as sr
import pyttsx3
import time
import threading

# Initialize the pyttsx3 engine globally to avoid reinitialization
engine = pyttsx3.init()
is_speaking = False  # Global flag to prevent overlapping speech

def speak(text):
    """Convert text to speech while preventing overlap."""
    global is_speaking
    if is_speaking:
        print("⚠️ Already speaking. Skipping duplicate speech request.")
        return

    is_speaking = True

    def _speak():
        global is_speaking
        engine.say(text)
        try:
            engine.runAndWait()
        except RuntimeError:
            print("⚠️ Speech engine error.")
        time.sleep(0.5)  # Allow a slight pause
        is_speaking = False

    threading.Thread(target=_speak, daemon=True).start()


def listen():
    """Capture voice input and convert it to text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        try:
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=6)
            command = recognizer.recognize_google(audio)
            print(f"User said: {command}")
            return command.lower()
        except sr.UnknownValueError:
            print("🤖 Could not understand audio. Try again.")
            return None
        except sr.RequestError:
            print("❌ Speech recognition service unavailable.")
            return None
        except Exception as e:
            print(f"⚠️ Error: {e}")
            return None
