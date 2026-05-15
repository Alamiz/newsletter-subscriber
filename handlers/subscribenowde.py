"""
subscribe-now.de newsletter subscription handler.

Flow:
1. Navigate to homepage
2. Locate the embedded Beehiiv iframe
3. Fill email + submit inside the iframe
4. Confirm success via div#root p inside the same iframe
"""

from __future__ import annotations

import random

from utils.human import delay, post_load_pause

_URL = "https://www.subscribe-now.de/"

_SEL_IFRAME   = 'iframe[src^="https://embeds.beehiiv.com"]'
_SEL_EMAIL    = 'input[type="email"]'
_SEL_SUBMIT   = 'button[type="submit"]'
_SEL_SUCCESS  = 'div#root p'


async def run(page, email: str, logger) -> None:
    # ------------------------------------------------------------------ #
    # 1. Navigate
    # ------------------------------------------------------------------ #
    logger.step("navigate", _URL)
    logger.navigate(_URL)
    await page.goto(_URL, wait_until="domcontentloaded", timeout=30_000)
    await post_load_pause(page)

    # ------------------------------------------------------------------ #
    # 2. Locate Beehiiv iframe and get a FrameLocator scoped to it
    # ------------------------------------------------------------------ #
    logger.step("locate_iframe", _SEL_IFRAME)
    logger.wait(_SEL_IFRAME, 15_000)
    await page.wait_for_selector(_SEL_IFRAME, timeout=15_000)
    logger.debug("iframe element present in DOM")

    frame = page.frame_locator(_SEL_IFRAME)

    # ------------------------------------------------------------------ #
    # 3. Wait for the email input inside the iframe
    # ------------------------------------------------------------------ #
    logger.step("wait_email_input")
    logger.wait(_SEL_EMAIL, 15_000)
    email_loc = frame.locator(_SEL_EMAIL)
    await email_loc.wait_for(timeout=15_000)
    logger.debug("email input found inside iframe")

    # ------------------------------------------------------------------ #
    # 4. Fill email with human-like typing
    # ------------------------------------------------------------------ #
    logger.fill(_SEL_EMAIL, email, "email input inside iframe")
    await email_loc.click()
    await delay(0.3, 0.8)

    for char in email:
        await email_loc.type(char, delay=random.uniform(70, 185))
        if random.random() < 0.04:
            await delay(0.1, 0.4)

    await delay(0.7, 1.8)

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
    logger.wait(_SEL_SUCCESS, 15_000)
    success_loc = frame.locator(_SEL_SUCCESS)
    await success_loc.wait_for(timeout=15_000)

    text = await success_loc.first.inner_text()
    logger.success(f"success text: {text!r}")
