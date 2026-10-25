import asyncio
import logging
import re
from typing import List, Optional, Tuple

from telethon import types
from services.media import fetch
from services.media import ytsummary

log = logging.getLogger("ytdownload")

PRIMARY_BOT = "MegaSaverBot"
FALLBACK_BOTS = ["Gozilla_bot", "SaveYoutubeBot"]

CONFIRM_HINTS = ("تایید", "تأیید", "بررسی", "عضویت", "عضو شدم", "چک", "check", "confirm", "✅", "شدم", "دریافت")
SPONSOR_HINTS = ("عضو", "عضویت", "کانال", "جوین", "سبسکرایب", "subscribe", "join")


def _pick_best_quality_button(buttons: list, target_quality: int = 720):
    """یافتن مناسب‌ترین دکمه کیفیت (پیش‌فرض 720) در کیبوردهای شیشه‌ای ربات."""
    quality_buttons = []
    for b in buttons:
        txt = b.text or ""
        q = fetch._label_quality(txt)
        if q:
            quality_buttons.append((q, b))

    if not quality_buttons:
        # اگر دکمه عددی پیدا نشد، دکمه‌های ویدیو/دانلود را جستجو کن
        for b in buttons:
            txt = (b.text or "").lower()
            if any(k in txt for k in ("video", "ویدیو", "720", "mp4", "دانلود")):
                return b
        return buttons[0] if buttons else None

    # ۱. تطبیق دقیق کیفیت درخواستی
    for q, b in quality_buttons:
        if q == target_quality:
            return b

    # ۲. نزدیک‌ترین کیفیت موجود به کیفیت درخواستی
    quality_buttons.sort(key=lambda x: abs(x[0] - target_quality))
    return quality_buttons[0][1]


async def _run_bot_download(
    client,
    bot_name: str,
    url: str,
    target_quality: int,
    event,
    status
) -> Tuple[bool, str]:
    """ارسال لینک یوتیوب به یک ربات تلگرام، انتخاب کیفیت و فوروارد فایل نهایی."""
    try:
        bot = await client.get_entity(bot_name)
    except Exception as e:
        log.warning("Could not resolve bot @%s: %s", bot_name, e)
        return False, f"ربات @{bot_name} در دسترس نیست."

    sent = await client.send_message(bot, url)
    base_id = sent.id
    joined_channels = []

    if status:
        try:
            await status.edit(f"🎬 لینک یوتیوب به ربات @{bot_name} ارسال شد. در حال دریافت گزینه‌های دانلود...")
        except Exception:
            pass

    clicked_data = set()
    quality_selected = False

    # حلقه بررسی پاسخ ربات (حداکثر ۱۸ گام ~ ۳۵ ثانیه)
    for step in range(18):
        await asyncio.sleep(2.0)
        msgs = await client.get_messages(bot, limit=10)

        # ۱. بررسی فایل‌های ویدیویی ارسالی توسط ربات
        for m in msgs:
            if m.out or m.id <= base_id:
                continue
            if isinstance(m.media, types.MessageMediaDocument):
                # ویدیوی نهایی آماده شده و ارسال گردید
                if status:
                    try:
                        await status.edit("🎬 فایل ویدیویی دریافت شد؛ در حال ارسال به شما...")
                    except Exception:
                        pass
                await client.forward_messages(event.chat_id, m)
                # ترک کانال‌های اسپانسری که احیاناً عضو شده بودیم
                for ch in joined_channels:
                    await fetch._leave(client, ch)
                return True, f"✅ ویدیوی یوتیوب با موفقیت با کیفیت {target_quality}p دریافت و ارسال شد."

        # ۲. بررسی پیام‌های دکمه‌دار ربات
        act = next((m for m in msgs if not m.out and m.id > base_id and m.buttons), None)
        if not act:
            continue

        buttons = [b for row in act.buttons for b in row]

        # ۲-الف) قفل اسپانسر / عضویت اجباری
        if fetch._is_sponsor(act):
            for b in buttons:
                if fetch._is_invite_url(b.url):
                    ch = await fetch._join(client, b.url)
                    if ch is not None and not any(getattr(c, "id", None) == ch.id for c in joined_channels):
                        joined_channels.append(ch)
                    await asyncio.sleep(1.0)
            confirm_btn = next((b for b in buttons if b.data and b.data not in clicked_data and any(h in (b.text or "").lower() for h in CONFIRM_HINTS)), None)
            if confirm_btn:
                try:
                    await act.click(data=confirm_btn.data)
                    clicked_data.add(confirm_btn.data)
                except Exception as e:
                    log.warning("Error clicking confirm button: %s", e)
                await asyncio.sleep(2.0)
                continue

        # ۲-ب) انتخاب کیفیت ویدیو (پیش‌فرض 720 یا کیفیت درخواستی کاربر)
        if not quality_selected:
            target_btn = _pick_best_quality_button(buttons, target_quality)
            if target_btn and target_btn.data and target_btn.data not in clicked_data:
                btn_label = target_btn.text or f"{target_quality}p"
                if status:
                    try:
                        await status.edit(f"🎬 کیفیت «{btn_label}» انتخاب شد؛ در حال پردازش و آپلود ویدیو...")
                    except Exception:
                        pass
                try:
                    await act.click(data=target_btn.data)
                    clicked_data.add(target_btn.data)
                    quality_selected = True
                except Exception as e:
                    log.warning("Error clicking quality button: %s", e)
                await asyncio.sleep(2.5)
                continue

    # پاکسازی کانال‌ها در صورت اتمام گام‌ها
    for ch in joined_channels:
        await fetch._leave(client, ch)

    return False, f"ربات @{bot_name} در زمان مقرر فایل ویدیو را ارسال نکرد."


async def download_youtube_video(
    client,
    url: str,
    quality: Optional[int] = None,
    event=None,
    status=None
) -> str:
    """دریافت ویدیوی یوتیوب از طریق ربات‌های رایگان تلگرام و فوروارد مستقیم فایل ویدیو."""
    clean_url = (url or "").strip()
    video_id = ytsummary.extract_youtube_id(clean_url)
    if not video_id:
        # جستجوی لینک در متن در صورت وجود متن اضافه
        m = ytsummary.YT_URL_PATTERN.search(clean_url)
        if m:
            clean_url = m.group(0)
            video_id = m.group(1)
        else:
            return "❌ لینک ارسالی یک لینک معتبر یوتیوب نیست."

    target_quality = 720
    if quality:
        m_q = re.search(r"\d+", str(quality))
        if m_q:
            target_quality = int(m_q.group(0))

    if status:
        try:
            await status.edit(f"🎬 در حال آماده‌سازی دانلود ویدیوی یوتیوب با کیفیت {target_quality}p...")
        except Exception:
            pass

    # ۱. تلاش با ربات اصلی @MegaSaverBot
    ok, msg = await _run_bot_download(client, PRIMARY_BOT, clean_url, target_quality, event, status)
    if ok:
        return msg

    # ۲. تلاش با ربات‌های پشتیبان در صورت عدم پاسخ ربات اول
    for fallback in FALLBACK_BOTS:
        if status:
            try:
                await status.edit(f"🎬 ربات اول مشغول بود؛ در حال تلاش با @{fallback}...")
            except Exception:
                pass
        ok_fb, msg_fb = await _run_bot_download(client, fallback, clean_url, target_quality, event, status)
        if ok_fb:
            return msg_fb

    return f"متأسفانه ربات‌های دانلود تلگرام در این لحظه پاسخگو نبودند. می‌توانید مستقیماً لینک را در @{PRIMARY_BOT} ارسال کنید."
