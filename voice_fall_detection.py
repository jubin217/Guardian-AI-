import sounddevice as sd
import queue
import json
import time
import threading

import speech_recognition as sr
from vosk import Model, KaldiRecognizer

# ===================== CONFIG =====================
SAMPLE_RATE = 16000
BLOCK_SIZE = 4000

# Callback set by main.py
VOICE_EVENT_CALLBACK = None

# Independent cooldowns
EN_COOLDOWN = 2
ML_COOLDOWN = 2
last_en_time = 0
last_ml_time = 0

# =================================================

# ---------- ENGLISH (VOSK) ----------
vosk_model = Model("models/en")
vosk_recognizer = KaldiRecognizer(vosk_model, SAMPLE_RATE)

ENGLISH_KEYWORDS = {
    "help", "emergency", "accident", "danger", "save",
    "hurt", "pain", "fall", "fell", "fire", "attack",
    "bleed", "bleeding"
}

# ---------- MALAYALAM (GOOGLE ASR) ----------
sr_recognizer = sr.Recognizer()
sr_microphone = sr.Microphone()

MALAYALAM_KEYWORDS = {
    "സഹായം",
    "രക്ഷിക്കൂ",
    "വീണു",
    "വയ്യ",
    "അയ്യോ",
    "രക്തം",
    "അപകടം",
    "ആശുപത്രി",
    "ഡോക്ടർ"
}

# =================================================

audio_queue = queue.Queue()
stop_event = threading.Event()


def audio_callback(indata, frames, time_info, status):
    audio_queue.put(bytes(indata))


def english_vosk_loop():
    global last_en_time

    while not stop_event.is_set():
        data = audio_queue.get()

        if vosk_recognizer.AcceptWaveform(data):
            result = json.loads(vosk_recognizer.Result())
            text = result.get("text", "").lower()
        else:
            partial = json.loads(vosk_recognizer.PartialResult())
            text = partial.get("partial", "").lower()

        if not text:
            continue

        words = set(text.split())
        matched = words & ENGLISH_KEYWORDS

        if matched:
            now = time.time()
            if now - last_en_time < EN_COOLDOWN:
                continue

            last_en_time = now

            if VOICE_EVENT_CALLBACK:
                VOICE_EVENT_CALLBACK("ENGLISH", now)

            print("\n🔊 English Emergency Detected")
            print(f"   Keyword : {', '.join(matched)}")
            print(f"   Heard   : {text}")
            print("-" * 45)


def malayalam_google_loop():
    global last_ml_time

    with sr_microphone as source:
        sr_recognizer.adjust_for_ambient_noise(source, duration=1)

    while not stop_event.is_set():
        try:
            with sr_microphone as source:
                audio = sr_recognizer.listen(source, phrase_time_limit=4)

            text = sr_recognizer.recognize_google(audio, language="ml-IN")
            print(f"\n🔊 Malayalam Transcribed: {text}")

            for kw in MALAYALAM_KEYWORDS:
                if kw in text:
                    now = time.time()
                    if now - last_ml_time < ML_COOLDOWN:
                        break

                    last_ml_time = now

                    if VOICE_EVENT_CALLBACK:
                        VOICE_EVENT_CALLBACK("MALAYALAM", now)

                    print(f"   Keyword : {kw}")
                    print(f"   Heard   : {text}")
                    print("-" * 45)
                    break

        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print("⚠️ Google ASR error:", e)
        except Exception as e:
            print("⚠️ Malayalam loop error:", e)


def start_voice_detection():
    print("\n🎤 Voice detection started")

    stream = sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        dtype="int16",
        channels=1,
        callback=audio_callback
    )

    stream.start()

    threading.Thread(target=english_vosk_loop, daemon=True).start()
    threading.Thread(target=malayalam_google_loop, daemon=True).start()


def stop_voice_detection():
    stop_event.set()
