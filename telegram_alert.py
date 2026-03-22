import requests

BOT_TOKEN = "8129067049:AAGiTMnzZscTvEzB7ixsl-IBSLtRg00vboc"

EMERGENCY_CONTACTS = [
    1682650677,
    5088861608
]

def send_telegram_alert(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for chat_id in EMERGENCY_CONTACTS:

        payload = {
            "chat_id": chat_id,
            "text": message
        }

        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print("Telegram send failed:", e)
