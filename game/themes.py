"""Cyber palette: the single fixed color context for Quick Snake (Task 24).

The old Dark / Light / High Contrast themes are gone. get_theme() and
set_theme() always resolve to CYBER no matter which name is passed in, so
legacy settings.json "theme" values are harmless leftovers. Every draw path
(screen, widget, snake, apple, background) reads colors through get_theme(),
so there is one palette and zero hardcoded colors.

Palette: deep blue-purple night sky with magenta (#ff2ea6) + cyan (#00e5ff)
neon accents and glowing text.
"""

from __future__ import annotations

CYBER = {
    # --- City background --------------------------------------------------
    "bg": (10, 10, 26),
    "bg_city_dark": (16, 14, 40),
    "sky_top": (6, 6, 20),
    "sky_mid": (16, 14, 40),
    "sky_horizon": (54, 14, 62),  # magenta-ish glow at the horizon
    "building": (22, 20, 55),
    "building_edge": (40, 38, 90),
    "window_cyan": (0, 229, 255),
    "window_magenta": (255, 46, 166),
    "star": (176, 196, 255),
    # --- Neon accents -----------------------------------------------------
    "neon_cyan": (0, 229, 255),
    "neon_magenta": (255, 46, 166),
    # --- Surfaces / chrome ------------------------------------------------
    "hud_bg": (12, 12, 30),
    "panel": (14, 14, 34),
    "panel_border": (0, 110, 140),
    "grid_line": (30, 36, 74),
    "grid_width": 1,
    "button": (16, 16, 40),
    "button_hover": (26, 28, 62),
    "button_accent": (16, 54, 72),
    "button_accent_hover": (24, 80, 104),
    "slider_track": (38, 42, 80),
    "overlay_dim": (6, 6, 18),
    # --- Type -------------------------------------------------------------
    "text": (225, 245, 255),
    "text_dim": (132, 160, 205),
    "accent": (0, 229, 255),
    "accent_dark": (0, 150, 180),
    "danger": (255, 74, 110),
    "warning": (255, 196, 80),
    # --- Snake / apples ---------------------------------------------------
    "snake_head": (140, 250, 255),  # brighter Cybork head
    "snake_body": (0, 200, 235),
    "snake_tail": (0, 120, 150),
    "eye": (6, 8, 20),  # dark electronic visor strip on the head
    "apple": (255, 46, 166),
    "apple_dark": (150, 20, 95),
    "apple_shine": (255, 236, 250),
    "golden": (255, 210, 60),
    "golden_dark": (175, 135, 30),
}

# Single fixed palette: legacy theme names have no entry to switch to.
THEMES = {"cyber": CYBER}

_active = CYBER


def get_theme(name=None):
    """Always the Cyber palette; `name` is a ignored legacy argument."""
    return _active


def set_theme(name=None):
    """No-op kept for API compatibility: the palette is fixed to Cyber."""
    global _active
    _active = CYBER
    return _active
