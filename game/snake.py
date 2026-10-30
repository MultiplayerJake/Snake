"""Snake: list of grid cells (head first), buffered turn, growth, drawing.

Logic stays on the fixed grid tick; rendering lerps between prev_body and
body using alpha = tick_accum / ticks_per_step for smooth movement.

Drawing is the "Cybork" skin (Task 25): neon cyan rounded segments with an
alpha-blended under-glow, a brighter head carrying a dark electronic visor
strip with a glowing slit, and a tiny magenta antenna node on the back corner.
"""

from __future__ import annotations

import pygame

from game.constants import (
    GRID_SIZE,
    VECTORS,
    lerp_color,
)
from game.themes import get_theme
from game.ui import draw_glow_circle, draw_glow_rect


class Snake:
    def __init__(self):
        mid = GRID_SIZE // 2
        self.body = [(mid, mid), (mid - 1, mid), (mid - 2, mid)]  # head first
        self.prev_body = list(self.body)  # snapshot for interpolation
        self.direction = VECTORS["right"]
        self.pending_dir = None  # exactly one buffered turn
        self.grow_by = 0

    def on_action(self, action):
        """Queue a turn; 180-degree reversals are ignored."""
        new = VECTORS.get(action)
        if new is None:
            return
        if new == (-self.direction[0], -self.direction[1]):
            return
        self.pending_dir = new

    def step(self):
        """Advance one grid step and return the new head cell."""
        self.prev_body = list(self.body)  # snapshot BEFORE the step
        if self.pending_dir is not None:
            self.direction = self.pending_dir
            self.pending_dir = None
        head_col, head_row = self.body[0]
        dx, dy = self.direction
        head = (head_col + dx, head_row + dy)
        self.body.insert(0, head)
        if self.grow_by > 0:
            self.grow_by -= 1
        else:
            self.body.pop()
        return head

    # --- Rendering -----------------------------------------------------------
    def interpolated_centers(self, origin_x, origin_y, cell, alpha=1.0):
        """Pixel center of each segment lerped from prev_body to body.

        The growing tail has no previous position; its index is clamped to
        len(prev_body) - 1 so the new segment slides out of the old tail.
        """
        alpha = max(0.0, min(1.0, float(alpha)))
        prev = self.prev_body if self.prev_body else self.body
        centers = []
        for i, (col, row) in enumerate(self.body):
            pcol, prow = prev[min(i, len(prev) - 1)]
            c = pcol + (col - pcol) * alpha
            r = prow + (row - prow) * alpha
            centers.append((origin_x + c * cell + cell // 2, origin_y + r * cell + cell // 2))
        return centers

    def _draw_head_details(self, surface, center, cell, direction):
        """Electronic visor strip + glowing antenna node (code-drawn only)."""
        theme = get_theme()
        cx, cy = center
        dx, dy = direction
        px, py = -dy, dx  # perpendicular unit

        # Dark visor strip across the head, perpendicular to travel, nudged
        # slightly forward; a thin bright slit runs inside it.
        fwd = int(round(cell * 0.12))
        half_len = max(2, int(round(cell * 0.30)))  # spans ~60% of the head
        half_w = max(2, int(round(cell * 0.14)))
        sx = cx + dx * fwd
        sy = cy + dy * fwd
        strip = [
            (sx + dx * half_w + px * half_len, sy + dy * half_w + py * half_len),
            (sx + dx * half_w - px * half_len, sy + dy * half_w - py * half_len),
            (sx - dx * half_w - px * half_len, sy - dy * half_w - py * half_len),
            (sx - dx * half_w + px * half_len, sy - dy * half_w + py * half_len),
        ]
        try:
            pygame.draw.polygon(surface, theme["eye"], [(int(a), int(b)) for a, b in strip])
            slit_half = max(1, int(round(cell * 0.21)))
            slit_w = max(1, cell // 12)
            pygame.draw.line(
                surface,
                theme["snake_head"],
                (int(sx - px * slit_half), int(sy - py * slit_half)),
                (int(sx + px * slit_half), int(sy + py * slit_half)),
                slit_w,
            )
        except (ValueError, TypeError):
            pass

        # Antenna node on the back corner: tiny stalk dot with a magenta glow.
        ax = cx - dx * int(round(cell * 0.30)) + px * int(round(cell * 0.30))
        ay = cy - dy * int(round(cell * 0.30)) + py * int(round(cell * 0.30))
        node_r = max(1, cell // 12)
        draw_glow_circle(surface, theme["neon_magenta"], (ax, ay),
                         node_r, alpha=90, grow=max(2, cell // 8))
        try:
            pygame.draw.circle(surface, theme["neon_magenta"], (int(ax), int(ay)), node_r)
            pygame.draw.circle(surface, (255, 214, 244), (int(ax), int(ay)), max(1, node_r // 2))
        except (ValueError, TypeError):
            pass

    def draw(self, surface, origin_x, origin_y, cell, alpha=1.0):
        if cell < 4 or not self.body:
            return
        theme = get_theme()
        inset = max(1, cell // 10)
        gap = max(3, cell // 4)  # connector width between segments
        count = len(self.body)
        centers = self.interpolated_centers(origin_x, origin_y, cell, alpha)

        def body_color(index):
            t = index / max(1, count - 1)
            return lerp_color(theme["snake_body"], theme["snake_tail"], t)

        radius = max(2, cell // 4)
        size = max(1, cell - 2 * inset)
        reach = cell * 1.6

        # 1) Glow pass (under everything): soft alpha halo under each
        #    connector and segment so nothing overlaps an already-lit body.
        for i in range(count - 1):
            x1, y1 = centers[i]
            x2, y2 = centers[i + 1]
            if abs(x2 - x1) > reach or abs(y2 - y1) > reach:
                continue
            conn = pygame.Rect(
                min(x1, x2) - gap // 2,
                min(y1, y2) - gap // 2,
                abs(x2 - x1) + gap,
                abs(y2 - y1) + gap,
            )
            draw_glow_rect(surface, body_color(i), conn, max(1, gap // 3),
                           alpha=55, grow=max(3, cell // 6))
        seg_rects = []
        for cx, cy in centers:
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (int(cx), int(cy))
            seg_rects.append(rect)
            draw_glow_rect(surface, theme["neon_cyan"], rect, radius,
                           alpha=70, grow=max(3, cell // 6))

        # 2) Connectors first so segment rounds overlap them nicely. Skip
        #    non-adjacent pairs (can happen when the head wraps in the demo).
        for i in range(count - 1):
            x1, y1 = centers[i]
            x2, y2 = centers[i + 1]
            if abs(x2 - x1) > reach or abs(y2 - y1) > reach:
                continue
            conn = pygame.Rect(
                min(x1, x2) - gap // 2,
                min(y1, y2) - gap // 2,
                abs(x2 - x1) + gap,
                abs(y2 - y1) + gap,
            )
            pygame.draw.rect(surface, body_color(i), conn, border_radius=max(1, gap // 3))

        # 3) Body segments (tail -> head so the head always sits on top).
        for i in range(count - 1, -1, -1):
            color = theme["snake_head"] if i == 0 else body_color(i)
            pygame.draw.rect(surface, color, seg_rects[i], border_radius=radius)

        # 4) Head electronics: visor + antenna over the bright head block.
        self._draw_head_details(surface, centers[0], cell, self.direction)
