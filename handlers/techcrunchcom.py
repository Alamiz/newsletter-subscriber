"""
TechCrunch Newsletters subscription handler.

Flow:
1. Navigate to newsletters page
2. Click "Select All" button (button.force-small)
3. Sticky bottom bar appears — fill email input inside it
4. Click the first radio label in the form group
5. Click Subscribe button inside the form
6. Confirm: div[aria-labelledby="popupMessage"] appears
"""

from __future__ import annotations

import random

from utils.human import delay, post_load_pause, type_text

_URL = "https://techcrunch.com/newsletters/"

_SEL_SELECT_ALL  = "button.force-small"
_SEL_EMAIL       = 'input[type="email"]'
_SEL_RADIO_FIRST = "div.form-input__radio-group > label:nth-child(1)"
_SEL_SUBMIT      = "div.form-input button[type=\"submit\"]"
_SEL_SUCCESS     = 'div[aria-labelledby="popupMessage"]'
_SEL_COOKIE_ROOT   = "div.fc-consent-root"
_SEL_COOKIE_ACCEPT = "button.fc-cta-consent"


async def run(page, email: str, logger) -> None:
    # ------------------------------------------------------------------ #
    # 1. Navigate
    # ------------------------------------------------------------------ #
    logger.step("navigate", _URL)
    logger.navigate(_URL)
    await page.goto(_URL, wait_until="domcontentloaded", timeout=30_000)
    await post_load_pause(page)
    await _accept_cookies(page, logger)

    # ------------------------------------------------------------------ #
    # 2. Click "Select All"
    # ------------------------------------------------------------------ #
    logger.step("wait_select_all", _SEL_SELECT_ALL)
    logger.wait(_SEL_SELECT_ALL, 12_000)
    await page.wait_for_selector(_SEL_SELECT_ALL, timeout=12_000)

    logger.click(_SEL_SELECT_ALL, "Select All button")
    await page.hover(_SEL_SELECT_ALL)
    await delay(0.1, 0.3)
    await page.click(_SEL_SELECT_ALL)
    await delay(1.5, 3.0)

    # ------------------------------------------------------------------ #
    # 3. Fill email in sticky bar
    # ------------------------------------------------------------------ #
    logger.step("wait_email_input")
    logger.wait(_SEL_EMAIL, 12_000)
    await page.wait_for_selector(_SEL_EMAIL, timeout=12_000)

    logger.fill(_SEL_EMAIL, email, "email input in sticky bar")
    await page.click(_SEL_EMAIL)
    await delay(0.3, 0.8)
    await type_text(page, _SEL_EMAIL, email)
    await delay(0.8, 1.5)

    # ------------------------------------------------------------------ #
    # 4. Click first radio label
    # ------------------------------------------------------------------ #
    logger.step("click_radio", _SEL_RADIO_FIRST)
    logger.wait(_SEL_RADIO_FIRST, 8_000)
    await page.wait_for_selector(_SEL_RADIO_FIRST, timeout=8_000)

    logger.click(_SEL_RADIO_FIRST, "first radio option")
    await page.hover(_SEL_RADIO_FIRST)
    await delay(0.1, 0.3)
    await page.click(_SEL_RADIO_FIRST)
    await delay(0.5, 1.0)

    # ------------------------------------------------------------------ #
    # 5. Click Subscribe
    # ------------------------------------------------------------------ #
    logger.step("submit", _SEL_SUBMIT)
    logger.wait(_SEL_SUBMIT, 8_000)
    await page.wait_for_selector(_SEL_SUBMIT, timeout=8_000)

    logger.click(_SEL_SUBMIT, "Subscribe button in sticky bar")
    await page.hover(_SEL_SUBMIT)
    await delay(0.1, 0.3)
    await page.click(_SEL_SUBMIT)
    await delay(2.5, 5.0)

    # ------------------------------------------------------------------ #
    # 6. Confirm success
    # ------------------------------------------------------------------ #
    logger.step("check_success", _SEL_SUCCESS)
    logger.wait(_SEL_SUCCESS, 15_000)
    await page.wait_for_selector(_SEL_SUCCESS, timeout=15_000)
    logger.success("confirmation popup detected")


async def _accept_cookies(page, logger) -> None:
    try:
        await page.wait_for_selector(_SEL_COOKIE_ROOT, timeout=5_000)
        logger.step("cookie_dialog_found", _SEL_COOKIE_ROOT)
        await page.click(_SEL_COOKIE_ACCEPT)
        logger.click(_SEL_COOKIE_ACCEPT, "accept cookies")
        await page.wait_for_selector(_SEL_COOKIE_ROOT, state="hidden", timeout=5_000)
        logger.debug("cookie dialog dismissed")
    except Exception:
        logger.debug("no cookie dialog detected — continuing")
