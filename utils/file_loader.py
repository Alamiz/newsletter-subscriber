from __future__ import annotations

from pathlib import Path
from typing import List


def _load_lines(filepath: str | Path) -> List[str]:
    path = Path(filepath)
    if not path.exists():
        return []
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def load_emails(path: str = "emails.txt") -> List[str]:
    return _load_lines(path)


def load_proxies(path: str = "proxies.txt") -> List[str]:
    return _load_lines(path)


def load_newsletters(path: str = "newsletters.txt") -> List[str]:
    return _load_lines(path)
