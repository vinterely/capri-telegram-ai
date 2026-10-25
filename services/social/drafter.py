import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, Optional, Tuple

from ai_engine import ai
from services.telegram import channels

log = logging.getLogger("drafter")

# ذخیره موقت پیش‌نویس‌های دارای دکمه اینلاین
active_drafts: Dict[str, Dict[str, Any]] = {}


async def resolve_target(client, event, target_str: str):
    """
    یافتن مخاطب هدف بر اساس:
    ۱. ریپلای روی پیام شخص دیگر
    ۲. یوزرنیم (@username یا t.me/...)
    ۳. چت فعلی اگر در پی‌وی هستیم و کاربر گفته «بهش بگو»
    ۴. جستجو در لیست دیالوگ‌ها و چت‌های کاربر بر اساس نام
    """
    target_clean = (target_str or "").strip()

    # حالت ۱: ریپلای روی پیام شخص
    if getattr(event, "reply_to_msg_id", None) and (not target_clean or target_clean in ("این", "این شخص", "بهش", "طرف", "reply")):
        try:
            r_msg = await client.get_messages(event.chat_id, ids=event.reply_to_msg_id)
            if r_msg and r_msg.sender:
                return r_msg.sender, getattr(r_msg.sender, "first_name", "") or getattr(r_msg.sender, "title", "مخاطب")
        except Exception as e:
            log.warning(f"Failed to get reply target: {e}")

    # حالت ۲: اگر در پی‌وی هستیم و کاربر گفته «بهش بگو» یا خالی است
    if event.is_private and (not target_clean or target_clean in ("این", "بهش", "طرف", "همین")):
        try:
            entity = await client.get_entity(event.chat_id)
            name = getattr(entity, "first_name", "") or getattr(entity, "title", "مخاطب")
            return entity, name
        except Exception as e:
            log.warning(f"Failed to get private chat entity: {e}")

    # حالت ۳: یوزرنیم تلگرام (@username)
    if target_clean.startswith("@") or "t.me/" in target_clean:
        un = target_clean.replace("t.me/", "").replace("@", "").strip("/ ")
        try:
            entity = await client.get_entity(un)
            name = getattr(entity, "first_name", "") or getattr(entity, "title", un)
            return entity, name
        except Exception as e:
            log.warning(f"Failed to get entity for @{un}: {e}")

    # حالت ۴: جستجو بر اساس نام در دیالوگ‌های کاربر
    if target_clean:
        name_lower = target_clean.lower()
        candidates = []
        async for d in client.iter_dialogs(limit=100):
            if d.is_user:
                d_name = d.name.lower()
                if name_lower in d_name or d_name in name_lower:
                    candidates.append((d.entity, d.name))
                    if len(candidates) >= 3:
                        break
        if candidates:
            # اولین یا دقیق‌ترین تطابق
            return candidates[0][0], candidates[0][1]

    return None, None


async def craft_message(target_name: str, intent: str, tone: str = "friendly_polite") -> str:
    """تولید و نگارش هوشمند متن پیام با لحن و اصول روان‌شناسی ارتباطی."""
    prompt = (
        "تو یک دستیار نویسنده هوشمند پیام‌های تلگرامی (Ghostwriter) برای کاربرت هستی.\n"
        "وظیفه تو این است که بر اساس نیت کاربر، یک پیام تمیز، روان، جذاب و بی‌نقص بنویسی که کاربر برای مخاطب ارسال کند.\n\n"
        f"مخاطب: {target_name or 'دوست/همکار'}\n"
        f"مقصود و ایده پیام کاربر: «{intent}»\n"
        f"لحن درخواستی: {tone}\n\n"
        "قوانین نگارش:\n"
        "۱. پیام باید دقیقاً از زبان کاربر خطاب به مخاطب باشد (اول شخص).\n"
        "۲. فقط و فقط متن پیام نهایی را بنویس.\n"
        "۳. هیچ توضیح اضافه، سلام و درود به کاربر، عنوان یا علامت گیومه در ابتدا و انتهای پیام نگذار."
    )
    res = await asyncio.to_thread(ai.ask, prompt)
    # پاکسازی گیومه‌ها در صورت وجود
    clean = res.strip().strip("«»\"'")
    return clean


def set_pending_draft(chat_id: int, msg_id: Optional[int], target_entity, target_name: str, draft_text: str) -> dict:
    data = {
        "target": target_entity,
        "name": target_name,
        "text": draft_text,
        "chat_id": chat_id,
        "msg_id": msg_id,
        "time": time.time()
    }
    active_drafts[str(chat_id)] = data
    if msg_id:
        active_drafts[f"msg_{msg_id}"] = data
    return data


def get_pending_draft(chat_id: int, reply_to_msg_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if reply_to_msg_id and f"msg_{reply_to_msg_id}" in active_drafts:
        return active_drafts[f"msg_{reply_to_msg_id}"]
    return active_drafts.get(str(chat_id))


def pop_pending_draft(chat_id: int, reply_to_msg_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    # اگر کاربر روی پیام پیش‌نویس ریپلای زده باشد
    if reply_to_msg_id and f"msg_{reply_to_msg_id}" in active_drafts:
        data = active_drafts.pop(f"msg_{reply_to_msg_id}")
        active_drafts.pop(str(chat_id), None)
        return data
    if str(chat_id) in active_drafts:
        data = active_drafts.pop(str(chat_id))
        if data.get("msg_id"):
            active_drafts.pop(f"msg_{data['msg_id']}", None)
        return data
    return None


def register_draft(draft_id: str, target_entity, target_name: str, draft_text: str, chat_id: int) -> None:
    set_pending_draft(chat_id, None, target_entity, target_name, draft_text)


def get_draft(draft_id: str) -> Optional[Dict[str, Any]]:
    return active_drafts.get(draft_id)


def remove_draft(draft_id: str) -> Optional[Dict[str, Any]]:
    return active_drafts.pop(draft_id, None)


async def send_draft_message(client, target_entity, draft_text: str) -> Tuple[bool, str]:
    try:
        await client.send_message(target_entity, draft_text)
        return True, "✅ پیام با موفقیت ارسال شد."
    except Exception as e:
        return False, f"❌ خطا در ارسال پیام: {e}"

