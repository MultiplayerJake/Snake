"""Fully procedural neon cyber-city background — no image files (Task 24).

Static layers (sky gradient, star field, three building layers with glowing
magenta/cyan window grids) render once into a cached Surface and are rebuilt
only when the screen size changes. Animated overlays — shooting light streaks
and flickering windows — draw on top of that cache every frame and are
skipped entirely under reduced_motion (accessibility).

Dim levels: menus/settings draw the city at DIM_MENUS (light), the play
screen at DIM_PLAY (heavy) so the 25x25 grid stays readable.
"""

from __future__ import annotations

import math
import random

import pygame

from game.constants import lerp_color
from game.themes import get_theme

# Overlay strength for the dim blit in draw(surface, dim=...).
DIM_MENUS = 110
DIM_PLAY = 200

STAR_COUNT = 120
LIT_RATIO = 0.6  # ~60% of window slots are lit
FLICKER_WINDOWS = 22  # windows eligible to flicker
MAX_STREAKS = 4
STREAK_MIN_MS = 1400.0
STREAK_MAX_MS = 3800.0
STREAK_LIFE_MS = (700.0, 1100.0)
FLICKER_MIN_MS = 500.0
FLICKER_MAX_MS = 2200.0
FLICKER_OFF_MS = (90.0, 380.0)

# Building layers, back -> front: (width frac range, height frac range,
# silhouette fill, roof edge color, window scale). Front layer is the
# largest/darkest per the spec.
_LAYERS = (
    ((0.030, 0.075), (0.16, 0.40), (26, 23, 62), (46, 42, 100), 1.0),
    ((0.040, 0.090), (0.13, 0.30), (19, 17, 48), (38, 35, 84), 1.3),
    ((0.055, 0.120), (0.10, 0.24), (11, 10, 28), (30, 28, 66), 1.7),
)

# (position, color) stops for the vertical sky gradient.
_SKY_STOPS = (
    (0.00, (6, 6, 20)),     # deep blue-purple top
    (0.45, (16, 14, 40)),
    (0.72, (54, 14, 62)),   # magenta-ish glow at the horizon
    (1.00, (20, 12, 44)),
)


class _Streak:
    """One shooting light streak: position, velocity (px/ms), life."""

    __slots__ = ("x", "y", "dx", "dy", "life_ms", "max_life_ms", "length")

    def __init__(self, x, y, dx, dy, speed, length, life_ms):
        self.x = float(x)
        self.y = float(y)
        self.dx = dx * speed
        self.dy = dy * speed
        self.length = float(length)
        self.life_ms = float(life_ms)
        self.max_life_ms = float(life_ms)


def _sky_color(t):
    """Sample the vertical sky gradient at 0..1."""
    stops = _SKY_STOPS
    t = max(0.0, min(1.0, float(t)))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1 or i == len(stops) - 2:
            span = t1 - t0
            k = 0.0 if span <= 0 else (t - t0) / span
            return lerp_color(c0, c1, max(0.0, min(1.0, k)))
    return stops[-1][1]


class CyberBackground:
    """Procedural neon skyline with cached static layers + animated overlays.

    `reduced_motion` disables streaks and window flicker; it can be flipped
    at runtime (screens sync it from settings every frame).
    """

    def __init__(self, w, h, reduced_motion=False, seed=None):
        self.reduced_motion = bool(reduced_motion)
        self.rng = random.Random(seed)
        self.streaks = []
        self.flicker_windows = []  # (x, y, size, color, fill) samples
        self.flicker_off = {}  # index -> ms left of darkness
        self._dims = {}  # alpha -> cached SRCALPHA dim surface
        self._overlay = None
        self.size = (0, 0)
        self.static = None
        self.build(w, h)

    # --- Static layer (built once, rebuilt on resize) -----------------------
    def build(self, w, h):
        w = max(40, int(w))
        h = max(40, int(h))
        rng = self.rng
        theme = get_theme()
        static = pygame.Surface((w, h))

        # Sky gradient.
        for y in range(h):
            pygame.draw.line(static, _sky_color(y / max(1, h - 1)), (0, y), (w, y))

        # Static star field over the upper 60%.
        star = theme["star"]
        for _ in range(STAR_COUNT):
            sx = rng.randrange(0, w)
            sy = rng.randrange(0, max(1, int(h * 0.6)))
            b = rng.randint(90, 220)
            color = (int(b * star[0] / 255), int(b * star[1] / 255), int(b * star[2] / 255))
            pygame.draw.circle(static, color, (sx, sy), 1 if rng.random() < 0.85 else 2)

        # Three building layers, back -> front, each with a window grid.
        window_cyan = theme["window_cyan"]
        window_magenta = theme["window_magenta"]
        lit = []
        for w_range, h_range, fill, edge, wscale in _LAYERS:
            x = -rng.randint(0, max(1, int(w * 0.05)))
            while x < w:
                bw = max(14, int(w * rng.uniform(*w_range)))
                bh = max(24, int(h * rng.uniform(*h_range)))
                top = h - bh
                pygame.draw.rect(static, fill, (x, top, bw, bh))
                pygame.draw.line(static, edge, (x, top), (x + bw - 1, top), 1)

                ws = max(2, int(2 * wscale) + rng.randrange(0, 2))
                y0 = top + ws * 2
                y1 = h - ws * 2
                x0 = x + ws * 2
                x1 = x + bw - ws * 2
                step_x = ws * 3
                step_y = ws * 4
                if x1 > x0 and y1 > y0:
                    for wy in range(y0, max(y0 + 1, y1), step_y):
                        for wx in range(x0, max(x0 + 1, x1), step_x):
                            if rng.random() > LIT_RATIO:
                                continue
                            base = window_cyan if rng.random() < 0.68 else window_magenta
                            level = rng.uniform(0.55, 1.0)
                            color = (
                                min(255, int(base[0] * level)),
                                min(255, int(base[1] * level)),
                                min(255, int(base[2] * level)),
                            )
                            pygame.draw.rect(static, color, (wx, wy, ws, ws))
                            lit.append((wx, wy, ws, color, fill))

                gap = rng.randint(2, max(6, int(w * 0.012)))
                x += bw + gap

        self.flicker_windows = rng.sample(lit, min(FLICKER_WINDOWS, len(lit)))
        self.static = static
        self._overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        self._dims = {}
        self.size = (w, h)
        # Animated state resets with the geometry.
        self.streaks = []
        self.flicker_off = {}
        self._streak_in = rng.uniform(STREAK_MIN_MS, STREAK_MAX_MS)
        self._flicker_in = rng.uniform(FLICKER_MIN_MS, FLICKER_MAX_MS)

    # --- Animated overlays --------------------------------------------------
    def _spawn_streak(self):
        rng = self.rng
        w, h = self.size
        dx = 1.0 if rng.random() < 0.5 else -1.0
        dy = rng.uniform(-0.45, 0.45)
        mag = math.hypot(dx, dy) or 1.0
        dx /= mag
        dy /= mag
        speed = rng.uniform(0.45, 0.95)  # px/ms
        length = rng.uniform(70.0, 160.0) * max(0.6, w / 1280.0)
        life = rng.uniform(*STREAK_LIFE_MS)
        self.streaks.append(
            _Streak(rng.uniform(0, w), rng.uniform(0, h * 0.55),
                    dx, dy, speed, length, life)
        )

    def update(self, dt):
        """Advance streaks + window flicker; no-op under reduced_motion."""
        dt = min(float(dt), 100.0)
        if self.reduced_motion:
            self.streaks = []
            self.flicker_off = {}
            return
        w, h = self.size

        self._streak_in -= dt
        if self._streak_in <= 0.0:
            self._streak_in = self.rng.uniform(STREAK_MIN_MS, STREAK_MAX_MS)
            if len(self.streaks) < MAX_STREAKS:
                self._spawn_streak()
        alive = []
        for streak in self.streaks:
            streak.x += streak.dx * dt
            streak.y += streak.dy * dt
            streak.life_ms -= dt
            if (streak.life_ms > 0.0 and -200.0 < streak.x < w + 200.0
                    and -200.0 < streak.y < h + 200.0):
                alive.append(streak)
        self.streaks = alive

        self._flicker_in -= dt
        if self._flicker_in <= 0.0:
            self._flicker_in = self.rng.uniform(FLICKER_MIN_MS, FLICKER_MAX_MS)
            if self.flicker_windows:
                idx = self.rng.randrange(len(self.flicker_windows))
                self.flicker_off[idx] = self.rng.uniform(*FLICKER_OFF_MS)
        for idx in list(self.flicker_off):
            self.flicker_off[idx] -= dt
            if self.flicker_off[idx] <= 0.0:
                del self.flicker_off[idx]

    def _draw_flicker(self, surface):
        """Paint currently-flickered windows dark (they return when done)."""
        windows = self.flicker_windows
        for idx in self.flicker_off:
            if not 0 <= idx < len(windows):
                continue
            x, y, size, _color, fill = windows[idx]
            pygame.draw.rect(surface, fill, (x, y, size, size))

    def _draw_streaks(self, surface):
        """Glowing trail + spark head via one reusable SRCALPHA overlay."""
        overlay = self._overlay
        if overlay is None:
            return
        overlay.fill((0, 0, 0, 0))
        cyan = get_theme()["neon_cyan"]
        drew = False
        for streak in self.streaks:
            ratio = streak.life_ms / max(1.0, streak.max_life_ms)
            fade = min(1.0, max(0.0, ratio) * 1.8)
            if fade <= 0.02:
                continue
            head = (int(streak.x), int(streak.y))
            tail = (int(streak.x - streak.dx * streak.length),
                    int(streak.y - streak.dy * streak.length))
            try:
                pygame.draw.line(overlay, (*cyan, int(46 * fade)), tail, head, 6)
                pygame.draw.line(overlay, (170, 240, 255, int(150 * fade)), tail, head, 3)
                pygame.draw.line(overlay, (255, 255, 255, int(240 * fade)), tail, head, 1)
                pygame.draw.circle(overlay, (*cyan, int(70 * fade)), head, 5)
                pygame.draw.circle(overlay, (255, 255, 255, int(240 * fade)), head, 2)
            except (ValueError, TypeError):
                continue
            drew = True
        if drew:
            surface.blit(overlay, (0, 0))

    # --- Draw ---------------------------------------------------------------
    def _dim_surface(self, alpha):
        alpha = max(0, min(255, int(alpha)))
        surf = self._dims.get(alpha)
        if surf is None:
            surf = pygame.Surface(self.size, pygame.SRCALPHA)
            surf.fill((*get_theme()["bg"], alpha))
            self._dims[alpha] = surf
        return surf

    def draw(self, surface, dim=0):
        """Blit the city (rebuilding if the surface resized) + dim overlay."""
        w, h = surface.get_size()
        if (w, h) != self.size:
            self.build(w, h)
        surface.blit(self.static, (0, 0))
        if not self.reduced_motion:
            self._draw_flicker(surface)
            if self.streaks:
                self._draw_streaks(surface)
        if dim > 0:
            surface.blit(self._dim_surface(dim), (0, 0))
