import time
import queue
import json
import sounddevice as sd
import speech_recognition as sr
from multiprocessing import Queue
from vosk import Model, KaldiRecognizer
import numpy as np
import scipy.signal

print("🎤 Unified Voice Process Started - v2.4 (Overflow Fix)")

def run_voice_process(event_queue: Queue):
    SAMPLE_RATE = 16000
    BLOCK_SIZE = 24000 # Process 1.5s chunks (Less CPU interrupts than 0.5s)
    
    # ---------- AUDIO QUEUE ----------
    # Limit queue size to prevent memory leaks/lag if processing falls behind
    # Increased to 50 to absorb temporary CPU spikes from camera process
    audio_q = queue.Queue(maxsize=50)

    # Callback must be robust to different input rates
    # We will handle resampling in the main loop if needed
    last_overflow_time = 0
    
    def audio_callback(indata, frames, time_info, status):
        nonlocal last_overflow_time
        if status:
            # Rate limit the overflow warning (max 1 per 5 seconds)
            if "overflow" in str(status):
                if time.time() - last_overflow_time > 5:
                    print(f"⚠️ Audio Status: {status} (throttling logs)")
                    last_overflow_time = time.time()
            else:
                print(f"⚠️ Audio Status: {status}")
                
        try:
            audio_q.put_nowait(indata.copy())
        except queue.Full:
            pass # Drop frame if CPU is too slow, better than crashing or infinite lag

    # ---------- ENGLISH (VOSK) ----------
    try:
        vosk_model = Model("models/en")
        vosk_rec = KaldiRecognizer(vosk_model, SAMPLE_RATE)
    except Exception as e:
        print(f"🔴 VOSK Model Error: {e}")
        return

    ENGLISH_KEYWORDS = {
        "help", "emergency", "accident", "danger",
        "save", "hurt", "fall", "fire"
    }

    # ---------- MALAYALAM (GOOGLE ASR) ----------
    sr_rec = sr.Recognizer()

    MALAYALAM_KEYWORDS = {
        "സഹായം", "രക്ഷിക്കൂ", "വീണു",
        "അയ്യോ", "വയ്യ"
    }

    last_ml_time = 0

    # ---------- AUDIO DEVICE SELECTION & CONFIG ----------
    device_index = None
    mic_rate = SAMPLE_RATE  # Default to 16k, but might change
    
    try:
        devices = sd.query_devices()
        print(f"🔍 Scanning {len(devices)} audio devices...")
        
        candidates = []
        
        # Priority 1: "pulse" or "default" (SYSTEM MANAGED) - HIGHEST PRIORITY
        # We prefer this because the system handles resampling efficiently
        for i, dev in enumerate(devices):
            name = dev['name'].lower()
            if ("pulse" in name or "default" in name) and dev['max_input_channels'] > 0:
                candidates.append((i, dev['name'], 3)) # Changed to 3 (Highest)

        # Priority 2: Raw USB Device - LOWER PRIORITY
        # Only use if system mixer isn't working, but this requires manual resampling
        for i, dev in enumerate(devices):
            if "usb" in dev['name'].lower() and dev['max_input_channels'] > 0:
                candidates.append((i, dev['name'], 2)) # Changed to 2
        
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        if candidates:
            # Try to open the best candidate
            for cand in candidates:
                idx = cand[0]
                name = cand[1]
                print(f"Trying device: [{idx}] {name}")
                
                # Test 16000Hz
                try:
                    sd.check_input_settings(device=idx, channels=1, samplerate=16000, dtype='int16')
                    device_index = idx
                    mic_rate = 16000
                    print(f"✅ Device supports 16kHz natively.")
                    break
                except Exception as e:
                    print(f"⚠️ Device rejected 16kHz: {e}")
                    
                    # Test 44100Hz or 48000Hz (Native Fallback)
                    try:
                        dev_info = sd.query_devices(idx)
                        native_rate = int(dev_info['default_samplerate'])
                        sd.check_input_settings(device=idx, channels=1, samplerate=native_rate, dtype='int16')
                        device_index = idx
                        mic_rate = native_rate
                        print(f"✅ Device accepted native rate: {mic_rate}Hz. Will resample.")
                        break
                    except Exception as e2:
                        print(f"❌ Device rejected native rate: {e2}")
                        continue
        
        if device_index is None:
            print("⚠️ No specific device found. Using system default.")

    except Exception as e:
        print(f"⚠️ Error scanning devices: {e}. Using default.")
        device_index = None

    # ---------- MAIN LOOP ----------
    while True:
        try:
            print(f"🎤 Opening stream on Device {device_index} @ {mic_rate}Hz")
            with sd.InputStream(
                samplerate=mic_rate,
                blocksize=BLOCK_SIZE,
                dtype="int16",
                channels=1,
                callback=audio_callback,
                device=device_index
            ):
                print(f"🎤 Stream active")
                
                while True:
                    # Adaptive Load Shedding
                    # If queue is backing up, we are too slow.
                    q_size = audio_q.qsize()
                    
                    if q_size > 5:
                        # CRITICAL LAG: Drop frame to catch up
                        try:
                            _ = audio_q.get_nowait()
                            print(f"⚠️ Dropping audio frame (Queue: {q_size}) to catch up!")
                            continue
                        except queue.Empty:
                            break
                    
                    indata = audio_q.get()
                    
                    # Logic: If queue > 2, skip heavy processing (Malayalam/Resampling)
                    skip_heavy = (q_size > 2)
                    
                    # RESAMPLING (if mic_rate != 16000)
                    if mic_rate != SAMPLE_RATE:
                        if skip_heavy:
                             # Skip resampling if lagging
                             continue
                        
                        # Simple resampling (number of samples)
                        num_samples = int(len(indata) * SAMPLE_RATE / mic_rate)
                        indata = scipy.signal.resample(indata, num_samples).astype(np.int16)
                    
                    data_bytes = indata.tobytes()

                    # ---------- ENGLISH (FAST) ----------
                    # Always try English as it's local and fast
                    if vosk_rec.AcceptWaveform(data_bytes):
                        text = json.loads(vosk_rec.Result()).get("text", "").lower()
                    else:
                        text = json.loads(vosk_rec.PartialResult()).get("partial", "").lower()

                    if text:
                        for w in ENGLISH_KEYWORDS:
                            if w in text:
                                event_queue.put({
                                    "type": "voice",
                                    "lang": "EN",
                                    "word": w,
                                    "time": time.time()
                                })
                                print(f"🔊 EN detected: {w}")
                                break # Found one keyword, enough for this frame

                    # ---------- MALAYALAM (SLOW) ----------
                    # Google Speech API is slow (network call). Skip if lagging.
                    if skip_heavy:
                         if q_size > 2:
                             # Only print if significantly skipping
                             # print(f"⚠️ Skipping Malayalam check (Lag: {q_size})")
                             pass
                         continue

                    now = time.time()
                    if now - last_ml_time > 2:
                        last_ml_time = now
                        try:
                            # SR requires AudioData
                            audio = sr.AudioData(data_bytes, SAMPLE_RATE, 2)
                            ml_text = sr_rec.recognize_google(audio, language="ml-IN")

                            for w in MALAYALAM_KEYWORDS:
                                if w in ml_text:
                                    event_queue.put({
                                        "type": "voice",
                                        "lang": "ML",
                                        "word": w,
                                        "time": now
                                    })
                                    print(f"🔊 ML detected: {w}")
                                    break

                        except sr.UnknownValueError:
                            pass
                        except sr.RequestError:
                            print("⚠️ Google Speech API unavailable")
                        except Exception as e:
                            # print(f"⚠️ MLA processing error: {e}")
                            pass

        except Exception as e:
            print(f"🔴 Stream error: {e}. Restarting in 1s...")
            time.sleep(1)
