"""
📁 Capri Smart Reactions Handler - سامانه تعامل و اجرای خودکار با ری‌اکشن‌های تلگرام
تشخیص ری‌اکشن‌های ثبت‌شده توسط صاحب اکانت بر اساس سناریوهای هوشمند:
۱. کانال: ری‌اکشن قلب یا لایک (❤️، 👍) -> تحلیل هوش مصنوعی و بایگانی در تاپیک مربوطه در Capri Vault
۲. پیوی و گروه: ری‌اکشن دست‌نوشته، میکروفون، برگه (✍️، 🎙️، 📝) -> پیاده‌سازی ویس با Whisper + تحلیل هوش مصنوعی
۳. پیوی و گروه: ری‌اکشن پرنده یا ربات (🕊️، 🤖) -> تحلیل محتوا با AI و ارسال به Capri Vault
۴. هر چت: ری‌اکشن دلقک (🤡) -> پاسخ دندان‌شکن و روست مستقیم روی پیام در چت
۵. هر چت: ری‌اکشن چشم یا برنامه‌نویس (👀، 👨‍💻، 💻) -> تنظیم خودکار تایمر و یادآور در DND
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Set

from telethon import types

from ai_engine import ai
from core import config
from services.social import dnd, roast
from services.telegram import vault
from services.voice import voice

logger = logging.getLogger("reactions")

# ذخیره شناسه صاحب اکانت جهت تشخیص دقیق ری‌اکشن در چت‌های دوطرفه
_OWNER_ID: Optional[int] = None


def set_owner_id(uid: int):
    """تنظیم شناسه کاربری صاحب اکانت."""
    global _OWNER_ID
    if uid:
        _OWNER_ID = int(uid)


def get_owner_id() -> Optional[int]:
    """دریافت شناسه صاحب اکانت."""
    return _OWNER_ID


def normalize_emoji(emot: str) -> str:
    """حذف کاراکترهای مخفی و Variation Selector جهت تطبیق دقیق یونیکد تلگرام."""
    if not emot:
        return ""
    return emot.replace("\ufe0f", "").replace("\ufe0e", "").strip()


def make_emoji_set(*emojis) -> Set[str]:
    """ایجاد مجموعه شامل هر دو حالت نرمال و خام ایموجی."""
    res = set()
    for e in emojis:
        res.add(e)
        res.add(normalize_emoji(e))
    return res


# ۱. ری‌اکشن قلب و لایک در کانال -> صندوق هوشمند
CHANNEL_VAULT_EMOJIS = make_emoji_set(
    "❤️", "♥️", "❤", "💖", "💓", "💗", "💘", "💝",
    "👍", "👍🏻", "👍🏼", "👍🏽", "👍🏾", "👍🏿",
    "🔥", "⭐", "🌟", "⚡", "👏", "👌", "💯", "📥", "🎉", "🥰", "😍"
)

# ۲. ری‌اکشن پرنده یا ربات در پیوی و گروه -> صندوق هوشمند
CHAT_VAULT_EMOJIS = make_emoji_set(
    "🕊️", "🕊", "🤖", "🐦", "🦅", "🐥", "📥", "📦", "💾"
)

# ۳. ری‌اکشن دست‌نوشته، میکروفون و برگه -> پیاده‌سازی ویس + تحلیل هوشمند
VOICE_ANALYZE_EMOJIS = make_emoji_set(
    "✍️", "✍", "🎙️", "🎙", "📝", "🎤", "📄", "📜"
)

# ۴. ری‌اکشن دلقک و ترول -> روست کوبنده
ROAST_EMOJIS = make_emoji_set(
    "🤡", "💩", "👎", "👎🏻", "👎🏼", "👎🏽", "👎🏾", "👎🏿", "🤮", "🤢"
)

# ۵. ری‌اکشن چشم و برنامه‌نویس -> تنظیم تایمر یادآوری
REMINDER_EMOJIS = make_emoji_set(
    "👀", "👁️", "👁",
    "👨‍💻", "🧑‍💻", "👩‍💻", "💻",
    "📌", "⏰", "⏳", "⏱️", "⏱", "🔔"
)

# کش تبدیل ReactionCustomEmoji (انیمیشنی/پرمیوم تلگرام) به یونیکد اصلی
_CUSTOM_EMOJI_CACHE: Dict[int, str] = {}

# حافظه ضد تکرار (Deduplication Cache): key -> timestamp
_handled_reactions: Dict[str, float] = {}
DEDUP_TTL = 15.0  # ۱۵ ثانیه مهلت جلوگیری از پردازش همزمان ایونت‌های تکراری


def is_already_handled(peer_id: int, msg_id: int, emoji: str, auto_mark: bool = True) -> bool:
    """جلوگیری از پردازش تکراری ایونت‌های چندباره ری‌اکشن تلگرام."""
    now = time.time()
    stale = [k for k, v in _handled_reactions.items() if now - v > DEDUP_TTL]
    for k in stale:
        _handled_reactions.pop(k, None)

    key = f"{peer_id}:{msg_id}:{normalize_emoji(emoji)}"
    if key in _handled_reactions:
        return True
    if auto_mark:
        _handled_reactions[key] = now
    return False


def mark_handled(peer_id: int, msg_id: int, emoji: str):
    """ثبت دستی شناسه پیام در حافظه ضدتکرار ری‌اکشن."""
    key = f"{peer_id}:{msg_id}:{normalize_emoji(emoji)}"
    _handled_reactions[key] = time.time()


def unmark_handled(peer_id: int, msg_id: int, emoji: str):
    """حذف ری‌اکشن از حافظه ضدتکرار در صورت بروز خطا تا کاربر بتواند بلافاصله مجدداً تست کند."""
    key = f"{peer_id}:{msg_id}:{normalize_emoji(emoji)}"
    _handled_reactions.pop(key, None)


def extract_owner_reactions(obj, my_id: Optional[int] = None) -> List[str]:
    """
    استخراج ایموجی‌های ری‌اکشن که توسط خود صاحب اکانت (مالک) ثبت شده‌اند.
    پشتیبانی همزمان از:
    - UpdateMessageReactions
    - UpdateEditMessage / UpdateEditChannelMessage
    - MessageReactions مستقیم
    - ایموجی‌های استاندارد و کاستوم ایموجی‌های کش‌شده
    """
    emojis = []
    if obj is None:
        return emojis

    reactions = None
    if isinstance(obj, types.MessageReactions):
        reactions = obj
    elif hasattr(obj, "reactions") and obj.reactions:
        reactions = obj.reactions
    elif hasattr(obj, "message") and hasattr(obj.message, "reactions") and obj.message.reactions:
        reactions = obj.message.reactions

    if not reactions:
        return emojis

    target_my_id = my_id or _OWNER_ID

    # ۱. پیوی و گروه‌ها (بررسی recent_reactions)
    if getattr(reactions, "recent_reactions", None):
        for r in reactions.recent_reactions:
            is_my = bool(getattr(r, "my", False))
            if not is_my and target_my_id:
                peer_uid = getattr(getattr(r, "peer_id", None), "user_id", None)
                if peer_uid == target_my_id:
                    is_my = True
            if is_my and hasattr(r, "reaction"):
                emot = getattr(r.reaction, "emoticon", "")
                if not emot and isinstance(r.reaction, types.ReactionCustomEmoji):
                    doc_id = getattr(r.reaction, "document_id", 0)
                    emot = _CUSTOM_EMOJI_CACHE.get(doc_id, "")
                if emot and emot not in emojis:
                    emojis.append(emot)

    # ۲. کانال‌ها و چت‌های عمومی (بررسی chosen_order در results)
    if getattr(reactions, "results", None):
        for rc in reactions.results:
            if getattr(rc, "chosen_order", None) is not None and hasattr(rc, "reaction"):
                emot = getattr(rc.reaction, "emoticon", "")
                if not emot and isinstance(rc.reaction, types.ReactionCustomEmoji):
                    doc_id = getattr(rc.reaction, "document_id", 0)
                    emot = _CUSTOM_EMOJI_CACHE.get(doc_id, "")
                if emot and emot not in emojis:
                    emojis.append(emot)

    return emojis


async def extract_owner_reactions_async(client, obj, my_id: Optional[int] = None) -> List[str]:
    """
    استخراج ناهمگام ری‌اکشن‌های صاحب اکانت همراه با ریزالو آنلاین ایموجی‌های متحرک/پرمیوم تلگرام.
    """
    emojis = extract_owner_reactions(obj, my_id=my_id)
    if emojis:
        return emojis

    # در صورت وجود ReactionCustomEmoji نامشخص، دریافت اطلاعات متادیتا از سرور تلگرام
    reactions = None
    if isinstance(obj, types.MessageReactions):
        reactions = obj
    elif hasattr(obj, "reactions") and obj.reactions:
        reactions = obj.reactions
    elif hasattr(obj, "message") and hasattr(obj.message, "reactions") and obj.message.reactions:
        reactions = obj.message.reactions

    if not reactions:
        return emojis

    target_my_id = my_id or _OWNER_ID
    custom_ids = []

    if getattr(reactions, "recent_reactions", None):
        for r in reactions.recent_reactions:
            is_my = bool(getattr(r, "my", False))
            if not is_my and target_my_id:
                peer_uid = getattr(getattr(r, "peer_id", None), "user_id", None)
                if peer_uid == target_my_id:
                    is_my = True
            if is_my and isinstance(getattr(r, "reaction", None), types.ReactionCustomEmoji):
                doc_id = getattr(r.reaction, "document_id", 0)
                if doc_id and doc_id not in _CUSTOM_EMOJI_CACHE:
                    custom_ids.append(doc_id)

    if getattr(reactions, "results", None):
        for rc in reactions.results:
            if getattr(rc, "chosen_order", None) is not None and isinstance(getattr(rc, "reaction", None), types.ReactionCustomEmoji):
                doc_id = getattr(rc.reaction, "document_id", 0)
                if doc_id and doc_id not in _CUSTOM_EMOJI_CACHE:
                    custom_ids.append(doc_id)

    if custom_ids and client:
        try:
            from telethon.tl.functions.messages import GetCustomEmojiDocumentsRequest
            docs = await client(GetCustomEmojiDocumentsRequest(document_id=custom_ids))
            if docs:
                for doc in docs:
                    for attr in getattr(doc, "attributes", []):
                        alt = getattr(attr, "alt", "")
                        if alt:
                            _CUSTOM_EMOJI_CACHE[doc.id] = alt
                            if alt not in emojis:
                                emojis.append(alt)
        except Exception as e:
            logger.debug(f"Failed to resolve custom emoji docs {custom_ids}: {e}")

    return emojis


async def _handle_voice_reaction(client, msg, emoji: str, sender_name: str, chat_title: str) -> bool:
    """تبدیل خودکار ویس به متن توسط Whisper و تحلیل هوشمند متن با AI با دریافت ری‌اکشن."""
    logger.info(f"Voice reaction {emoji} detected on msg {msg.id}. Transcribing with Whisper...")
    try:
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
        temp_path = await client.download_media(msg, file=config.DOWNLOAD_DIR)
        if not temp_path or not os.path.exists(temp_path):
            logger.warning("Failed to download voice media for transcription.")
            return False

        # پیاده‌سازی صوت با مدل Whisper
        transcript = await asyncio.to_thread(voice.transcribe, temp_path)

        # پاک‌سازی فایل موقت دانلودی
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

        if not transcript:
            logger.warning("Whisper returned empty transcript.")
            return False

        # Voice analysis transcription
        analysis = ""
        try:
            analysis_prompt = (
                "شما یک دستیار هوشمند و موشکاف تلگرام هستید. متن زیر پیاده‌شده از یک ویس تلگرامی است:\n"
                f"«{transcript}»\n\n"
                "لطفاً در ۲ الی ۳ خط بسیار خلاصه، شکیل و کاربردی:\n"
                "• موضوع و خواسته اصلی فرستنده\n"
                "• لحن و اتمسفر پیام\n"
                "• نکات کلیدی یا اقدام مورد نیاز\n"
                "را با بولت‌پوینت بنویس بدون هیچ مقدمه یا حاشیه‌پردازی."
            )
            analysis = await asyncio.to_thread(ai.ask_direct, analysis_prompt)
            analysis = analysis.strip()
        except Exception as ea:
            logger.warning(f"Voice AI analysis skipped or failed: {ea}")

        report = (
            f"🎙️ **پیاده‌سازی و تحلیل هوشمند ویس با ری‌اکشن {emoji}**\n\n"
            f"• **فرستنده:** {sender_name}\n"
            f"• **مبدأ:** {chat_title}\n\n"
            f"📝 **متن کامل پیاده‌شده:**\n«{transcript}»"
        )
        if analysis:
            report += f"\n\n💡 **تحلیل هوش مصنوعی:**\n{analysis}"

        await client.send_message("me", report)
        logger.info(f"Voice transcription & analysis successfully sent to Saved Messages for msg {msg.id}")
        return True
    except Exception as e:
        logger.error(f"Error handling voice reaction: {e}", exc_info=True)
        return False


async def _handle_text_analysis_reaction(client, msg, emoji: str, sender_name: str, chat_title: str) -> bool:
    """تحلیل و خلاصه پیام متنی با ری‌اکشن دست‌نوشته / برگه در پیوی یا گروه."""
    logger.info(f"Text analysis reaction {emoji} on msg {msg.id}...")
    try:
        text = msg.raw_text or ""
        if not text:
            return False

        prompt = (
            "متن زیر یک پیام از چت تلگرام است:\n"
            f"«{text}»\n\n"
            "لطفاً در ۲ الی ۳ خط کوتاه، موجز و کاربردی:\n"
            "• خلاصه مفهوم پیام\n"
            "• نکات کلیدی و اقدام احتمالی\n"
            "را با بولت‌پوینت بنویس بدون هیچ مقدمه یا توضیحات اضافی."
        )
        analysis = await asyncio.to_thread(ai.ask_direct, prompt)
        analysis = (analysis or "").strip()

        report = (
            f"📝 **تحلیل هوشمند پیام با ری‌اکشن {emoji}**\n\n"
            f"• **فرستنده:** {sender_name}\n"
            f"• **مبدأ:** {chat_title}\n\n"
            f"📄 **متن پیام:**\n«{text[:300]}»\n\n"
            f"💡 **تحلیل هوش مصنوعی:**\n{analysis}"
        )
        await client.send_message("me", report)
        return True
    except Exception as e:
        logger.error(f"Error handling text analysis reaction: {e}", exc_info=True)
        return False


async def _handle_vault_reaction(client, msg, emoji: str, chat_title: str, source_label: str = "چت") -> bool:
    """تحلیل هوشمند و بایگانی پیام کانال/گروه/پیوی در صندوق هوشمند (Capri Vault)."""
    logger.info(f"Vault archiving reaction {emoji} ({source_label}) on msg {msg.id} in {chat_title}...")
    try:
        # ۱. بررسی و واکشی کلیه پیام‌های آلبوم در صورت وجود grouped_id
        album_msgs = await vault.get_album_messages(client, msg)
        album_ids = [m.id for m in album_msgs]

        # استخراج کپشن/متن از هر پیامی از آلبوم که دارای متن باشد
        caption_text = ""
        for m in album_msgs:
            t = getattr(m, "raw_text", "") or ""
            if t.strip():
                caption_text = t.strip()
                break

        # علامت‌گذاری سایر رسانه‌های همین آلبوم تا پردازش مجدد نشوند
        raw_peer = getattr(msg, "peer_id", None)
        peer_id = getattr(raw_peer, "channel_id", None) or getattr(raw_peer, "chat_id", None) or getattr(raw_peer, "user_id", None) or 0
        for mid in album_ids:
            mark_handled(peer_id, mid, emoji)

        # ۲. آماده‌سازی سوپرگروه صندوق و تاپیک‌ها
        group_id, link = await vault.ensure_vault_group(client)
        topic_map = await vault.ensure_vault_topics(client, group_id)
        vault_entity = await client.get_input_entity(group_id)

        # ۳. دسته‌بندی هوشمند موضوع محتوا (با در نظر گرفتن متن، کانال مبدأ و آلبوم)
        cat, conf = vault.classify_message_heuristic(msg, chat_title=chat_title, override_text=caption_text)
        if conf < 0.85:
            meta = [{
                "id": msg.id,
                "text": caption_text or msg.raw_text or "",
                "media_type": f"آلبوم ({len(album_ids)} رسانه)" if len(album_ids) > 1 else ("فایل" if getattr(msg, "file", None) else "رسانه/متن"),
                "fwd": getattr(getattr(msg, "fwd_from", None), "from_name", "") or "",
                "chat": chat_title,
                "heuristic": cat
            }]
            ai_res = await vault.classify_messages_batch_ai(meta)
            cat = ai_res.get(msg.id, cat)

        topic_id = topic_map.get(cat) or topic_map.get("misc") or 1
        topic_title = vault.TOPIC_TITLE_MAP.get(cat, "متفرقه")

        # ۴. فوروارد امن به تاپیک هدف (تمام مدیاهای آلبوم همزمان ارسال می‌شوند)
        ok = await vault.forward_to_topic(client, vault_entity, msg, topic_id, album_ids=album_ids)
        if not ok:
            logger.warning(f"Failed to forward message(s) {album_ids} to vault topic {topic_id}")
            return False

        # ۵. ثبت در دیتابیس لوکال صندوق
        data = vault.load_vault_data()
        for mid in album_ids:
            if mid not in data.get("processed_msg_ids", []):
                data["processed_msg_ids"].append(mid)
        data["total_organized_count"] = data.get("total_organized_count", 0) + 1
        vault.save_vault_data(data)

        # ۶. اعلام لاگ شکیل به Saved Messages
        snippet = (caption_text or msg.raw_text or "").replace("\n", " ")[:120]
        if not snippet and getattr(msg, "file", None):
            snippet = f"فایل: {getattr(msg.file, 'name', '') or getattr(msg.file, 'mime_type', '')}"
        elif not snippet:
            snippet = f"آلبوم شامل {len(album_ids)} تصویر/رسانه" if len(album_ids) > 1 else "رسانه / تصویر"

        album_badge = f" ({len(album_ids)} تصویر/رسانه به صورت یکجا)" if len(album_ids) > 1 else ""
        report = (
            f"📥 **بایگانی خودکار در صندوق هوشمند با ری‌اکشن {emoji}**\n\n"
            f"• **مبدأ:** {chat_title} ({source_label})\n"
            f"• **تاپیک مقصد:** {topic_title}\n"
            f"• **خلاصه محتوا:** «{snippet}»{album_badge}"
        )
        if link:
            report += f"\n\n🔗 [مشاهده در سوپرگروه صندوق]({link})"

        await client.send_message("me", report)
        logger.info(f"Message(s) {album_ids} successfully archived into topic {topic_title}")
        return True
    except Exception as e:
        logger.error(f"Error handling vault reaction: {e}", exc_info=True)
        return False


async def _handle_roast_reaction(client, msg, emoji: str, sender_name: str, chat_title: str, peer) -> bool:
    """پاسخ دندان‌شکن و روست کوبنده روی پیام طرف مقابل با ری‌اکشن دلقک (🤡)."""
    logger.info(f"Roast reaction {emoji} on msg {msg.id} by {sender_name} in {chat_title}...")
    try:
        target_name = sender_name or "طرف مقابل"
        target_text = msg.raw_text or ""
        if not target_text and getattr(msg, "file", None):
            target_text = f"[یک فایل یا رسانه {getattr(msg.file, 'name', '')} فرستاده]"
        elif not target_text:
            target_text = "[یک پیام رسانه‌ای یا استیکر فرستاده]"

        # تولید روست فوق‌العاده تیز و دندان‌شکن
        roast_text = await roast.generate_roast(target_name, target_text)
        if not roast_text:
            logger.warning("Roast generator returned empty text.")
            return False

        # ارسال پاسخ مستقیم به عنوان ریپلای روی پیام در همان چت
        # اولویت اول send_message(peer)، و در صورت خطای عدم یافتن input entity در پیوی، از msg.reply استفاده می‌شود
        sent_ok = False
        try:
            await client.send_message(peer, roast_text, reply_to=msg.id)
            sent_ok = True
            logger.info(f"Roast reply sent via send_message to msg {msg.id}")
        except Exception as send_err:
            logger.info(f"send_message to peer failed ({send_err}), retrying via msg.reply...")
            try:
                if hasattr(msg, "reply"):
                    await msg.reply(roast_text)
                    sent_ok = True
                    logger.info(f"Roast reply sent via msg.reply to msg {msg.id}")
            except Exception as reply_err:
                logger.warning(f"Failed to reply roast in chat: {reply_err}")

        if not sent_ok:
            await client.send_message(
                "me",
                f"⚠️ **خطا در ارسال روست در {chat_title}:** اجازه ارسال پیام یا ریپلای در این چت وجود ندارد.\n\n"
                f"• متن آماده‌شده: «{roast_text}»"
            )
            return False

        # ارسال لاگ به Saved Messages
        report = (
            f"🤡 **روست دندان‌شکن شلیک شد! (ری‌اکشن {emoji})**\n\n"
            f"• **مخاطب:** {target_name}\n"
            f"• **چت:** {chat_title}\n"
            f"• **پیام او:** «{target_text[:120]}»\n\n"
            f"🔥 **پاسخ کوبنده کاپری:**\n«{roast_text}»"
        )
        await client.send_message("me", report)
        return True
    except Exception as e:
        logger.error(f"Error handling roast reaction: {e}", exc_info=True)
        return False


async def _handle_reminder_reaction(client, msg, emoji: str, sender_name: str, chat_title: str) -> bool:
    """ثبت پیام به عنوان یادآور با ری‌اکشن چشم (👀) یا برنامه‌نویس (👨‍💻)."""
    logger.info(f"Reminder reaction {emoji} on msg {msg.id}...")
    try:
        snippet = (msg.raw_text or "").replace("\n", " ")[:150]
        if not snippet and getattr(msg, "file", None):
            snippet = f"فایل {getattr(msg.file, 'name', '')}"
        elif not snippet:
            snippet = "پیام تلگرام"

        rem_text = f"بررسی پیام از {sender_name} ({chat_title}): «{snippet}»"
        due_ts = time.time() + 3600  # ۱ ساعت بعد
        due_str = "۱ ساعت دیگر"

        dnd.add_reminder(rem_text, due_ts, due_str)

        report = (
            f"⏰ **ثبت خودکار یادآور با ری‌اکشن {emoji}**\n\n"
            f"• **موضوع:** «{snippet}»\n"
            f"• **سررسید:** {due_str}\n"
            f"• **فرستنده:** {sender_name} ({chat_title})\n\n"
            "🔔 در موعد مقرر، هشدار این پیام در Saved Messages برای شما ارسال خواهد شد."
        )
        await client.send_message("me", report)
        return True
    except Exception as e:
        logger.error(f"Error handling reminder reaction: {e}", exc_info=True)
        return False


async def handle_reaction_update(client, update) -> bool:
    """
    روتر جامع و هوشمند پردازش رویدادهای ری‌اکشن در Telethon.
    پشتیبانی از:
    - UpdateMessageReactions (رویداد اختصاصی تغییر ری‌اکشن)
    - UpdateEditMessage (ادیت پیام شامل ری‌اکشن در پیوی و گروه)
    - UpdateEditChannelMessage (ادیت پیام شامل ری‌اکشن در کانال)
    """
    peer = None
    msg_id = None
    reactions_data = None

    if isinstance(update, types.UpdateMessageReactions):
        peer = getattr(update, "peer", None)
        msg_id = getattr(update, "msg_id", None)
        reactions_data = getattr(update, "reactions", None)
    elif isinstance(update, (types.UpdateEditMessage, types.UpdateEditChannelMessage)):
        msg_obj = getattr(update, "message", None)
        if not msg_obj:
            return False
        reactions_data = getattr(msg_obj, "reactions", None)
        if not reactions_data:
            return False
        peer = getattr(msg_obj, "peer_id", None)
        msg_id = getattr(msg_obj, "id", None)
    elif hasattr(update, "peer") and hasattr(update, "msg_id"):
        peer = getattr(update, "peer", None)
        msg_id = getattr(update, "msg_id", None)
        reactions_data = getattr(update, "reactions", None)
    else:
        return False

    if not peer or not msg_id or not reactions_data:
        return False

    # دریافت یا شناسایی شناسه صاحب اکانت
    my_id = get_owner_id()
    if not my_id:
        my_id = getattr(client, "_self_id", None)
    if not my_id and hasattr(client, "get_me"):
        try:
            me = await client.get_me()
            if me:
                my_id = me.id
                set_owner_id(my_id)
        except Exception:
            pass

    owner_emojis = await extract_owner_reactions_async(client, reactions_data, my_id=my_id)
    if not owner_emojis:
        return False

    try:
        peer_id = await client.get_peer_id(peer)
    except Exception:
        peer_id = getattr(peer, "user_id", None) or getattr(peer, "channel_id", None) or getattr(peer, "chat_id", None) or 0

    # اگر ری‌اکشن داخل خود سوپرگروه صندوق بود، پردازش نشود تا لوپ ایجاد نگردد
    vault_data = vault.load_vault_data()
    vault_group_id = vault_data.get("group_id")
    if vault_group_id and peer_id == vault_group_id:
        return False

    handled_any = False
    for emoji in owner_emojis:
        if is_already_handled(peer_id, msg_id, emoji):
            logger.debug(f"Reaction {emoji} on msg {msg_id} already handled recently, skipping.")
            continue

        try:
            msg = await client.get_messages(peer, ids=msg_id)
            if not msg:
                unmark_handled(peer_id, msg_id, emoji)
                continue
        except Exception as e:
            logger.warning(f"Failed to fetch message {msg_id} for reaction update: {e}")
            unmark_handled(peer_id, msg_id, emoji)
            continue

        # استخراج مشخصات چت و نوع آن
        chat = None
        chat_title = "چت"
        try:
            chat = await msg.get_chat()
            if chat:
                chat_title = getattr(chat, "title", "") or getattr(chat, "first_name", "") or "چت"
        except Exception:
            pass

        # تشخیص دقیق نوع چت (کانال، گروه، پیوی)
        is_channel = False
        is_group = False
        is_pv = False

        if isinstance(peer, types.PeerUser):
            is_pv = True
        elif isinstance(peer, types.PeerChat):
            is_group = True
        elif isinstance(peer, types.PeerChannel):
            if getattr(msg, "post", False) or getattr(chat, "broadcast", False):
                is_channel = True
            elif getattr(chat, "megagroup", False) or getattr(chat, "gigagroup", False):
                is_group = True
            elif getattr(msg, "from_id", None) is None:
                is_channel = True
            else:
                is_channel = True
        else:
            if getattr(msg, "is_private", False):
                is_pv = True
            elif getattr(msg, "is_group", False):
                is_group = True
            elif getattr(msg, "is_channel", False):
                is_channel = True
            else:
                is_pv = True

        # استخراج فرستنده
        sender_name = ""
        try:
            sender = await msg.get_sender()
            if sender:
                sender_name = getattr(sender, "first_name", "")
        except Exception:
            pass
        if not sender_name:
            sender_name = chat_title

        # تشخیص ویس یا صوت
        is_voice = bool(getattr(msg, "voice", None)) or (
            bool(getattr(msg, "audio", None))
            and getattr(getattr(msg, "file", None), "mime_type", "").startswith("audio/ogg")
        )

        norm_emoji = normalize_emoji(emoji)
        logger.info(
            f"⚡ Smart Reaction: emoji='{emoji}' on msg {msg_id} in '{chat_title}' "
            f"(channel={is_channel}, pv={is_pv}, group={is_group})"
        )

        # ۱. ری‌اکشن دلقک و ترول (🤡) -> روست دندان‌شکن روی پیام در همان چت (در هر محیطی)
        if emoji in ROAST_EMOJIS or norm_emoji in ROAST_EMOJIS:
            ok = await _handle_roast_reaction(client, msg, emoji, sender_name, chat_title, peer)
            if ok:
                handled_any = True
                continue
            else:
                unmark_handled(peer_id, msg_id, emoji)

        # ۲. ری‌اکشن چشم و برنامه‌نویس (👀، 👨‍💻، 💻 و ساعت/پین) -> تنظیم تایمر و یادآور (در هر محیطی)
        if emoji in REMINDER_EMOJIS or norm_emoji in REMINDER_EMOJIS:
            ok = await _handle_reminder_reaction(client, msg, emoji, sender_name, chat_title)
            if ok:
                handled_any = True
                continue
            else:
                unmark_handled(peer_id, msg_id, emoji)

        # Voice reaction handler
        if emoji in VOICE_ANALYZE_EMOJIS or norm_emoji in VOICE_ANALYZE_EMOJIS:
            if is_voice:
                ok = await _handle_voice_reaction(client, msg, emoji, sender_name, chat_title)
                if ok:
                    handled_any = True
                    continue
                else:
                    unmark_handled(peer_id, msg_id, emoji)
            elif (is_pv or is_group) and msg.raw_text:
                ok = await _handle_text_analysis_reaction(client, msg, emoji, sender_name, chat_title)
                if ok:
                    handled_any = True
                    continue
                else:
                    unmark_handled(peer_id, msg_id, emoji)

        # ۴. ری‌اکشن پرنده یا ربات (🕊️، 🤖) در پیوی یا گروه -> تحلیل هوشمند و ارسال به صندوق
        if (is_pv or is_group) and (emoji in CHAT_VAULT_EMOJIS or norm_emoji in CHAT_VAULT_EMOJIS):
            ok = await _handle_vault_reaction(client, msg, emoji, chat_title, source_label="پیوی/گروه")
            if ok:
                handled_any = True
                continue
            else:
                unmark_handled(peer_id, msg_id, emoji)

        # ۵. ری‌اکشن قلب یا لایک (❤️، 👍) در کانال‌ها -> تحلیل هوشمند و ارسال به صندوق
        if is_channel and (emoji in CHANNEL_VAULT_EMOJIS or norm_emoji in CHANNEL_VAULT_EMOJIS or emoji in CHAT_VAULT_EMOJIS or norm_emoji in CHAT_VAULT_EMOJIS):
            ok = await _handle_vault_reaction(client, msg, emoji, chat_title, source_label="کانال")
            if ok:
                handled_any = True
                continue
            else:
                unmark_handled(peer_id, msg_id, emoji)

    return handled_any
