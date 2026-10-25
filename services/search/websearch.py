import re
import urllib.parse
import urllib.request

from core import config

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _opener():
    proxy = config.get_http_proxy_url()
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    return urllib.request.build_opener()


UNTRUSTED_DOMAINS = (
    "aparat.com", "tamasha.com", "namasha.com", "dalfak.com", "mp4.ir", "namayesh.com",
    "tarafdari.com", "ninisite.com", "virgool.io",
    "blogfa.com", "mihanblog.com", "blogsky.com", "rozblog.com", "parsiblog.com",
    "yasdl.com", "sarzamindownload.com", "p30download.com", "downloadha.com", "par30dl.net",
    "soft98.ir", "farsroid.com"
)


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


def search(query: str, limit: int = 5):
    """جستجوی DuckDuckGo (نسخه‌ی لایت) — لیست {title, url, snippet} برمی‌گردونه."""
    url = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    html = _opener().open(req, timeout=20).read().decode("utf-8", "ignore")

    results = []
    fallback = []
    for m in re.finditer(r"<a[^>]*class='result-link'[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", html, re.S):
        href, title = m.group(1), _clean(m.group(2))
        tail = html[m.end():m.end() + 3000]
        sm = re.search(r"class='result-snippet'>\s*(.*?)</td>", tail, re.S)
        snippet = _clean(sm.group(1)) if sm else ""
        real = ""
        um = re.search(r"uddg=([^&]+)", href)
        if um:
            real = urllib.parse.unquote(um.group(1))
        if not title or not real:
            continue
        entry = {"title": title, "url": real, "snippet": snippet, "date": ""}
        if _is_untrusted(real, query):
            fallback.append(entry)
        else:
            results.append(entry)
        if len(results) >= limit:
            break

    candidates = results if results else fallback
    return candidates[:limit]


def format_results(results) -> str:
    lines = []
    for i, r in enumerate(results, 1):
        dt = f" [تاریخ: {r['date']}]" if r.get("date") else ""
        lines.append(f"{i}. {r['title']}{dt}\n   خلاصه: {r['snippet']}\n   منبع معتبر: {r['url']}")
    return "\n\n".join(lines)
