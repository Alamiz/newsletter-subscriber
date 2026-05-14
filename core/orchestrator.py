from __future__ import annotations

import asyncio
import importlib
import json
import random
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from camoufox.pkgman import get_path as _camoufox_exe
from playwright.async_api import async_playwright

from core.browser_manager import BrowserManager
from core.logger_system import RunLogger
from core.models import (
    CaptchaDetected,
    EmailTask,
    NewsletterResult,
    ProxyError,
    Status,
)
from core.proxy_manager import ProxyManager
from core.status_manager import StatusManager
from utils.output_manager import OutputManager
from utils.screenshot_manager import ScreenshotManager


_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds; multiplied by attempt number


class Orchestrator:
    """
    Top-level coordinator.

    Spawns one thread per email (up to *concurrency*). Each thread runs
    its own asyncio event loop and processes all newsletters sequentially
    using a single persistent browser profile.
    """

    def __init__(
        self,
        emails: List[str],
        proxies: List[str],
        newsletters: List[str],
        concurrency: int = 10,
        profiles_dir: Path = Path("profiles"),
        output_dir: Path = Path("output"),
        headless: bool = False,
        on_result: Optional[Callable[[NewsletterResult], None]] = None,
    ) -> None:
        self.emails = emails
        self.newsletters = newsletters
        self.concurrency = concurrency
        self.profiles_dir = profiles_dir
        self.output_dir = output_dir
        self.headless = headless
        self.on_result = on_result

        self.proxy_manager = ProxyManager(proxies)
        self.browser_manager = BrowserManager(profiles_dir)
        self.status_manager = StatusManager()
        self.output_manager = OutputManager(output_dir)

    # ------------------------------------------------------------------
    # Entry point (blocking, called from the main thread)
    # ------------------------------------------------------------------

    def run(self) -> List[NewsletterResult]:
        all_results: List[NewsletterResult] = []

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {}
            for email in self.emails:
                proxy = self.proxy_manager.assign(email) or ""
                profile_path = self.browser_manager.ensure_profile(email)
                task = EmailTask(
                    email=email,
                    proxy=proxy,
                    newsletters=list(self.newsletters),
                    profile_path=str(profile_path),
                )
                future = pool.submit(self._thread_worker, task)
                futures[future] = email

            for future in as_completed(futures):
                email = futures[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as exc:
                    pass  # worker-level error: already logged inside the thread

        return all_results

    # ------------------------------------------------------------------
    # Thread worker — runs its own event loop
    # ------------------------------------------------------------------

    def _thread_worker(self, task: EmailTask) -> List[NewsletterResult]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._process_email(task))
        finally:
            loop.close()
            # Profile deleted once every newsletter for this email is done
            self.browser_manager.delete_profile(task.email)
            self.status_manager.clear_active(task.email)

    # ------------------------------------------------------------------
    # Email-level coroutine
    # ------------------------------------------------------------------

    async def _process_email(self, task: EmailTask) -> List[NewsletterResult]:
        """
        Process all newsletters for one email.

        Each newsletter gets its own browser launch so that retries can
        cleanly restart with a fresh session (and optionally a new proxy)
        while still reusing the same persistent profile directory.
        """
        results: List[NewsletterResult] = []
        current_proxy = task.proxy

        self.status_manager.set_active(task.email, "-", "starting")

        # Resolve Camoufox binary path once per email worker
        try:
            camoufox_exe = str(_camoufox_exe())
        except Exception:
            camoufox_exe = None  # falls back to system Firefox

        async with async_playwright() as pw:
            for newsletter in task.newsletters:
                self.status_manager.set_active(task.email, newsletter, "queued")

                result = await self._process_newsletter(
                    pw=pw,
                    camoufox_exe=camoufox_exe,
                    email=task.email,
                    newsletter=newsletter,
                    profile_path=task.profile_path,
                    proxy=current_proxy,
                )

                # Carry forward any proxy rotation that occurred during retries
                current_proxy = result.proxy

                self.status_manager.record(newsletter, task.email, result.status)
                results.append(result)

                if self.on_result:
                    try:
                        self.on_result(result)
                    except Exception:
                        pass

                # Human-like pause between newsletters
                await asyncio.sleep(random.uniform(2.0, 5.0))

        return results

    # ------------------------------------------------------------------
    # Newsletter-level coroutine (with retry loop)
    # ------------------------------------------------------------------

    async def _process_newsletter(
        self,
        pw,
        camoufox_exe: Optional[str],
        email: str,
        newsletter: str,
        profile_path: str,
        proxy: str,
    ) -> NewsletterResult:
        start_time = datetime.now()
        current_proxy = proxy
        retry_count = 0
        screenshots: List[str] = []
        last_error: Optional[str] = None

        # Temp log file — moved to final location after status is known
        tmp_log = self.output_manager.get_tmp_log(email, newsletter)
        logger = RunLogger(tmp_log, email, newsletter)

        logger.banner(f"NEWSLETTER={newsletter}  EMAIL={email}")
        logger.proxy_info(current_proxy)

        handler = self._load_handler(newsletter, logger)
        if handler is None:
            end_time = datetime.now()
            result = NewsletterResult(
                newsletter=newsletter,
                email=email,
                status=Status.ERROR,
                proxy=current_proxy,
                retry_count=0,
                start_time=start_time,
                end_time=end_time,
                error_reason=f"Handler not found: handlers/{newsletter}.py",
            )
            logger.failure(result.error_reason)
            logger.close()
            await self._write_output(result, tmp_log, screenshots)
            return result

        final_status = Status.ERROR

        for attempt in range(_MAX_RETRIES + 1):
            if attempt > 0:
                retry_count = attempt
                delay = _RETRY_BASE_DELAY * attempt
                logger.retry(attempt, _MAX_RETRIES, last_error or "unknown error")
                await asyncio.sleep(delay)

                # Rotate proxy on every retry
                rotated = self.proxy_manager.rotate(email)
                if rotated and rotated != current_proxy:
                    current_proxy = rotated
                    logger.proxy_rotated(current_proxy)

            self.status_manager.set_active(
                email, newsletter, f"attempt {attempt + 1}/{_MAX_RETRIES + 1}"
            )

            t0 = time.perf_counter()
            proxy_config = BrowserManager.parse_proxy(current_proxy)

            try:
                launch_kwargs = dict(
                    headless=self.headless,
                    user_data_dir=profile_path,
                )
                if camoufox_exe:
                    launch_kwargs["executable_path"] = camoufox_exe
                if proxy_config:
                    launch_kwargs["proxy"] = proxy_config

                ctx = await pw.firefox.launch_persistent_context(**launch_kwargs)
                try:
                    page = await ctx.new_page()
                    logger.step("browser_launched", f"attempt={attempt + 1}")

                    try:
                        await handler.run(page, email, logger)

                        elapsed = (time.perf_counter() - t0) * 1000
                        logger.timing("handler_run", elapsed)

                        ss = await ScreenshotManager.capture(
                            page, email, newsletter, "success", attempt
                        )
                        if ss:
                            screenshots.append(ss)
                            logger.screenshot(ss, "success")

                        logger.success()
                        final_status = Status.SUCCESS
                        last_error = None

                    except CaptchaDetected as exc:
                        elapsed = (time.perf_counter() - t0) * 1000
                        logger.timing("handler_captcha", elapsed)
                        logger.captcha(str(exc))
                        ss = await ScreenshotManager.capture(
                            page, email, newsletter, "captcha", attempt
                        )
                        if ss:
                            screenshots.append(ss)
                            logger.screenshot(ss, "captcha")
                        final_status = Status.CAPTCHA
                        last_error = str(exc)

                    except Exception as exc:
                        elapsed = (time.perf_counter() - t0) * 1000
                        logger.timing("handler_error", elapsed)
                        raw_msg = str(exc)
                        last_error = raw_msg
                        logger.failure(raw_msg)

                        is_last = attempt >= _MAX_RETRIES
                        if is_last:
                            ss = await ScreenshotManager.capture(
                                page, email, newsletter, "failed", attempt
                            )
                            if ss:
                                screenshots.append(ss)
                                logger.screenshot(ss, "failed")
                            final_status = Status.FAILED

                        # Detect proxy failures for smarter rotation
                        if any(
                            kw in raw_msg.lower()
                            for kw in ("proxy", "tunnel", "socks", "407", "econnrefused")
                        ):
                            rotated = self.proxy_manager.rotate(email)
                            if rotated:
                                current_proxy = rotated
                                logger.proxy_rotated(current_proxy)

                    finally:
                        try:
                            await page.close()
                        except Exception:
                            pass

                finally:
                    try:
                        await ctx.close()
                    except Exception:
                        pass

            except Exception as outer:
                # Browser launch failed
                elapsed = (time.perf_counter() - t0) * 1000
                logger.timing("browser_launch_error", elapsed)
                raw_msg = str(outer)
                last_error = raw_msg
                logger.error(f"[BROWSER_LAUNCH] {raw_msg}")
                if attempt >= _MAX_RETRIES:
                    final_status = Status.ERROR

            if final_status in (Status.SUCCESS, Status.CAPTCHA):
                break

        end_time = datetime.now()
        result = NewsletterResult(
            newsletter=newsletter,
            email=email,
            status=final_status,
            proxy=current_proxy,
            retry_count=retry_count,
            start_time=start_time,
            end_time=end_time,
            error_reason=last_error,
            screenshots=screenshots,
        )

        logger.info(
            f"[DONE] status={final_status.value}  duration={result.duration:.1f}s"
        )
        logger.close()

        await self._write_output(result, tmp_log, screenshots)
        return result

    # ------------------------------------------------------------------
    # Output writer
    # ------------------------------------------------------------------

    async def _write_output(
        self,
        result: NewsletterResult,
        tmp_log: Path,
        screenshots: List[str],
    ) -> None:
        email_dir = self.output_manager.get_email_dir(
            result.newsletter, result.status, result.email
        )
        email_dir.mkdir(parents=True, exist_ok=True)

        # Move log
        if tmp_log.exists():
            shutil.move(str(tmp_log), str(email_dir / "run.log"))

        # Copy screenshots
        if screenshots:
            ss_dir = email_dir / "screenshots"
            ss_dir.mkdir(exist_ok=True)
            for ss_path in screenshots:
                src = Path(ss_path)
                if src.exists():
                    shutil.copy2(src, ss_dir / src.name)

        # Write metadata
        meta_path = email_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(result.to_dict(), fh, indent=2, default=str)

    # ------------------------------------------------------------------
    # Handler loader
    # ------------------------------------------------------------------

    def _load_handler(self, newsletter: str, logger: RunLogger):
        try:
            module = importlib.import_module(f"handlers.{newsletter}")
            if not hasattr(module, "run"):
                logger.error(
                    f"Handler handlers/{newsletter}.py has no 'run' function"
                )
                return None
            logger.step("handler_loaded", f"handlers/{newsletter}.py")
            return module
        except ModuleNotFoundError as exc:
            logger.error(f"Handler not found: handlers/{newsletter}.py  ({exc})")
            return None
        except Exception as exc:
            logger.error(f"Handler import error: handlers/{newsletter}.py  ({exc})")
            return None
