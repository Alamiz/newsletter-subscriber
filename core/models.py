from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ERROR = "ERROR"
    CAPTCHA = "CAPTCHA"


@dataclass
class NewsletterResult:
    newsletter: str
    email: str
    status: Status
    proxy: str
    retry_count: int
    start_time: datetime
    end_time: datetime
    error_reason: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        return {
            "newsletter": self.newsletter,
            "email": self.email,
            "status": self.status.value,
            "proxy": self._masked_proxy(),
            "retry_count": self.retry_count,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": round(self.duration, 2),
            "error_reason": self.error_reason,
            "screenshots": self.screenshots,
        }

    def _masked_proxy(self) -> str:
        if "@" in self.proxy:
            return "***@" + self.proxy.rsplit("@", 1)[-1]
        return self.proxy


@dataclass
class EmailTask:
    email: str
    proxy: str
    newsletters: List[str]
    profile_path: str


class CaptchaDetected(Exception):
    """Raised by a handler when a CAPTCHA is detected."""


class ProxyError(Exception):
    """Raised when a proxy connection fails."""


class HandlerError(Exception):
    """Raised for handler-level subscription failures."""
