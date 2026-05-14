"""
dr-dsgvo.de newsletter subscription handler.

Flow:
1. Navigate to newsletter page
2. Fill email into input[type="email"].mailpoet_text
3. Click input[type="submit"].mailpoet_submit
4. Confirm success: div.mailpoet_message > p.mailpoet_validate_success
   must be visible (no display:none)
"""

from __future__ import annotations

import random

from core.models import CaptchaDetected
from utils.human import delay, post_load_pause

_URL = "https://dr-dsgvo.de/newsletter/"

_SEL_EMAIL   = 'input[type="email"].mailpoet_text'
_SEL_SUBMIT  = 'input[type="submit"].mailpoet_submit'
_SEL_SUCCESS = 'div.mailpoet_message > p.mailpoet_validate_success'

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
    logger.debug("email input found")

    logger.fill(_SEL_EMAIL, email, "mailpoet email input")
    await page.click(_SEL_EMAIL)
    await delay(0.3, 0.9)

    for char in email:
        await page.type(_SEL_EMAIL, char, delay=random.uniform(70, 185))
        if random.random() < 0.04:
            await delay(0.1, 0.4)

    await delay(0.8, 1.8)

    # ------------------------------------------------------------------ #
    # 3. Submit
    # ------------------------------------------------------------------ #
    logger.step("submit")
    logger.click(_SEL_SUBMIT, "mailpoet submit button")
    await page.hover(_SEL_SUBMIT)
    await delay(0.1, 0.3)
    await page.click(_SEL_SUBMIT)
    await delay(2.0, 4.5)

    # ------------------------------------------------------------------ #
    # 4. Confirm success — element must be visible (not display:none)
    # ------------------------------------------------------------------ #
    logger.step("check_success", _SEL_SUCCESS)
    logger.wait(_SEL_SUCCESS + " [visible]", 15_000)

    success_loc = page.locator(_SEL_SUCCESS)
    await success_loc.wait_for(state="visible", timeout=15_000)

    text = await success_loc.inner_text()
    logger.success(f"success text: {text!r}")


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
