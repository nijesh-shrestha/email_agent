import os
import time
import threading
from typing import Tuple

# Simple in-memory sliding-window rate limiter.
# Not suitable for multi-process deployments; use Redis or similar in production.

RATE_LIMIT_SENDS = int(os.getenv("RATE_LIMIT_SENDS", "5"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

_lock = threading.Lock()
# mapping: user_id -> list[timestamp_seconds]
_timestamps: dict[str, list[float]] = {}


def allow_send(user_id: str) -> Tuple[bool, dict]:
    """Return (allowed, meta) where meta contains remaining, limit, window_seconds."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    with _lock:
        lst = _timestamps.get(str(user_id))
        if lst is None:
            lst = []
            _timestamps[str(user_id)] = lst

        # remove old timestamps
        while lst and lst[0] < window_start:
            lst.pop(0)

        if len(lst) >= RATE_LIMIT_SENDS:
            # not allowed
            return False, {
                "limit": RATE_LIMIT_SENDS,
                "window_seconds": RATE_LIMIT_WINDOW,
                "remaining": 0,
                "retry_after": int(RATE_LIMIT_WINDOW - (now - lst[0])) if lst else RATE_LIMIT_WINDOW,
            }

        # allow and record
        lst.append(now)
        return True, {
            "limit": RATE_LIMIT_SENDS,
            "window_seconds": RATE_LIMIT_WINDOW,
            "remaining": max(0, RATE_LIMIT_SENDS - len(lst)),
        }
