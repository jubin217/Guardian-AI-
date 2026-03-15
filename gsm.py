import serial
import time

PHONE_NUMBER = "+919645064490"   # Replace with your phone number


def send_sms(message):

    try:
        print("?? Connecting to GSM module...")

        gsm = serial.Serial("/dev/serial0", 9600, timeout=1)

        time.sleep(2)

        gsm.write(b'AT\r')
        time.sleep(1)

        gsm.write(b'AT+CMGF=1\r')   # Set SMS text mode
        time.sleep(1)

        command = f'AT+CMGS="{PHONE_NUMBER}"\r'
        gsm.write(command.encode())

        time.sleep(1)

        gsm.write(message.encode())

        time.sleep(1)

        gsm.write(bytes([26]))   # CTRL+Z to send SMS

        print("? Emergency SMS Sent")

    except Exception as e:
        print("? GSM Error:", e)
