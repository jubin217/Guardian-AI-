import time
import sys
import os
import warnings
warnings.filterwarnings('ignore')

# HACK: Enable system-installed Picamera2 (needs system numpy usually)
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
    print("[GestureProcess] Global import: Picamera2 loaded successfully.")
except ImportError:
    Picamera2 = None
    print("[GestureProcess] Global import: Picamera2 not found (yet).")
except Exception as e:
    Picamera2 = None
    print(f"[GestureProcess] Global import: Picamera2 error: {e}")

import cv2
from multiprocessing import Queue
from ultralytics import YOLO
from gesture import detect_gesture


def run_gesture_process(event_queue: Queue, cam_index=0, emergency_flag=None):
    print("⏳ Loading YOLO Pose Model...")
    model = YOLO("yolov8n-pose.pt")

    class PiCamera2Wrapper:
        def __init__(self):
            self.is_running = False
            self.picam2 = None
            
            if Picamera2 is None:
                print("⚠️ Picamera2 library not declared globally.")
                return

            try:
                self.picam2 = Picamera2()
                self.picam2.preview_configuration.main.size = (640, 480)
                self.picam2.preview_configuration.main.format = "RGB888"
                self.picam2.configure("preview")
                self.picam2.start()
                time.sleep(2)
                self.is_running = True
                print("✅ Picamera2 initialized successfully!")
            except Exception as e:
                print(f"⚠️ Picamera2 init failed: {e}")
                if self.picam2:
                    self.picam2.stop()
                self.is_running = False

        def read(self):
            if not self.is_running:
                return False, None
            try:
                frame = self.picam2.capture_array()
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

    def open_camera():
        print("[GestureProcess] Attempting Picamera2...")
        try:
            picam = PiCamera2Wrapper()
            if picam.isOpened():
                return picam
        except Exception as e:
             print(f"⚠️ Picamera2 failed: {e}")

        print("[GestureProcess] Attempting GStreamer pipeline (libcamerasrc)...")
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
            cap.release()

        indices = [cam_index, -1, 0, 1]
        indices = list(dict.fromkeys(indices))
        
        for idx in indices:
            print(f"[GestureProcess] Attempting to open camera index {idx}...")
            cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap = cv2.VideoCapture(idx)
            
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                ret, _ = cap.read()
                if ret:
                    print(f"✅ Camera index {idx} opened and reading frames!")
                    return cap
                
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
                ret, _ = cap.read()
                if ret:
                     print(f"✅ Camera index {idx} opened with YUYV!")
                     return cap

                cap.release()
        return None

    cap = open_camera()

    if cap is None:
        print("❌ CRITICAL: Could not open any camera for gesture.")
        event_queue.put({"type": "error", "source": "gesture_camera", "message": "No camera found"})
        return

    event_queue.put({
        "type": "gesture_state",
        "state": "CAMERA_ACTIVE",
        "time": time.time()
    })

    print("📷 Camera opened, gesture detection running")

    last_heartbeat_time = 0
    current_state = "MONITORING"

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Camera read failed (empty frame)")
            time.sleep(0.1)
            continue

        results = model(frame, verbose=False)
        detected_gesture = "MONITORING"

        for res in results:
            if hasattr(res, "keypoints") and res.keypoints is not None:
                keypoints = res.keypoints.data.cpu().numpy()
                for person in keypoints:
                    gesture = detect_gesture(person, frame.shape)
                    if "Hand on Chest" in gesture:
                        detected_gesture = "Hand on Chest"
                        break
                    elif "Hand on Head" in gesture:
                        detected_gesture = "Hand on Head"
                    elif "Hands Raised" in gesture:
                        detected_gesture = "Hands Raised"
                    elif "Crossed Arms" in gesture:
                        detected_gesture = "Crossed Arms"

        if detected_gesture != current_state:
            event_queue.put({
                "type": "gesture_state",
                "state": detected_gesture,
                "time": time.time()
            })
            current_state = detected_gesture

        now = time.time()
        if current_state != "MONITORING" and (now - last_heartbeat_time > 0.5):
            event_queue.put({
                "type": "gesture_state",
                "state": current_state,
                "time": now
            })
            last_heartbeat_time = now

        try:
            color = (0, 0, 255) if current_state != "MONITORING" else (0, 255, 0)
            cv2.putText(frame, f"Gesture: {current_state}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.imshow("Gesture Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        except Exception:
            pass

    cap.release()
    cv2.destroyAllWindows()
