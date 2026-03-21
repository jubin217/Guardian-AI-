import time
from multiprocessing import Process, Queue, Value

from decision_engine import EmergencyDecisionEngine
from fall_process import run_fall_process
from voice_process import run_voice_process
from gsm import send_sms


if __name__ == "__main__":

    print("\n?? MULTIPROCESS EMERGENCY SYSTEM STARTED\n")

    event_queue = Queue()

    # Shared flag for emergency state
    emergency_flag = Value('b', False)

    engine = EmergencyDecisionEngine(emergency_flag)

    fall_p = Process(
        target=run_fall_process,
        args=(event_queue, 0, emergency_flag)
    )

    voice_en_p = Process(
        target=run_voice_process,
        args=(event_queue,)
    )

    fall_p.start()
    voice_en_p.start()

    last_emergency_state = False

    try:
        while True:

            event = event_queue.get()

            if event["type"] == "fall_state":

                print(f"?? Fall event received: {event['state']}")

                engine.update_fall_state(
                    event["state"],
                    event["time"]
                )

            elif event["type"] == "voice":

                print(f"?? Voice keyword detected: {event['word']}")

                engine.register_voice_keyword(
                    event["word"],
                    event["time"]
                )

            elif event["type"] == "gesture_state":

                print(f"?? Gesture event received: {event['state']}")

                engine.update_gesture_state(
                    event["state"],
                    event["time"]
                )

            # Check emergency trigger
            if emergency_flag.value and not last_emergency_state:

                print("\n?? EMERGENCY DETECTED ??\n")

                message = """
?? EMERGENCY ALERT

Fall detected with distress voice.

Immediate assistance required.
"""

                send_sms(message)

                last_emergency_state = True

            # Reset state
            if not emergency_flag.value:
                last_emergency_state = False

    except KeyboardInterrupt:

        print("\n?? Shutting down system")

        fall_p.terminate()
        voice_en_p.terminate()
