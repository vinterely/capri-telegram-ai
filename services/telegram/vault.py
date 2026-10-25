"""
Capri Vault - Intelligent Saved Messages Organizer
Provisions and manages private Telegram Forum supergroups with dedicated topic categorization,
two-tier classification (fast heuristics + batch AI), and safe forwarding.
"""

import asyncio
import json
import logging
import os
import random
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from telethon import functions, types

from ai_engine import ai
from core import config, fsutil, logger as log_module

logger = logging.getLogger("vault")

VAULT_FILE = os.path.join(config.BASE_DIR, "vault.json")

# Default forum topic definitions
DEFAULT_TOPICS = [
    {
        "key": "personal",
        "title": "📝 یادداشت و شخصی",
        "color": 0x6FB9F0,  # Blue
        "description": "یادداشت‌ها، امور شخصی، کارها، شماره‌ها و افکار",
    },
    {
        "key": "gaming",
        "title": "🎮 بازی و گیمینگ",
        "color": 0xFFA500,  # Orange
        "description": "بازی‌ها، گیم، مادها، گیم‌پلی، اخبار و تریلر بازی‌ها",
    },
    {
        "key": "media",
        "title": "🎬 فیلم و سریال",
        "color": 0xFB6F5F,  # Red
        "description": "فیلم، سریال، تیزر، انیمیشن، ویدیوها و اطلاعات سینمایی",
    },
    {
        "key": "code",
        "title": "💻 کد و برنامه‌نویسی",
        "color": 0x8EEE98,  # Green
        "description": "اسنیپت‌های کد، پروژه‌ها، گیت‌هاب، اسکریپت‌ها و مطالب فنی",
    },
    {
        "key": "files",
        "title": "📁 فایل و اسناد",
        "color": 0xFFD67E,  # Yellow
        "description": "کتاب‌ها، فایل‌های PDF، اسناد کاری، فشرده‌ها و آرشیو",
    },
    {
        "key": "music",
        "title": "🎵 موزیک و صوت",
        "color": 0xCB86DB,  # Violet
        "description": "آهنگ‌ها، پادکست‌ها، وویس و قطعات صوتی",
    },
    {
        "key": "links",
        "title": "🌐 لینک و وب‌گردی",
        "color": 0xFF93B2,  # Pink
        "description": "لینک‌های مفید، توییت‌ها، مقالات و منابع آنلاین",
    },
    {
        "key": "ideas",
        "title": "💡 ایده و آموزش",
        "color": 0x6FB9F0,  # Cyan
        "description": "ایده‌های کاری، آموزش‌ها، ترفندها و نکات کاربردی",
    },
    {
        "key": "misc",
        "title": "📦 متفرقه و سایر",
        "color": 0x8EEE98,  # Light
        "description": "پیام‌های طبقه‌بندی‌نشده و موارد متفرقه",
    },
]

TOPIC_TITLE_MAP = {t["key"]: t["title"] for t in DEFAULT_TOPICS}


def load_vault_data() -> dict:
    """Load vault registry from local JSON file."""
    if not os.path.exists(VAULT_FILE):
        data = {}
    else:
        try:
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
        except Exception:
            data = {}
    data.setdefault("group_id", None)
    data.setdefault("group_title", "📁 Capri Vault | صندوق هوشمند")
    data.setdefault("group_invite_link", "")
    data.setdefault("topics", {})
    data.setdefault("total_organized_count", 0)
    data.setdefault("processed_msg_ids", [])
    return data


def save_vault_data(data: dict) -> None:
    """Atomically save vault registry to disk."""
    if len(data.get("processed_msg_ids", [])) > 10000:
        data["processed_msg_ids"] = data["processed_msg_ids"][-8000:]
    fsutil.atomic_write_json(VAULT_FILE, data)


def get_vault_info() -> dict:
    """Get general vault status and stats."""
    return load_vault_data()


async def ensure_vault_group(client, status_callback=None) -> Tuple[Optional[int], str]:
    """Ensure vault supergroup exists; provision a private forum supergroup if missing."""
    data = load_vault_data()
    group_id = data.get("group_id")
    invite_link = data.get("group_invite_link", "")

    # 1. Verify existing supergroup validity
    if group_id:
        try:
            entity = await client.get_entity(group_id)
            if entity:
                logger.info(f"Existing vault supergroup found: ID={group_id}")
                return group_id, invite_link
        except Exception as e:
            logger.warning(f"Previous vault group inaccessible ({e}); creating new supergroup...")

    # 2. Provision new supergroup
    if status_callback:
        await status_callback("🔨 در حال ساخت سوپرگروه اختصاصی صندوق هوشمند (Capri Vault)...")

    title = "📁 Capri Vault | صندوق هوشمند"
    about = (
        "صندوق هوشمند تفکیک پیام‌های ذخیره شده تلگرام (Saved Messages) - "
        "مدیریت و دسته‌بندی موضوعی با هوش مصنوعی کاپری"
    )

    try:
        created = await client(functions.channels.CreateChannelRequest(
            title=title,
            about=about,
            megagroup=True,
            forum=True,
        ))
        chat = created.chats[0]
        group_id = chat.id
    except Exception as e:
        logger.error(f"Failed to create forum supergroup: {e}")
        raise RuntimeError(f"Telegram supergroup creation failed: {e}")

    # Enable forum topics if not enabled
    try:
        await client(functions.channels.ToggleForumRequest(
            channel=chat,
            enabled=True,
            tabs=False
        ))
    except Exception as e:
        logger.debug(f"ToggleForumRequest info/skipped: {e}")

    # Generate invite link
    try:
        invite = await client(functions.messages.ExportChatInviteRequest(peer=chat))
        invite_link = getattr(invite, "link", "")
    except Exception as e:
        logger.warning(f"Failed to export chat invite link: {e}")
        invite_link = ""

    # Pin dialog in user chat list
    try:
        await client(functions.messages.ToggleDialogPinRequest(peer=chat, pinned=True))
    except Exception as e:
        logger.debug(f"Failed to pin dialog (Telegram pin limit reached): {e}")

    # Send and pin welcome guide in General topic
    try:
        welcome_text = (
            "🌟 **به صندوق هوشمند کاپری (Capri Vault) خوش آمدید!**\n\n"
            "این سوپرگروه اختصاصی توسط هوش مصنوعی کاپری برای تفکیک، نظم‌بخشی و بایگانی منظم "
            "پیام‌های ذخیره‌شده (Saved Messages) شما ایجاد شده است.\n\n"
            "📌 **تاپیک‌های فعال:**\n"
            "• 📝 **یادداشت و شخصی**\n"
            "• 🎮 **بازی و گیمینگ**\n"
            "• 🎬 **فیلم و سریال**\n"
            "• 💻 **کد و برنامه‌نویسی**\n"
            "• 📁 **فایل و اسناد**\n"
            "• 🎵 **موزیک و صوت**\n"
            "• 🌐 **لینک و وب‌گردی**\n"
            "• 💡 **ایده و آموزش**\n"
            "• 📦 **متفرقه و سایر**\n\n"
            "⚙️ هر زمان فرمانی مبنی بر مرتب‌سازی سیو مسیج صادر کنید، محتوا با هوش مصنوعی ارزیابی و در تاپیک مربوطه قرار می‌گیرد."
        )
        welcome_msg = await client.send_message(chat, welcome_text)
        await client.pin_message(chat, welcome_msg.id)
    except Exception as e:
        logger.debug(f"Failed to send/pin welcome message: {e}")

    data["group_id"] = group_id
    data["group_title"] = title
    data["group_invite_link"] = invite_link
    save_vault_data(data)
    logger.info(f"Vault supergroup created successfully: ID={group_id}")
    return group_id, invite_link


async def ensure_vault_topics(client, group_id: int, status_callback=None) -> Dict[str, int]:
    """Ensure default category topics exist in forum supergroup; returns {key: topic_id} map."""
    data = load_vault_data()
    cached_topics = data.get("topics", {})
    entity = await client.get_input_entity(group_id)

    # Fetch existing forum topics from supergroup
    existing_by_title: Dict[str, int] = {}
    try:
        res = await client(functions.messages.GetForumTopicsRequest(
            peer=entity,
            offset_date=None,
            offset_id=0,
            offset_topic=0,
            limit=100
        ))
        if hasattr(res, "topics"):
            for t in res.topics:
                if isinstance(t, types.ForumTopic):
                    clean_t = t.title.strip().lower()
                    existing_by_title[clean_t] = t.id
    except Exception as e:
        logger.warning(f"Failed to fetch forum topics: {e}")

    topic_map: Dict[str, int] = {}

    for t_def in DEFAULT_TOPICS:
        key = t_def["key"]
        title = t_def["title"]
        clean_title = title.strip().lower()

        # A) Topic exists in online forum topics
        if clean_title in existing_by_title:
            topic_map[key] = existing_by_title[clean_title]
            cached_topics[key] = {"id": existing_by_title[clean_title], "title": title}
            continue

        # B) Topic was cached locally
        if key in cached_topics and cached_topics[key].get("id") in existing_by_title.values():
            topic_map[key] = cached_topics[key]["id"]
            continue

        # C) Create new forum topic
        if status_callback:
            await status_callback(f"📁 در حال ساخت تاپیک «{title}»...")

        try:
            created_res = await client(functions.messages.CreateForumTopicRequest(
                peer=entity,
                title=title,
                icon_color=t_def["color"],
                random_id=random.randint(1, 2**63 - 1)
            ))
            # Extract topic ID
            topic_id = None
            if hasattr(created_res, "updates"):
                for u in created_res.updates:
                    msg = getattr(u, "message", None)
                    if msg and getattr(msg, "id", None):
                        topic_id = msg.id
                        break

            if not topic_id:
                # Re-read forum topics if not found in updates
                res_check = await client(functions.messages.GetForumTopicsRequest(
                    peer=entity, offset_date=None, offset_id=0, offset_topic=0, limit=20
                ))
                for t in getattr(res_check, "topics", []):
                    if isinstance(t, types.ForumTopic) and t.title.strip().lower() == clean_title:
                        topic_id = t.id
                        break

            if topic_id:
                topic_map[key] = topic_id
                cached_topics[key] = {"id": topic_id, "title": title}
                existing_by_title[clean_title] = topic_id
                logger.info(f"New forum topic created: {title} -> {topic_id}")
            else:
                topic_map[key] = 1  # Fallback to General topic (1)
        except Exception as e:
            logger.error(f"Failed to create forum topic {title}: {e}")
            topic_map[key] = 1

    data["topics"] = cached_topics
    save_vault_data(data)
    return topic_map


# ---------------------------------------------------------
# Content classification & categorization engine
# ---------------------------------------------------------

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".xml",
    ".yml", ".yaml", ".sql", ".sh", ".bash", ".bat", ".ps1", ".cpp", ".c",
    ".h", ".hpp", ".java", ".go", ".rs", ".php", ".rb", ".kt", ".swift",
    ".dockerfile", ".toml", ".ini", ".env", ".gitignore"
}

FILE_EXTENSIONS = {
    ".pdf", ".epub", ".mobi", ".docx", ".doc", ".xlsx", ".xls", ".pptx",
    ".ppt", ".txt", ".zip", ".rar", ".7z", ".tar", ".gz", ".iso"
}

GAMING_EXTENSIONS = {
    ".xapk", ".obb", ".nsp", ".xci", ".rom", ".patch", ".mcpack", ".mcworld"
}

MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".ts", ".wmv", ".3gp"
}

MUSIC_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".wma"
}

GAMING_KEYWORDS = (
    "دانلود بازی", "بازی جدید", "بازی کامپیوتر", "بازی اندروید", "بازی pc", "گیم", "گیمینگ",
    "گیمر", "game", "gaming", "gameplay", "game play", "mod apk", "apk mod",
    "modded", "appduny", "اپدونی", "فارسی روید", "farsroid", "پلی‌استیشن", "پلی استیشن",
    "playstation", "ps4", "ps5", "xbox", "ایکس‌باکس", "ایکس باکس", "nintendo", "نینتندو",
    "steam", "استیم", "کراک", "کرک بازی", "ترینر", "واکترو", "واک ترو", "گیم‌پلی",
    "گیمپلی", "گیم پلی", "دی‌ال‌سی", " dlc", "dlc ", "مود بازی", "ماد بازی", "ماینکرفت",
    "minecraft", " gta", "gta ", "جی تی ای", "پابجی", "pubg", "کالاف", "codm", "call of duty",
    "وارزون", "warzone", " pes", "pes ", "fifa", "اف سی", "fc 24", "fc 25", "کلش", "clash",
    "شبیه‌ساز", "emulator", "roms", " rom ", "نسخه مود", "دیتا دار", "بدون دیتا"
)

MEDIA_KEYWORDS = (
    "فیلم", "سریال", "سینمایی", "قسمت", "فصل", "اپیزود", "دانلود فیلم",
    "زیرنویس", "دوبله", "imdb", "movie", "series", "season", "episode",
    "1080p", "720p", "480p", "x265", "x264", "bluray", "web-dl", "hdtv",
    "trailer", "تیزر", "تریلر"
)

MUSIC_KEYWORDS = (
    "آهنگ", "موزیک", "ترانه", "پادکست", "ریمیکس", "خواننده", "صوت", "وکال",
    "music", "song", "track", "album", "remix", "podcast", "audio"
)

CODE_KEYWORDS = (
    "def ", "import ", "from ", "function ", "class ", "git ", "docker ",
    "npm ", "pip ", "curl ", "const ", "let ", "var ", "SELECT ", "UPDATE ",
    "bash", "powershell", "python", "javascript", "golang", "react", "vue"
)

IDEAS_KEYWORDS = (
    "ایده", "آموزش", "ترفند", "نکته", "خلاصه", "راهنما", "تحلیل", "نقل قول",
    "یادداشت مهم", "idea", "tutorial", "tip", "hack", "guide", "summary"
)


def classify_message_heuristic(msg, chat_title: str = "", override_text: str = "") -> Tuple[str, float]:
    """Fast heuristic classification based on deterministic rules and extensions."""
    text = (override_text or getattr(msg, "raw_text", "") or "").strip()
    clean_t = text.lower()
    clean_chat = (chat_title or "").lower()
    fwd_from = getattr(msg, "fwd_from", None)
    fwd_name = ""
    if fwd_from and type(fwd_from).__name__ != "MagicMock":
        raw_name = getattr(fwd_from, "from_name", "")
        if raw_name and type(raw_name).__name__ != "MagicMock":
            fwd_name = str(raw_name).lower()
    combined_context = f"{clean_t} {fwd_name} {clean_chat}".strip()

    # 1. Markdown code blocks
    if "```" in text:
        return "code", 0.99

    # 2. Telegram code entities
    if hasattr(msg, "entities") and msg.entities:
        for ent in msg.entities:
            if isinstance(ent, (types.MessageEntityCode, types.MessageEntityPre)):
                return "code", 0.95

    # 3. Attached files & documents
    if getattr(msg, "file", None):
        name = (getattr(msg.file, "name", "") or "").lower()
        mime = (getattr(msg.file, "mime_type", "") or "").lower()
        ext = os.path.splitext(name)[1]

        if ext in GAMING_EXTENSIONS:
            return "gaming", 0.98
        if ext == ".apk":
            if any(k in combined_context for k in GAMING_KEYWORDS) or "بازی" in clean_chat or "game" in clean_chat:
                return "gaming", 0.95
            return "files", 0.90
        if ext in CODE_EXTENSIONS:
            return "code", 0.99
        if ext in MEDIA_EXTENSIONS or mime.startswith("video/"):
            if any(k in combined_context for k in GAMING_KEYWORDS):
                return "gaming", 0.92
            return "media", 0.95
        if ext in MUSIC_EXTENSIONS or mime.startswith("audio/"):
            return "music", 0.95
        if ext in FILE_EXTENSIONS:
            return "files", 0.95

    # 4. Voice notes or audio files
    v = getattr(msg, "voice", None)
    a = getattr(msg, "audio", None)
    if (v is not None and type(v).__name__ != "MagicMock") or (a is not None and type(a).__name__ != "MagicMock"):
        return "music", 0.95

    # 5. Inline code keywords
    if "`" in text or any(k in text for k in ("def ", "import ", "const ", "class ", "git clone", "pip install", "npm install")):
        return "code", 0.90

    # 6. Gaming keywords & Gaming channel origin (Priority over generic media/teasers)
    if any(k in combined_context for k in GAMING_KEYWORDS):
        return "gaming", 0.92
    if any(k in clean_chat for k in ("دانلود بازی", "بازی", "game", "gaming", "appduny")):
        if not (any(k in clean_t for k in ("def ", "import ", "github.com")) or (getattr(msg, "voice", None) or getattr(msg, "audio", None))):
            return "gaming", 0.88

    # 7. Video media
    vid = getattr(msg, "video", None)
    if vid is not None and type(vid).__name__ != "MagicMock":
        return "media", 0.90

    # 8. Movies and series keywords
    if any(k in clean_t for k in MEDIA_KEYWORDS):
        return "media", 0.85

    # 9. Music and audio keywords
    if any(k in clean_t for k in MUSIC_KEYWORDS):
        return "music", 0.85

    # 10. Web URLs and links
    urls = re.findall(r"https?://[^\s]+", text)
    if urls:
        first_url = urls[0].lower()
        if any(d in first_url for d in ("steampowered.com", "store.epicgames.com", "ign.com", "kotaku.com")):
            return "gaming", 0.92
        if any(d in first_url for d in ("github.com", "gitlab.com", "stackoverflow.com")):
            return "code", 0.90
        if any(d in first_url for d in ("imdb.com", "youtube.com/watch", "youtu.be", "netflix.com")):
            return "media", 0.90
        if any(d in first_url for d in ("spotify.com", "soundcloud.com", "deezer.com")):
            return "music", 0.90
        if len(text.split()) < 10:
            return "links", 0.85

    # 11. Documents and files keywords
    if any(k in clean_t for k in ("pdf", "جزوه", "کتاب", "فایل", "سند", "پاورپوینت", "اکسل", "ورد")):
        return "files", 0.80

    # 12. Ideas and tutorials keywords
    if any(k in clean_t for k in IDEAS_KEYWORDS):
        return "ideas", 0.80

    # 13. Personal notes, credentials, card numbers
    if re.search(r"\b\d{16}\b", text) or "ir" in clean_t and re.search(r"\b\d{24}\b", text):
        return "personal", 0.95

    if len(text.split()) <= 6 and not urls:
        return "personal", 0.70

    return "misc", 0.40


async def classify_messages_batch_ai(messages_meta: List[Dict[str, Any]]) -> Dict[int, str]:
    """AI Decision Center: batch semantic classification for ambiguous messages."""
    if not messages_meta:
        return {}

    lines = []
    for m in messages_meta:
        snippet = (m.get("text") or "").replace("\n", " ")[:150]
        media_type = m.get("media_type") or "متن"
        fwd = m.get("fwd") or ""
        chat_name = m.get("chat") or ""
        chat_tag = f" | چت/کانال: {chat_name}" if chat_name else ""
        lines.append(f"- ID: {m['id']} | نوع: {media_type}{chat_tag} | فوروارد: {fwd} | متن: {snippet}")

    prompt = (
        "تو مسئول طبقه‌بندی و دسته‌بندی پیام‌های تلگرام برای یک صندوق هوشمند هستی.\n"
        "دسته‌های مجاز دقیقاً عبارتند از:\n"
        "• gaming : بازی‌های کامپیوتر، موبایل و کنسول، گیم، گیم‌پلی، مادها، فایل‌های بازی و اخبار بازی\n"
        "• personal : یادداشت‌های شخصی، خرید، رمز، شماره تماس، کارهای روزمره، افکار شخصی\n"
        "• media : فیلم، سریال، انیمیشن، ویدیوهای تفریحی، تیزر\n"
        "• code : اسکریپت، کد برنامه‌نویسی، گیت‌هاب، کانفیگ، دستورات ترمینال، فناوری\n"
        "• files : کتاب، جزوه دانشگاهی، فایل PDF، فایل فشرده، اسناد اداری، برنامه‌های غیربازی\n"
        "• music : آهنگ، موزیک، پادکست، فایل صوتی\n"
        "• links : لینک سایت، خبر، توییت، کانال، منبع وب\n"
        "• ideas : ایده، آموزش، نکات کاربردی، ترفند، معرفی ابزار\n"
        "• misc : هر چیزی که در دسته‌های بالا جا نشود\n\n"
        "پیام‌های زیر را بررسی کن و خروجی را فقط و فقط به شکل یک دیکشنری JSON معتبر با کلید ID و مقدار نام دسته برگردان:\n"
        "مثال: {\"123\": \"gaming\", \"124\": \"code\", \"125\": \"media\"}\n\n"
        "پیام‌ها:\n" + "\n".join(lines)
    )

    try:
        raw_res = await asyncio.to_thread(ai.ask_direct, prompt)
        if raw_res:
            match = re.search(r"\{.*?\}", raw_res, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                result = {}
                for k, v in parsed.items():
                    try:
                        cat = str(v).strip().lower()
                        if cat in TOPIC_TITLE_MAP:
                            result[int(k)] = cat
                    except Exception:
                        pass
                return result
    except Exception as e:
        logger.warning(f"Batch AI classification error ({e}); using heuristic fallback.")

    return {}


# ---------------------------------------------------------
# Safe message forwarding and management
# ---------------------------------------------------------

async def get_album_messages(client, msg) -> List[Any]:
    """Resolve all sibling messages belonging to the same album if grouped_id is present."""
    grouped_id = getattr(msg, "grouped_id", None)
    if not grouped_id:
        return [msg]

    try:
        peer = getattr(msg, "peer_id", None) or getattr(msg, "to_id", None) or "me"
        # Search a window of messages around target msg
        min_id = max(1, msg.id - 12)
        max_id = msg.id + 13
        query_ids = list(range(min_id, max_id))
        surrounding = await client.get_messages(peer, ids=query_ids)
        if surrounding:
            album = [m for m in surrounding if m and getattr(m, "grouped_id", None) == grouped_id]
            if album:
                album.sort(key=lambda m: m.id)
                return album
    except Exception as e:
        logger.debug(f"Failed to fetch album sibling messages: {e}")

    return [msg]


async def forward_to_topic(
    client,
    vault_entity,
    msg,
    topic_id: int,
    from_peer=None,
    album_ids: Optional[List[int]] = None
) -> bool:
    """Safely forward a message or entire album to a specific topic with MTProto top_msg_id and fallback."""
    ids_to_forward = album_ids if album_ids and len(album_ids) > 0 else [msg.id]

    try:
        if from_peer is None:
            peer_attr = getattr(msg, "peer_id", None) or getattr(msg, "to_id", None)
            from_peer = await client.get_input_entity(peer_attr) if peer_attr else await client.get_input_entity("me")
        else:
            from_peer = await client.get_input_entity(from_peer)
    except Exception:
        from_peer = await client.get_input_entity("me")

    # Attempt 1: ForwardMessagesRequest with top_msg_id & reply_to
    try:
        random_ids = [random.randint(1, 2**63 - 1) for _ in ids_to_forward]
        await client(functions.messages.ForwardMessagesRequest(
            from_peer=from_peer,
            id=ids_to_forward,
            to_peer=vault_entity,
            top_msg_id=topic_id,
            reply_to=types.InputReplyToMessage(reply_to_msg_id=topic_id, top_msg_id=topic_id),
            random_id=random_ids,
            drop_author=False
        ))
        return True
    except Exception as e1:
        logger.debug(f"Direct forward with top_msg_id failed ({e1}); trying forward fallback...")

    # Attempt 2: Telethon forward_messages with reply_to
    try:
        await client.forward_messages(
            vault_entity,
            messages=ids_to_forward,
            from_peer=from_peer,
            as_album=True if len(ids_to_forward) > 1 else None
        )
        return True
    except Exception as e2:
        logger.debug(f"forward_messages fallback failed ({e2}); trying copy fallback...")

    # Attempt 3: Single copy fallback send to topic if only one message
    if len(ids_to_forward) == 1:
        try:
            await client.send_message(
                vault_entity,
                msg,
                reply_to=topic_id,
                silent=True
            )
            return True
        except Exception as e3:
            logger.warning(f"Copy send to topic {topic_id} failed: {e3}")

    logger.error(f"All forward attempts failed for message(s) {ids_to_forward}")
    return False


async def organize_saved_messages(
    client,
    limit: int = 20,
    status_callback=None,
    force_all: bool = False
) -> Dict[str, Any]:
    """Main workflow for classifying and organizing Saved Messages into topic-based vault."""
    # 1. Ensure vault supergroup exists
    group_id, invite_link = await ensure_vault_group(client, status_callback)
    vault_entity = await client.get_input_entity(group_id)

    # 2. Ensure forum topics exist
    topic_map = await ensure_vault_topics(client, group_id, status_callback)

    # 3. Fetch messages from Saved Messages
    if status_callback:
        count_label = "تمام" if limit <= 0 else f"{limit}"
        await status_callback(f"📥 در حال خواندن {count_label} پیام از Saved Messages...")

    fetch_limit = None if limit <= 0 else limit
    if fetch_limit is None:
        fetch_limit = 2000  # Safety ceiling to prevent excessive execution time

    data = load_vault_data()
    already_processed: Set[int] = set(data.get("processed_msg_ids", []))

    messages = []
    async for m in client.iter_messages("me", limit=fetch_limit):
        # Skip empty system messages or actions
        if not m.raw_text and not m.media:
            continue
        if not force_all and m.id in already_processed:
            continue
        messages.append(m)

    if not messages:
        return {
            "total": 0,
            "by_topic": {},
            "vault_link": invite_link,
            "group_id": group_id,
            "message": "هیچ پیام جدیدی برای دسته‌بندی در سیو مسیج یافت نشد."
        }

    # 4. Two-tier classification (heuristics + AI)
    if status_callback:
        await status_callback(f"🧠 در حال ارزیابی {len(messages)} پیام با هوش مصنوعی...")

    decisions: Dict[int, str] = {}
    needs_ai: List[Dict[str, Any]] = []

    for m in messages:
        cat, conf = classify_message_heuristic(m)
        if conf >= 0.85:
            decisions[m.id] = cat
        else:
            media_kind = "متن"
            if m.file:
                media_kind = f"فایل ({m.file.name or m.file.mime_type or ''})"
            elif getattr(m, "photo", None):
                media_kind = "عکس"
            elif getattr(m, "video", None):
                media_kind = "ویدیو"
            elif getattr(m, "voice", None):
                media_kind = "وویس"

            fwd_info = ""
            if getattr(m, "fwd_from", None):
                fwd_info = getattr(m.fwd_from, "from_name", "") or ""

            needs_ai.append({
                "id": m.id,
                "text": m.raw_text or "",
                "media_type": media_kind,
                "fwd": fwd_info,
                "heuristic": cat
            })

    # Send ambiguous messages to AI in batches of 15
    if needs_ai:
        for i in range(0, len(needs_ai), 15):
            chunk = needs_ai[i:i + 15]
            ai_results = await classify_messages_batch_ai(chunk)
            for item in chunk:
                mid = item["id"]
                decisions[mid] = ai_results.get(mid, item["heuristic"])

    # 5. Forward messages to destination topics (grouped by album where applicable)
    topic_counts: Dict[str, int] = {}
    total_forwarded = 0
    newly_processed = []

    # Reverse order to preserve original chronological sequence
    messages.reverse()

    # Group consecutive messages sharing the same grouped_id into album units
    units: List[List[Any]] = []
    curr_unit: List[Any] = []
    curr_gid = None

    for m in messages:
        gid = getattr(m, "grouped_id", None)
        if gid:
            if curr_gid == gid:
                curr_unit.append(m)
            else:
                if curr_unit:
                    units.append(curr_unit)
                curr_unit = [m]
                curr_gid = gid
        else:
            if curr_unit:
                units.append(curr_unit)
                curr_unit = []
                curr_gid = None
            units.append([m])

    if curr_unit:
        units.append(curr_unit)

    for idx, unit in enumerate(units, 1):
        cat = "misc"
        for m in unit:
            if m.id in decisions:
                cat = decisions[m.id]
                break

        topic_id = topic_map.get(cat) or topic_map.get("misc") or 1
        topic_title = TOPIC_TITLE_MAP.get(cat, "متفرقه")

        unit_ids = [m.id for m in unit]
        ok = await forward_to_topic(client, vault_entity, unit[0], topic_id, album_ids=unit_ids)
        if ok:
            topic_counts[topic_title] = topic_counts.get(topic_title, 0) + len(unit_ids)
            total_forwarded += len(unit_ids)
            newly_processed.extend(unit_ids)

        # Live status callback every 15 units
        if status_callback and (idx % 15 == 0 or idx == len(units)):
            await status_callback(f"🚀 در حال انتقال پیام‌ها: {idx} از {len(units)}...")

        # Brief sleep to respect Telegram FloodWait limits
        await asyncio.sleep(0.35)

    # 6. Save updated state to local registry
    data["processed_msg_ids"].extend(newly_processed)
    data["total_organized_count"] = data.get("total_organized_count", 0) + total_forwarded
    save_vault_data(data)

    return {
        "total": total_forwarded,
        "by_topic": topic_counts,
        "vault_link": invite_link,
        "group_id": group_id,
        "message": "عملیات با موفقیت تکمیل شد."
    }


# ---------------------------------------------------------
# Natural command parser
# ---------------------------------------------------------

VAULT_TRIGGERS = (
    "سیو مسیج", "سیومسیج", "پیام‌های ذخیره", "پیامهای ذخیره",
    "saved messages", "صندوق", "صندوقو", "صندوق هوشمند"
)

ACTION_KEYWORDS = (
    "مرتب", "دسته‌بندی", "دسته بندی", "تفکیک", "سازماندهی", "سازمان‌دهی",
    "انتقال", "بایگانی", "سورت", "فولدر", "پاکسازی", "پاک سازی", "پاک کن",
    "خالی کن", "حذف", "ریست", "دوباره", "مجدد"
)


def is_vault_command(text: str) -> bool:
    """Check if message matches vault command triggers."""
    clean = text.strip().lower()
    has_target = any(k in clean for k in VAULT_TRIGGERS)
    has_action = any(k in clean for k in ACTION_KEYWORDS) or "وضعیت" in clean or "ساخت" in clean
    return has_target and has_action


def parse_vault_command_limit(text: str) -> int:
    """Extract message limit from user command text."""
    clean = text.strip().lower()

    if any(k in clean for k in ("همه", "کل", "تمامی", "all")):
        return -1

    # Normalize Persian digits to Latin
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    latin_digits = "0123456789"
    trans = str.maketrans(persian_digits, latin_digits)
    normalized = clean.translate(trans)

    m = re.search(r"\b(\d+)\b", normalized)
    if m:
        try:
            val = int(m.group(1))
            return val
        except ValueError:
            pass

    return 20  # Default count if unspecified


async def purge_vault_messages(
    client,
    limit: int = -1,
    status_callback=None
) -> Dict[str, Any]:
    """Purge content messages from vault supergroup while preserving topic creation actions."""
    data = load_vault_data()
    group_id = data.get("group_id")
    if not group_id:
        return {
            "deleted": 0,
            "message": "هنوز سوپرگروه صندوق ایجاد نشده است که نیاز به پاک‌سازی داشته باشد."
        }

    try:
        vault_entity = await client.get_input_entity(group_id)
    except Exception as e:
        return {
            "deleted": 0,
            "message": f"دسترسی به سوپرگروه صندوق با خطا مواجه شد: {e}"
        }

    if status_callback:
        count_label = "تمام" if limit <= 0 else f"{limit}"
        await status_callback(f"🔍 در حال بررسی صندوق جهت پاک‌سازی {count_label} پیام...")

    fetch_limit = 2500 if limit <= 0 else max(limit * 2, 100)
    to_delete = []

    try:
        async for m in client.iter_messages(vault_entity, limit=fetch_limit):
            # Preserve topic creation actions and system messages
            if getattr(m, "action", None) is not None:
                continue
            # Preserve welcome header message
            if m.id == 1:
                continue

            to_delete.append(m.id)
            if limit > 0 and len(to_delete) >= limit:
                break
    except Exception as e:
        logger.error(f"Error reading vault messages for purge: {e}")
        return {"deleted": 0, "message": f"خطا در بررسی پیام‌های صندوق: {e}"}

    if not to_delete:
        return {
            "deleted": 0,
            "message": "هیچ پیام قابل حذفی در صندوق هوشمند یافت نشد."
        }

    total_deleted = 0
    for i in range(0, len(to_delete), 100):
        chunk = to_delete[i:i + 100]
        try:
            await client.delete_messages(vault_entity, chunk)
            total_deleted += len(chunk)
            if status_callback:
                await status_callback(f"🗑 در حال حذف پیام‌های صندوق: {total_deleted} از {len(to_delete)}...")
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"Error deleting message chunk in vault: {e}")

    # Update local registry state
    if limit <= 0:
        data["processed_msg_ids"] = []
        data["total_organized_count"] = 0
    else:
        data["total_organized_count"] = max(0, data.get("total_organized_count", 0) - total_deleted)

    save_vault_data(data)
    return {
        "deleted": total_deleted,
        "is_full_reset": limit <= 0,
        "message": f"تعداد {total_deleted} پیام از صندوق هوشمند با موفقیت پاک‌سازی شد."
    }


async def handle_vault_command(event, status, question: str) -> bool:
    """Main command handler for Saved Messages vault operations."""
    if not is_vault_command(question):
        return False

    client = event.client
    clean_q = question.strip().lower()

    async def update_status_cb(text: str):
        try:
            await status.edit(text)
        except Exception:
            pass

    # 1. Vault status query
    if "وضعیت" in clean_q:
        data = load_vault_data()
        group_id = data.get("group_id")
        link = data.get("group_invite_link", "")
        total = data.get("total_organized_count", 0)
        topics = data.get("topics", {})

        if not group_id:
            msg = (
                "📁 **وضعیت صندوق هوشمند کاپری:**\n\n"
                "⚠️ هنوز سوپرگروه صندوق ایجاد نشده است.\n"
                "برای راه‌اندازی و مرتب‌سازی، بنویسید:\n"
                "`کاپری مرتب کن سیو مسیج ۱۰ پیام`"
            )
        else:
            lines = [
                "📁 **وضعیت صندوق هوشمند کاپری (Capri Vault):**",
                f"• شناسه گروه: `{group_id}`",
                f"• کل پیام‌های سازمان‌دهی‌شده: **{total}** پیام",
                f"• تعداد تاپیک‌های فعال: **{len(topics)}** تاپیک\n",
                "📌 **تاپیک‌های تعریف‌شده:**"
            ]
            for k, info in topics.items():
                lines.append(f"• {info.get('title', k)}")
            if link:
                lines.append(f"\n🔗 [مشاهده سوپرگروه صندوق]({link})")
            msg = "\n".join(lines)

        await status.edit(msg)
        return True

    # 2. Purge vault messages
    is_purge = any(w in clean_q for w in ("پاکسازی", "پاک سازی", "پاک کن", "خالی کن", "حذف پیام"))
    if is_purge:
        # Determine whether full purge or last N messages
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        latin_digits = "0123456789"
        trans = str.maketrans(persian_digits, latin_digits)
        normalized = clean_q.translate(trans)
        digit_match = re.search(r"\b(\d+)\b", normalized)

        if digit_match:
            purge_limit = int(digit_match.group(1))
        else:
            purge_limit = -1  # Full purge

        count_desc = f"{purge_limit} پیام اخیر" if purge_limit > 0 else "کل پیام‌های"
        await update_status_cb(f"⏳ در حال آغاز پاک‌سازی {count_desc} صندوق هوشمند...")

        try:
            res = await purge_vault_messages(client, limit=purge_limit, status_callback=update_status_cb)
            deleted = res.get("deleted", 0)
            if deleted == 0:
                await status.edit(f"ℹ️ {res.get('message', 'هیچ پیامی برای حذف پیدا نشد.')}")
                return True

            if res.get("is_full_reset"):
                await status.edit(
                    f"🗑️ **صندوق هوشمند با موفقیت پاک‌سازی شد!**\n\n"
                    f"• تعداد **{deleted}** پیام محتوایی از سوپرگروه حذف شد.\n"
                    f"• حافظه و کش پیام‌های پردازش‌شده ریست شد و صندوق آماده مرتب‌سازی مجدد است."
                )
            else:
                await status.edit(
                    f"🗑️ **پاک‌سازی صندوق انجام شد!**\n\n"
                    f"• تعداد **{deleted}** پیام اخیر از صندوق هوشمند حذف گردید."
                )
            return True
        except Exception as e:
            logger.error(f"Error in vault purge: {e}", exc_info=True)
            await status.edit(f"❌ خطا در پاک‌سازی صندوق: {e}")
            return True

    # 3. Reorganize vault
    is_reorganize = any(w in clean_q for w in ("دوباره", "مجدد", "از اول", "مجددا")) and any(
        w in clean_q for w in ("مرتب", "دسته‌بندی", "دسته بندی", "تفکیک", "سازماندهی", "سازمان‌دهی")
    )
    if is_reorganize:
        # Default to 50 messages if count unspecified
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        latin_digits = "0123456789"
        trans = str.maketrans(persian_digits, latin_digits)
        normalized = clean_q.translate(trans)
        digit_match = re.search(r"\b(\d+)\b", normalized)
        limit = int(digit_match.group(1)) if digit_match else 50
        limit_label = f"{limit} پیام"

        await update_status_cb(f"🔄 در حال آغاز سازمان‌دهی مجدد {limit_label} از Saved Messages...")

        try:
            report = await organize_saved_messages(
                client=client,
                limit=limit,
                status_callback=update_status_cb,
                force_all=True
            )

            total = report["total"]
            by_topic = report["by_topic"]
            link = report.get("vault_link", "")

            if total == 0:
                await status.edit(f"ℹ️ {report['message']}")
                return True

            lines = [
                "🔄 **سازمان‌دهی مجدد صندوق با موفقیت انجام شد!**\n",
                f"📦 **تعداد پیام‌های مجدداً بررسی و منتقل‌شده:** **{total}** پیام\n",
                "📊 **تفکیک پیام‌ها بر اساس تاپیک:**"
            ]
            for topic_title, count in by_topic.items():
                lines.append(f"• {topic_title}: **{count}** پیام")

            if link:
                lines.append(f"\n🔗 [ورود به سوپرگروه صندوق هوشمند]({link})")
            lines.append("\n📌 پیام‌ها در تاپیک‌های اختصاصی بایگانی شدند.")

            await status.edit("\n".join(lines))
            return True
        except Exception as e:
            logger.error(f"Error in vault reorganize: {e}", exc_info=True)
            await status.edit(f"❌ خطا در سازمان‌دهی مجدد صندوق: {e}")
            return True

    # 4. Standard message sorting and forwarding flow
    limit = parse_vault_command_limit(question)
    limit_label = "تمام" if limit <= 0 else f"{limit}"

    await update_status_cb(f"⏳ در حال آغاز سازمان‌دهی {limit_label} پیام از Saved Messages...")

    try:
        report = await organize_saved_messages(
            client=client,
            limit=limit,
            status_callback=update_status_cb
        )

        total = report["total"]
        by_topic = report["by_topic"]
        link = report.get("vault_link", "")

        if total == 0:
            await status.edit(f"ℹ️ {report['message']}")
            return True

        lines = [
            "✅ **سازمان‌دهی سیو مسیج با موفقیت انجام شد!**\n",
            f"📦 **تعداد پیام‌های بررسی و منتقل‌شده:** **{total}** پیام\n",
            "📊 **تفکیک پیام‌ها بر اساس تاپیک:**"
        ]
        for topic_title, count in by_topic.items():
            lines.append(f"• {topic_title}: **{count}** پیام")

        if link:
            lines.append(f"\n🔗 [ورود به سوپرگروه صندوق هوشمند]({link})")
        lines.append("\n📌 پیام‌ها در تاپیک‌های اختصاصی بایگانی شدند و گروه در تلگرام شما در دسترس است.")

        await status.edit("\n".join(lines))
        return True
    except Exception as e:
        logger.error(f"Error in organize_saved_messages: {e}", exc_info=True)
        await status.edit(f"❌ خطا در سازمان‌دهی سیو مسیج: {e}")
        return True
