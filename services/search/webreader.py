import html
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

from core import config

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# تگ‌هایی که باید کلاً حذف شوند
DROP_TAGS_RE = re.compile(
    r"<(script|style|noscript|header|footer|nav|svg|iframe|aside)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL
)

TAG_RE = re.compile(r"<[^>]+>")


def _clean_html(raw_html: str, max_chars: int = 10000) -> dict:
    """استخراج عنوان و متن تمیز صفحه بدون کدهای جاوااسکریپت، استایل‌ها و تبلیغات."""
    # استخراج تایتل
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_html, re.IGNORECASE | re.DOTALL)
    title = html.unescape(title_match.group(1)).strip() if title_match else ""

    # استخراج توضیحات متا
    desc_match = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
        raw_html,
        re.IGNORECASE | re.DOTALL
    )
    desc = html.unescape(desc_match.group(1)).strip() if desc_match else ""

    # حذف تگ‌های زائد
    text = DROP_TAGS_RE.sub(" ", raw_html)

    # تبدیل تگ‌های پاراگراف و خط به لاین‌بریک
    text = re.sub(r"<(?:p|div|h[1-6]|li|br)[^>]*>", "\n", text, flags=re.IGNORECASE)

    # حذف سایر تگ‌های HTML
    text = TAG_RE.sub(" ", text)

    # تبدیل موجودیت‌های HTML (مانند &amp; و &nbsp;)
    text = html.unescape(text)

    # تمیزکاری فاصله‌ها و خطوط خالی مکرر
    lines = []
    for line in text.splitlines():
        l = " ".join(line.split())
        if l and len(l) > 20:  # خطوط معنی‌دار
            lines.append(l)

    cleaned_text = "\n\n".join(lines)
    if len(cleaned_text) > max_chars:
        cleaned_text = cleaned_text[:max_chars] + "\n\n... (ادامه متن به دلیل حجم بالا کوتاه شد)"

    return {
        "title": title,
        "description": desc,
        "content": cleaned_text
    }


_BLOCKED_NAMES = ("localhost",)
_BLOCKED_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home", ".localdomain")


def _is_safe_url(url: str) -> bool:
    """جلوگیری از دسترسی به localhost، شبکه داخلی و آدرس‌های خصوصی (SSRF)."""
    try:
        p = urllib.parse.urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return False
        host = p.hostname.strip().lower().rstrip(".")
        if not host or any(ch.isspace() for ch in host):
            return False
        if host in _BLOCKED_NAMES or host.endswith(_BLOCKED_SUFFIXES):
            return False
        try:
            ip = ipaddress.ip_address(host)
            if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
                ip = ip.ipv4_mapped
            return ip.is_global
        except ValueError:
            pass  # نام دامنه است، نه IP
        if config.get_http_proxy_url():
            # با پروکسی، DNS را پروکسی حل می‌کند (DNS محلی ممکن است مسموم/فیلتر باشد) → فقط بررسی نام
            return "." in host
        for info in socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP):
            resolved = ipaddress.ip_address(info[4][0])
            if isinstance(resolved, ipaddress.IPv6Address) and resolved.ipv4_mapped:
                resolved = resolved.ipv4_mapped
            if not resolved.is_global:
                return False
        return True
    except Exception:
        return False


_MAX_REDIRECTS = 5


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self._redirect_count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self._redirect_count += 1
        if self._redirect_count > _MAX_REDIRECTS:
            raise urllib.error.URLError("تعداد ریدایرکت‌ها بیش از حد مجاز است")
        if not _is_safe_url(newurl):
            raise urllib.error.URLError("ریدایرکت به آدرس غیرمجاز مسدود شد")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch_url(url: str, timeout: int = 25) -> dict:
    """دریافت و استخراج محتوای متنی یک لینک وب با پشتیبانی از پروکسی."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    if not _is_safe_url(url):
        return {"url": url, "title": "", "description": "", "content": "", "error": "این آدرس مجاز نیست (شبکه داخلی/لوکال)."}

    proxy = config.get_http_proxy_url()
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}),
            _SafeRedirect(),
        )
    else:
        opener = urllib.request.build_opener(_SafeRedirect())

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fa,en-US;q=0.9,en;q=0.8",
        }
    )

    try:
        with opener.open(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()

            raw_bytes = resp.read(3_000_000)  # سقف ۳ مگابایت
            try:
                raw_text = raw_bytes.decode(charset, errors="replace")
            except Exception:
                raw_text = raw_bytes.decode("utf-8", errors="replace")

        data = _clean_html(raw_text)
        data["url"] = url
        return data
    except Exception as e:
        return {"url": url, "title": "", "description": "", "content": "", "error": str(e)}
