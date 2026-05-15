"""
Sinocism newsletter subscription handler.

Flow:
1. Navigate to homepage
2. Fill email input
3. Click Subscribe button
4. Click the free plan button
5. Confirm: div[data-testid="subscribe-confirm-email-screen"] appears
   (email confirmation is handled manually — stop here)
"""

from __future__ import annotations

from utils.human import delay, post_load_pause, type_text

_URL = "https://sinocism.com/"

_SEL_EMAIL  = 'input[type="email"][name="email"][placeholder="Type your email..."]'
_SEL_SUBMIT     = 'button[type="submit"]:has-text("Subscribe")'
_SEL_FREE_PLAN  = 'div.box.with-button:has(div.plan-info-container.free) button[type="submit"]'
_SEL_SUCCESS    = 'div[data-testid="subscribe-confirm-email-screen"]'


async def run(page, email: str, logger) -> None:
    # ------------------------------------------------------------------ #
    # 1. Navigate
    # ------------------------------------------------------------------ #
    logger.step("navigate", _URL)
    logger.navigate(_URL)
    await page.goto(_URL, wait_until="domcontentloaded", timeout=30_000)
    await post_load_pause(page)

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
    # 4. Click free plan button
    # ------------------------------------------------------------------ #
    logger.step("wait_free_plan_button")
    logger.wait(_SEL_FREE_PLAN, 15_000)
    await page.wait_for_selector(_SEL_FREE_PLAN, timeout=15_000)

    logger.click(_SEL_FREE_PLAN, "free plan submit button (double-click)")
    await page.hover(_SEL_FREE_PLAN)
    await delay(0.1, 0.3)
    await page.dblclick(_SEL_FREE_PLAN)
    await delay(2.0, 4.0)

    # ------------------------------------------------------------------ #
    # 5. Confirm email-confirm screen appeared
    # ------------------------------------------------------------------ #
    logger.step("check_success", _SEL_SUCCESS)
    logger.wait(_SEL_SUCCESS, 15_000)
    await page.wait_for_selector(_SEL_SUCCESS, timeout=15_000)
    logger.success("confirm-email screen detected")
