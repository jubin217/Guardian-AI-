import time
from collections import deque

class EmergencyDecisionEngine:
    def __init__(self, emergency_flag=None):
        # --- SHARED STATE ---
        self.emergency_flag = emergency_flag

        # --- FALL TRACKING ---
        self.fall_state = "MONITORING"
        self.fall_start_time = None

        # --- VOICE TRACKING ---
        self.voice_events = deque()  # stores timestamps of voice keywords
        self.last_voice_time = 0

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

    def emergency_complete(self):
       self.emergency_active = False
       self.voice_history.clear()
       print("🟢 Emergency state reset")

