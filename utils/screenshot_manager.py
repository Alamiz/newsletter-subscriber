from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional


_TMP_BASE = Path("output") / "_screenshots"


class ScreenshotManager:
    """Captures full-page screenshots and returns the saved path."""

    @staticmethod
    async def capture(
        page,
        email: str,
        newsletter: str,
        reason: str,
        attempt: int = 0,
    ) -> Optional[str]:
        try:
            safe_email = (
                email
                .replace("@", "_at_")
                .replace(".", "_dot_")
            )
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_email}__{newsletter}__{reason}__a{attempt}__{ts}.png"
            dest = _TMP_BASE / newsletter / safe_email
            dest.mkdir(parents=True, exist_ok=True)
            path = dest / filename
            await page.screenshot(path=str(path), full_page=True)
            return str(path)
        except Exception:
            return None
