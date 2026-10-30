"""Personal lifetime stats in stats.dat: JSON serialized then base64-encoded.

stats.dat holds *lifetime aggregates* (how much you have played overall);
settings.json keeps *per-run bests*. Keep the two separate, mirroring the
settings.py patterns: every read/write is wrapped in try/except and falls
back to defaults on any error.
"""

from __future__ import annotations

import base64
import copy
import json
import os

from game.constants import PROJECT_ROOT

STATS_PATH = os.path.join(PROJECT_ROOT, "stats.dat")

STATS_DEFAULTS = {
    "games_played": 0,
    "total_apples": 0,
    "total_score": 0,
    "total_playtime_ms": 0,
    "total_deaths": 0,
    "wins": 0,
    "golden_apples": 0,
}


def _sanitize(stats):
    """Coerce every field to a non-negative int so game code can trust it."""
    clean = {}
    for key, default in STATS_DEFAULTS.items():
        value = stats.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
            clean[key] = int(value)
        else:
            clean[key] = int(default)
    return clean


def load_stats():
    """Load stats.dat (base64 JSON). Never raises; defaults on any error."""
    try:
        with open(STATS_PATH, "r", encoding="ascii") as handle:
            raw = base64.b64decode(handle.read().encode("ascii"), validate=True)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("stats.dat root must be a JSON object")
        merged = copy.deepcopy(STATS_DEFAULTS)
        merged.update(data)
        return _sanitize(merged)
    except Exception:
        return copy.deepcopy(STATS_DEFAULTS)


def save_stats(stats):
    """Persist stats.dat as base64-encoded JSON. Prints (never raises) on failure."""
    try:
        payload = json.dumps(_sanitize(stats)).encode("utf-8")
        with open(STATS_PATH, "w", encoding="ascii") as handle:
            handle.write(base64.b64encode(payload).decode("ascii"))
    except OSError as exc:
        print("[stats] Could not save stats.dat: %s" % exc)


def record_result(stats, score, apples, playtime_ms, won, golden_apples=0):
    """Apply one finished run to the stats dict (caller saves afterwards)."""
    stats["games_played"] += 1
    stats["total_apples"] += max(0, int(apples))
    stats["total_score"] += max(0, int(score))
    stats["total_playtime_ms"] += max(0, int(playtime_ms))
    stats["golden_apples"] += max(0, int(golden_apples))
    if won:
        stats["wins"] += 1
    else:
        stats["total_deaths"] += 1
    return stats
