from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


_FMT = "[%(asctime)s] [%(levelname)-7s] %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


class RunLogger:
    """
    Per-email per-newsletter verbose file logger.

    Writes a structured run.log capturing every meaningful action:
    navigations, clicks, fills, waits, timings, retries, proxy info,
    CAPTCHA events, and final status.
    """

    def __init__(self, log_file: Path, email: str, newsletter: str) -> None:
        self.email = email
        self.newsletter = newsletter
        self.log_file = log_file
        self._logger = self._build(log_file, email, newsletter)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _build(log_file: Path, email: str, newsletter: str) -> logging.Logger:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        name = f"{email}::{newsletter}::{id(log_file)}"
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        logger.propagate = False

        fmt = logging.Formatter(_FMT, datefmt=_DATE_FMT)

        fh = logging.FileHandler(str(log_file), encoding="utf-8", mode="a")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        return logger

    # ------------------------------------------------------------------
    # Public API — thin wrappers that encode a consistent tag schema
    # ------------------------------------------------------------------

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def debug(self, msg: str) -> None:
        self._logger.debug(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)

    # -- Structured events --

    def banner(self, msg: str) -> None:
        sep = "=" * 60
        self._logger.info(sep)
        self._logger.info(f"  {msg}")
        self._logger.info(sep)

    def step(self, name: str, detail: str = "") -> None:
        line = f"[STEP] {name}"
        if detail:
            line += f"  |  {detail}"
        self._logger.info(line)

    def navigate(self, url: str) -> None:
        self._logger.info(f"[NAVIGATE] {url}")

    def click(self, selector: str, label: str = "") -> None:
        self._logger.debug(f"[CLICK]    selector={selector!r}  label={label!r}")

    def fill(self, selector: str, value: str, label: str = "") -> None:
        display = value if "@" not in value else value[:4] + "****"
        self._logger.debug(
            f"[FILL]     selector={selector!r}  value={display!r}  label={label!r}"
        )

    def wait(self, selector: str, timeout_ms: int = 0) -> None:
        self._logger.debug(
            f"[WAIT]     selector={selector!r}  timeout={timeout_ms}ms"
        )

    def timing(self, action: str, ms: float) -> None:
        self._logger.debug(f"[TIMING]   action={action!r}  elapsed={ms:.1f}ms")

    def proxy_info(self, proxy: str) -> None:
        host = proxy.rsplit("@", 1)[-1] if "@" in proxy else proxy
        self._logger.info(f"[PROXY]    host={host!r}")

    def retry(self, attempt: int, max_attempts: int, reason: str) -> None:
        self._logger.warning(
            f"[RETRY]    attempt={attempt}/{max_attempts}  reason={reason!r}"
        )

    def proxy_rotated(self, new_proxy: str) -> None:
        host = new_proxy.rsplit("@", 1)[-1] if "@" in new_proxy else new_proxy
        self._logger.warning(f"[PROXY_ROTATE]  new_host={host!r}")

    def captcha(self, url: str) -> None:
        self._logger.warning(f"[CAPTCHA]  detected at url={url!r}")

    def screenshot(self, path: str, reason: str) -> None:
        self._logger.info(f"[SCREENSHOT]  reason={reason!r}  path={path!r}")

    def success(self, detail: str = "") -> None:
        line = "[SUCCESS]  Subscription confirmed"
        if detail:
            line += f"  |  {detail}"
        self._logger.info(line)

    def failure(self, reason: str) -> None:
        self._logger.error(f"[FAILURE]  {reason}")

    def close(self) -> None:
        for handler in self._logger.handlers[:]:
            handler.flush()
            handler.close()
            self._logger.removeHandler(handler)
