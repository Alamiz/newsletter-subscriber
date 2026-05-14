"""
CNN Newsletters subscription handler.

Flow:
1. Navigate to newsletters hub
2. Randomly click 5 newsletter cards to select them
3. Fill email input and click first submit button
4. Fill password input with a random password (logged) and click second submit
5. Confirm success: button[data-zjs-user-status="logged_in"] is visible
"""

from __future__ import annotations

import random
import secrets
import string

from core.models import CaptchaDetected
from utils.human import delay, move_and_click, post_load_pause, type_text

_URL = "https://edition.cnn.com/newsletters"

_SEL_CARD_BTN  = "button.newsletter-hub__button.newsletter-hub__button--card"
_SEL_EMAIL     = "input#newsletter-subscribe-email-input"
_SEL_PASSWORD  = "div.formfield-text__input-wrapper > input#reg-password-input"
_SEL_SUBMIT    = 'button[data-uri^="cms.cnn.com"][type="submit"]'
_SEL_SUCCESS   = 'button[data-zjs-user-status="logged_in"]'
_SEL_COOKIE_ACCEPT = "div#onetrust-button-group > button#onetrust-accept-btn-handler"

_CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    "#cf-challenge-running",
    "iframe[title*='challenge']",
]

_NEWSLETTERS_TO_SELECT = 5


def _random_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&"
    # Guarantee at least one of each required class
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&"),
    ]
    pwd += [secrets.choice(alphabet) for _ in range(length - len(pwd))]
    random.shuffle(pwd)
    return "".join(pwd)


async def run(page, email: str, logger) -> None:
    # ------------------------------------------------------------------ #
    # 1. Navigate
    # ------------------------------------------------------------------ #
    logger.step("navigate", _URL)
    logger.navigate(_URL)
    await page.goto(_URL, wait_until="domcontentloaded", timeout=30_000)
    await post_load_pause(page)

    await _check_captcha(page, logger)
    await _accept_cookies(page, logger)

    # ------------------------------------------------------------------ #
    # 2. Randomly select 5 newsletter cards
    # ------------------------------------------------------------------ #
    logger.step("wait_newsletter_cards")
    logger.wait(_SEL_CARD_BTN, 12_000)
    await page.wait_for_selector(_SEL_CARD_BTN, timeout=12_000)

    all_cards = await page.query_selector_all(_SEL_CARD_BTN)
    pick_count = min(_NEWSLETTERS_TO_SELECT, len(all_cards))
    selected = random.sample(all_cards, pick_count)
    logger.step("select_newsletters", f"picking {pick_count} of {len(all_cards)} cards")

    for i, card in enumerate(selected):
        logger.click(_SEL_CARD_BTN, f"newsletter card {i + 1}/{pick_count}")
        await card.scroll_into_view_if_needed()
        await delay(0.3, 0.7)
        await card.click()
        await delay(0.4, 1.0)

    await delay(0.8, 1.5)

    # ------------------------------------------------------------------ #
    # 3. Fill email
    # ------------------------------------------------------------------ #
    logger.step("fill_email")
    logger.wait(_SEL_EMAIL, 12_000)
    await page.wait_for_selector(_SEL_EMAIL, timeout=12_000)

    logger.fill(_SEL_EMAIL, email, "email input")
    await page.click(_SEL_EMAIL)
    await delay(0.3, 0.8)
    await type_text(page, _SEL_EMAIL, email)
    await delay(0.8, 1.5)

    # ------------------------------------------------------------------ #
    # 4. Click FIRST submit (email step)
    # ------------------------------------------------------------------ #
    logger.step("submit_email")
    submits = await page.query_selector_all(_SEL_SUBMIT)
    if not submits:
        raise Exception(f"No submit buttons found with selector: {_SEL_SUBMIT}")

    logger.click(_SEL_SUBMIT, f"first submit button ({len(submits)} found)")
    await submits[0].scroll_into_view_if_needed()
    await submits[0].hover()
    await delay(0.1, 0.3)
    await submits[0].click()
    await delay(2.0, 4.0)

    await _check_captcha(page, logger)

    # ------------------------------------------------------------------ #
    # 5. Fill password
    # ------------------------------------------------------------------ #
    logger.step("wait_password_field")
    logger.wait(_SEL_PASSWORD, 15_000)
    await page.wait_for_selector(_SEL_PASSWORD, timeout=15_000)

    password = _random_password()
    logger.info(f"[PASSWORD] generated={password!r}")
    logger.fill(_SEL_PASSWORD, "***", "password input")
    await page.click(_SEL_PASSWORD)
    await delay(0.3, 0.8)
    await type_text(page, _SEL_PASSWORD, password)
    await delay(0.8, 1.5)

    # ------------------------------------------------------------------ #
    # 6. Click SECOND submit (registration step)
    # ------------------------------------------------------------------ #
    logger.step("submit_registration")
    submits = await page.query_selector_all(_SEL_SUBMIT)
    if len(submits) < 2:
        raise Exception(
            f"Expected at least 2 submit buttons, found {len(submits)}"
        )

    logger.click(_SEL_SUBMIT, f"second submit button ({len(submits)} found)")
    await submits[1].scroll_into_view_if_needed()
    await submits[1].hover()
    await delay(0.1, 0.3)
    await submits[1].click()
    await delay(3.0, 6.0)

    # ------------------------------------------------------------------ #
    # 7. Confirm success
    # ------------------------------------------------------------------ #
    logger.step("check_success", _SEL_SUCCESS)
    logger.wait(_SEL_SUCCESS, 20_000)
    await page.wait_for_selector(_SEL_SUCCESS, timeout=20_000)
    logger.success("logged_in button found")


async def _accept_cookies(page, logger) -> None:
    try:
        await page.wait_for_selector(_SEL_COOKIE_ACCEPT, timeout=5_000)
        logger.step("cookie_dialog_found", _SEL_COOKIE_ACCEPT)
        await page.click(_SEL_COOKIE_ACCEPT)
        logger.click(_SEL_COOKIE_ACCEPT, "accept all cookies")
        await page.wait_for_selector(_SEL_COOKIE_ACCEPT, state="hidden", timeout=5_000)
        logger.debug("cookie dialog dismissed")
    except Exception:
        logger.debug("no cookie dialog detected — continuing")


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
