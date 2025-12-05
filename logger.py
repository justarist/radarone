import logging
import re

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

logger = logging.getLogger("project")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.addFilter(EmojiStripFilter())

file_handler = logging.FileHandler("project.log", encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.addFilter(EmojiStripFilter())
 
logger.addHandler(console_handler)
logger.addHandler(file_handler)
