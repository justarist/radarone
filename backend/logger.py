import re
import os
import logging
import requests
from dotenv import load_dotenv
from logging.handlers import TimedRotatingFileHandler

load_dotenv()
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

EMOJI_PATTERN = re.compile(
    "[" 
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)

class EmojiStripFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = EMOJI_PATTERN.sub("", record.msg)
        return True
    
class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url):
        super().__init__()
        self.webhook_url = webhook_url

    def emit(self, record):
        try:
            msg = self.format(record)
            
            max_length = 1950 
            if len(msg) > max_length:
                msg = msg[:max_length] + "...\n[full in logs]"
                
            content = f"```text\n{msg}\n```"
            payload = {
                "content": content,
                "username": "Radar ONE Logger"
            }
            
            requests.post(self.webhook_url, json=payload, timeout=5)
            
        except Exception:
            self.handleError(record)

class TelegramHandler(logging.Handler):
    def __init__(self, token, chat_id):
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def emit(self, record):
        try:
            msg = self.format(record)
            max_length = 4000
            if len(msg) > max_length:
                msg = msg[:max_length] + "...\n[full in logs]"
            
            payload = {
                "chat_id": self.chat_id,
                "text": f"<code>{msg}</code>",
                "parse_mode": "HTML"
            }
            requests.post(self.api_url, json=payload, timeout=5)
        except Exception:
            self.handleError(record)

def renamer(name):
    base, date = name.rsplit(".", 1)
    filename, ext = os.path.splitext(base)
    return f"{filename}_{date}{ext}"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.addFilter(EmojiStripFilter())

file_handler = TimedRotatingFileHandler(
    os.path.join(log_dir, "radarone.log"),
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
file_handler.namer = renamer

file_handler.setFormatter(formatter)
file_handler.addFilter(EmojiStripFilter())

if DISCORD_WEBHOOK_URL:
    discord_handler = DiscordWebhookHandler(DISCORD_WEBHOOK_URL)
    discord_handler.setFormatter(formatter)
    logger.addHandler(discord_handler)

logger.addHandler(console_handler)
logger.addHandler(file_handler)
