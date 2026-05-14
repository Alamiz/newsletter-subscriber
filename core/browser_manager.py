from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


class BrowserManager:
    """
    Manages persistent browser profile paths and proxy configuration.

    One profile directory per email — created once, reused across all
    newsletters, deleted only after the email's worker finishes.
    """

    def __init__(self, profiles_dir: Path) -> None:
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Profile helpers
    # ------------------------------------------------------------------

    def get_profile_path(self, email: str) -> Path:
        safe = (
            email
            .replace("@", "_at_")
            .replace(".", "_dot_")
            .replace("+", "_plus_")
            .replace("-", "_dash_")
        )
        return self.profiles_dir / safe

    def ensure_profile(self, email: str) -> Path:
        path = self.get_profile_path(email)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def delete_profile(self, email: str) -> None:
        path = self.get_profile_path(email)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    # ------------------------------------------------------------------
    # Proxy helpers
    # ------------------------------------------------------------------

    @staticmethod
    def parse_proxy(proxy_str: str) -> Optional[dict]:
        """
        Parse 'user:pass@host:port' into a Playwright-compatible proxy dict.
        Returns None if the string is empty.
        """
        proxy_str = (proxy_str or "").strip()
        if not proxy_str:
            return None

        if "@" in proxy_str:
            credentials, host_port = proxy_str.rsplit("@", 1)
            if ":" in credentials:
                username, password = credentials.split(":", 1)
                return {
                    "server": f"http://{host_port}",
                    "username": username,
                    "password": password,
                }
            return {"server": f"http://{host_port}"}

        return {"server": f"http://{proxy_str}"}
