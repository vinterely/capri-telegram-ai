import concurrent.futures
import json
import random
import threading
import time
from urllib.parse import urlsplit
import requests

from core import config
from core import logger
from ai_engine import models

log = logger.get_logger(__name__)

TIMEOUT = 25
RACE_COUNT = 3

RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3

_tls = threading.local()


def _session() -> requests.Session:
    """Thread-local Session with connection pooling and resilient keep-alive adapters."""
    s = getattr(_tls, "session", None)
    if s is None:
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=0
        )
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _tls.session = s
    return s


def _backoff(attempt: int, retry_after=None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except (TypeError, ValueError):
            pass
    return min(2 ** attempt, 8.0) + random.uniform(0, 0.5)

FREEMODEL_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "claude-3-haiku"]
HF_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct"]
GROQ_MODELS = [m["id"] for m in models.GROQ]
OPENROUTER_MODELS = [m["id"] for m in models.OPENROUTER]
GITHUB_MODELS = ["gpt-4o", "gpt-4o-mini"]
COHERE_MODELS = ["command-r7b-12-2024", "command-a-03-2025"]
HOOSHIA_MODELS = ["GLM-4.5-Flash", "GLM-4.6V-Flash", "GLM-4.7-Flash"]
INCEPTION_MODELS = ["mercury-3"]


def _get_proxies():
    proxy = config.get_http_proxy_url()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}


def _post(url: str, payload: dict, headers: dict, timeout: int = TIMEOUT) -> dict:
    all_headers = {**DEFAULT_HEADERS, "Content-Type": "application/json", **headers}
    domain = urlsplit(url).netloc.lower()
    # هوشیا و دامنه‌های ایرانی بدون پراکسی مستقیم و سریع‌تر هستند
    is_domestic = "hooshia.com" in domain or domain.endswith(".ir")
    proxies = None if is_domestic else _get_proxies()

    last_err = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            resp = _session().post(url, json=payload, headers=all_headers, proxies=proxies, timeout=timeout)
        except requests.exceptions.SSLError as e:
            # Stale SSL keep-alive socket in session pool - close and reset session
            try:
                if hasattr(_tls, "session") and _tls.session:
                    _tls.session.close()
            except Exception:
                pass
            _tls.session = None
            last_err = e
            # در صورتی که هاست ایرانی با اتصال مستقیم خطای SSL داد، یک بار با پراکسی تلاش کن
            if is_domestic and proxies is None and attempt == 0:
                sys_proxies = _get_proxies()
                if sys_proxies:
                    proxies = sys_proxies
                    continue
            # سوکت کهنه یا نوسان موقت پروکسی: یک‌بار با نشست جدید و سوکت تمیز تلاش مجدد کن
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(0.2)
                continue
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # خطای شبکه‌ی موقت: با backoff نمایی + jitter دوباره تلاش کن
            last_err = e
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(_backoff(attempt))
                continue
            break
        except requests.exceptions.RequestException as e:
            last_err = e
            break

        if resp.status_code in RETRYABLE_STATUS:
            last_err = requests.exceptions.HTTPError(
                f"{resp.status_code} error from {domain}", response=resp)
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(_backoff(attempt, resp.headers.get("Retry-After")))
                continue
            break

        if resp.status_code >= 400:
            # 400/401/403/404 و... هرگز retry نمی‌شوند
            last_err = requests.exceptions.HTTPError(
                f"{resp.status_code} error from {domain}", response=resp)
            break

        return resp.json()

    status = getattr(getattr(last_err, "response", None), "status_code", "unknown")
    log.info("Provider %s unavailable: %s (%s). Swapping to fallback provider.", domain, type(last_err).__name__, status)
    raise last_err


def _openai_chat(endpoint, model, api_key, system, user, extra_headers=None, timeout=TIMEOUT, max_tokens=1024):
    headers = {"Authorization": f"Bearer {api_key}"}
    if extra_headers:
        headers.update(extra_headers)
    data = _post(
        endpoint,
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.8,
            "max_tokens": max_tokens,
        },
        headers,
        timeout=timeout,
    )
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        return ""


def _cohere_chat(model, system, user, api_key, timeout=TIMEOUT):
    data = _post(
        "https://api.cohere.ai/v1/chat",
        {
            "model": model,
            "message": user,
            "preamble": system,
            "temperature": 0.7,
            "max_tokens": 1024,
        },
        {
            "Authorization": f"Bearer {api_key}",
            "Cohere-Version": "2024-03-14",
        },
        timeout=timeout,
    )
    return (data.get("text") or "").strip()


def _try(fn):
    try:
        return fn()
    except Exception as e:
        log.debug("Provider try failed: %s", type(e).__name__)
        return ""


def _layer_cohere(system, user):
    if not config.COHERE_API_KEY:
        return None, None
    for model in COHERE_MODELS:
        for attempt in range(2):
            try:
                text = _cohere_chat(model, system, user, config.COHERE_API_KEY)
                if text:
                    return text, f"Cohere-{model}"
                break
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429 and attempt < 1:
                    time.sleep(1.5)
                    continue
                break
            except Exception:
                break
    return None, None


def _layer_openai(endpoint, models, api_key, name, system, user, extra_headers=None, timeout=TIMEOUT, max_tokens=1024):
    if not api_key:
        return None, None
    for model in models:
        text = _try(lambda m=model: _openai_chat(
            endpoint, m, api_key, system, user, extra_headers, timeout, max_tokens))
        if text:
            return text, f"{name}-{model}"
    return None, None


def _layer_freemodel(system, user):
    return _layer_openai(
        "https://api.freemodel.dev/v1/chat/completions",
        FREEMODEL_MODELS, config.FREEMODEL_API_KEY, "FreeModel", system, user)


def _layer_hf(system, user):
    return _layer_openai(
        "https://router.huggingface.co/v1/chat/completions",
        HF_MODELS, config.HF_TOKEN, "HF", system, user)


def _layer_groq(system, user):
    return _layer_openai(
        "https://api.groq.com/openai/v1/chat/completions",
        GROQ_MODELS, config.GROQ_API_KEY, "Groq", system, user)


def _layer_openrouter(system, user):
    return _layer_openai(
        "https://openrouter.ai/api/v1/chat/completions",
        OPENROUTER_MODELS, config.OPENROUTER_API_KEY, "OpenRouter", system, user,
        extra_headers={"HTTP-Referer": "https://github.com", "X-Title": "Capri"})


def _layer_github(system, user):
    return _layer_openai(
        "https://models.inference.ai.azure.com/chat/completions",
        GITHUB_MODELS, config.GITHUB_TOKEN, "GitHub", system, user, timeout=8)


def _layer_hooshia(system, user):
    return _layer_openai(
        "https://hooshia.com/api/v1/chat/completions",
        HOOSHIA_MODELS, config.HOOSHIA_API_KEY, "Hooshia", system, user, timeout=60, max_tokens=2048)


def _layer_inception(system, user):
    return _layer_openai(
        "https://api.inceptionlabs.ai/v1/chat/completions",
        INCEPTION_MODELS, config.INCEPTION_API_KEY, "Inception", system, user, timeout=40, max_tokens=2048)


LAYERS = {
    "cohere": _layer_cohere,
    "freemodel": _layer_freemodel,
    "hf": _layer_hf,
    "groq": _layer_groq,
    "openrouter": _layer_openrouter,
    "github": _layer_github,
    "hooshia": _layer_hooshia,
    "inception": _layer_inception,
}

FALLBACK_ORDER = ["hooshia", "inception", "cohere", "openrouter", "groq", "freemodel", "hf", "github"]


def ask_layer(name: str, system: str, user: str):
    fn = LAYERS.get(name)
    if not fn:
        return None, None
    return fn(system, user)


def ask_model(service: str, model: str, system: str, user: str):
    """یه مدل خاص از یه سرویس رو صدا می‌زنه. (text, source) یا (None, None)."""
    s = (service or "").lower()
    if s == "groq":
        return _layer_openai(
            "https://api.groq.com/openai/v1/chat/completions",
            [model], config.GROQ_API_KEY, "Groq", system, user)
    if s == "openrouter":
        return _layer_openai(
            "https://openrouter.ai/api/v1/chat/completions",
            [model], config.OPENROUTER_API_KEY, "OpenRouter", system, user,
            extra_headers={"HTTP-Referer": "https://github.com", "X-Title": "Capri"})
    if s == "hooshia":
        return _layer_openai(
            "https://hooshia.com/api/v1/chat/completions",
            [model], config.HOOSHIA_API_KEY, "Hooshia", system, user, timeout=60, max_tokens=2048)
    if s == "inception":
        return _layer_openai(
            "https://api.inceptionlabs.ai/v1/chat/completions",
            [model], config.INCEPTION_API_KEY, "Inception", system, user, timeout=40, max_tokens=2048)
    if s == "freemodel":
        return _layer_openai(
            "https://api.freemodel.dev/v1/chat/completions",
            [model], config.FREEMODEL_API_KEY, "FreeModel", system, user)
    if s == "github":
        return _layer_openai(
            "https://models.inference.ai.azure.com/chat/completions",
            [model], config.GITHUB_TOKEN, "GitHub", system, user)
    if s == "hf":
        return _layer_openai(
            "https://router.huggingface.co/v1/chat/completions",
            [model], config.HF_TOKEN, "HF", system, user)
    return None, None


def ask_race(names, system: str, user: str):
    """چند مدل رو همزمان امتحان می‌کنه؛ اولین جواب غیرخالی. (text, source) یا (None, None)."""
    if not names:
        return None, None
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=len(names), thread_name_prefix="capri")
    try:
        futs = {ex.submit(ask_layer, n, system, user): n for n in names}
        for fut in concurrent.futures.as_completed(futs):
            try:
                text, source = fut.result()
            except Exception:
                continue
            if text:
                return text, source
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    return None, None


def ask_fallback(system: str, user: str):
    """چند مدل اول همزمان (race)، بعد بقیه به ترتیب. اولین جواب غیرخالی رو برمی‌گردونه."""
    text, source = ask_race(FALLBACK_ORDER[:RACE_COUNT], system, user)
    if text:
        return text, source
    for name in FALLBACK_ORDER[RACE_COUNT:]:
        text, source = ask_layer(name, system, user)
        if text:
            return text, source
    return None, None
