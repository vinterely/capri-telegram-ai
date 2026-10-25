import asyncio
import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from ai_engine import ai
from core import config
from services.search import gsearch

log = logging.getLogger("ytsummary")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

YT_URL_PATTERN = re.compile(
    r"(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?.*?v=|shorts\/|embed\/|v\/|live\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)


def extract_youtube_id(text_or_url: str) -> Optional[str]:
    """استخراج شناسه ۱۱ رقمی ویدیوی یوتیوب از متن یا لینک."""
    if not text_or_url:
        return None
    m = YT_URL_PATTERN.search(text_or_url)
    return m.group(1) if m else None


def _opener():
    proxy = config.get_http_proxy_url()
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    return urllib.request.build_opener()


def get_oembed_data(video_id: str) -> Dict[str, Any]:
    """دریافت متادیتای اولیه ویدیو از سرویس رسمی و سبک oEmbed یوتیوب."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
    req = urllib.request.Request(oembed_url, headers={"User-Agent": UA})
    try:
        with _opener().open(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.warning(f"oEmbed fetch failed for {video_id}: {e}")
        return {}


def get_ytdlp_data(video_id: str) -> Dict[str, Any]:
    """دریافت اطلاعات تکمیلی (دیسکریپشن، فصول، زمان و زیرنویس) از طریق yt-dlp بدون دانلود ویدیو."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    proxy = config.get_http_proxy_url()
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "proxy": proxy if proxy else None,
    }
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info or {}
    except Exception as e:
        log.warning(f"yt-dlp extract failed for {video_id}: {e}")
        return {}


def _format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def summarize_youtube_video(video_url_or_id: str) -> str:
    """
    خلاصه‌سازی هوشمند ویدیوی یوتیوب بدون مصرف پهنای باند و بدون دانلود فایل ویدیو.
    از متادیتا، توضیحات، فصول (Chapters)، و نتایج جستجوی موتور وب برای نگارش خلاصه استفاده می‌کند.
    """
    vid = extract_youtube_id(video_url_or_id)
    if not vid:
        # اگر کاربر فقط شناسه ۱۱ رقمی فرستاده باشد
        clean = video_url_or_id.strip()
        if len(clean) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", clean):
            vid = clean
        else:
            return "❌ لینک یا شناسه ویدیوی یوتیوب معتبر یافت نشد."

    # ۱. متادیتای پایه از oEmbed
    oembed = get_oembed_data(vid)
    title = oembed.get("title", "")
    author = oembed.get("author_name", "")

    # ۲. اطلاعات تکمیلی از yt-dlp (در صورت در دسترس بودن بدون بلاک)
    ytdlp = get_ytdlp_data(vid)
    if not title and ytdlp.get("title"):
        title = ytdlp.get("title")
    if not author and ytdlp.get("uploader"):
        author = ytdlp.get("uploader")

    description = ytdlp.get("description", "")
    duration_sec = ytdlp.get("duration")
    duration_str = _format_duration(duration_sec)
    chapters = ytdlp.get("chapters") or []
    tags = ytdlp.get("tags") or []

    # ساخت متن فصل‌ها در صورت وجود
    chapters_text = ""
    if chapters:
        ch_lines = []
        for ch in chapters[:15]:
            st = _format_duration(ch.get("start_time"))
            ch_lines.append(f"- {st} : {ch.get('title')}")
        chapters_text = "\n".join(ch_lines)

    # ۳. جستجوی وب برای اطلاعات و خلاصه تکمیلی پیرامون ویدیو
    search_context = ""
    query_title = title or vid
    search_q = f"\"{query_title}\" {author} youtube summary review"
    try:
        web_res = gsearch.web_search(search_q, limit=4)
        if web_res:
            snippets = []
            for item in web_res:
                snippets.append(f"• {item.get('title')}: {item.get('snippet')}")
            search_context = "\n".join(snippets)
    except Exception as e:
        log.warning(f"Web search for youtube summary failed: {e}")

    # ۴. تجمیع زمینه برای هوش مصنوعی
    context_parts = []
    context_parts.append(f"شناسه ویدیو: {vid}")
    if title:
        context_parts.append(f"عنوان ویدیو: {title}")
    if author:
        context_parts.append(f"سازنده/کانال: {author}")
    if duration_str:
        context_parts.append(f"مدت زمان: {duration_str}")
    if tags:
        context_parts.append(f"برچسب‌ها: {', '.join(tags[:10])}")
    if chapters_text:
        context_parts.append(f"فصل‌بندی و زمان‌بندی ویدیو (Chapters):\n{chapters_text}")
    if description:
        # حداکثر ۲۰۰۰ کاراکتر از دیسکریپشن برای پرهیز از شلوغی
        context_parts.append(f"توضیحات ویدیو (Description):\n{description[:2500]}")
    if search_context:
        context_parts.append(f"اطلاعات وب و بازخوردها درباره این ویدیو:\n{search_context}")

    full_context = "\n\n".join(context_parts)

    if not title and not description and not search_context:
        return f"❌ متأسفانه اطلاعاتی برای ویدیوی یوتیوب `{vid}` یافت نشد (احتمالاً ویدیو خصوصی یا حذف شده است)."

    # ۵. دستور خلاصه سازی برای هوش مصنوعی
    prompt = (
        "تو کاپری (Capri) هستی. یک ویدیوی یوتیوب با اطلاعات زیر در اختیارت قرار گرفته است:\n\n"
        f"{full_context}\n\n"
        "وظیفه تو این است که یک خلاصه‌ی بسیار حرفه‌ای، تمیز، ساختاریافته و جذاب به زبان فارسی بنویسی.\n"
        "قالب پاسخ دقیقاً باید به شکل زیر باشد:\n"
        f"🎬 **{title or 'ویدیوی یوتیوب'}**\n"
        f"👤 **کانال:** {author or 'مشخص نشده'}" + (f" | ⏱ **مدت:** {duration_str}" if duration_str else "") + f"\n"
        f"🔗 https://youtu.be/{vid}\n\n"
        "📌 **ایده و موضوع اصلی ویدیو:**\n"
        "(در ۱ تا ۲ پاراگراف روان و صمیمی توضیح بده ویدیو دقیقاً درباره چیه و چه هدفی داره)\n\n"
        "🔑 **نکات کلیدی و مباحث مهم (Key Takeaways):**\n"
        "- (نکته یا آموزش مهم ۱)\n"
        "- (نکته یا آموزش مهم ۲)\n"
        "- (نکته یا آموزش مهم ۳)\n"
        "- ...\n\n"
        + ("📑 **سرفصل‌های ویدیو (Chapters):**\n(سرفصل‌های مهم به همراه زمان)\n\n" if chapters_text else "")
        + "💡 **جمع‌بندی نهایی و ارزش تماشا:**\n"
        "(آیا تماشای این ویدیو ارزشش رو داره و برای چه کسانی مفیده؟)\n\n"
        "نکته مهم: لحنت صمیمی، محاوره‌ای و محترم باشه. هیچ متنی درباره دانلود ویدیو یا حجم ننویس."
    )

    try:
        summary = ai.ask(prompt)
        return summary
    except Exception as e:
        return f"❌ خطا در پردازش خلاصه‌ساز یوتیوب: {e}"
