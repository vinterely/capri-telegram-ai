import asyncio
import hashlib
import importlib.util
import json
import logging
import ast
import os
import re
import sys
import traceback
from typing import Any, Dict, List, Optional

from core import config

log = logging.getLogger("skills_manager")

SKILLS_DIR = os.path.join(config.BASE_DIR, "custom_skills")
REGISTRY_FILE = os.path.join(SKILLS_DIR, "registry.json")

os.makedirs(SKILLS_DIR, exist_ok=True)


# ساخت اسکیل جدید توسط هوش مصنوعی به‌صورت پیش‌فرض خاموش است. روشن کردن: ALLOW_SKILL_CREATION=1 در .env
ALLOW_SKILL_CREATION = os.getenv("ALLOW_SKILL_CREATION", "0").strip() == "1"
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,32}$")

INTEGRITY_FILE = os.path.join(config.BASE_DIR, "core", "skills_integrity.json")


def is_skill_creation_allowed() -> bool:
    """بررسی فعال بودن امکان ساخت یا تغییر اسکیل‌ها."""
    from core import config as _cfg
    if getattr(_cfg, "ALLOW_SKILL_CREATION", False):
        return True
    return os.getenv("ALLOW_SKILL_CREATION", "0").strip() == "1"


def _calc_file_sha256(path: str) -> str:
    """محاسبه هش امن SHA-256 فایل."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _load_integrity() -> Dict[str, str]:
    if not os.path.exists(INTEGRITY_FILE):
        return {}
    try:
        with open(INTEGRITY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning(f"Failed to read skills integrity: {e}")
        return {}


def _save_integrity(hashes: Dict[str, str]) -> None:
    try:
        from core import fsutil
        fsutil.atomic_write_json(INTEGRITY_FILE, hashes)
    except Exception as e:
        log.error(f"Failed to save skills integrity: {e}")

# سقف زمان اجرای اسکیل‌های داینامیک (ثانیه)
SKILL_TIMEOUT = 60

# ماژول‌ها و نام‌هایی که در کد اسکیل مجاز نیستند (جلوگیری از دسترسی به سیستم‌عامل، شبکه خام، فایل‌ها و فرار از سندباکس)
_FORBIDDEN_MODULES = {
    "os", "subprocess", "socket", "sys", "shutil", "importlib",
    "ctypes", "builtins", "pickle", "marshal", "pathlib", "io",
    "multiprocessing", "signal", "gc",
}
_FORBIDDEN_NAMES = {
    "eval", "exec", "__import__", "compile", "open", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "__builtins__", "exit", "quit", "breakpoint",
}
_FORBIDDEN_ATTRS = {
    "__class__", "__bases__", "__mro__", "__subclasses__", "__globals__",
    "__builtins__", "__code__", "__func__", "__self__", "__loader__",
    "__spec__", "__getattribute__", "__dict__", "__reduce__", "__reduce_ex__",
}


def _validate_skill_code(python_code: str) -> str:
    """بازرسی امنیتی AST کد اسکیل. خروجی خالی یعنی کد مجاز است."""
    try:
        tree = ast.parse(python_code)
    except SyntaxError as se:
        return f"خطای سینتکس در کد اسکیل: {se.msg} (خط {se.lineno})"

    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in _FORBIDDEN_MODULES:
                    problems.append(f"import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in _FORBIDDEN_MODULES:
                problems.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Name):
            if node.id in _FORBIDDEN_NAMES:
                problems.append(node.id)
        elif isinstance(node, ast.Attribute):
            if node.attr in _FORBIDDEN_ATTRS:
                problems.append(node.attr)

    if problems:
        uniq = []
        for p in problems:
            if p not in uniq:
                uniq.append(p)
        return "کد اسکیل شامل سازه‌ی ناامن است: " + "، ".join(uniq)
    return ""


def validate_skill(name: str, python_code: str) -> str:
    """پیش‌اعتبارسنجی نام و کد اسکیل بدون نوشتن روی دیسک. خروجی خالی یعنی معتبر."""
    if not is_skill_creation_allowed():
        return "ساخت یا ویرایش اسکیل غیرفعال است. (ALLOW_SKILL_CREATION=0)"
    name = name.strip().lower()
    if not _NAME_RE.match(name):
        return f"نام اسکیل «{name}» باید انگلیسی کوچک، عدد و آندرلاین باشد (۳ تا ۳۳ کاراکتر، شروع با حرف انگلیسی)."
    from ai_engine import tools as _tools
    if name in {d["function"]["name"] for d in _tools.TOOL_DEFINITIONS}:
        return f"نام «{name}» با یکی از ابزارهای اصلی سیستم تداخل دارد؛ نام دیگری انتخاب کن."
    return _validate_skill_code(python_code)


def _skill_path(name: str) -> str:
    return os.path.join(SKILLS_DIR, f"{name}.py")
def _load_registry() -> Dict[str, Any]:
    if not os.path.exists(REGISTRY_FILE):
        return {}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Failed to read skills registry: {e}")
        return {}


def _save_registry(registry: Dict[str, Any]) -> None:
    try:
        from core import fsutil
        fsutil.atomic_write_json(REGISTRY_FILE, registry)
    except Exception as e:
        log.error(f"Failed to save skills registry: {e}")


def get_all_skills() -> Dict[str, Any]:
    """دریافت لیست تمام اسکیل‌های داینامیک ثبت‌شده."""
    return _load_registry()


_cached_mtime: Optional[float] = None
_cached_definitions: List[Dict[str, Any]] = []


def get_skill_tool_definitions() -> List[Dict[str, Any]]:
    """تبدیل اسکیل‌های معتبر و دارای صحت هش به فرمت استاندارد ابزارها با کش mtime."""
    global _cached_mtime, _cached_definitions
    try:
        mtime = os.path.getmtime(REGISTRY_FILE) if os.path.exists(REGISTRY_FILE) else 0
    except OSError:
        mtime = 0

    if _cached_mtime is not None and mtime == _cached_mtime:
        return _cached_definitions

    registry = _load_registry()
    integrity = _load_integrity()
    definitions = []
    for name, skill in registry.items():
        file_path = _skill_path(name)
        expected_sha = integrity.get(name)
        if not expected_sha or not os.path.exists(file_path):
            continue
        actual_sha = _calc_file_sha256(file_path)
        if actual_sha != expected_sha:
            log.warning("Skill '%s' skipped from definitions due to integrity mismatch.", name)
            continue

        definitions.append({
            "type": "function",
            "function": {
                "name": name,
                "description": skill.get("description", f"Dynamic skill: {name}"),
                "parameters": skill.get("parameters", {
                    "type": "object",
                    "properties": {},
                })
            }
        })
    _cached_mtime = mtime
    _cached_definitions = definitions
    return definitions


def create_or_update_skill(name: str, description: str, parameters: dict, python_code: str) -> str:
    """ساخت یا ارتقای یک اسکیل پایتونی جدید با کنترل سطح دسترسی و محاسبه هش امن."""
    if not is_skill_creation_allowed():
        return "❌ ساخت یا ویرایش اسکیل غیرفعال است (ALLOW_SKILL_CREATION=0)."

    err = validate_skill(name, python_code)
    if err:
        return f"❌ {err}"
    name = name.strip().lower()

    # اعتبارسنجی سینتکس کد (در کنار بازرسی امنیتی AST)
    try:
        compile(python_code, f"{name}.py", "exec")
    except SyntaxError as se:
        return f"❌ خطای سینتکس در کد اسکیل: {se.msg} (خط {se.lineno})"

    file_path = _skill_path(name)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(python_code)
    except Exception as e:
        return f"❌ خطا در نوشتن فایل اسکیل: {e}"

    # ثبت هش صحت اسکریپت خارج از custom_skills
    file_sha = _calc_file_sha256(file_path)
    integrity = _load_integrity()
    integrity[name] = file_sha
    _save_integrity(integrity)

    registry = _load_registry()
    registry[name] = {
        "name": name,
        "description": description,
        "parameters": parameters or {"type": "object", "properties": {}},
        "file": file_path
    }
    _save_registry(registry)

    log.info("Skill '%s' saved (sha256=%s, %d bytes)", name, file_sha[:16], len(python_code.encode("utf-8")))

    # بررسی ساختار بدون اجرای کد
    try:
        tree = ast.parse(python_code)
        has_execute = any(
            isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == "execute"
            for n in tree.body
        )
        if not has_execute:
            return "⚠️ اسکیل ذخیره شد، اما تابع `async def execute(args, client, event)` در کد پیدا نشد."
    except Exception as e:
        return f"⚠️ اسکیل ذخیره شد اما بررسی ساختار خطا داد: {e}"

    return f"✅ اسکیل «{name}» با موفقیت ساخته و در رجیستری ابزارهای کاپری ثبت شد."


def delete_skill(name: str) -> str:
    """حذف یک اسکیل داینامیک و ابطال رکورد هش آن."""
    if not is_skill_creation_allowed():
        return "❌ حذف اسکیل غیرفعال است (ALLOW_SKILL_CREATION=0)."

    name = name.strip().lower()
    registry = _load_registry()
    if name not in registry:
        return f"اسکیلی به نام «{name}» وجود ندارد."
    file_path = _skill_path(name) if _NAME_RE.match(name) else None
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    del registry[name]
    _save_registry(registry)

    integrity = _load_integrity()
    integrity.pop(name, None)
    _save_integrity(integrity)

    return f"🗑 اسکیل «{name}» حذف شد."


async def execute_skill(name: str, args: dict, client, event) -> str:
    """اجرای مستقیم یک اسکیل داینامیک پس از تایید صحت و یکپارچگی هش فایل."""
    name = name.strip().lower()
    registry = _load_registry()
    if name not in registry:
        return f"❌ اسکیل «{name}» در سیستم یافت نشد."

    file_path = _skill_path(name) if _NAME_RE.match(name) else None
    if not file_path or not os.path.exists(file_path):
        return f"❌ فایل اسکریپت اسکیل «{name}» روی دیسک پیدا نشد."

    integrity = _load_integrity()
    expected_sha = integrity.get(name)
    if not expected_sha:
        return f"❌ خطای یکپارچگی: رکورد هش امن برای اسکیل «{name}» یافت نشد."

    actual_sha = _calc_file_sha256(file_path)
    if actual_sha != expected_sha:
        log.error("Skill integrity mismatch for %s: expected %s, got %s", name, expected_sha, actual_sha)
        return f"❌ هشدار امنیتی: هش فایل اسکریپت «{name}» با امضای مجاز مطابقت ندارد و تغییر یافته است. اجرا مسدود شد."

    try:
        spec = importlib.util.spec_from_file_location(name, file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        if not hasattr(mod, "execute"):
            return f"❌ اسکیل «{name}» فاقد تابع execute است."

        fn = getattr(mod, "execute")
        try:
            if asyncio.iscoroutinefunction(fn):
                res = await asyncio.wait_for(fn(args, client, event), timeout=SKILL_TIMEOUT)
            else:
                res = await asyncio.wait_for(asyncio.to_thread(fn, args, client, event), timeout=SKILL_TIMEOUT)
            return str(res)
        except asyncio.TimeoutError:
            log.error(f"Custom skill {name} exceeded {SKILL_TIMEOUT}s timeout")
            return f"⏱ اسکیل «{name}» بیش از {SKILL_TIMEOUT} ثانیه طول کشید و متوقف شد."
    except Exception as e:
        tb = traceback.format_exc()
        log.error(f"Error executing custom skill {name}: {tb}")
        return f"❌ خطا در اجرای اسکیل {name}: {e}"
