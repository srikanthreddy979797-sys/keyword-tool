import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_whatsapp_alert(message: str) -> bool:
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            print("Telegram credentials missing")
            print(message)
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print("Telegram alert sent")
            return True
        else:
            print(f"Telegram error: {r.text}")
            return False

    except Exception as e:
        print(f"Telegram error: {e}")
        return False
