import sys
import os
import time

print("--- Testing Picamera2 Custom Import ---")

# HACK: Enable system-installed Picamera2 
picam2_paths = [
    "/usr/lib/python3/dist-packages",
    "/usr/lib/python3.11/dist-packages",
    "/usr/lib/python3.9/dist-packages",
]
for p in picam2_paths:
    if os.path.exists(p) and p not in sys.path:
        sys.path.append(p)
        print(f"Added path: {p}")

try:
    import picamera2
    print(f"✅ Module 'picamera2' imported. File: {picamera2.__file__}")
    
    from picamera2 import Picamera2
    print("✅ Class 'Picamera2' imported.")
    
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (640, 480)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.configure("preview")
    picam2.start()
    print("✅ Camera started successfully!")
    time.sleep(2)
    picam2.stop()
    print("✅ Camera stopped.")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

import numpy
print(f"Numpy version: {numpy.__version__}")
