"""
BBC Newsletters subscription handler.

All interactive elements live inside:
    iframe[src^="https://session.bbc.com"]

Flow:
1. Navigate to newsletters page
2. Wait for the BBC session iframe to load
3. Randomly check 5 of the newsletter checkboxes
4. Fill email input
5. Click submit
6. Confirm: div[data-testid="iframe-magic-link-confirmation"] appears
"""

from __future__ import annotations

import random

from core.models import CaptchaDetected
from utils.human import delay, post_load_pause, type_text

_URL = "https://www.bbc.com/newsletters"

_SEL_IFRAME    = 'iframe[src^="https://session.bbc.com"]'
_SEL_CHECKBOX  = 'input[type="checkbox"]'
_SEL_EMAIL     = 'input[type="text"]'
_SEL_SUBMIT    = 'button[type="submit"]'
_SEL_SUCCESS   = 'div[data-testid="iframe-magic-link-confirmation"]'

_CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    "#cf-challenge-running",
    "iframe[title*='challenge']",
]

_NEWSLETTERS_TO_SELECT = 5


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
    # 2. Wait for BBC session iframe
    # ------------------------------------------------------------------ #
    logger.step("wait_iframe", _SEL_IFRAME)
    logger.wait(_SEL_IFRAME, 15_000)
    await page.wait_for_selector(_SEL_IFRAME, timeout=15_000)
    logger.debug("BBC session iframe present in DOM")

    frame = page.frame_locator(_SEL_IFRAME)

    # ------------------------------------------------------------------ #
    # 3. Randomly check 5 newsletter checkboxes
    # ------------------------------------------------------------------ #
    logger.step("wait_checkboxes")
    logger.wait(_SEL_CHECKBOX, 15_000)
    checkbox_loc = frame.locator(_SEL_CHECKBOX)
    await checkbox_loc.first.wait_for(timeout=15_000)

    all_checkboxes = await checkbox_loc.all()
    pick_count = min(_NEWSLETTERS_TO_SELECT, len(all_checkboxes))
    selected = random.sample(all_checkboxes, pick_count)
    logger.step(
        "select_newsletters",
        f"picking {pick_count} of {len(all_checkboxes)} checkboxes",
    )

    for i, cb in enumerate(selected):
        logger.click(_SEL_CHECKBOX, f"checkbox {i + 1}/{pick_count}")
        await cb.scroll_into_view_if_needed()
        await delay(0.3, 0.8)
        await cb.click()
        await delay(0.4, 1.0)

    await delay(0.8, 1.5)

    # ------------------------------------------------------------------ #
    # 4. Fill email
    # ------------------------------------------------------------------ #
    logger.step("fill_email")
    logger.wait(_SEL_EMAIL, 12_000)
    email_loc = frame.locator(_SEL_EMAIL)
    await email_loc.wait_for(timeout=12_000)

    logger.fill(_SEL_EMAIL, email, "email input inside iframe")
    await email_loc.click()
    await delay(0.3, 0.9)

    for char in email:
        await email_loc.type(char, delay=random.uniform(70, 185))
        if random.random() < 0.04:
            await delay(0.1, 0.4)

    await delay(0.8, 1.8)

    # ------------------------------------------------------------------ #
    # 5. Submit
    # ------------------------------------------------------------------ #
    logger.step("submit")
    logger.click(_SEL_SUBMIT, "submit button inside iframe")
    submit_loc = frame.locator(_SEL_SUBMIT)
    await submit_loc.wait_for(timeout=8_000)
    await submit_loc.hover()
    await delay(0.1, 0.3)
    await submit_loc.click()
    await delay(2.5, 5.0)

    # ------------------------------------------------------------------ #
    # 6. Confirm success
    # ------------------------------------------------------------------ #
    logger.step("check_success", _SEL_SUCCESS)
    logger.wait(_SEL_SUCCESS, 20_000)
    success_loc = frame.locator(_SEL_SUCCESS)
    await success_loc.wait_for(timeout=20_000)
    logger.success("magic-link confirmation screen detected")


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
