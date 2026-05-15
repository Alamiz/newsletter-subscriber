"""
Bertelsmann newsletter subscription handler.

Flow:
1. Navigate to newsletter page (two subscribe forms present)
2. Fill the FIRST input[type="email"] with email
3. Click the FIRST [type="submit"] → opens a new tab
4. On the new tab: fill input[name="email"]
5. On the new tab: click button[type="submit"]
6. Check success: div.mce_text visible on the new tab
7. Screenshot on success
"""

from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path

from utils.human import delay, post_load_pause

_URL = "https://www.bertelsmann.com/en/media/newsletter/"

# -- First page (page 1) --
_SEL_P1_EMAIL  = 'input[type="email"]'
_SEL_P1_SUBMIT = 'input[type="submit"], button[type="submit"]'

# -- New tab (page 2) --
_SEL_P2_EMAIL   = 'input[name="email"]'
_SEL_P2_SUBMIT  = 'button[type="submit"]'
_SEL_P2_SUCCESS = 'div.mce_text'

_SEL_COOKIE_DIALOG = "div#CybotCookiebotDialog"
_SEL_COOKIE_ACCEPT = "button#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"


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
    # 2. Fill FIRST email input
    # ------------------------------------------------------------------ #
    logger.step("wait_first_email_input")
    logger.wait(_SEL_P1_EMAIL, 12_000)
    await page.wait_for_selector(_SEL_P1_EMAIL, timeout=12_000)

    first_email = page.locator(_SEL_P1_EMAIL).first
    logger.fill(_SEL_P1_EMAIL, email, "first email input (page 1)")
    await first_email.click()
    await delay(0.3, 0.9)

    for char in email:
        await first_email.type(char, delay=random.uniform(70, 185))
        if random.random() < 0.04:
            await delay(0.1, 0.4)

    await delay(0.8, 1.8)

    # ------------------------------------------------------------------ #
    # 3. Click FIRST submit — expect a new tab to open
    # ------------------------------------------------------------------ #
    logger.step("submit_page1")
    logger.click(_SEL_P1_SUBMIT, "first submit button (page 1) — expects new tab")

    first_submit = page.locator(_SEL_P1_SUBMIT).first
    await first_submit.wait_for(timeout=8_000)

    async with page.expect_popup() as popup_info:
        await first_submit.hover()
        await delay(0.1, 0.3)
        await first_submit.click()

    page2 = await popup_info.value
    logger.step("new_tab_opened", page2.url)
    logger.navigate(page2.url)

    await page2.wait_for_load_state("domcontentloaded", timeout=30_000)
    await post_load_pause(page2)

    # ------------------------------------------------------------------ #
    # 4. Fill email on new tab
    # ------------------------------------------------------------------ #
    logger.step("wait_email_input_page2")
    logger.wait(_SEL_P2_EMAIL, 12_000)
    await page2.wait_for_selector(_SEL_P2_EMAIL, timeout=12_000)

    logger.fill(_SEL_P2_EMAIL, email, "email input (page 2)")
    await page2.click(_SEL_P2_EMAIL)
    await delay(0.3, 0.9)

    for char in email:
        await page2.type(_SEL_P2_EMAIL, char, delay=random.uniform(70, 185))
        if random.random() < 0.04:
            await delay(0.1, 0.4)

    await delay(0.8, 1.8)

    # ------------------------------------------------------------------ #
    # 5. Submit on new tab
    # ------------------------------------------------------------------ #
    logger.step("submit_page2")
    logger.click(_SEL_P2_SUBMIT, "submit button (page 2)")
    await page2.hover(_SEL_P2_SUBMIT)
    await delay(0.1, 0.3)
    await page2.click(_SEL_P2_SUBMIT)
    await delay(2.5, 5.0)

    # ------------------------------------------------------------------ #
    # 6. Confirm success
    # ------------------------------------------------------------------ #
    logger.step("check_success", _SEL_P2_SUCCESS)
    logger.wait(_SEL_P2_SUCCESS, 15_000)
    await page2.wait_for_selector(_SEL_P2_SUCCESS, timeout=15_000)

    success_el = await page2.query_selector(_SEL_P2_SUCCESS)
    text = (await success_el.inner_text()).strip() if success_el else ""
    logger.success(f"success text: {text!r}")

    # ------------------------------------------------------------------ #
    # 7. Screenshot after success
    # ------------------------------------------------------------------ #
    safe_email = email.replace("@", "_at_").replace(".", "_dot_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ss_dir = Path("output") / "_screenshots" / "bertelsmanncom" / safe_email
    ss_dir.mkdir(parents=True, exist_ok=True)
    ss_path = str(ss_dir / f"success__{ts}.png")
    await page2.screenshot(path=ss_path, full_page=True)
    logger.screenshot(ss_path, "success")

    await page2.close()


async def _accept_cookies(page, logger) -> None:
    try:
        await page.wait_for_selector(_SEL_COOKIE_DIALOG, timeout=5_000)
        logger.step("cookie_dialog_found", _SEL_COOKIE_DIALOG)
        await page.click(_SEL_COOKIE_ACCEPT)
        logger.click(_SEL_COOKIE_ACCEPT, "accept all cookies")
        await page.wait_for_selector(_SEL_COOKIE_DIALOG, state="hidden", timeout=5_000)
        logger.debug("cookie dialog dismissed")
    except Exception:
        logger.debug("no cookie dialog detected — continuing")
