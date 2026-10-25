import asyncio
import re
import time

from telethon import types

from ai_engine import ai

BOT = "DeezerMusicBot"
AUDIO_EXTS = (".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".wav", ".wma")
_PERSIAN_DIGITS = {'۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
                   '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'}
DOWNLOAD_HINTS = ("دانلود", "دریافت", "download", "پخش", "play", "گرفتن")
START_HINTS = ("شروع", "start", "▶️", "بزن بریم")


def _norm(s: str) -> str:
    if not s:
        return ""
    for ch in ".:_-/،":
        s = s.replace(ch, " ")
    return " ".join(s.lower().split())


def _is_audio(m) -> bool:
    if not m or not m.media:
        return False
    if isinstance(m.media, types.MessageMediaDocument):
        doc = m.media.document
        if doc.mime_type and doc.mime_type.startswith("audio/"):
            return True
        for a in doc.attributes:
            if isinstance(a, types.DocumentAttributeAudio):
                return True
            if isinstance(a, types.DocumentAttributeFilename) and a.file_name:
                if a.file_name.lower().endswith(AUDIO_EXTS):
                    return True
    return False


async def _wait_for_buttons(client, bot, after_id, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot, limit=20)
        for m in msgs:
            if not m.out and m.id > after_id and m.buttons:
                return m
        await asyncio.sleep(1.5)
    return None


def _is_start_prompt(panel) -> bool:
    """پنلی که فقط یه دکمه‌ی «شروع» داره، نتیجهٔ جستجو نیست."""
    if not panel or not panel.buttons:
        return False
    flat = [b for row in panel.buttons for b in row]
    if len(flat) != 1:
        return False
    t = (flat[0].text or "").lower()
    return any(h in t for h in START_HINTS) or flat[0].url is not None


def _parse_choice(raw, buttons):
    if not raw:
        return None
    s = raw.strip()
    for p, a in _PERSIAN_DIGITS.items():
        s = s.replace(p, a)
    m = re.search(r"\d+", s)
    if m:
        v = int(m.group(0))
        if 1 <= v <= len(buttons):
            return v - 1
    low = s.lower()
    for i, b in enumerate(buttons):
        t = (b.text or "").strip().lower()
        if len(t) >= 3 and t in low:
            return i
    return None


def _ai_pick(buttons, query):
    n = len(buttons)
    if n == 1:
        return 0
    numbered = "\n".join(f"{i + 1}. {(b.text or '').strip()}" for i, b in enumerate(buttons))
    system = "تو یک موتور تطبیق آهنگ هستی. فقط و فقط یک عدد جواب بده، بدون هیچ توضیح اضافه."
    prompt = (
        f"کاربر این آهنگ را خواسته: «{query}»\n\n"
        f"نتایج جستجو:\n{numbered}\n\n"
        "کدام گزینه دقیقاً همان آهنگی است که کاربر خواسته؟ فقط شمارهٔ گزینه (یک عدد) را بنویس. اگر هیچ‌کدام درست نیست بنویس 0."
    )
    try:
        raw = ai.ask_direct(prompt, system=system)
    except Exception:
        raw = ""
    return _parse_choice(raw, buttons)


def _heuristic_pick(buttons, query):
    qn = _norm(query)
    qwords = [w for w in qn.split() if len(w) >= 3]
    best, best_score = None, -1
    for i, b in enumerate(buttons):
        t = _norm(b.text or "")
        if not t:
            continue
        score = 0
        if qn and qn in t:
            score += 100
        for w in qwords:
            if w in t:
                score += 10
        if score > best_score:
            best, best_score = i, score
    return best if best_score > 0 else None


async def _drain_audio(client, bot, after_id, timeout=25):
    files = {}
    clicked = set()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msgs = await client.get_messages(bot, limit=20)
        for m in msgs:
            if m.out or m.id <= after_id:
                continue
            if _is_audio(m):
                files[m.id] = m
        if files:
            await asyncio.sleep(1.0)
            msgs = await client.get_messages(bot, limit=10)
            for m in msgs:
                if not m.out and m.id > after_id and _is_audio(m):
                    files[m.id] = m
            return sorted(files.values(), key=lambda x: x.id)

        act = next((m for m in msgs if not m.out and m.buttons), None)
        if act:
            dl = next((b for row in act.buttons for b in row
                       if b.data and b.data not in clicked
                       and any(h in (b.text or "").lower() for h in DOWNLOAD_HINTS)), None)
            if dl:
                await act.click(data=dl.data)
                clicked.add(dl.data)
                continue
        await asyncio.sleep(1.5)
    return sorted(files.values(), key=lambda x: x.id)


async def fetch_music(client, query, event=None, status=None):
    """در @DeezerMusicBot جستجو می‌کند، با هوش مصنوعی گزینهٔ درست را می‌زند و فایل را بدون کپشن می‌فرستد.

    برمی‌گرداند (sent, err): sent تعداد فایل‌های ارسال‌شده و err پیام خطا (None یعنی موفق).
    """
    if not query or not query.strip():
        return 0, "نام آهنگ خالی است."
    try:
        bot = await client.get_entity(BOT)
    except Exception:
        return 0, f"ربات @{BOT} پیدا نشد. اول توی تلگرام بهش /start بده."

    try:
        s1 = await client.send_message(bot, "/start")
        await asyncio.sleep(1.5)
        for _ in range(5):
            msgs = await client.get_messages(bot, limit=5)
            if any(not m.out and m.id > s1.id for m in msgs):
                break
            await asyncio.sleep(1.0)
        sent = await client.send_message(bot, query)
    except Exception as e:
        return 0, f"نتونستم به @{BOT} پیام بدم: {e}"
    base = sent.id

    panel = await _wait_for_buttons(client, bot, base)
    if panel is None:
        return 0, f"@{BOT} پنل نتایج نفرستاد (شاید آهنگ پیدا نشد یا ربات در دسترس نیست)."
    if _is_start_prompt(panel):
        try:
            await client.send_message(bot, "/start")
            await asyncio.sleep(1.5)
            sent = await client.send_message(bot, query)
            base = sent.id
        except Exception:
            return 0, f"@{BOT} جواب نداد."
        panel = await _wait_for_buttons(client, bot, base)
        if panel is None:
            return 0, f"@{BOT} پنل نتایج نفرستاد (شاید آهنگ پیدا نشد)."

    buttons = [b for row in panel.buttons for b in row if b.data]
    if not buttons:
        return 0, f"@{BOT} نتیج‌های با دکمه نفرستاد."

    idx = await asyncio.to_thread(_ai_pick, buttons, query)
    if idx is None:
        idx = _heuristic_pick(buttons, query)
    if idx is None:
        return 0, "نتونستم تشخیص بدم کدوم گزینه همون آهنگه."

    await panel.click(data=buttons[idx].data)

    files = await _drain_audio(client, bot, panel.id)
    if not files:
        return 0, "فایل صوتی از ربات نیومد (شاید سهمیه یا خطا)."

    sent_n = 0
    for m in files:
        try:
            # آپلود تمیز بدون کپشن تا «Forwarded from» و منبع ربات فاش نشود
            await client.send_file(event.chat_id, m.media)
            sent_n += 1
            await asyncio.sleep(0.5)
        except Exception:
            continue
    if not sent_n:
        return 0, "فایل اومد ولی ارسالش ممکن نشد."
    return sent_n, None
