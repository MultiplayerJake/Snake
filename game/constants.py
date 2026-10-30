"""Shared constants for Quick Snake: grid size, defaults, key maps, modes.

Colors live in game/themes.py (single fixed "Cyber" palette);
draw code reads them through themes.get_theme().
"""

from __future__ import annotations

import os
import sys

import pygame

# --- Paths -------------------------------------------------------------------
# Task 31 (frozen path resolution): in a PyInstaller build, __file__ points
# into the temporary _MEIxxxx extraction dir (onefile) or the bundled app
# dir (onedir) — deriving paths from it would make settings.json/stats.dat
# vanish on exit and music//sfx/ resolve to a throwaway temp location. When
# frozen, everything runtime-writable must live NEXT TO THE EXE instead.
if getattr(sys, "frozen", False):  # PyInstaller onefile/onedir
    PROJECT_ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    # Dev mode: unchanged — __file__ is game/constants.py, so the parent of
    # its parent dir is the project root.
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.json")
MUSIC_DIR = os.path.join(PROJECT_ROOT, "music")
SFX_DIR = os.path.join(PROJECT_ROOT, "sfx")  # procedural WAVs (Task 28)

# --- Grid / timing -----------------------------------------------------------
GRID_SIZE = 25
FPS = 60

DIFFICULTY_TICKS = {"easy": 12, "medium": 9, "hard": 6}  # frames per move @60fps
DIFFICULTY_ORDER = ("easy", "medium", "hard")
DIFFICULTY_LABELS = {"easy": "EASY", "medium": "MEDIUM", "hard": "HARD"}

# --- Game modes --------------------------------------------------------------
MODE_PICKER = "mode_picker"
MODES = ("classic", "speedrun", "time_attack")
MODE_LABELS = {
    "classic": "CLASSIC",
    "speedrun": "SPEEDRUN",
    "time_attack": "TIME ATTACK",
}
MODE_BLURBS = {
    "classic": "walls kill - chase a high score",
    "speedrun": "hard speed, timer always on",
    "time_attack": "beat the clock - eat the target",
}

# --- Golden apple ------------------------------------------------------------
# Task 21: lifetime 8 s -> 5 s (apple visuals scale off remaining lifetime).
GOLDEN_LIFETIME_MS = 5000.0
GOLDEN_CHANCE = 0.15  # rolled when a red apple is eaten
GOLDEN_POINTS = 5

# --- Time Attack targets (scale with difficulty) -----------------------------
TIME_ATTACK_SPECS = {
    "easy": {"apples": 5, "seconds": 90},
    "medium": {"apples": 8, "seconds": 75},
    "hard": {"apples": 10, "seconds": 60},
}

# --- Screen states -----------------------------------------------------------
MENU = "menu"
SETTINGS = "settings"
PLAYING = "playing"
PAUSED = "paused"
GAME_OVER = "game_over"

# --- Directions --------------------------------------------------------------
VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
ACTIONS = ("up", "down", "left", "right")
ACTION_LABELS = {
    "up": "Move Up",
    "down": "Move Down",
    "left": "Move Left",
    "right": "Move Right",
}

# --- Defaults ----------------------------------------------------------------
DEFAULT_BESTS = {
    "classic": {"best_score": 0, "best_time_ms": None},
    "speedrun": {"best_score": 0, "best_time_ms": None},
    "time_attack": {
        "best_score": 0,
        "best_time_ms": None,
        # Fastest clear (elapsed ms at win) per difficulty.
        "by_difficulty": {"easy": None, "medium": None, "hard": None},
    },
}

DEFAULT_SETTINGS = {
    "keybinds": {"up": "w", "down": "s", "left": "a", "right": "d"},
    "music_volume": 0.5,
    "sfx_volume": 0.5,
    "timer_enabled": False,
    "grid_lines": True,
    "difficulty": "medium",
    # Legacy key (Task 24): the palette is fixed to Cyber, so any stored
    # value is ignored; the default is kept to avoid churning settings.json.
    "theme": "dark",
    "reduced_motion": False,
    "current_track": "Auto",
    "display_mode": "borderless",
    "last_mode": "classic",
    "bests": DEFAULT_BESTS,
}

# --- Key name <-> pygame key maps --------------------------------------------
# Keybinds are stored in settings.json as portable strings ("w", "up", ...).
_KEY_OVERRIDES = {
    pygame.K_ESCAPE: "esc",
    pygame.K_RETURN: "enter",
    pygame.K_KP_ENTER: "kpenter",
    pygame.K_SPACE: "space",
    pygame.K_TAB: "tab",
    pygame.K_BACKSPACE: "backspace",
    pygame.K_DELETE: "delete",
    pygame.K_INSERT: "insert",
    pygame.K_HOME: "home",
    pygame.K_END: "end",
    pygame.K_PAGEUP: "pgup",
    pygame.K_PAGEDOWN: "pgdn",
    pygame.K_UP: "up",
    pygame.K_DOWN: "down",
    pygame.K_LEFT: "left",
    pygame.K_RIGHT: "right",
    pygame.K_LSHIFT: "lshift",
    pygame.K_RSHIFT: "rshift",
    pygame.K_LCTRL: "lctrl",
    pygame.K_RCTRL: "rctrl",
    pygame.K_LALT: "lalt",
    pygame.K_RALT: "ralt",
    pygame.K_MINUS: "-",
    pygame.K_EQUALS: "=",
    pygame.K_COMMA: ",",
    pygame.K_PERIOD: ".",
    pygame.K_SLASH: "/",
    pygame.K_SEMICOLON: ";",
    pygame.K_QUOTE: "'",
    pygame.K_LEFTBRACKET: "[",
    pygame.K_RIGHTBRACKET: "]",
    pygame.K_BACKSLASH: "\\",
}


def _build_key_maps():
    """Build name->key and key->name maps from pygame's K_* constants."""
    name_to_key = {}
    key_to_name = {}
    for attr in dir(pygame):
        if not attr.startswith("K_"):
            continue
        key = getattr(pygame, attr)
        if not isinstance(key, int) or key < 0:
            continue
        name = attr[2:].lower()
        if key not in key_to_name:
            key_to_name[key] = name
            name_to_key[name] = key
    for key, label in _KEY_OVERRIDES.items():
        old = key_to_name.get(key)
        if old is not None and name_to_key.get(old) == key:
            del name_to_key[old]
        key_to_name[key] = label
        name_to_key[label] = key
    return name_to_key, key_to_name


NAME_TO_KEY, KEY_TO_NAME = _build_key_maps()


def key_name(key):
    """Portable string name for a pygame key code."""
    return KEY_TO_NAME.get(key, "key%d" % key)


def key_label(key):
    """Short display label for a pygame key code (e.g. K_w -> 'W')."""
    name = key_name(key)
    if name.startswith("key"):
        return name
    return name.upper()


def lerp_color(a, b, t):
    """Linearly interpolate between two RGB colors."""
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def format_time_ms(ms):
    """Format milliseconds as mm:ss.mmm."""
    total = max(0, int(ms))
    minutes, rest = divmod(total, 60000)
    seconds, millis = divmod(rest, 1000)
    return "%02d:%02d.%03d" % (minutes, seconds, millis)
