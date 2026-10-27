"""Active Operations Registry and Per-Chat Task Cancellation.

Tracks running asynchronous tasks (ReAct loops, media downloads, search operations) per chat_id.
Enables immediate cancellation of long-running operations upon user request, preventing
stale background tasks from waking up or resuming agent turns.
"""

import asyncio
import time
from typing import Dict, Optional


class _Operation:
    __slots__ = ("task", "chat_id", "status", "started_at")

    def __init__(self, task: "asyncio.Task", chat_id: str, status=None):
        self.task = task
        self.chat_id = chat_id
        self.status = status
        self.started_at = time.time()


_active: Dict[str, _Operation] = {}


def register(chat_id: str, task: "asyncio.Task", status=None) -> None:
    """Register an active task for a chat. Replaces any existing task for the same chat."""
    if not chat_id:
        return
    _active[str(chat_id)] = _Operation(task, str(chat_id), status)


def unregister(chat_id: str, task: Optional["asyncio.Task"] = None) -> None:
    """Remove a task from registry. If task is provided, only unregisters if matching."""
    op = _active.get(str(chat_id)) if chat_id else None
    if op and (task is None or op.task is task):
        _active.pop(str(chat_id), None)


def set_status(chat_id: str, status) -> None:
    op = _active.get(str(chat_id)) if chat_id else None
    if op:
        op.status = status


def get(chat_id: str) -> Optional[_Operation]:
    return _active.get(str(chat_id)) if chat_id else None


async def _edit_status(status, text: str) -> None:
    try:
        await status.edit(text)
    except Exception:
        pass


def cancel(chat_id: str) -> bool:
    """Cancel the active task for the specified chat. Returns True if a task was cancelled."""
    key = str(chat_id) if chat_id else None
    op = _active.pop(key, None) if key else None
    if op is None:
        return False
    current = asyncio.current_task()
    if op.task is current:
        # Prevent cancelling the cancellation command itself
        _active[key] = op
        return False
    op.task.cancel()
    if op.status is not None:
        try:
            asyncio.create_task(_edit_status(op.status, "🛑 عملیات در حال اجرا لغو شد."))
        except Exception:
            pass
    return True


def cancel_all() -> int:
    """Cancel all active tasks (e.g. during shutdown). Returns number of cancelled tasks."""
    n = 0
    for op in list(_active.values()):
        try:
            op.task.cancel()
            n += 1
        except Exception:
            pass
    _active.clear()
    return n
