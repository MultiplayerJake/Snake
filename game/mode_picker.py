"""Mode picker: choose Classic / Speedrun / Time Attack between menu and game.

Stores the chosen mode as settings["last_mode"] for quick replay; Speedrun
forces the timer ON regardless of the timer_enabled pref (handled in
PlayingState). Per-mode bests live under settings["bests"].
"""

from __future__ import annotations

import pygame

from game.background import DIM_MENUS, CyberBackground
from game.constants import (
    MODE_BLURBS,
    MODE_LABELS,
    MODES,
    format_time_ms,
)
from game.settings import save_settings
from game.themes import get_theme
from game.ui import Button, draw_neon_text, draw_text


class ModePicker:
    def __init__(self, settings, audio, on_start, on_back):
        self.settings = settings
        self.audio = audio
        self.on_start = on_start
        self.on_back = on_back
        self._size = None
        self.bg = None  # procedural cyber-city backdrop, built on first draw
        self.mode_buttons = [
            Button(
                pygame.Rect(0, 0, 1, 1),
                MODE_LABELS[mode],
                lambda mode=mode: self._start(mode),
                # Task 23: uniform style — last_mode is still stored, but it
                # no longer accents/highlights any button.
            )
            for mode in MODES
        ]
        self.buttons_by_mode = dict(zip(MODES, self.mode_buttons))
        self.back_btn = Button(pygame.Rect(0, 0, 1, 1), "BACK", self._back)

    def _start(self, mode):
        self.settings["last_mode"] = mode
        save_settings(self.settings)
        self.on_start(mode)

    def _back(self):
        self.on_back()

    def _best_line(self, mode):
        """Compact per-mode bests for the blurb under each button."""
        best = self.settings.get("bests", {}).get(mode, {})
        parts = []
        score = best.get("best_score", 0)
        if score:
            parts.append("best %d" % score)
        if mode == "time_attack":
            by = best.get("by_difficulty", {})
            clears = [
                "%s %s" % (level[:1].upper(), format_time_ms(ms))
                for level, ms in by.items()
                if ms is not None
            ]
            if clears:
                parts.append(" - ".join(clears))
        else:
            best_time = best.get("best_time_ms")
            if best_time is not None:
                parts.append("time %s" % format_time_ms(best_time))
        return "  -  ".join(parts) if parts else "no record yet"

    # --- Layout --------------------------------------------------------------
    def _layout(self, w, h):
        btn_w = max(220, min(int(w * 0.44), 480))
        btn_h = max(34, min(h // 14, 72))
        # Task 27: vertical gap grew by exactly +10px over the base gap;
        # still resolution-derived (scales with btn_h) and x stays centered.
        gap = max(18, btn_h) + 10
        start_y = int(h * 0.30)
        x = (w - btn_w) // 2
        y = start_y
        for button in self.mode_buttons:
            button.rect = pygame.Rect(x, y, btn_w, btn_h)
            y += btn_h + gap
        back_w = max(140, int(btn_w * 0.4))
        back_h = max(28, int(btn_h * 0.8))
        self.back_btn.rect = pygame.Rect(
            (w - back_w) // 2, h - back_h - max(14, h // 40), back_w, back_h
        )

    # --- State API -----------------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
            return
        for button in self.mode_buttons:
            if button.handle_event(event):
                return
        self.back_btn.handle_event(event)

    def update(self, dt):
        if self.bg is not None:
            self.bg.reduced_motion = bool(self.settings.get("reduced_motion", False))
            self.bg.update(dt)

    def draw(self, surface):
        w, h = surface.get_size()
        if self._size != (w, h):
            self._layout(w, h)
            self._size = (w, h)
        theme = get_theme()
        if self.bg is None or self.bg.size != (w, h):
            self.bg = CyberBackground(
                w, h, reduced_motion=bool(self.settings.get("reduced_motion", False))
            )
        self.bg.reduced_motion = bool(self.settings.get("reduced_motion", False))
        self.bg.draw(surface, dim=DIM_MENUS)

        draw_neon_text(
            surface,
            "SELECT MODE",
            max(24, min(h // 10, 72)),
            theme["neon_cyan"],
            (w // 2, int(h * 0.14)),
            "center",
        )

        blurb_size = max(11, min(self.mode_buttons[0].rect.h // 3, 20))
        for mode, button in zip(MODES, self.mode_buttons):
            button.draw(surface)
            y = button.rect.bottom + max(8, blurb_size)
            draw_text(
                surface,
                MODE_BLURBS[mode],
                blurb_size,
                theme["text_dim"],
                (button.rect.centerx, y),
                "center",
            )
            draw_text(
                surface,
                self._best_line(mode),
                blurb_size,
                theme["text_dim"],
                (button.rect.centerx, y + blurb_size * 2),
                "center",
            )

        draw_text(
            surface,
            "esc to go back",
            max(10, h // 60),
            theme["text_dim"],
            (w // 2, self.back_btn.rect.top - max(10, h // 60)),
            "center",
        )
        self.back_btn.draw(surface)
