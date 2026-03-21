import time
import sys
import os
import warnings
warnings.filterwarnings('ignore')

# HACK: Enable system-installed Picamera2 (needs system numpy usually)
# We do this EARLY, before importing 'fall' OR 'cv2' which might import 'numpy'
# This avoids ABI conflicts between venv-numpy and system-picamera2.
picam2_paths = [
    "/usr/lib/python3/dist-packages",
    "/usr/lib/python3.11/dist-packages",
    "/usr/lib/python3.9/dist-packages",
]
for p in picam2_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.append(p)

try:
    from picamera2 import Picamera2
    print("[FallProcess] Global import: Picamera2 loaded successfully.")
except ImportError:
    Picamera2 = None
    print("[FallProcess] Global import: Picamera2 not found (yet).")
except Exception as e:
    Picamera2 = None
    # Just print warning, don't crash yet
    print(f"[FallProcess] Global import: Picamera2 error: {e}")

# Now safe to import cv2 (it will use the numpy loaded by picamera2 if verified)
import cv2
from multiprocessing import Queue
from fall import SimpleHighAccuracyFallDetector
from gesture import detect_gesture


def run_fall_process(event_queue: Queue, cam_index=0, emergency_flag=None):
    detector = SimpleHighAccuracyFallDetector()

    def fall_state_callback(state, timestamp):
        event_queue.put({
            "type": "fall_state",
            "state": state,
            "time": timestamp
        })

    detector.on_state_change = fall_state_callback

    # Wrapper for Picamera2 to mimic cv2.VideoCapture
    class PiCamera2Wrapper:
        def __init__(self):
            self.is_running = False
            self.picam2 = None
            
            if Picamera2 is None:
                print("⚠️ Picamera2 library not declared globally.")
                return

            try:
                # Use globally imported class
                self.picam2 = Picamera2()
                
                # CONFIG FROM old.py
                self.picam2.preview_configuration.main.size = (640, 480)
                self.picam2.preview_configuration.main.format = "RGB888"
                self.picam2.configure("preview")
                self.picam2.start()
                
                # Warmup
                time.sleep(2)
                
                self.is_running = True
                print("✅ Picamera2 initialized successfully! (Matches old.py config)")
            except Exception as e:
                print(f"⚠️ Picamera2 init failed: {e}")
                if self.picam2:
                    self.picam2.stop()
                self.is_running = False

        def read(self):
            if not self.is_running:
                return False, None
            try:
                # wait=True ensures we get the latest frame
                frame = self.picam2.capture_array()
                
                # Convert RGB (Picamera2) to BGR (OpenCV)
                # old.py used RGB but OpenCV imshow expects BGR. 
                # We convert to ensure colors are correct.
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                return True, frame
            except Exception as e:
                print(f"⚠️ Picamera2 capture failed: {e}")
                return False, None
        
        def isOpened(self):
            return self.is_running

        def release(self):
            if self.is_running:
                self.picam2.stop()
                self.is_running = False
        
        def set(self, prop, val):
            pass

    # Try different camera indices to find a working one
    def open_camera():
        # 0. Try Picamera2 (Requested by User for Pi Bookworm)
        print("[FallProcess] Attempting Picamera2...")
        try:
            picam = PiCamera2Wrapper()
            if picam.isOpened():
                return picam
        except ImportError:
            print("⚠️ Picamera2 library not found (okay if on Windows).")
        except Exception as e:
             print(f"⚠️ Picamera2 failed: {e}")

        # 1. Try GStreamer Pipeline (Best for Pi Bookworm + libcamera)
        print("[FallProcess] Attempting GStreamer pipeline (libcamerasrc)...")
        gst_pipeline = (
            "libcamerasrc ! video/x-raw, width=640, height=480, framerate=30/1 ! "
            "videoconvert ! videoscale ! video/x-raw, format=BGR ! appsink drop=1"
        )
        cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print("✅ GStreamer pipeline opened and reading frames!")
                return cap
            else:
                print("⚠️ GStreamer opened but failed to read frame.")
                cap.release()
        else:
            print("⚠️ GStreamer pipeline failed to open.")

        # 2. Try standard indices if GStreamer fails
        # Indices to try: default 0, then -1 (any), then 1 (common for USB)
        indices = [cam_index, -1, 0, 1]
        # Remove duplicates while preserving order
        indices = list(dict.fromkeys(indices))
        
        for idx in indices:
            print(f"[FallProcess] Attempting to open camera index {idx}...")
            # Try V4L2 backend for Linux/Pi (often more reliable)
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            if not cap.isOpened():
                 # Fallback to default backend
                cap = cv2.VideoCapture(idx)
            
            if cap.isOpened():
                # FORCE MJPG (Critical for Raspberry Pi V4L2)
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                # Verify we can actually read a frame
                ret, _ = cap.read()
                if ret:
                    print(f"✅ Camera index {idx} opened and reading frames!")
                    return cap
                
                # If MJPG failed, try YUYV
                print(f"⚠️ Index {idx} MJPG failed, trying YUYV...")
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
                ret, _ = cap.read()
                if ret:
                     print(f"✅ Camera index {idx} opened with YUYV!")
                     return cap

                print(f"⚠️ Camera index {idx} opened but failed to read frame (MJPG & YUYV). releasing...")
                cap.release()
        return None

    cap = open_camera()

    if cap is None:
        print("❌ CRITICAL: Could not open any camera.")
        event_queue.put({"type": "error", "source": "camera", "message": "No camera found"})
        return

    # ✅ NEW: confirm camera + fall pipeline is alive
    event_queue.put({
        "type": "fall_state",
        "state": "CAMERA_ACTIVE",
        "time": time.time()
    })
    event_queue.put({
        "type": "gesture_state",
        "state": "CAMERA_ACTIVE",
        "time": time.time()
    })

    print("📷 Camera opened, vision (fall & gesture) detection running")

    last_heartbeat_time = 0
    current_gesture_state = "MONITORING"

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Camera read failed (empty frame)")
            time.sleep(0.1)
            continue

        fall_conf, stand_conf, keypoints = detector.process_frame_fast(frame)
        now = time.time()

        # ======== GESTURE LOGIC ========
        detected_gesture = "MONITORING"
        if keypoints is not None and len(keypoints) > 0:
            for person in keypoints:
                # Normalize keypoints to 0.0-1.0 as gesture.py expects
                norm_person = []
                for kp in person:
                    norm_person.append([kp[0] / 640.0, kp[1] / 480.0, kp[2]])
                
                gesture = detect_gesture(norm_person, (480, 640, 3))
                if "Hand on Chest" in gesture:
                    detected_gesture = "Hand on Chest"
                    break
                elif "Hand on Head" in gesture:
                    detected_gesture = "Hand on Head"
                elif "Hands Raised" in gesture:
                    detected_gesture = "Hands Raised"
                elif "Crossed Arms" in gesture:
                    detected_gesture = "Crossed Arms"

        if detected_gesture != current_gesture_state:
            event_queue.put({
                "type": "gesture_state",
                "state": detected_gesture,
                "time": now
            })
            current_gesture_state = detected_gesture

        # ======== RECORD & DRAW ========
        is_emergency = False
        if emergency_flag:
            is_emergency = bool(emergency_flag.value)
            
        detector.draw_results(frame, fall_conf, stand_conf, keypoints, emergency_active=is_emergency)
        
        color = (0, 0, 255) if current_gesture_state != "MONITORING" else (0, 255, 0)
        cv2.putText(frame, f"Gesture: {current_gesture_state}", (20, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # ✅ HEARTBEAT: Force update every 0.5s if active
        if (detector.state == "FALL_DETECTED" or current_gesture_state != "MONITORING") and (now - last_heartbeat_time > 0.5):
            if detector.state == "FALL_DETECTED":
                event_queue.put({
                    "type": "fall_state",
                    "state": "FALL_DETECTED",
                    "time": now
                })
            if current_gesture_state != "MONITORING":
                event_queue.put({
                    "type": "gesture_state",
                    "state": current_gesture_state,
                    "time": now
                })
            last_heartbeat_time = now

        # Display - wrap in try-except for headless support
        try:
            cv2.imshow("Fall Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        except Exception:
            # Likely headless environment or no X11 forwarding
            pass

    cap.release()
    cv2.destroyAllWindows()
