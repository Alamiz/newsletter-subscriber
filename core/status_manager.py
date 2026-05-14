from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from core.models import Status


class StatusManager:
    """
    Thread-safe tracker for live CLI updates.

    Records per-newsletter status counts, which emails are currently
    active (and what they are doing), and a rolling event log.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._active: Dict[str, Dict] = {}
        self._events: List[Dict] = []
        self._emails_completed: int = 0
        self._max_events = 150

    # ------------------------------------------------------------------
    # Writers (called from worker threads)
    # ------------------------------------------------------------------

    def record(
        self,
        newsletter: str,
        email: str,
        status: Status,
        message: str = "",
    ) -> None:
        with self._lock:
            self._counts[newsletter][status.value] += 1
            self._events.append(
                {
                    "ts": datetime.now(),
                    "newsletter": newsletter,
                    "email": email,
                    "status": status,
                    "message": message,
                }
            )
            if len(self._events) > self._max_events:
                self._events.pop(0)

    def set_active(self, email: str, newsletter: str, step: str) -> None:
        with self._lock:
            self._active[email] = {
                "newsletter": newsletter,
                "step": step,
                "since": datetime.now(),
            }

    def clear_active(self, email: str) -> None:
        with self._lock:
            self._active.pop(email, None)
            self._emails_completed += 1

    # ------------------------------------------------------------------
    # Readers (called from the main CLI thread)
    # ------------------------------------------------------------------

    def get_snapshot(self) -> Dict:
        with self._lock:
            return {
                "counts": {k: dict(v) for k, v in self._counts.items()},
                "active": dict(self._active),
                "events": list(self._events[-25:]),
                "emails_completed": self._emails_completed,
            }

    def total_by_status(self, status: Status) -> int:
        with self._lock:
            return sum(
                v.get(status.value, 0) for v in self._counts.values()
            )

    def grand_total(self) -> int:
        with self._lock:
            return sum(
                sum(v.values()) for v in self._counts.values()
            )
