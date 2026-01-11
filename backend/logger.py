import re
import os
import datetime
import logging
from logging.handlers import TimedRotatingFileHandler

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
 
logger.addHandler(console_handler)
logger.addHandler(file_handler)
