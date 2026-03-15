import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import deque
import warnings
warnings.filterwarnings('ignore')

class SimpleHighAccuracyFallDetector:
    def __init__(self):
        print("Loading YOLOv8 Pose Estimation for fall detection...")
        
        self.on_state_change = None  # callback hook for decision engine

        # Load YOLOv8 pose model (this works reliably)
        self.pose_model = YOLO('yolov8n-pose.pt')  # Fast and accurate
        
        # State management
        self.state = "MONITORING"
        self.total_falls = 0
        self.consecutive_fall_frames = 0
        self.consecutive_stand_frames = 0
        self.fall_start_time = 0
        
        # Detection thresholds (tuned for accuracy)
        self.fall_confidence_threshold = 0.65
        self.required_fall_frames = 5
        self.required_stand_frames = 8
        
        # History for temporal consistency
        self.fall_confidence_history = deque(maxlen=8)
        self.pose_history = deque(maxlen=10)
        
        print("✅ Fall detection system ready!")
        print("📊 Using proven pose-based fall detection algorithms")

    def calculate_fall_confidence(self, keypoints, frame_shape):
        """Proven fall detection using multiple heuristics"""
        if keypoints is None or len(keypoints) == 0:
            return 0.0
        
        confidence_scores = []
        keypoints = keypoints[0]  # First person
        
        # 1. Torso Angle (Most reliable indicator)
        if len(keypoints) >= 13:
            left_shoulder = keypoints[5]
            right_shoulder = keypoints[6]
            left_hip = keypoints[11]
            right_hip = keypoints[12]
            
            # Check confidence scores for these keypoints
            if (left_shoulder[2] > 0.2 and right_shoulder[2] > 0.2 and 
                left_hip[2] > 0.2 and right_hip[2] > 0.2):
                
                shoulder_center = (left_shoulder[:2] + right_shoulder[:2]) / 2
                hip_center = (left_hip[:2] + right_hip[:2]) / 2
                
                # Calculate angle from vertical (0° = standing, 90° = lying)
                dx = hip_center[0] - shoulder_center[0]
                dy = hip_center[1] - shoulder_center[1]
                
                # Avoid division by zero
                if abs(dy) > 0.001:
                    angle = np.degrees(np.arctan2(abs(dx), abs(dy)))
                else:
                    angle = 90.0  # Horizontal
                
                # Research shows: angle > 45° indicates potential fall
                angle_confidence = max(0.0, min(1.0, (angle - 30) / 60.0))
                confidence_scores.append(angle_confidence * 0.5)  # 50% weight
        
        # 2. Body Aspect Ratio
        if len(keypoints) >= 17:
            valid_points = [kp for kp in keypoints if kp[2] > 0.2]  # Low confidence threshold
            if len(valid_points) >= 4:
                y_coords = [kp[1] for kp in valid_points]
                x_coords = [kp[0] for kp in valid_points]
                
                if y_coords and x_coords:
                    height = max(y_coords) - min(y_coords)
                    width = max(x_coords) - min(x_coords)
                    
                    if width > 0 and height > 0:
                        aspect_ratio = height / width
                        # Standing: ~2.0-3.0, Falling: ~0.5-1.5
                        if aspect_ratio < 1.0:
                            aspect_confidence = 1.0
                        elif aspect_ratio < 2.0:
                            aspect_confidence = 1.5 - (aspect_ratio / 2.0)
                        else:
                            aspect_confidence = 0.0
                        
                        confidence_scores.append(aspect_confidence * 0.3)  # 30% weight
        
        # 3. Ground Proximity
        if len(keypoints) >= 17:
            # Use ankles and head to determine if person is low in frame
            ankle_indices = [15, 16]
            head_indices = [3, 4]
            
            valid_ankles = [keypoints[i] for i in ankle_indices if keypoints[i][2] > 0.2]
            valid_head = [keypoints[i] for i in head_indices if keypoints[i][2] > 0.2]
            
            if valid_ankles and valid_head:
                ankle_y = max([kp[1] for kp in valid_ankles])
                head_y = min([kp[1] for kp in valid_head])
                
                # If ankles are very low in frame (fallen position)
                ground_confidence = min(1.0, ankle_y * 1.5)  # Normalized
                confidence_scores.append(ground_confidence * 0.2)  # 20% weight
        
        return min(1.0, sum(confidence_scores)) if confidence_scores else 0.0

    def calculate_stand_confidence(self, keypoints):
        """Calculate confidence that person is standing"""
        if keypoints is None or len(keypoints) == 0:
            return 0.0
        
        stand_scores = []
        keypoints = keypoints[0]
        
        # 1. Torso Verticality
        if len(keypoints) >= 13:
            left_shoulder = keypoints[5]
            right_shoulder = keypoints[6]
            left_hip = keypoints[11]
            right_hip = keypoints[12]
            
            if (left_shoulder[2] > 0.2 and right_shoulder[2] > 0.2 and 
                left_hip[2] > 0.2 and right_hip[2] > 0.2):
                
                shoulder_center = (left_shoulder[:2] + right_shoulder[:2]) / 2
                hip_center = (left_hip[:2] + right_hip[:2]) / 2
                
                dx = hip_center[0] - shoulder_center[0]
                dy = hip_center[1] - shoulder_center[1]
                
                if abs(dy) > 0.001:
                    angle = np.degrees(np.arctan2(abs(dx), abs(dy)))
                else:
                    angle = 90.0
                
                # Standing: angle < 25 degrees
                if angle < 25:
                    stand_confidence = 1.0
                elif angle < 45:
                    stand_confidence = 1.0 - ((angle - 25) / 20.0)
                else:
                    stand_confidence = 0.0
                
                stand_scores.append(stand_confidence)
        
        # 2. Body Height (standing people are taller in frame)
        if len(keypoints) >= 17:
            valid_points = [kp for kp in keypoints if kp[2] > 0.2]
            if len(valid_points) >= 4:
                y_coords = [kp[1] for kp in valid_points]
                if y_coords:
                    height = max(y_coords) - min(y_coords)
                    # Normalize height confidence
                    height_confidence = min(1.0, height * 2.0)
                    stand_scores.append(height_confidence * 0.5)
        
        return np.mean(stand_scores) if stand_scores else 0.0

    def update_state_machine(self, fall_confidence, stand_confidence):
        """Smart state management to reduce false alarms"""
        now = time.time()
        current_time = now
        
        if self.state == "MONITORING":
            if fall_confidence > self.fall_confidence_threshold:
                self.consecutive_fall_frames += 1
                self.fall_confidence_history.append(fall_confidence)
                
                # Confirm fall only after consistent detection
                if (self.consecutive_fall_frames >= self.required_fall_frames and 
                    np.mean(list(self.fall_confidence_history)) > self.fall_confidence_threshold):
                    
                    self.state = "FALL_DETECTED"
                    self.fall_start_time = current_time
                    self.total_falls += 1
                    self.consecutive_stand_frames = 0
                    
                    if self.on_state_change:
                        self.on_state_change(self.state, now)
                    
                    print(f"🚨 FALL DETECTED! Confidence: {fall_confidence:.3f}")
                    # print("System paused. Stand up to resume monitoring...")
            else:
                # Reset if confidence drops
                self.consecutive_fall_frames = max(0, self.consecutive_fall_frames - 2)
        
        elif self.state == "FALL_DETECTED":
            # Wait for person to stand up
            if stand_confidence > 0.7:
                self.consecutive_stand_frames += 1
                
                if self.consecutive_stand_frames >= self.required_stand_frames:
                    self.state = "MONITORING"
                    self.consecutive_fall_frames = 0
                    self.fall_confidence_history.clear()
                    
                    if self.on_state_change:
                        self.on_state_change(self.state, now)
                        
                    print("✅ PERSON STOOD UP! Resuming monitoring...")
            
            # Safety timeout - resume monitoring after 30 seconds
            # Note: For emergency system, we might NOT want to auto-resume so quickly, 
            # but falling back to monitoring if it was a false alarm is okay.
            elif current_time - self.fall_start_time > 30:
                # Optional: Don't auto-reset if we want to force manual reset for true emergencies
                # But for this logic we'll keep it to avoid getting stuck
                self.state = "MONITORING"
                self.consecutive_fall_frames = 0
                self.fall_confidence_history.clear()
                
                if self.on_state_change:
                        self.on_state_change(self.state, now)
                        
                print("⏰ Safety timeout: Resuming monitoring")

    def process_frame_fast(self, frame):
        """Optimized frame processing for real-time performance"""
        # Resize for faster processing while maintaining accuracy
        processing_frame = cv2.resize(frame, (640, 480))
        
        # Run pose estimation
        results = self.pose_model(processing_frame, verbose=False, conf=0.5, imgsz=320)
        
        fall_confidence = 0.0
        stand_confidence = 0.0
        keypoints = None
        
        if len(results) > 0 and results[0].keypoints is not None:
            keypoints = results[0].keypoints.data.cpu().numpy()
            
            if len(keypoints) > 0:
                # Calculate confidences
                fall_confidence = self.calculate_fall_confidence(keypoints, frame.shape)
                stand_confidence = self.calculate_stand_confidence(keypoints)
        
        # Update state machine
        self.update_state_machine(fall_confidence, stand_confidence)
        
        return fall_confidence, stand_confidence, keypoints

    def draw_results(self, frame, fall_confidence=0.0, stand_confidence=0.0, keypoints=None, emergency_active=False):
        """Draw comprehensive visualization"""
        # ================= EMERGENCY OVERLAY =================
        if emergency_active:
            # Flashing red/yellow alert
            pulse = int(time.time() * 10) % 2
            bg_color = (0, 0, 255) if pulse == 0 else (0, 255, 255)  # Red / Yellow flash
            text_color = (255, 255, 255) if pulse == 0 else (0, 0, 0) # White / Black text
            
            # Draw semi-transparent background
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), bg_color, -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            # Draw massive text
            alert_text = "🚨 EMERGENCY CONFIRMED! 🚨"
            font_scale = 1.2
            thickness = 4
            text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
            text_x = (frame.shape[1] - text_size[0]) // 2
            text_y = (frame.shape[0] + text_size[1]) // 2
            
            cv2.putText(frame, alert_text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness)
            
            # Subtitle
            sub_text = "HELP IS ON THE WAY"
            sub_size = cv2.getTextSize(sub_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
            sub_x = (frame.shape[1] - sub_size[0]) // 2
            cv2.putText(frame, sub_text, (sub_x, text_y + 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
            
            return # Skip other drawings to keep focus on emergency

        # ================= STANDARD DRAWING =================
        # State-based coloring
        if self.state == "MONITORING":
            color = (0, 255, 0)  # Green
            status_text = "MONITORING - System Active"
        else:
            color = (0, 0, 255)  # Red
            status_text = "FALL DETECTED!"
        
        # Draw status header
        cv2.putText(frame, status_text, (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Draw confidence information
        info_y = 80
        cv2.putText(frame, f"Fall Conf: {fall_confidence:.2f}", (20, info_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Stand Conf: {stand_confidence:.2f}", (20, info_y + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw pose skeleton if keypoints available
        if keypoints is not None and len(keypoints) > 0:
            keypoints = keypoints[0]
            
            # Define skeleton connections
            skeleton = [
                (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
                (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)  # Body & legs
            ]
            
            # Scale keypoints back to original frame size
            scale_x = frame.shape[1] / 640
            scale_y = frame.shape[0] / 480
            
            # Draw skeleton
            for i, j in skeleton:
                if (i < len(keypoints) and j < len(keypoints) and 
                    keypoints[i][2] > 0.1 and keypoints[j][2] > 0.1):
                    
                    x1 = int(keypoints[i][0] * scale_x)
                    y1 = int(keypoints[i][1] * scale_y)
                    x2 = int(keypoints[j][0] * scale_x)
                    y2 = int(keypoints[j][1] * scale_y)
                    
                    cv2.line(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw keypoints
            for i, kp in enumerate(keypoints):
                if kp[2] > 0.1:  # Low confidence threshold for visibility
                    x = int(kp[0] * scale_x)
                    y = int(kp[1] * scale_y)
                    cv2.circle(frame, (x, y), 4, color, -1)
        
        # Draw fall alert
        if self.state == "FALL_DETECTED":
            # Pulsing effect
            pulse_intensity = int(128 + 127 * np.sin(time.time() * 6))
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), 
                         (0, 0, pulse_intensity), -1)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            
            alert_text = "FALL DETECTED!"
            text_size = cv2.getTextSize(alert_text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 4)[0]
            text_x = (frame.shape[1] - text_size[0]) // 2
            text_y = (frame.shape[0] + text_size[1]) // 2
            cv2.putText(frame, alert_text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 4)

