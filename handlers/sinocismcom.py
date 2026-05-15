"""
Sinocism newsletter subscription handler.

Flow:
1. Navigate to homepage
2. Fill email input
3. Click Subscribe button
4. Confirm submission: URL contains "/subscribe?" or a second subscribe
   screen appears — stop there (email confirmation is handled manually)
"""

from __future__ import annotations

import random

from core.models import CaptchaDetected
from utils.human import delay, post_load_pause, type_text

_URL = "https://sinocism.com/"

_SEL_EMAIL  = 'input[type="email"][name="email"][placeholder="Type your email..."]'
_SEL_SUBMIT = 'button[type="submit"]:has-text("Subscribe")'

_CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    "#cf-challenge-running",
    "iframe[title*='challenge']",
]


async def run(page, email: str, logger) -> None:
    # ------------------------------------------------------------------ #
    # 1. Navigate
    # ------------------------------------------------------------------ #
    logger.step("navigate", _URL)
    logger.navigate(_URL)
    await page.goto(_URL, wait_until="domcontentloaded", timeout=30_000)
    await post_load_pause(page)

    await _check_captcha(page, logger)

    # ------------------------------------------------------------------ #
    # 2. Fill email
    # ------------------------------------------------------------------ #
    logger.step("wait_email_input")
    logger.wait(_SEL_EMAIL, 12_000)
    await page.wait_for_selector(_SEL_EMAIL, timeout=12_000)

    logger.fill(_SEL_EMAIL, email, "email input")
    await page.click(_SEL_EMAIL)
    await delay(0.3, 0.9)
    await type_text(page, _SEL_EMAIL, email)
    await delay(0.8, 1.8)

    # ------------------------------------------------------------------ #
    # 3. Click Subscribe
    # ------------------------------------------------------------------ #
    logger.step("submit")
    logger.click(_SEL_SUBMIT, "Subscribe button")
    await page.hover(_SEL_SUBMIT)
    await delay(0.1, 0.3)
    await page.click(_SEL_SUBMIT)
    await delay(2.0, 4.0)

    # ------------------------------------------------------------------ #
    # 4. Confirm submission — URL redirect or second subscribe screen
    # ------------------------------------------------------------------ #
    logger.step("check_success")

    try:
        await page.wait_for_url("**/subscribe?**", timeout=12_000)
        logger.success(f"URL redirected to subscribe page: {page.url}")
        return
    except Exception:
        pass

    # Fallback: second subscribe input appeared on the same page
    try:
        await page.wait_for_selector(_SEL_EMAIL, timeout=6_000)
        logger.success("second subscribe screen appeared")
        return
    except Exception:
        pass

    raise Exception(
        f"No success indicator found after submit. Current URL: {page.url}"
    )


async def _check_captcha(page, logger) -> None:
    for sel in _CAPTCHA_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if el:
                logger.captcha(page.url)
                raise CaptchaDetected(page.url)
        except CaptchaDetected:
            raise
        except Exception:
            pass
