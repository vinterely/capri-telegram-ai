"""ابزارهای کمکی برای نوشتن اتمیک فایل‌های JSON (temp + os.replace + قفل thread)."""
import json
import os
import tempfile
import threading

_locks = {}
_locks_guard = threading.Lock()


def _lock_for(path: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(path, threading.Lock())


def atomic_write_json(path: str, data, mode: int = 0o600) -> None:
    """نوشتن اتمیک داده به فایل JSON: ابتدا در فایل موقت، سپس os.replace (بدون نیمه‌نوشته شدن) با پرمیشن ایمن."""
    lock = _lock_for(path)
    with lock:
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            try:
                os.chmod(tmp, mode)
            except Exception:
                pass
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
            try:
                os.chmod(path, mode)
            except Exception:
                pass
        except Exception:
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
