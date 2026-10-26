import os
import uuid

from dotenv import load_dotenv

VERSION = "2.2.0"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def _get_int(name: str, default: int = 0) -> int:
    val = os.getenv(name, "").strip()
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default

def _get_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

API_ID = _get_int("API_ID", 123456)
API_HASH = _get_str("API_HASH", "00000000000000000000000000000000")
GEMINI_API_KEY = _get_str("GEMINI_API_KEY", "")
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_KEY_2", "").strip()
GEMINI_API_KEYS = list(dict.fromkeys([k for k in (GEMINI_API_KEY, GEMINI_API_KEY_2) if k]))
GEMINI_VIDEO_API_KEY = os.getenv("GEMINI_VIDEO_API_KEY", "").strip() or GEMINI_API_KEY
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
GEMINI_MODELS = [m.strip() for m in GEMINI_MODEL.split(",") if m.strip()]
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "کاپری,capri").strip()
ASSISTANT_NAMES = [n.strip() for n in ASSISTANT_NAME.split(",") if n.strip()]
OWNER_NAME = os.getenv("OWNER_NAME", "Owner").strip()
FREEMODEL_API_KEY = os.getenv("FREEMODEL_API_KEY", "").strip()
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "").strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
HOOSHIA_API_KEY = os.getenv("HOOSHIA_API_KEY", "").strip()
INCEPTION_API_KEY = os.getenv("INCEPTION_API_KEY", "").strip()
ANYAPI_KEY = os.getenv("ANYAPI_KEY", "").strip()
BAI_KEY = os.getenv("BAI_KEY", "").strip()
XKIRO_KEY = os.getenv("XKIRO_KEY", "").strip()
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
ALLOW_SKILL_CREATION = os.getenv("ALLOW_SKILL_CREATION", "0").strip() == "1"
SOCIAL_DL_BOT = os.getenv("SOCIAL_DL_BOT", "@MooNDLBoT").strip()
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
SESSION_FILE = os.path.join(BASE_DIR, "session")
PROXY_TYPE = os.getenv("PROXY_TYPE", "").strip().lower()
PROXY_HOST = os.getenv("PROXY_HOST", "").strip()
PROXY_PORT = int(os.getenv("PROXY_PORT", "0") or 0)
PROXY_USER = os.getenv("PROXY_USER", "").strip()
PROXY_PASS = os.getenv("PROXY_PASS", "").strip()

def get_proxy():
    if not PROXY_TYPE or not PROXY_HOST or not PROXY_PORT:
        return None
    if PROXY_USER:
        return (PROXY_TYPE, PROXY_HOST, PROXY_PORT, True, PROXY_USER, PROXY_PASS)
    return (PROXY_TYPE, PROXY_HOST, PROXY_PORT)

def get_http_proxy_url():
    """Resolve HTTP/HTTPS proxy URL using socks5h for remote DNS resolution or explicit scheme."""
    if not PROXY_TYPE or not PROXY_HOST or not PROXY_PORT:
        return None
    scheme = "socks5h" if PROXY_TYPE == "socks5" else PROXY_TYPE
    if PROXY_USER:
        return f"{scheme}://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
    return f"{scheme}://{PROXY_HOST}:{PROXY_PORT}"

def _load_instance_id() -> str:
    """شناسه یکتای پایدار این نمونه از ربات (بار اول ساخته و در فایل ذخیره می‌شود)."""
    path = os.path.join(BASE_DIR, "instance.id")
    try:
        with open(path, encoding="utf-8") as f:
            val = f.read().strip()
        if val:
            return val
    except OSError:
        pass
    new_id = uuid.uuid4().hex
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_id)
    except OSError:
        pass
    return new_id

INSTANCE_ID = _load_instance_id()

def validate() -> None:
    """Validate core configuration parameters on startup."""
    if not API_ID or API_ID == 123456:
        raise SystemExit("❌ API_ID is not configured in .env. Please see .env.example.")
    if not API_HASH or API_HASH == "00000000000000000000000000000000":
        raise SystemExit("❌ API_HASH is not configured in .env. Please see .env.example.")
    if not GEMINI_API_KEY:
        raise SystemExit("❌ GEMINI_API_KEY is not configured in .env. Please see .env.example.")
    if not ASSISTANT_NAMES:
        raise SystemExit("❌ ASSISTANT_NAME is empty; please set at least one wake name in .env.")
    proxy_parts = (PROXY_TYPE, PROXY_HOST, PROXY_PORT)
    if any(proxy_parts) and not all(proxy_parts):
        raise SystemExit("❌ Incomplete proxy configuration; PROXY_TYPE, PROXY_HOST, and PROXY_PORT must all be set together.")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    if not os.path.isdir(DOWNLOAD_DIR) or not os.access(DOWNLOAD_DIR, os.W_OK):
        raise SystemExit(f"❌ Download directory is not writable: {DOWNLOAD_DIR}")
