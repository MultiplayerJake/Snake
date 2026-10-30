"""Main menu screen: Play / Settings / Exit + animated demo AI snake.

Visuals (Tasks 24/26): the procedural neon skyline draws behind everything at
a light dim, the demo grid gets the neon frame, and the "QUICK SNAKE" title
uses GlitchTitle (occasional slice + magenta/cyan fringe glitch, disabled by
reduced_motion).
"""

from __future__ import annotations

import pygame

from game.ai import DemoSnake, grid_metrics
from game.background import DIM_MENUS, CyberBackground
from game.constants import (
    GRID_SIZE,
    format_time_ms,
)
from game.themes import get_theme
from game.ui import Button, GlitchTitle, draw_neon_frame, draw_text

DEMO_DIM_ALPHA = 100  # dim over the demo so buttons stay readable


class MainMenu:
    def __init__(self, settings, audio, stats, on_play, on_settings, on_exit):
        self.settings = settings
        self.audio = audio
        self.stats = stats
        self.on_play = on_play
        self.on_settings = on_settings
        self.on_exit = on_exit
        self._size = None
        self.demo = DemoSnake()  # AI snake plays behind the menu
        self.bg = None  # procedural cyber-city backdrop, built on first draw
        self.title = GlitchTitle(
            "QUICK SNAKE",
            reduced_motion=bool(settings.get("reduced_motion", False)),
        )
        # Rects are placeholders until the first draw() lays them out.
        self.play_btn = Button(pygame.Rect(0, 0, 1, 1), "PLAY", self._play, accent=True)
        self.settings_btn = Button(pygame.Rect(0, 0, 1, 1), "SETTINGS", self.on_settings)
        self.exit_btn = Button(pygame.Rect(0, 0, 1, 1), "EXIT", self.on_exit)
        self.buttons = [self.play_btn, self.settings_btn, self.exit_btn]

    def _play(self):
        self.on_play()

    def _reduced_motion(self):
        return bool(self.settings.get("reduced_motion", False))

    # --- Layout --------------------------------------------------------------
    def _layout(self, w, h):
        btn_w = max(200, min(int(w * 0.4), 440))
        btn_h = max(34, min(h // 14, 72))
        gap = max(10, btn_h // 2)
        start_y = int(h * 0.38)
        x = (w - btn_w) // 2
        y = start_y
        for button in self.buttons:
            button.rect = pygame.Rect(x, y, btn_w, btn_h)
            y += btn_h + gap

    # --- State API -----------------------------------------------------------
    def handle_event(self, event):
        # ESC does nothing on the menu (must use Exit).
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return
        for button in self.buttons:
            if button.handle_event(event):
                return

    def update(self, dt):
        # Runs only while the menu is the active screen -> demo pauses elsewhere.
        self.demo.update(dt)
        self.title.reduced_motion = self._reduced_motion()
        self.title.update(dt)
        if self.bg is not None:
            self.bg.reduced_motion = self._reduced_motion()
            self.bg.update(dt)

    def draw(self, surface):
        w, h = surface.get_size()
        if self._size != (w, h):
            self._layout(w, h)
            self._size = (w, h)
        theme = get_theme()

        # City backdrop first: light dim in menus (heavier behind the play grid).
        if self.bg is None or self.bg.size != (w, h):
            self.bg = CyberBackground(w, h, reduced_motion=self._reduced_motion())
        self.bg.reduced_motion = self._reduced_motion()
        self.bg.draw(surface, dim=DIM_MENUS)

        # Demo grid + snake, then a dim so the UI stays readable.
        cell, origin_x, hud_h = grid_metrics(w, h)
        grid_px = cell * GRID_SIZE
        for i in range(GRID_SIZE + 1):
            x = origin_x + i * cell
            pygame.draw.line(
                surface, theme["grid_line"], (x, hud_h), (x, hud_h + grid_px)
            )
            y = hud_h + i * cell
            pygame.draw.line(
                surface, theme["grid_line"], (origin_x, y), (origin_x + grid_px, y)
            )
        draw_neon_frame(surface, pygame.Rect(origin_x, hud_h, grid_px, grid_px))
        self.demo.draw(surface, origin_x, hud_h, cell)

        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((*theme["overlay_dim"], DEMO_DIM_ALPHA))
        surface.blit(dim, (0, 0))

        self.title.draw(
            surface,
            max(28, min(h // 8, 110)),
            theme["neon_cyan"],
            (w // 2, int(h * 0.16)),
        )
        draw_text(
            surface,
            "a speedy little snake",
            max(12, min(h // 40, 26)),
            theme["text_dim"],
            (w // 2, int(h * 0.26)),
            "center",
        )

        for button in self.buttons:
            button.draw(surface)

        # Bests (classic) + compact personal stats, dimmed, near the bottom.
        margin = max(12, h // 40)
        line_h = max(14, h // 45)
        bests = self.settings.get("bests", {}).get("classic", {})
        lines = []
        if bests.get("best_score"):
            lines.append("Best score: %d" % bests["best_score"])
        best_time = bests.get("best_time_ms")
        if best_time is not None:
            lines.append("Best time: %s" % format_time_ms(best_time))
        lines.append(
            "Games %d - Apples %d - Wins %d - Golden %d"
            % (
                self.stats.get("games_played", 0),
                self.stats.get("total_apples", 0),
                self.stats.get("wins", 0),
                self.stats.get("golden_apples", 0),
            )
        )
        y = h - margin - (len(lines) - 1) * line_h
        for line in lines:
            draw_text(surface, line, max(11, h // 50), theme["text_dim"], (w // 2, y), "center")
            y -= line_h
