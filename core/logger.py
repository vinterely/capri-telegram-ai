import logging
from logging.handlers import RotatingFileHandler
import os
import re
import sys

_INITIALIZED = False


def setup_logging():
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True

    log_level_str = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bot.log")

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,  # 2MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Avoid duplicate handlers if setup is called multiple times
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(console_handler)

    # کتابخانه‌های پرچانه و داخلی: فیلتر کردن لاگ‌های متفرقه و هشدارهای غیرضروری سوکت و متادیتا
    for noisy in (
        "httpx", "httpcore",
        "urllib3", "urllib3.connectionpool", "urllib3.util.retry",
        "google_genai", "google_genai.types", "google.genai",
        "telethon.client.updates",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


def sanitize_text(text: str, max_len: int = 80) -> str:
    """خلاصه‌سازی متن برای ثبت ایمن در لاگ بدون افشای داده‌های طولانی."""
    if not text:
        return ""
    clean = " ".join(str(text).split())
    if len(clean) > max_len:
        return clean[:max_len] + "..."
    return clean


_SECRET_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"\bsk-[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization)\s*[=:]\s*[^\s,;]+"),
    re.compile(r"(?i)\b[a-f0-9]{32,}\b"),
)


def redact_secrets(text: str) -> str:
    """حذف کلیدها/توکن‌های احتمالی از متن پیش از لاگ یا نمایش."""
    if not text:
        return ""
    t = str(text)
    for pat in _SECRET_PATTERNS:
        t = pat.sub("<REDACTED>", t)
    return t
