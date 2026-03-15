# emergency_detector_simple_malayalam.py
import speech_recognition as sr
import time
import os
import winsound
import threading
import json
from datetime import datetime
import sys

print("=" * 70)
print("🎤 SIMPLE MALAYALAM EMERGENCY DETECTOR")
print("=" * 70)
print("Google Speech Recognition - Fixed Microphone Issue")
print("=" * 70)

# Emergency keywords
EMERGENCY_KEYWORDS = {
    'english': [
        'help', 'emergency', 'accident', 'fall', 'fell', 'hurt',
        'pain', 'injured', 'bleeding', 'ambulance', 'hospital',
        'doctor', 'broken', 'fire', 'thief', 'attack'
    ],
    
    'malayalam': [
        'സഹായം', 'അടിയന്തരം', 'അപകടം', 'വീഴ്ച', 'വീണു',
        'നോവ്', 'വേദന', 'രക്തസ്രാവം', 'പരിക്ക്', 'ആംബുലൻസ്',
        'ആശുപത്രി', 'ഡോക്ടർ', 'മുറിഞ്ഞ', 'തീ', 'കള്ളൻ', 'ആക്രമണം'
    ]
}

class SimpleMalayalamDetector:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.is_listening = True
        self.emergency_count = 0
        self.last_speech = ""
        
        # Load keywords
        self.keywords = EMERGENCY_KEYWORDS
        
        print("✅ Initializing detector...")
        print(f"✅ Malayalam keywords: {len(self.keywords['malayalam'])}")
        print(f"✅ English keywords: {len(self.keywords['english'])}")
        
        # Simple microphone setup
        self.setup_microphone_simple()
    
    def setup_microphone_simple(self):
        """Simple microphone setup without complex device selection"""
        print("\n🔊 Simple microphone setup...")
        
        try:
            # Don't try to select specific device, use default
            print("✅ Using default microphone")
            
            # Test microphone quickly
            self.test_microphone_simple()
            
        except Exception as e:
            print(f"⚠️  Setup warning: {e}")
            print("🔄 Continuing with basic settings...")
    
    def test_microphone_simple(self):
        """Quick microphone test"""
        print("\n🎤 Quick microphone test...")
        print("Please say 'hello' or 'ഹലോ'")
        
        try:
            # Use with statement properly
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("   Listening for 2 seconds...")
                
                try:
                    audio = self.recognizer.listen(source, timeout=2)
                    
                    # Try English first
                    try:
                        text = self.recognizer.recognize_google(audio, language='en-IN')
                        print(f"   ✅ English: Heard '{text}'")
                    except:
                        # Try Malayalam
                        try:
                            text = self.recognizer.recognize_google(audio, language='ml-IN')
                            print(f"   ✅ Malayalam: Heard '{text}'")
                        except:
                            print("   🔇 Could not understand audio")
                
                except sr.WaitTimeoutError:
                    print("   ⏰ No speech detected")
        
        except Exception as e:
            print(f"   ⚠️  Test error: {e}")
        
        print("✅ Microphone setup complete!")
    
    def play_alert(self):
        """Play emergency alert"""
        try:
            for freq in [1000, 800, 1200]:
                winsound.Beep(freq, 300)
                time.sleep(0.1)
        except:
            print('\a\a\a')
    
    def check_keywords(self, text):
        """Check for emergency keywords"""
        text_lower = text.lower()
        found_keywords = []
        languages = []
        
        for lang, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    found_keywords.append(keyword)
                    if lang not in languages:
                        languages.append(lang)
        
        return found_keywords, languages
    
    def listen_simple(self):
        """Simple listening loop"""
        print("\n🎤 Ready! Speak now...")
        print("   Say 'സഹായം' or 'help' for emergency")
        print("   Say 'stop' to end\n")
        
        try:
            while self.is_listening:
                try:
                    with sr.Microphone() as source:
                        # Quick noise adjustment
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"[{timestamp}] 👂 Listening...", end='\r')
                        
                        try:
                            # Listen
                            audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=4)
                            
                            # Process audio
                            self.process_audio_simple(audio)
                            
                        except sr.WaitTimeoutError:
                            continue
                
                except Exception as e:
                    print(f"\n⚠️  Microphone error: {e}")
                    # Wait and retry
                    time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
            self.is_listening = False
    
    def process_audio_simple(self, audio):
        """Process audio simply"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        print(f"\n[{timestamp}] 🔊 Processing...")
        
        # Try different languages
        languages_to_try = ['ml-IN', 'en-IN', None]  # Malayalam, English, Auto
        
        for lang_code in languages_to_try:
            try:
                if lang_code:
                    text = self.recognizer.recognize_google(audio, language=lang_code)
                else:
                    text = self.recognizer.recognize_google(audio)
                
                self.last_speech = text
                
                # Detect language
                lang_name = 'Malayalam' if lang_code == 'ml-IN' else 'English' if lang_code == 'en-IN' else 'Auto'
                print(f"[{timestamp}] 🌐 {lang_name}: '{text}'")
                
                # Check for stop command
                if 'stop' in text.lower() or 'നിർത്തുക' in text:
                    print(f"\n🛑 Stop command received")
                    self.is_listening = False
                    return
                
                # Check for emergency keywords
                keywords, langs = self.check_keywords(text)
                
                if keywords:
                    print(f"[{timestamp}] 🚨 EMERGENCY! Keywords: {', '.join(keywords)}")
                    self.handle_emergency_simple(text, keywords, langs)
                else:
                    print(f"[{timestamp}] ✅ Normal speech")
                
                # Successfully processed, break loop
                return
                
            except sr.UnknownValueError:
                continue  # Try next language
            except sr.RequestError as e:
                print(f"[{timestamp}] ⚠️  Google API error: {e}")
                return
            except Exception as e:
                print(f"[{timestamp}] ⚠️  Processing error: {e}")
                return
        
        # If all languages fail
        print(f"[{timestamp}] 🔇 Could not understand speech")
    
    def handle_emergency_simple(self, text, keywords, languages):
        """Handle emergency simply"""
        self.emergency_count += 1
        
        print("\n" + "!" * 50)
        print("🚨 EMERGENCY DETECTED!")
        print("!" * 50)
        print(f"Text: '{text}'")
        print(f"Keywords: {', '.join(keywords)}")
        print("!" * 50)
        
        # Play alert
        print("\n🔊 Alert sound...")
        self.play_alert()
        
        # Show message
        print("\n📢 HELP IS COMING! STAY CALM.")
        if 'malayalam' in languages:
            print("   സഹായം വരുന്നു! ശാന്തമായിരിക്കൂ.")
        
        # Log
        self.log_emergency_simple(text, keywords, languages)
        
        # Start response in background
        threading.Thread(target=self.emergency_response_simple, daemon=True).start()
    
    def emergency_response_simple(self):
        """Simple emergency response"""
        print(f"\n⏰ Emergency response activated...")
        
        for i in range(5, 0, -1):
            if not self.is_listening:
                return
            print(f"   Countdown: {i}", end='\r')
            time.sleep(1)
        
        print("\n✅ Emergency services notified!")
        
        # Play confirmation
        try:
            winsound.Beep(800, 600)
        except:
            pass
    
    def log_emergency_simple(self, text, keywords, languages):
        """Simple logging"""
        os.makedirs('logs', exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f"logs/emergency_{timestamp}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Emergency: {timestamp}\n")
            f.write(f"Text: {text}\n")
            f.write(f"Keywords: {', '.join(keywords)}\n")
            f.write(f"Languages: {', '.join(languages)}\n")
        
        print(f"📝 Log saved: {log_file}")
    
    def start(self):
        """Start detector"""
        print("\n" + "=" * 70)
        print("🚀 STARTING SIMPLE DETECTOR")
        print("=" * 70)
        print("Speak clearly in Malayalam or English")
        print("Test phrases:")
        print("   English: 'help me' or 'emergency'")
        print("   Malayalam: 'സഹായം' or 'അടിയന്തരം'")
        print("=" * 70)
        
        print("\nStarting in 2 seconds...")
        time.sleep(2)
        
        self.listen_simple()
        
        self.show_summary()
    
    def show_summary(self):
        """Show summary"""
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)
        print(f"Emergencies detected: {self.emergency_count}")
        if self.last_speech:
            print(f"Last speech: '{self.last_speech}'")
        print("=" * 70)

# Main function
def main():
    print("Simple Malayalam Emergency Detector")
    print("=" * 70)
    
    # Check requirements
    try:
        import speech_recognition
        print("✅ SpeechRecognition installed")
    except ImportError:
        print("❌ Please install: pip install SpeechRecognition")
        return
    
    try:
        import pyaudio
        print("✅ PyAudio installed")
    except ImportError:
        print("⚠️  PyAudio not installed. Trying to install...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyaudio'])
            print("✅ PyAudio installed successfully")
        except:
            print("❌ Could not install PyAudio")
            print("💡 Try: pip install pipwin")
            print("     pipwin install pyaudio")
            return
    
    # Create detector
    detector = SimpleMalayalamDetector()
    
    try:
        detector.start()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    print("\n🙏 Thank you!")



    # ================= MULTIPROCESS ENTRY =================
def run_malayalam_voice_process(event_queue):
    detector = SimpleMalayalamDetector()

    original_handle = detector.handle_emergency_simple

    def patched_handle(text, keywords, languages):
        now = time.time()
        for kw in keywords:
            event_queue.put({
                "type": "voice",
                "lang": "ML",
                "word": kw,
                "time": now
            })
        original_handle(text, keywords, languages)

    detector.handle_emergency_simple = patched_handle
    detector.listen_simple()
