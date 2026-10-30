"""Load/save settings.json with merge-with-defaults (corrupt files never crash).

Phase 2: per-mode bests under "bests" (legacy flat best_score/best_time_ms
are migrated into bests.classic on load), settings.json.bak backup before
every write, and a reset_to_defaults() helper that keeps bests.
"""

from __future__ import annotations

import copy
import json
import os
import shutil

from game.constants import (
    DEFAULT_SETTINGS,
    DIFFICULTY_TICKS,
    MODES,
    NAME_TO_KEY,
    SETTINGS_PATH,
    TIME_ATTACK_SPECS,
)
from game.themes import THEMES

DISPLAY_MODES = ("borderless", "windowed")


def _deep_merge(defaults, data):
    """Return defaults overlaid with data, recursing into dicts."""
    result = copy.deepcopy(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _is_score(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _is_time(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def _migrate_legacy_bests(data):
    """Move old flat best_score/best_time_ms into bests.classic (one-time)."""
    if "best_score" not in data and "best_time_ms" not in data:
        return data
    bests = data.get("bests")
    if not isinstance(bests, dict):
        bests = {}
    classic = bests.get("classic")
    if not isinstance(classic, dict):
        classic = {}
    score = data.pop("best_score", None)
    best_time = data.pop("best_time_ms", None)
    if _is_score(score):
        classic["best_score"] = int(score)
    if _is_time(best_time):
        classic["best_time_ms"] = int(best_time)
    bests["classic"] = classic
    data["bests"] = bests
    return data


def _sanitize_bests(settings):
    """Coerce bests into the full per-mode structure."""
    bests = settings.get("bests")
    clean = copy.deepcopy(DEFAULT_SETTINGS["bests"])
    if not isinstance(bests, dict):
        settings["bests"] = clean
        return settings
    for mode in MODES:
        entry = bests.get(mode)
        if not isinstance(entry, dict):
            continue
        score = entry.get("best_score")
        best_time = entry.get("best_time_ms")
        clean[mode]["best_score"] = int(score) if _is_score(score) else 0
        clean[mode]["best_time_ms"] = int(best_time) if _is_time(best_time) else None
    # Time attack tracks the fastest clear per difficulty.
    by = bests.get("time_attack")
    by = by.get("by_difficulty") if isinstance(by, dict) else None
    if isinstance(by, dict):
        for level in TIME_ATTACK_SPECS:
            value = by.get(level)
            clean["time_attack"]["by_difficulty"][level] = (
                int(value) if _is_time(value) else None
            )
    settings["bests"] = clean
    return settings


def _sanitize(settings):
    """Coerce values to sane types so game code can trust the dict."""
    defaults = DEFAULT_SETTINGS

    # Keybinds: action -> portable string known to the key map, or None
    # for an unbound action (Task 22 — null must round-trip through JSON).
    keybinds = settings.get("keybinds")
    clean = {}
    if isinstance(keybinds, dict):
        for action, default_name in defaults["keybinds"].items():
            name = keybinds.get(action)
            if name is None:
                clean[action] = None  # explicitly unbound
            elif isinstance(name, str) and name in NAME_TO_KEY:
                clean[action] = name
            else:
                clean[action] = default_name
    else:
        clean = dict(defaults["keybinds"])
    settings["keybinds"] = clean

    # Volumes: floats in [0, 1].
    for key in ("music_volume", "sfx_volume"):
        value = settings.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            settings[key] = min(1.0, max(0.0, float(value)))
        else:
            settings[key] = float(defaults[key])

    # Booleans.
    for key in ("timer_enabled", "grid_lines", "reduced_motion"):
        value = settings.get(key)
        settings[key] = value if isinstance(value, bool) else bool(defaults[key])

    # Difficulty.
    difficulty = settings.get("difficulty")
    if difficulty not in DIFFICULTY_TICKS:
        difficulty = defaults["difficulty"]
    settings["difficulty"] = difficulty

    # Theme.
    theme = settings.get("theme")
    settings["theme"] = theme if theme in THEMES else defaults["theme"]

    # Display mode.
    display_mode = settings.get("display_mode")
    settings["display_mode"] = (
        display_mode if display_mode in DISPLAY_MODES else defaults["display_mode"]
    )

    # Music track: "Auto" or a file name found in music/ (checked at runtime).
    track = settings.get("current_track")
    settings["current_track"] = track if isinstance(track, str) and track else "Auto"

    # Last played mode.
    last_mode = settings.get("last_mode")
    settings["last_mode"] = last_mode if last_mode in MODES else defaults["last_mode"]

    # Per-mode bests (after legacy migration).
    return _sanitize_bests(settings)


def load_settings():
    """Load settings.json, merging missing keys from defaults. Never raises."""
    if not os.path.isfile(SETTINGS_PATH):
        return copy.deepcopy(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("settings.json root must be a JSON object")
    except Exception:
        return copy.deepcopy(DEFAULT_SETTINGS)
    data = _migrate_legacy_bests(data)
    return _sanitize(_deep_merge(DEFAULT_SETTINGS, data))


def save_settings(settings):
    """Back up any existing settings.json to .bak, then persist. Never raises."""
    try:
        if os.path.isfile(SETTINGS_PATH):
            try:
                shutil.copy2(SETTINGS_PATH, SETTINGS_PATH + ".bak")
            except OSError as exc:
                print("[settings] Could not write settings.json.bak: %s" % exc)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
    except OSError as exc:
        print("[settings] Could not save settings.json: %s" % exc)


def reset_to_defaults(settings):
    """Overwrite settings in place with defaults, keeping per-mode bests."""
    bests = settings.get("bests")
    defaults = copy.deepcopy(DEFAULT_SETTINGS)
    if isinstance(bests, dict):
        defaults["bests"] = copy.deepcopy(bests)
    settings.clear()
    settings.update(defaults)
    return settings
