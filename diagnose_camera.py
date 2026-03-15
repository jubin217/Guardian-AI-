import cv2
import os
import glob
import time

def list_video_devices():
    devices = glob.glob('/dev/video*')
    print(f"Found video devices: {sorted(devices)}")
    return sorted(devices)

def test_camera(index):
    print(f"\n--- Testing Camera Index {index} ---")
    cap = cv2.VideoCapture(index)
    
    if not cap.isOpened():
        print(f"❌ Cannot open camera index {index}")
        return False
    
    print(f"✅ Camera index {index} opened successfully.")
    
    # Try setting properties (sometimes wakes it up)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Try reading frames
    success_count = 0
    for i in range(10):
        ret, frame = cap.read()
        if ret:
            success_count += 1
            if i == 0:
                print(f"✅ First frame captured! Resolution: {frame.shape}")
        else:
            print(f"⚠️ Frame {i} read failed (ret=False)")
            time.sleep(0.1)
            
    cap.release()
    
    if success_count > 0:
        print(f"✅ PASSED: Captured {success_count}/10 frames.")
        return True
    else:
        print("❌ FAILED: Opened but captured 0 frames.")
        return False

def main():
    print("search Raspberry Pi Camera Diagnostics")
    print("=======================================")
    
    devices = list_video_devices()
    
    indices_to_test = [0, 1, 2, -1]
    
    # Extract indices from /dev/videoX
    system_indices = []
    for dev in devices:
        try:
            idx = int(dev.replace('/dev/video', ''))
            system_indices.append(idx)
        except:
            pass
            
    if system_indices:
        indices_to_test = sorted(list(set(indices_to_test + system_indices)))
    
    working_indices = []
    for idx in indices_to_test:
        if idx < 0 and -1 not in indices_to_test: continue # skip negative usually unless explicit
        if test_camera(idx):
            working_indices.append(idx)
            
    print("\n=======================================")
    print(f"Summary: Working Camera Indices: {working_indices}")
    if not working_indices:
        print("❌ No working cameras found via OpenCV.")
        print("Tip: If using a Pi Camera Module, ensure legacy camera support is enabled (raspi-config -> Interfaces -> Legacy Camera) OR use libcamera-based OpenCV build.")

if __name__ == "__main__":
    main()
