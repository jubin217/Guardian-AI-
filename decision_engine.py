import time
from collections import deque
import datetime
import json
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
try:
    from telegram_alert import send_telegram_alert
except ImportError:
    send_telegram_alert = None

class EmergencyDecisionEngine:
    def __init__(self, emergency_flag=None):
        # --- Firebase Setup ---
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate('service_account.json')
                firebase_admin.initialize_app(cred)
                print("🟢 Firebase Admin initialized successfully.")
            except Exception as e:
                print(f"🔴 Error initializing Firebase: {e}")
                
        try:
            self.db = firestore.client()
        except Exception as e:
            self.db = None
            print(f"🔴 Error getting Firestore client: {e}")

        # --- Device Pairing Setup ---
        self.user_id = "UNASSIGNED_DEVICE"
        config_path = os.path.join(os.path.dirname(__file__), 'device_config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    paired_id = config.get("user_id")
                    if paired_id and paired_id != "PASTE_YOUR_ACCOUNT_ID_HERE":
                        self.user_id = paired_id
                        print(f"🔗 Device paired to user: {self.user_id}")
                    else:
                        print("⚠️ WARNING: device_config.json found but no valid user_id provided.")
            except Exception as e:
                print(f"🔴 Error reading device_config.json: {e}")
        else:
            print("⚠️ WARNING: device_config.json not found! Emergencies will not be tied to your account.")

        # --- SHARED STATE ---
        self.emergency_flag = emergency_flag

        # --- FALL TRACKING ---
        self.fall_state = "MONITORING"
        self.fall_start_time = None

        # --- VOICE TRACKING ---
        self.voice_events = deque()  # stores timestamps of voice keywords
        self.last_voice_time = 0

        # --- GESTURE TRACKING ---
        self.gesture_state = "MONITORING"
        self.gesture_start_time = None

        # --- EMERGENCY STATE ---
        self.emergency_triggered = False

    # ================= FALL INPUT =================
    def update_fall_state(self, state: str, timestamp: float):
        if state == "CAMERA_ACTIVE":
            print("🟢 Fall system ACTIVE (camera + model running)")
            self.fall_state = "MONITORING"
            return
            
        if state != self.fall_state:
            print(f"🔄 State change: {self.fall_state} -> {state}")
            self.fall_state = state
            
            if state == "FALL_DETECTED":
                self.fall_start_time = timestamp
            elif state == "MONITORING":
                self.fall_start_time = None
        
        # Always evaluate after a state update
        self.evaluate(timestamp)


    # ================= VOICE INPUT =================
    def register_voice_keyword(self, keyword: str, timestamp: float):
        # Debounce: Ignore duplicate keywords within 1 second
        if timestamp - self.last_voice_time < 1.0:
            print(f"⏳ Ignoring duplicate voice event ({keyword})")
            return
            
        self.last_voice_time = timestamp
        self.voice_events.append(timestamp)
        self.cleanup_voice_events(timestamp)
        self.evaluate(timestamp)

    # ================= GESTURE INPUT =================
    def update_gesture_state(self, state: str, timestamp: float):
        if state == "CAMERA_ACTIVE":
            print("🟢 Gesture system ACTIVE (camera + model running)")
            self.gesture_state = "MONITORING"
            return
            
        if state != self.gesture_state:
            print(f"🔄 Gesture State change: {self.gesture_state} -> {state}")
            self.gesture_state = state
            
            if state != "MONITORING":
                if self.gesture_start_time is None:
                    self.gesture_start_time = timestamp
            else:
                self.gesture_start_time = None
        
        self.evaluate(timestamp)

    # ================= CORE LOGIC =================
    def cleanup_voice_events(self, now):
        # Keep only last 20 seconds
        while self.voice_events and now - self.voice_events[0] > 20:
            self.voice_events.popleft()

    def evaluate(self, now):
        if self.emergency_triggered:
            return  # fire only once

        # ---------- RULE 1 ----------
        if self.fall_state == "FALL_DETECTED" and self.fall_start_time:
            fall_duration = now - self.fall_start_time

            if fall_duration >= 10:
                self.trigger_emergency(
                    reason="Fall detected for ≥ 10 seconds"
                )
                return

        # ---------- RULE 2 ----------
        if self.fall_state == "FALL_DETECTED" and self.fall_start_time:
            fall_duration = now - self.fall_start_time

            if fall_duration >= 5 and len(self.voice_events) >= 1:
                self.trigger_emergency(
                    reason="Fall ≥ 5 seconds + voice emergency keyword"
                )
                return

        # ---------- RULE 3 ----------
        if len(self.voice_events) >= 3:
            self.trigger_emergency(
                reason="Voice emergency keyword repeated ≥ 3 times within 20 seconds"
            )
            return

        # ---------- RULE 4 (Gesture) ----------
        if self.gesture_state == "Hand on Chest" and self.gesture_start_time:
            gesture_duration = now - self.gesture_start_time
            if gesture_duration >= 10:
                self.trigger_emergency(
                    reason="Hand on chest detected for ≥ 10 seconds"
                )
                return

        # ---------- RULE 5 (Gesture + Voice) ----------
        if self.gesture_state == "Hand on Chest" and self.gesture_start_time:
            if len(self.voice_events) >= 1:
                self.trigger_emergency(
                    reason="Hand on chest + voice emergency keyword"
                )
                return

    # ================= OUTPUT =================
    def trigger_emergency(self, reason):
        self.emergency_triggered = True
        
        # Set shared flag if available
        if self.emergency_flag:
            self.emergency_flag.value = True
            
        print("\n" + "!" * 60)
        print("🚨🚨🚨 EMERGENCY CONFIRMED 🚨🚨🚨")
        print(f"Reason: {reason}")
        print(f"Time  : {time.strftime('%H:%M:%S')}")
        print("!" * 60 + "\n")

        # Sync to Firebase
        if hasattr(self, 'db') and self.db:
            try:
                doc_ref = self.db.collection('users').document(self.user_id).collection('emergencies').document()
                doc_ref.set({
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'reason': reason,
                    'status': 'active'
                })
                print(f"📡 Emergency synced to Firebase for user {self.user_id}")
            except Exception as e:
                print(f"🔴 Failed to sync emergency to Firestore: {e}")

        # Dispatch Telegram Alert
        if send_telegram_alert:
            try:
                telegram_msg = f"🚨 GUARDIAN AI CRITICAL ALERT 🚨\n\nReason: {reason}\nTime: {time.strftime('%H:%M:%S')}\nDevice: {self.user_id}"
                send_telegram_alert(telegram_msg)
                print("📩 Telegram emergency message dispatched.")
            except Exception as e:
                print(f"🔴 Failed to invoke Telegram alert module: {e}")

    def emergency_complete(self):
       self.emergency_active = False
       self.voice_history.clear()
       print("🟢 Emergency state reset")

