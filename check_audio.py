import sounddevice as sd

print("🎧 Audio Device Scanner 🎧")
print("--------------------------------------------------")

try:
    devices = sd.query_devices()
    default_input = sd.default.device[0]
    
    for i, dev in enumerate(devices):
        mark = " "
        if i == default_input:
            mark = "*"
        
        name = dev.get('name')
        inputs = dev.get('max_input_channels')
        sample_rate = dev.get('default_samplerate')
        
        if inputs > 0:
            print(f"{mark} [{i}] {name}")
            print(f"      Inputs: {inputs}, Default Rate: {sample_rate}Hz")
            
            # Test if it supports 16000Hz (needed for Vosk)
            try:
                sd.check_input_settings(device=i, channels=1, samplerate=16000, dtype='int16')
                print("      ✅ Supports 16kHz")
            except Exception as e:
                print(f"      ⚠️ No 16kHz support: {e}")
            print("--------------------------------------------------")

except Exception as e:
    print(f"Error querying devices: {e}")
