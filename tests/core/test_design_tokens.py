"""Verify every text pairing specified by the Material You light palette."""

import re
from pathlib import Path

import pytest

TOKENS = Path(__file__).resolve().parents[2] / "static/css/tokens.css"
COLORS = dict(re.findall(r"(--md-[\w-]+):\s*(#[0-9A-Fa-f]{6})", TOKENS.read_text()))

TEXT_PAIRS = [
    ("on-surface", "surface"),
    ("on-surface-variant", "surface"),
    ("on-surface-variant", "surface-container"),
    ("primary", "surface"),
    ("on-primary", "primary"),
    ("on-secondary-container", "secondary-container"),
    ("on-tertiary", "tertiary"),
    ("error", "surface"),
    ("on-error-container", "error-container"),
    ("on-success-container", "success-container"),
    ("on-warning-container", "warning-container"),
    ("on-info-container", "info-container"),
]

UI_BORDER_PAIRS = [
    ("outline", "surface"),
    ("outline", "surface-container-low"),
]


def luminance(color):
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return sum(
        channel * weight
        for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
    )


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("foreground,background", TEXT_PAIRS)
def test_md3_text_contrast(foreground, background):
    assert contrast(COLORS[f"--md-{foreground}"], COLORS[f"--md-{background}"]) >= 4.5


@pytest.mark.parametrize("foreground,background", UI_BORDER_PAIRS)
def test_md3_control_border_contrast(foreground, background):
    assert contrast(COLORS[f"--md-{foreground}"], COLORS[f"--md-{background}"]) >= 3
