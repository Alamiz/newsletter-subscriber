from __future__ import annotations

import asyncio
import random


async def delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """Random pause that mimics human think-time."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def type_text(page, selector: str, text: str) -> None:
    """Type text character-by-character with randomised inter-key timing."""
    for char in text:
        await page.type(selector, char, delay=random.uniform(70, 190))
        if random.random() < 0.04:
            await asyncio.sleep(random.uniform(0.15, 0.55))


async def move_and_click(page, selector: str) -> None:
    """Hover then click to simulate natural mouse movement."""
    await page.hover(selector)
    await asyncio.sleep(random.uniform(0.1, 0.4))
    await page.click(selector)


async def scroll_natural(page, distance: int = 300) -> None:
    jitter = random.randint(-40, 40)
    await page.evaluate(f"window.scrollBy(0, {distance + jitter})")
    await delay(0.4, 1.2)


async def post_load_pause(page) -> None:
    """Wait for network to settle after navigation, then add human pause."""
    try:
        await page.wait_for_load_state("networkidle", timeout=8_000)
    except Exception:
        pass
    await delay(1.5, 3.5)
