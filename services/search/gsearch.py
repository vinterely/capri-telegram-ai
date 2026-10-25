import concurrent.futures
import json
import re
import urllib.parse
import urllib.request

from core import config

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# سایت‌های فاقد اعتبار استنادی (ویدیوهای اشتراکی، فروم‌های عمومی نامرتبط، بلاگ‌های زرد و سایت‌های دانلود با نسخه‌بندی نامعتبر)
UNTRUSTED_DOMAINS = (
    "aparat.com", "tamasha.com", "namasha.com", "dalfak.com", "mp4.ir", "namayesh.com",
    "tarafdari.com", "ninisite.com", "virgool.io",
    "blogfa.com", "mihanblog.com", "blogsky.com", "rozblog.com", "parsiblog.com",
    "yasdl.com", "sarzamindownload.com", "p30download.com", "downloadha.com", "par30dl.net",
    "soft98.ir", "farsroid.com"
)

# نشانه‌های منابع دست‌اول، رسمی، دانشگاهی، فروم‌های گیمینگ/فنی یا ژورنالیستی معتبر
AUTHORITATIVE_INDICATORS = (
    ".gov", ".edu", ".org", "wikipedia.org", "github.com", "reddit.com", "stackoverflow.com",
    "medium.com", "dev.to", "arxiv.org", "w3schools.com", "geeksforgeeks.org",
    "docs.", "developer.", "support.", "feedback.", "news.",
    "theverge.com", "reuters.com", "bbc.com", "ign.com", "bloomberg.com",
    "zoomit.ir", "digiato.com", "isna.ir", "irna.ir"
)


def _opener():
    proxy = config.get_http_proxy_url()
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    return urllib.request.build_opener()


def _post(url: str, payload: dict, timeout: int = 20) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-KEY": config.SERPER_API_KEY,
            "User-Agent": UA,
        },
        method="POST",
    )
    with _opener().open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _is_untrusted(url: str, query: str) -> bool:
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        host = url.lower()
    q_low = query.lower()
    for domain in UNTRUSTED_DOMAINS:
        if domain in host:
            d_name = domain.split(".")[0]
            if d_name in q_low or ("آپارات" in query and "aparat" in domain):
                return False
            return True
    return False


def _is_authoritative(url: str) -> bool:
    u = url.lower()
    return any(ind in u for ind in AUTHORITATIVE_INDICATORS)


def generate_multilingual_queries(topic: str) -> dict:
    """
    تولید ۳ عبارت جستجوی هدفمند و بهینه به زبان‌های انگلیسی، چینی و فارسی:
    - انگلیسی: جهت دسترسی به فروم‌های بین‌المللی، ردیت، گیت‌هاب و مستندات رسمی
    - چینی: جهت دسترسی به عمیق‌ترین پایگاه‌های ترفندها، دیتابیس‌ها و فروم‌های تخصصی (NGA, Tieba, Bilibili)
    - فارسی: جهت دسترسی به وب فارسی
    """
    from ai_engine import providers
    sys_prompt = (
        "You are an expert research search query optimizer. Given a user topic or question, "
        "produce 3 optimal, concise search queries for Google:\n"
        "- en: English (optimized for Reddit, specialized forums, guides, wikis)\n"
        "- zh: Simplified Chinese (optimized for NGA, Baidu, gaming/tech wikis)\n"
        "- fa: Persian (concise keywords for Iranian web)\n\n"
        "Return ONLY a valid JSON object with keys 'en', 'zh', 'fa'. No commentary or markdown."
    )
    try:
        res, _ = providers.ask_model("groq", "qwen/qwen3.8-27b", sys_prompt, topic)
        if not res and config.OPENROUTER_API_KEY:
            res, _ = providers.ask_model("openrouter", "google/gemma-4-31b-it:free", sys_prompt, topic)
        if res:
            m = re.search(r"\{[\s\S]*\}", res)
            if m:
                d = json.loads(m.group(0))
                if all(k in d for k in ("en", "zh", "fa")):
                    return d
    except Exception:
        pass

    return {
        "en": topic,
        "zh": topic,
        "fa": topic,
    }


def multilingual_deep_search(query: str, limit_per_lang: int = 3) -> str:
    """
    کاوش عمیق، موازی و سه‌زبانه در وب (انگلیسی، چینی و فارسی):
    بررسی هم‌زمان مراجع بین‌المللی، فروم‌های تخصصی چین و وب فارسی.
    """
    if not config.SERPER_API_KEY:
        results = web_search(query, limit=5)
        return format_search_results(results) if results else "نتیجه‌ای یافت نشد."

    q_map = generate_multilingual_queries(query)

    def _fetch_lang(lang: str, q_str: str):
        hl = "en" if lang == "en" else ("zh-CN" if lang == "zh" else "fa")
        gl = "us" if lang == "en" else ("hk" if lang == "zh" else "ir")
        try:
            data = _post("https://google.serper.dev/search", {"q": q_str, "hl": hl, "gl": gl, "num": limit_per_lang + 3})
            organic = data.get("organic", [])
            valid = []
            for it in organic:
                u = it.get("link", "")
                if not u or _is_untrusted(u, q_str):
                    continue
                valid.append({
                    "title": it.get("title", ""),
                    "url": u,
                    "snippet": it.get("snippet", ""),
                    "date": it.get("date", "")
                })
                if len(valid) >= limit_per_lang:
                    break
            return lang, valid
        except Exception:
            return lang, []

    lang_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(_fetch_lang, lang, q_str) for lang, q_str in q_map.items()]
        for f in concurrent.futures.as_completed(futures):
            l, res = f.result()
            lang_results[l] = res

    output_lines = [f"📊 نتایج کاوش تخصصی سه‌زبانه برای موضوع: «{query}»\n"]

    labels = {
        "en": ("🌐 مراجع بین‌المللی و فروم‌های تخصصی (English)", q_map.get("en", "")),
        "zh": ("🇨🇳 منابع و فروم‌های تخصصی چینی (Chinese / NGA / Guides)", q_map.get("zh", "")),
        "fa": ("🇮🇷 منابع و فروم‌های فارسی (Persian)", q_map.get("fa", "")),
    }

    found_any = False
    for code, (label, search_phrase) in labels.items():
        items = lang_results.get(code, [])
        if not items:
            continue
        found_any = True
        output_lines.append(f"### {label}\nعبارت جستجو شده: `{search_phrase}`")
        for i, it in enumerate(items, 1):
            date_str = f" ({it['date']})" if it.get("date") else ""
            output_lines.append(f"{i}. [{it['title']}]({it['url']}){date_str}")
            if it.get("snippet"):
                output_lines.append(f"   خلاصه/نکات: {it['snippet']}")
        output_lines.append("")

    if not found_any:
        std = web_search(query, limit=5)
        if std:
            return format_search_results(std)
        return "هیچ نتیجه‌ای در جستجوی اینترنت یافت نشد."

    return "\n".join(output_lines)


def web_search(query: str, limit: int = 5):
    """Serper (Google results) با فیلتر منابع نامعتبر و اولویت‌بندی منابع رسمی."""
    if not config.SERPER_API_KEY:
        return None

    has_persian = bool(re.search(r"[\u0600-\u06FF]", query))
    hl = "fa" if has_persian else "en"

    fetch_num = max(limit * 2, 10)
    data = _post("https://google.serper.dev/search", {"q": query, "hl": hl, "num": fetch_num})

    results = []

    answer_box = data.get("answerBox")
    if isinstance(answer_box, dict):
        ab_title = answer_box.get("title") or "پاسخ مستقیم گوگل"
        ab_snip = answer_box.get("snippet") or answer_box.get("answer") or ""
        ab_link = answer_box.get("link", "")
        if ab_snip:
            results.append({
                "title": f"⭐ {ab_title}",
                "url": ab_link,
                "snippet": ab_snip,
                "date": answer_box.get("date", ""),
            })

    items = data.get("organic", [])
    valid_items = []
    fallback_items = []

    for it in items:
        url = it.get("link", "")
        if not url:
            continue
        entry = {
            "title": it.get("title", ""),
            "url": url,
            "snippet": it.get("snippet", ""),
            "date": it.get("date", ""),
        }
        if _is_untrusted(url, query):
            fallback_items.append(entry)
        else:
            valid_items.append(entry)

    candidates = valid_items if valid_items else fallback_items
    candidates.sort(key=lambda x: (1 if _is_authoritative(x["url"]) else 0, 1 if x["date"] else 0), reverse=True)

    for c in candidates:
        if len(results) >= limit:
            break
        if not any(r["url"] == c["url"] for r in results):
            results.append(c)

    return results[:limit]


def format_search_results(results: list) -> str:
    """فرمت‌دهی شکیل نتایج جهت مصرف مستقیم ایجنت."""
    if not results:
        return "هیچ نتیجه‌ای یافت نشد."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. [{r.get('title')}]({r.get('url')})")
        if r.get("snippet"):
            lines.append(f"   خلاصه: {r.get('snippet')}")
    return "\n".join(lines)


def image_search(query: str, limit: int = 5):
    if not config.SERPER_API_KEY:
        return None
    data = _post("https://google.serper.dev/images", {"q": query, "hl": "fa"})
    items = data.get("images", [])[:limit]
    out = [
        {"url": it.get("imageUrl", ""), "thumb": it.get("thumbnailUrl", ""), "title": it.get("title", "")}
        for it in items
    ]
    return [x for x in out if x["url"]]


def _looks_like_image(data: bytes) -> bool:
    if len(data) < 512:
        return False
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    if data[:2] == b"BM":
        return True
    return False


def _fetch(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Referer": "https://www.google.com/"},
    )
    with _opener().open(req, timeout=timeout) as resp:
        return resp.read()


def download(url: str, path: str) -> bool:
    for attempt in range(2):
        try:
            data = _fetch(url)
            if _looks_like_image(data):
                with open(path, "wb") as f:
                    f.write(data)
                return True
        except Exception:
            pass
    return False
