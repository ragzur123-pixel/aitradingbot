import os
import requests
import logging
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Notifier:
    """
    Unified Notification System for Telegram and Discord.
    Handles trade alerts, system heartbeats, and error reporting.
    """
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.enabled = any([self.telegram_token and self.telegram_chat_id, self.discord_webhook_url])
        
        if not self.enabled:
            logging.warning("Notifier: No Telegram or Discord credentials found in .env. Notifications are disabled.")

    def send_telegram(self, message):
        """Send message via Telegram Bot API."""
        if not (self.telegram_token and self.telegram_chat_id):
            return False
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Telegram Notification Failed: {e}")
            return False

    def send_discord(self, message):
        """Send message via Discord Webhook."""
        if not self.discord_webhook_url:
            return False
        
        payload = {"content": message}
        try:
            response = requests.post(self.discord_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logging.error(f"Discord Notification Failed: {e}")
            return False

    def wait_for_approval(self, message, timeout=3600):
        """
        Sends an approval request to Telegram and waits for a response.
        In D1 cycle, we can wait up to 1 hour for a human decision.
        """
        if not self.telegram_token:
            logger.warning("HITL: No Telegram token. Auto-approving.")
            return True

        # Send the request with 'APPROVE' / 'VETO' buttons
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": f"🎯 <b>HITL APPROVAL REQUIRED</b>\n\n{message}\n\nShould we fire the trigger?",
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "✅ FIRE", "callback_data": "APPROVE"},
                    {"text": "❌ VETO", "callback_data": "VETO"}
                ]]
            }
        }
        
        try:
            requests.post(url, json=payload, timeout=10)
            logger.info("HITL: Approval request sent to Telegram. Waiting...")
            
            # Polling for response (Simplified for this architecture)
            # In a production env, use a webhook or a separate bot listener.
            # Here we poll the 'getUpdates' endpoint.
            start_time = time.time()
            while (time.time() - start_time) < timeout:
                upd_url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates"
                updates = requests.get(upd_url).json()
                if updates.get("result"):
                    # Find the latest callback from the user
                    for upd in reversed(updates["result"]):
                        cb = upd.get("callback_query")
                        if cb and cb.get("data") in ["APPROVE", "VETO"]:
                            decision = cb["data"]
                            logger.info(f"HITL: Human decision received: {decision}")
                            return decision == "APPROVE"
                time.sleep(10)
                
            logger.warning("HITL: Decision Timeout. Defaulting to VETO.")
            return False
        except Exception as e:
            logger.error(f"HITL Error: {e}")
            return False

    def notify(self, message, alert_type="INFO"):
        """
        Send notification to all enabled channels.
        alert_type: INFO, TRADE, ERROR, CRITICAL
        """
        if not self.enabled:
            # Safe print for Windows consoles to avoid charmap errors
            safe_message = message.encode('ascii', 'ignore').decode('ascii')
            print(f"[Notifier - {alert_type}] {safe_message}")
            return

        # Formatting based on type
        prefix = {
            "INFO": "ℹ️ <b>[SYSTEM INFO]</b>",
            "TRADE": "💰 <b>[TRADE ALERT]</b>",
            "ERROR": "⚠️ <b>[SYSTEM ERROR]</b>",
            "CRITICAL": "🚨 <b>[CRITICAL FAILURE]</b>"
        }.get(alert_type, "ℹ️")

        formatted_message = f"{prefix}\n{message}"
        
        # Telegram
        self.send_telegram(formatted_message)
        
        # Discord (Discord doesn't support HTML, so we strip or replace if needed, 
        # but standard markdown often works)
        discord_msg = formatted_message.replace("<b>", "**").replace("</b>", "**")
        self.send_discord(discord_msg)

    def get_log_tail(self, log_file, lines=20):
        """Fetches the last N lines of a log file."""
        if not os.path.exists(log_file):
            return "Log file not found."
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.readlines()
                tail = content[-lines:]
                return "".join(tail)
        except Exception as e:
            return f"Error reading log: {e}"

    def send_log_tail(self, log_file, lines=50):
        """Sends the last N lines of a log file to notification channels."""
        tail = self.get_log_tail(log_file, lines)
        msg = f"📜 <b>Log Tail: {log_file}</b>\n<pre>{tail}</pre>"
        self.notify(msg, alert_type="INFO")

if __name__ == "__main__":
    # Test Notifier
    logging.basicConfig(level=logging.INFO)
    n = Notifier()
    n.notify("Notification System initialized successfully.", alert_type="INFO")
