from deepface import DeepFace
import cv2

# Real-time emotion detection with DeepFace (no model files needed)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    try:
        analysis = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
        emotion = analysis[0]['dominant_emotion']
        
        cv2.putText(frame, f"Emotion: {emotion}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
    except Exception as e:
        cv2.putText(frame, "No face detected", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    cv2.imshow('Emotion Detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()