from __future__ import annotations

import threading
from typing import Dict, List, Optional


class ProxyManager:
    """
    Thread-safe proxy assignment and rotation.

    Each email is assigned a proxy on first access. If the proxy fails,
    rotate() advances the email to the next proxy in the pool.
    """

    def __init__(self, proxies: List[str]) -> None:
        self._proxies = proxies
        self._assignments: Dict[str, int] = {}
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        return len(self._proxies)

    @property
    def available(self) -> bool:
        return bool(self._proxies)

    def assign(self, email: str) -> Optional[str]:
        """Return the proxy assigned to *email*, creating one if needed."""
        with self._lock:
            if not self._proxies:
                return None
            if email not in self._assignments:
                idx = len(self._assignments) % len(self._proxies)
                self._assignments[email] = idx
            return self._proxies[self._assignments[email]]

    def rotate(self, email: str) -> Optional[str]:
        """Advance *email* to the next proxy and return it."""
        with self._lock:
            if not self._proxies:
                return None
            current = self._assignments.get(email, 0)
            next_idx = (current + 1) % len(self._proxies)
            self._assignments[email] = next_idx
            return self._proxies[next_idx]

    def get(self, email: str) -> Optional[str]:
        """Return currently-assigned proxy without changing assignment."""
        with self._lock:
            if not self._proxies:
                return None
            idx = self._assignments.get(email, 0)
            return self._proxies[idx]
