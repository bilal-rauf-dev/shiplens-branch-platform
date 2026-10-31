"""Reproduce the mobile font-swap shift seen in Lighthouse's cold-cache run."""

import io
import json
import re
import time
from pathlib import Path

import pytest
from PIL import Image

pytestmark = pytest.mark.e2e


def test_mobile_font_swap_does_not_move_content(page, context, target_url, output_path):
    page.set_viewport_size({"width": 412, "height": 823})
    context.add_init_script("""window.fontLayoutShift = 0;
        new PerformanceObserver(list => {
            for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) window.fontLayoutShift += entry.value;
            }
        }).observe({type: 'layout-shift', buffered: true});""")

    def slow_heading_font(route):
        # The regular face is preloaded; delay heading weights to force a swap.
        time.sleep(0.7)
        route.continue_()

    page.route(re.compile(r"/fonts/roboto-(?:500|700)-latin\."), slow_heading_font)
    response = page.goto(f"{target_url}/en/", wait_until="networkidle")
    assert response.status == 200
    shift = page.evaluate("""async () => {
        await document.fonts.ready;
        await new Promise(resolve => requestAnimationFrame(() =>
            requestAnimationFrame(resolve)));
        return window.fontLayoutShift;
    }""")
    destination = Path(output_path) / "font-layout.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"layout_shift": shift}), encoding="utf-8")
    assert shift <= 0.1, f"Cold mobile font swap moved content: CLS={shift:.4f}"


def luminance(rgb):
    """WCAG relative luminance for rendered sRGB pixels."""
    channels = [value / 255 for value in rgb]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return sum(
        value * weight
        for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
    )


@pytest.mark.parametrize("language", ["en", "ur"])
@pytest.mark.parametrize("state", ["rest", "hover", "focus"])
def test_hero_outline_contrast(page, target_url, output_path, language, state):
    """Axe cannot sample pseudo-element gradients, so inspect their real pixels."""
    page.set_viewport_size({"width": 412, "height": 823})
    page.emulate_media(reduced_motion="reduce")
    page.goto(f"{target_url}/{language}/", wait_until="networkidle")
    button = page.locator(".hero .btn--outlined")
    button.scroll_into_view_if_needed()
    if state == "hover":
        button.hover()
    elif state == "focus":
        button.focus()
    box = button.evaluate("""node => {
        const color = getComputedStyle(node).color;
        // Hide glyph paint only; preserve geometry, backgrounds and state layers.
        node.style.webkitTextFillColor = 'transparent';
        const range = document.createRange(); range.selectNodeContents(node);
        const box = range.getBoundingClientRect();
        return {color, x:box.x, y:box.y, width:box.width, height:box.height};
    }""")
    foreground = luminance(tuple(map(int, re.findall(r"\d+", box.pop("color"))[:3])))
    try:
        screenshot = page.screenshot(clip=box)
    finally:
        button.evaluate("node => node.style.removeProperty('-webkit-text-fill-color')")
    pixels = set(Image.open(io.BytesIO(screenshot)).convert("RGB").get_flattened_data())
    contrast = min(
        (max(foreground, luminance(pixel)) + 0.05)
        / (min(foreground, luminance(pixel)) + 0.05)
        for pixel in pixels
    )
    destination = Path(output_path) / "hero-contrast.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"contrast": contrast}), encoding="utf-8")
    assert contrast >= 4.5, f"{language} {state}: contrast={contrast:.3f}:1"
