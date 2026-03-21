import serial
import time

# CRITICAL: SIM800L requires the country code for reliable delivery
# Replace +91 with your country code if you are not in India
PHONE_NUMBER = "+919645064490"

def send_sms(message):
    try:
        print("📡 Connecting to GSM module (/dev/serial0 at 9600 baud)...")
        gsm = serial.Serial("/dev/serial0", 9600, timeout=2)
        time.sleep(2)

        def send_cmd(cmd, delay=1):
            gsm.write(cmd.encode() + b'\r')
            time.sleep(delay)
            # Read whatever the module responded with
            response = gsm.read_all().decode(errors='ignore').strip()
            print(f"CMD: {cmd} | RESP: {response.replace(chr(13), ' ').replace(chr(10), ' ')}")
            return response

        print("\n--- Testing Module & Network ---")
        send_cmd("AT", 1)
        send_cmd("AT+CPIN?", 1) # Check if SIM is locked
        
        # Check network registration (+CREG: 0,1 means registered to home network)
        creg = send_cmd("AT+CREG?", 1)
        if "0,1" not in creg and "0,5" not in creg:
            print("⚠️ WARNING: SIM might not be registered to the network!")
            print("To fix: Check SIM orientation, power supply (needs 2A), and antenna.")
        
        print("\n--- Configuring SMS Mode ---")
        send_cmd("AT+CMGF=1", 1)

        print("\n--- Sending SMS ---")
        # Start message prompt -> requires wait for '>'
        gsm.write(f'AT+CMGS="{PHONE_NUMBER}"\r'.encode())
        time.sleep(1)
        
        # Read the '>' prompt
        print(f"Prompt output: {gsm.read_all().decode(errors='ignore').strip()}")
        
        # Write actual message
        print(f"Uploading message content...")
        gsm.write(message.encode())
        time.sleep(1)
        
        # Send Ctrl+Z to execute and SEND
        gsm.write(bytes([26])) 
        
        # Sending an SMS takes longer than changing modes. Wait up to 5 seconds.
        print("⏳ Waiting for network delivery confirmation (this takes a few seconds)...")
        time.sleep(5)
        
        final_response = gsm.read_all().decode(errors='ignore').strip()
        print(f"\nFINAL OUTPUT:\n{final_response}\n")
        
        if "+CMGS:" in final_response or "OK" in final_response:
             print("✅ Emergency SMS Sent Successfully to telecom network!")
        else:
             print("❌ Failed or took too long to send. Check SIM balance, validity, and signal strength.")

    except serial.SerialException as e:
        print("❌ Serial Error: Could not connect to /dev/serial0.")
        print("Did you enable Serial Port in raspi-config and disable the serial login shell?")
        print(e)
    except Exception as e:
        print("❌ GSM Error:", e)

if __name__ == "__main__":
    send_sms("🚨 GUARDIAN AI TEST: Emergency system is online.")
