# Guardian AI - Core Hardware & Processing System

Welcome to the **Guardian AI Core Repository**. This project powers the hardware sensing, computer vision logic, and acoustic intelligence processing that operates locally on edge devices (such as a Raspberry Pi or Windows machine). 

*Note: The React frontend Web Dashboard is located in the `website/` directory (which acts as a separate application/repository).*

## 🧠 What is Guardian AI?
Guardian AI is a real-time, multi-modal anomaly detection system designed for personal security and health monitoring. It runs highly optimized AI inference models on video and audio streams simultaneously without manual user intervention. 

When an emergency or anomaly is confirmed, it seamlessly dispatches a critical alert through GSM (SMS) and pushes the event to Firebase Firestore, instantly updating the user's Web Dashboard.

## 🚀 Core Features & Capabilities

- **Instant Fall Detection**: Utilizes **YOLOv8 pose-estimation** to map 17 human keypoints in real-time. Sophisticated temporal and geometric heuristic engines classify falls with sub-second latency while rejecting false positives (e.g., sitting down).
- **Gesture Recognition**: Uses the same YOLOv8 skeleton to detect specific distress indicators like "Hands on Chest", "Hands Raised", or "Crossed Arms". 
- **Acoustic Intelligence**: A fully parallel background process (`voice_process.py`) continuously listens for explicit distress keywords across multiple localized languages (English, Malayalam, etc).
- **Intelligent Decision Engine**: State-machine logic in `decision_engine.py` evaluates combined sensor inputs. For example, if a "Hand on Chest" is detected concurrently with an acoustic distress keyword, an immediate "Critical Event" is synthesized.
- **Hardware Integration Ecosystem**: Supports standard webcams, PiCamera2, GStreamer workflows, and SIM-based GSM notification channels.

---

## 🛠️ Architecture Overview

The system runs on Python's `multiprocessing` architecture to achieve real-time capabilities without thread-blocking.
* **`main.py`**: The entry point. It spawns the Vision (`fall_process.py`) and Audio (`voice_process.py`) sub-processes, managing a unified Event Queue.
* **`fall_process.py`**: Handles video capture using efficient Pi pipelines if available, performs YOLO inference, and extracts both Fall and Gesture states per frame.
* **`decision_engine.py`**: Consumes the event queue. Handles logic rules (e.g., "Fall > 10s" or "Keyword repeated 3x"). Pushes active emergencies to Firebase.
* **`gsm.py`**: Hard-line fallback communication used to SMS emergency contacts when internet is unavailable.

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- **Python 3.9+** installed on your system.
- Standard webcam or Raspberry Pi Camera Module.
- Unix/Linux system is recommended (Raspberry Pi OS Bookworm/Bullseye), though Windows works flawlessly with standard cameras.

### 2. Clone the Repository
```bash
git clone <your-github-repo-url>
cd Guardian-AI
```

### 3. Install Python Dependencies
It is highly recommended to use a virtual environment.
```bash
pip install -r requirements.txt
```
*(Optional for Raspberry Pi users)*: If you are setting this up on a fresh Raspberry Pi, you might need system-level libraries for OpenCV and PyAudio. Run the provided helper script:
```bash
bash setup_pi.sh
```

### 4. Configure Firebase
To connect the hardware engine to the cloud Web Dashboard:
1. Navigate to your Firebase Console.
2. Generate an **Admin SDK Private Key** (`.json`).
3. Save that file in the root of this folder exactly as `service_account.json`.

*(Note: `service_account.json` is kept highly secure and is included in `.gitignore` to prevent leaking cloud credentials)*

### 5. Pair Your Device
To ensure the hardware syncs to your specific user account on the dashboard:
1. Edit or create the file `device_config.json`.
2. Format it with your matching Firebase Authentication `user_id`:
   ```json
   {
       "user_id": "YOUR_FIREBASE_UID_HERE"
   }
   ```

---

## 🏃 Running the System

To start the Guardian AI multi-process safeguard system:
```bash
python main.py
```

The system will:
1. Initialize the YOLOv8 pose model (downloading the `.pt` file if it's your first run).
2. Attempt to securely grab the `cv2` or `picamera2` video feed.
3. Hook into the microphone.
4. Output real-time events to the terminal and sync anomalies securely to the cloud.

Enjoy total peace of mind!
