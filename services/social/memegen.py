import asyncio
import logging
import os
import re
import textwrap
import time
from typing import Optional, Tuple

from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper

from ai_engine import ai
from core import config

log = logging.getLogger("memegen")

MEME_KEYWORDS = (
    "میم بساز", "میمش کن", "میم کن", "تبدیل به میم کن", "از این میم بساز",
    "ازش میم بساز", "یه میم ازش بساز", "میم دربیار", "میم این", "میمش بساز",
    "سمش کن", "کارت میم"
)

FONT_CANDIDATES = [
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf"
]


def _get_font(size: int = 30):
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _format_bidi_text(text: str) -> str:
    """اصلاح چسبندگی حروف و راست‌به‌چپ کردن متن فارسی برای Pillow."""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def is_meme_request(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in MEME_KEYWORDS)


async def generate_meme_caption(target_name: str, text_or_context: str, user_instruction: str = "") -> str:
    """تولید کپشن یا پانچ‌لاین میم فوق‌العاده سم، وایرال و خنده‌دار به سبک توییتر و اینستاگرام فارسی."""
    name_clean = target_name or "طرف"
    prompt = (
        "تو سلطان بلامنازع میم، طنز سیاه، توییت‌های وایرال و سم‌ترین شوخی‌های تلگرامی و اینستاگرامی فارسی هستی.\n"
        f"شخصی به نام «{name_clean}» این پیام یا ادعا را در چت مطرح کرده است:\n"
        f"پیام {name_clean}: «{text_or_context}»\n\n"
        f"دستور تکمیلی کاربر (در صورت وجود): {user_instruction or 'یک میم به شدت خنده‌دار و سم از این دربیار'}\n\n"
        "وظیفه تو: یک کپشن میم (Meme Punchline) فوق‌العاده خنده‌دار، نوآورانه، تند و همه‌پسند بساز.\n"
        "الگوهای پیشنهادی برای خلق شوخی:\n"
        "• الگوی POV یا وقتی که: «وقتی طرف فلان ادعا رو می‌کنه ولی در واقع...»\n"
        "• الگوی تضاد خنده‌دار: «سطح ادعا: ... / سطح عملکرد: ...»\n"
        "• الگوی دیالوگ سم یا صدای درونی مغز طرف\n"
        "• توییت تیکه‌دار کوتاه و اسیدی\n\n"
        "قوانین سفت‌وسخت:\n"
        "۱. حداکثر ۱ تا ۲ خط کوتاه، ضربتی و فوق‌العاده سم.\n"
        "۲. اصلاً از شوخی‌های لوس، قدیمی، یا جملات کلیشه‌ای استفاده نکن؛ کاملاً امروزی، خیابانی و ترند اینترنت فارسی باشد.\n"
        "۳. فقط و فقط متن نهایی میم را بنویس بدون هیچ مقدمه، توضیح، پرانتز یا علامت گیومه."
    )
    res = await asyncio.to_thread(ai.ask_direct, prompt)
    clean = res.strip().strip("«»\"'")
    return clean


def create_meme_on_image(image_path: str, caption_text: str, output_path: str) -> bool:
    """افزودن متن میم کلاسیک با خطوط برجسته مشکی روی عکس موجود."""
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            w, h = img.size

            font_size = max(24, int(w / 16))
            font = _get_font(font_size)

            wrap_width = max(14, int(w / (font_size * 0.75)))
            raw_lines = textwrap.wrap(caption_text, width=wrap_width)
            bidi_lines = [_format_bidi_text(line) for line in raw_lines]

            draw = ImageDraw.Draw(img)
            line_height = font_size + 10
            total_text_h = len(bidi_lines) * line_height

            # قرار دادن متن در پایین عکس با فاصله استاندارد
            y_start = max(10, h - total_text_h - 25)

            stroke_w = max(2, int(font_size / 10))
            for i, line in enumerate(bidi_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]
                x = (w - text_w) // 2
                y = y_start + (i * line_height)

                # کشیدن بوردر مشکی دور متن (Impact Meme Style)
                for ox in range(-stroke_w, stroke_w + 1):
                    for oy in range(-stroke_w, stroke_w + 1):
                        draw.text((x + ox, y + oy), line, font=font, fill=(0, 0, 0))
                # کشیدن متن اصلی زرد یا سفید
                draw.text((x, y), line, font=font, fill=(255, 255, 255))

            img.save(output_path, "JPEG", quality=92)
            return True
    except Exception as e:
        log.error(f"Error drawing meme on image: {e}")
        return False


def create_text_meme_card(quote: str, meme_caption: str, author_name: str, output_path: str) -> bool:
    """ساخت کارت میم مدرن، شیک و دارک‌مود با رنگ‌بندی نئونی و تایپوگرافی تمیز."""
    try:
        w, h = 820, 500
        # پس‌زمینه دارک باکلاس
        img = Image.new("RGB", (w, h), color=(15, 18, 25))
        draw = ImageDraw.Draw(img)

        # فریم داخلی کارت
        draw.rounded_rectangle([25, 25, w - 25, h - 25], radius=20, fill=(24, 29, 40), outline=(45, 55, 75), width=2)

        font_badge = _get_font(18)
        font_author = _get_font(22)
        font_quote = _get_font(24)
        font_punchline = _get_font(30)
        font_brand = _get_font(16)

        # تگ نشانگر بالای کارت (Badge)
        badge_text = "💀 سم خالص | Capri Meme"
        draw.rounded_rectangle([45, 45, 280, 85], radius=10, fill=(35, 45, 62))
        draw.text((60, 52), _format_bidi_text(badge_text), fill=(70, 200, 255), font=font_badge)

        # نام فرستنده در سمت راست هدر
        author_label = f"💬 ادعای: {author_name}"
        bidi_auth = _format_bidi_text(author_label)
        abbox = draw.textbbox((0, 0), bidi_auth, font=font_author)
        draw.text((w - 55 - (abbox[2] - abbox[0]), 52), bidi_auth, fill=(160, 175, 200), font=font_author)

        # نقل قول پیام طرف (Quote Box)
        draw.rounded_rectangle([45, 105, w - 45, 215], radius=14, fill=(18, 22, 31), outline=(35, 42, 56), width=1)
        clean_quote = quote.replace("\n", " ").strip()
        if len(clean_quote) > 130:
            clean_quote = clean_quote[:127] + "..."
        quote_wrapped = textwrap.wrap(f"« {clean_quote} »", width=42)
        for i, ql in enumerate(quote_wrapped[:2]):
            bidi_ql = _format_bidi_text(ql)
            draw.text((65, 122 + (i * 38)), bidi_ql, fill=(200, 212, 230), font=font_quote)

        # خط جداکننده افقی شیک
        draw.line([45, 235, w - 45, 235], fill=(50, 62, 85), width=2)

        # متن اصلی پانچ‌لاین میم (زرد درخشان نئونی)
        caption_wrapped = textwrap.wrap(meme_caption, width=32)
        for i, cl in enumerate(caption_wrapped[:4]):
            bidi_cl = _format_bidi_text(cl)
            cbbox = draw.textbbox((0, 0), bidi_cl, font=font_punchline)
            cw = cbbox[2] - cbbox[0]
            cx = (w - cw) // 2
            cy = 265 + (i * 44)
            draw.text((cx, cy), bidi_cl, fill=(255, 220, 60), font=font_punchline)

        # فوتر امضا
        footer_text = "⚡ Crafted with Capri AI"
        draw.text((w - 220, h - 55), footer_text, fill=(90, 110, 140), font=font_brand)

        img.save(output_path, "JPEG", quality=92)
        return True
    except Exception as e:
        log.error(f"Error creating text meme card: {e}")
        return False


async def handle_meme(client, event, question: str, status=None) -> bool:
    """اجرای درخواست ساخت میم و ارسال مستقیم با ریپلای روی پیام یا عکس طرف مقابل."""
    reply_id = getattr(event, "reply_to_msg_id", None)
    if not reply_id:
        if status:
            await status.edit("❌ برای ساخت میم، باید روی پیام یا عکس طرف ریپلای بزنی!")
        return False

    try:
        target_msg = await client.get_messages(event.chat_id, ids=reply_id)
        if not target_msg:
            if status:
                await status.edit("❌ نتونستم پیام طرف رو پیدا کنم.")
            return False

        target_name = "مخاطب"
        if target_msg.sender:
            target_name = getattr(target_msg.sender, "first_name", "") or getattr(target_msg.sender, "title", "مخاطب")

        ts = int(time.time() * 1000)
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        out_meme_path = os.path.join(config.DOWNLOAD_DIR, f"meme_{ts}.jpg")

        if status:
            try:
                await status.edit("🎭 در حال ایده‌پردازی و خلق میم سمی...")
            except Exception:
                pass

        # اگر عکس بود
        if target_msg.photo or (target_msg.media and hasattr(target_msg.media, "photo")):
            raw_img_path = os.path.join(config.DOWNLOAD_DIR, f"raw_{ts}.jpg")
            await client.download_media(target_msg, file=raw_img_path)
            caption = await generate_meme_caption(target_name, target_msg.message or "عکس طنز", question)
            ok = create_meme_on_image(raw_img_path, caption, out_meme_path)
            try:
                os.remove(raw_img_path)
            except Exception:
                pass
        else:
            # اگر پیام متنی بود
            quote_text = target_msg.message or "..."
            caption = await generate_meme_caption(target_name, quote_text, question)
            ok = create_text_meme_card(quote_text, caption, target_name, out_meme_path)

        if ok and os.path.exists(out_meme_path):
            # ارسال تصویر میم دقیقاً با ریپلای روی پیام خودِ طرف مقابل
            await client.send_file(event.chat_id, out_meme_path, reply_to=target_msg.id)
            try:
                os.remove(out_meme_path)
            except Exception:
                pass
            if status:
                try:
                    await status.delete()
                except Exception:
                    pass
            return True
        else:
            if status:
                await status.edit("❌ نتونستم میم رو تولید کنم.")
            return False
    except Exception as e:
        log.error(f"Error handling meme: {e}")
        if status:
            try:
                await status.edit(f"❌ خطا در میم‌ساز: {e}")
            except Exception:
                pass
        return False
