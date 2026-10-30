"""Apple + GoldenApple: spawn on a random free cell, drawing, urgency ring.

Drawing is the glow skin (Task 25): a magenta alpha halo + pulsing bright
core for the red apple; the golden apple keeps its gold colors, shrinking
body and countdown ring but gains the same halo/glow treatment. Spawn logic
and lifetime are untouched by the visual redesign.
"""

from __future__ import annotations

import math
import random

import pygame

from game.constants import (
    GOLDEN_LIFETIME_MS,
    GRID_SIZE,
    lerp_color,
)
from game.themes import get_theme
from game.ui import draw_glow_circle


def spawn_free_cell(occupied):
    """Pick a random cell not in `occupied`. None if the board is full."""
    taken = set(occupied)
    free = [
        (col, row)
        for col in range(GRID_SIZE)
        for row in range(GRID_SIZE)
        if (col, row) not in taken
    ]
    if not free:
        return None
    return random.choice(free)


def _pulse():
    """Shared heartbeat: 1.0 +/- 6%, matching the old sine pulse."""
    return 1.0 + 0.06 * math.sin(pygame.time.get_ticks() / 200.0)


class Apple:
    def __init__(self):
        self.pos = None

    def respawn(self, snake_body):
        """Pick a random free cell. Returns False if the board is full (win)."""
        self.pos = spawn_free_cell(snake_body)
        return self.pos is not None

    def draw(self, surface, origin_x, origin_y, cell):
        if self.pos is None or cell < 4:
            return
        theme = get_theme()
        col, row = self.pos
        cx = origin_x + col * cell + cell // 2
        cy = origin_y + row * cell + cell // 2
        pulse = _pulse()

        # Magenta glow halo (alpha circle), pulsing with the core.
        halo_r = max(3, int(cell * 0.9 * pulse))
        draw_glow_circle(surface, theme["apple"], (cx, cy), halo_r, alpha=70, grow=2)

        # Pulsing bright core + inner hot spot + shine dot.
        core_r = max(2, int(cell * 0.35 * pulse))
        inner = lerp_color(theme["apple"], (255, 255, 255), 0.45)
        try:
            pygame.draw.circle(surface, theme["apple"], (cx, cy), core_r)
            pygame.draw.circle(surface, inner, (cx, cy), max(1, int(core_r * 0.55)))
            shine_r = max(1, core_r // 4)
            pygame.draw.circle(
                surface, theme["apple_shine"],
                (cx - core_r // 3, cy - core_r // 3), shine_r,
            )
        except (ValueError, TypeError):
            pass


class GoldenApple:
    """Worth 5 points; lives GOLDEN_LIFETIME_MS, visibly shrinking with a ring."""

    def __init__(self, pos=None):
        self.pos = pos
        self.lifetime_ms = GOLDEN_LIFETIME_MS

    @property
    def urgency(self):
        """1.0 when fresh -> 0.0 when about to expire."""
        return max(0.0, min(1.0, self.lifetime_ms / GOLDEN_LIFETIME_MS))

    def update(self, dt):
        """Advance the lifetime (only while not paused). False = expired."""
        self.lifetime_ms -= float(dt)
        return self.lifetime_ms > 0.0

    def draw(self, surface, origin_x, origin_y, cell):
        if self.pos is None or cell < 4:
            return
        theme = get_theme()
        col, row = self.pos
        cx = origin_x + col * cell + cell // 2
        cy = origin_y + row * cell + cell // 2
        urgency = self.urgency
        pulse = _pulse()

        # Gold glow halo, tighter as the lifetime runs out.
        halo_r = max(3, int(cell * (0.45 + 0.45 * urgency) * pulse))
        draw_glow_circle(surface, theme["golden"], (cx, cy), halo_r, alpha=75, grow=2)

        # Shrinking body: visibly smaller as the lifetime runs out.
        core_r = max(2, int(cell * (0.17 + 0.22 * urgency) * pulse))
        inner = lerp_color(theme["golden"], (255, 255, 255), 0.4)
        try:
            pygame.draw.circle(
                surface, theme["golden_dark"], (cx, cy + max(1, cell // 12)), core_r
            )
            pygame.draw.circle(surface, theme["golden"], (cx, cy), core_r)
            pygame.draw.circle(surface, inner, (cx, cy), max(1, int(core_r * 0.55)))

            # Countdown ring: arc shrinks with remaining lifetime.
            ring_r = max(4, int(cell * 0.46))
            ring_rect = pygame.Rect(0, 0, ring_r * 2, ring_r * 2)
            ring_rect.center = (cx, cy)
            ring_w = max(1, cell // 12)
            if urgency > 0.01:
                pygame.draw.arc(
                    surface,
                    theme["golden"],
                    ring_rect,
                    -math.pi / 2.0,
                    -math.pi / 2.0 + 2.0 * math.pi * urgency,
                    ring_w,
                )

            # Sparkle.
            shine_r = max(1, core_r // 3)
            pygame.draw.circle(
                surface,
                theme["apple_shine"],
                (cx - core_r // 3, cy - core_r // 3),
                shine_r,
            )
        except (ValueError, TypeError):
            pass
