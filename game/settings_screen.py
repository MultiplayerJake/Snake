"""Settings screen: keybinds, volumes, toggles, difficulty, display,
music track picker, reduced motion, reset-to-defaults. Saves immediately.

Task 24: the theme CycleRow is gone — the palette is the fixed Cyber theme,
so settings only carries display/track rows. A lightly dimmed procedural
city draws behind the rows.
"""

from __future__ import annotations

import pygame

from game.background import DIM_MENUS, CyberBackground
from game.constants import (
    ACTIONS,
    DIFFICULTY_LABELS,
    DIFFICULTY_ORDER,
)
from game.settings import DISPLAY_MODES, reset_to_defaults, save_settings
from game.themes import get_theme, set_theme
from game.ui import Button, CycleRow, KeyBindRow, Slider, Toggle, UnbindButton, draw_neon_text, draw_text

DISPLAY_LABELS = {"borderless": "BORDERLESS", "windowed": "WINDOWED"}
NO_TRACKS = "no tracks found"


class SettingsScreen:
    def __init__(self, settings, audio, on_back, on_display_change=None):
        self.settings = settings
        self.audio = audio
        self.on_back = on_back
        self.on_display_change = on_display_change
        self._size = None
        self._scroll = 0
        self._content_h = 0
        self._max_scroll = 0
        self._content_top = 0
        self._content_bottom = 0
        self._reset_confirm = False
        self.bg = None  # procedural cyber-city backdrop, built on first draw

        keybinds = settings["keybinds"]
        self.bind_rows = {
            action: KeyBindRow(
                pygame.Rect(0, 0, 1, 1), action, keybinds[action], self._rebind
            )
            for action in ACTIONS
        }
        # Task 22: small bin-icon button right of each row -> binding = None.
        self.unbind_buttons = {
            action: UnbindButton(
                pygame.Rect(0, 0, 1, 1), action, self._unbind
            )
            for action in ACTIONS
        }

        self.music_slider = Slider(
            pygame.Rect(0, 0, 1, 1),
            settings["music_volume"],
            on_change=self._music_volume,
            on_commit=self._save,
        )
        self.sfx_slider = Slider(
            pygame.Rect(0, 0, 1, 1),
            settings["sfx_volume"],
            on_change=self._sfx_volume,
            on_commit=self._save,
        )
        self.timer_toggle = Toggle(
            pygame.Rect(0, 0, 1, 1),
            "Speedrun timer",
            settings["timer_enabled"],
            self._timer_changed,
        )
        self.grid_toggle = Toggle(
            pygame.Rect(0, 0, 1, 1),
            "Grid lines",
            settings["grid_lines"],
            self._grid_changed,
        )
        self.motion_toggle = Toggle(
            pygame.Rect(0, 0, 1, 1),
            "Reduced motion (no shake/particles)",
            settings.get("reduced_motion", False),
            self._motion_changed,
        )
        self.difficulty_buttons = [
            Button(
                pygame.Rect(0, 0, 1, 1),
                DIFFICULTY_LABELS[level],
                lambda level=level: self._set_difficulty(level),
            )
            for level in DIFFICULTY_ORDER
        ]
        self.display_row = CycleRow(
            pygame.Rect(0, 0, 1, 1),
            "Display mode",
            lambda: self._cycle_display(-1),
            lambda: self._cycle_display(1),
        )
        self.track_row = CycleRow(
            pygame.Rect(0, 0, 1, 1),
            "Music track",
            lambda: self._cycle_track(-1),
            lambda: self._cycle_track(1),
        )
        self.back_btn = Button(pygame.Rect(0, 0, 1, 1), "BACK", self._back)
        self.reset_btn = Button(
            pygame.Rect(0, 0, 1, 1), "RESET TO DEFAULTS", self._reset_clicked
        )

    # --- Change handlers (persist immediately) --------------------------------
    def _save(self):
        save_settings(self.settings)

    def _rebind(self, action, new_name):
        keybinds = self.settings["keybinds"]
        old_name = keybinds[action]
        # Conflict: swap the other action's binding with this action's old key.
        # old_name may be None (unbound) — the other slot simply becomes unbound.
        for other, name in keybinds.items():
            if other != action and name == new_name:
                keybinds[other] = old_name
                self.bind_rows[other].keyname = old_name
        keybinds[action] = new_name
        self.bind_rows[action].keyname = new_name
        self._save()

    def _unbind(self, action):
        """Task 22: clear the binding (None) and persist immediately."""
        self.settings["keybinds"][action] = None
        row = self.bind_rows[action]
        row.keyname = None
        row.waiting = False
        row.armed = False
        row.warning = ""
        self._save()

    def _music_volume(self, value):
        self.settings["music_volume"] = value
        self.audio.set_music_volume(value)

    def _sfx_volume(self, value):
        self.settings["sfx_volume"] = value
        self.audio.set_sfx_volume(value)

    def _timer_changed(self, value):
        self.settings["timer_enabled"] = value
        self._save()

    def _grid_changed(self, value):
        self.settings["grid_lines"] = value
        self._save()

    def _motion_changed(self, value):
        self.settings["reduced_motion"] = value
        self._save()

    def _set_difficulty(self, level):
        self.settings["difficulty"] = level
        self._save()

    def _cycle_display(self, direction):
        mode = self.settings.get("display_mode", "borderless")
        index = DISPLAY_MODES.index(mode) if mode in DISPLAY_MODES else 0
        new_mode = DISPLAY_MODES[(index + direction) % len(DISPLAY_MODES)]
        self.settings["display_mode"] = new_mode
        if self.on_display_change is not None:
            self.on_display_change(new_mode)  # recreate the window immediately
        self._save()

    def _track_options(self):
        return ["Auto"] + list(self.audio.scan_tracks())

    def _cycle_track(self, direction):
        options = self._track_options()
        if len(options) <= 1:
            return  # music/ is empty: nothing to cycle
        current = self.settings.get("current_track", "Auto")
        index = options.index(current) if current in options else 0
        name = options[(index + direction) % len(options)]
        self.audio.select_track(name, self.settings)  # loops immediately
        self._save()

    # --- Reset to defaults (click twice to confirm) ---------------------------
    def _reset_clicked(self):
        if not self._reset_confirm:
            self._reset_confirm = True
            self.reset_btn.label = "ARE YOU SURE? (CLICK AGAIN)"
            return
        self._reset_confirm = False
        self.reset_btn.label = "RESET TO DEFAULTS"
        reset_to_defaults(self.settings)  # keeps bests
        self._save()
        # Refresh widgets + live state from the reset values.
        for action in ACTIONS:
            self.bind_rows[action].keyname = self.settings["keybinds"][action]
            self.bind_rows[action].waiting = False
            self.bind_rows[action].armed = False
            self.bind_rows[action].warning = ""
        self.music_slider.value = self.settings["music_volume"]
        self.sfx_slider.value = self.settings["sfx_volume"]
        self.timer_toggle.value = self.settings["timer_enabled"]
        self.grid_toggle.value = self.settings["grid_lines"]
        self.motion_toggle.value = self.settings["reduced_motion"]
        self.audio.set_music_volume(self.settings["music_volume"])
        self.audio.set_sfx_volume(self.settings["sfx_volume"])
        self.audio.select_track(self.settings["current_track"], self.settings)
        set_theme(self.settings["theme"])
        if self.on_display_change is not None:
            self.on_display_change(self.settings["display_mode"])

    def _back(self):
        self._save()
        self.on_back()

    # --- Layout (scrollable content area) -------------------------------------
    def _layout(self, w, h):
        content_w = min(w - 40, max(360, int(h * 1.0)))
        x0 = (w - content_w) // 2
        row_h = max(24, min(46, h // 20))
        gap = max(5, row_h // 5)
        y_start = int(h * 0.13)
        y = y_start - self._scroll

        key_h = max(20, int(row_h * 0.8))
        unbind_gap = max(4, key_h // 5)
        for action in ACTIONS:
            # Row shrinks to leave a square bin-icon button at its right.
            self.bind_rows[action].rect = pygame.Rect(
                x0, y, content_w - key_h - unbind_gap, key_h
            )
            self.unbind_buttons[action].rect = pygame.Rect(
                x0 + content_w - key_h, y, key_h, key_h
            )
            y += key_h + gap

        label_w = int(content_w * 0.38)
        self._slider_label_x = x0 + 8
        track_x = x0 + label_w
        track_w = content_w - label_w
        for slider in (self.music_slider, self.sfx_slider):
            slider.rect = pygame.Rect(track_x, y, track_w, row_h)
            y += row_h + gap

        for toggle in (self.timer_toggle, self.grid_toggle, self.motion_toggle):
            toggle.rect = pygame.Rect(x0, y, content_w, row_h)
            y += row_h + gap

        seg_gap = max(4, gap // 2)
        seg_total = int(content_w * 0.58)
        seg_x = x0 + content_w - seg_total
        seg_w = (seg_total - 2 * seg_gap) // 3
        seg_h = max(22, int(row_h * 0.8))
        self._difficulty_label_x = x0 + 8
        for i, button in enumerate(self.difficulty_buttons):
            button.rect = pygame.Rect(
                seg_x + i * (seg_w + seg_gap), y + (row_h - seg_h) // 2, seg_w, seg_h
            )
        y += row_h + gap

        for row in (self.display_row, self.track_row):
            row.rect = pygame.Rect(x0, y, content_w, row_h)
            y += row_h + gap

        self._hint_y = y + row_h // 2 - gap // 2
        self._content_h = y - y_start + row_h

        btn_h = max(26, int(row_h * 0.9))
        bottom = max(14, h // 40)
        back_w = max(140, int(content_w * 0.26))
        reset_w = max(190, int(content_w * 0.38))
        total_w = back_w + gap + reset_w
        bx = (w - total_w) // 2
        by = h - btn_h - bottom
        self.back_btn.rect = pygame.Rect(bx + reset_w + gap, by, back_w, btn_h)
        self.reset_btn.rect = pygame.Rect(bx, by, reset_w, btn_h)

        # Clamp scrolling so the content fits between title and buttons.
        visible_h = max(40, by - bottom - y_start)
        self._max_scroll = max(0, self._content_h - visible_h)
        self._content_top = y_start - gap // 2
        self._content_bottom = by - bottom
        self._scroll = max(0, min(self._scroll, self._max_scroll))

    def _scroll_by(self, steps):
        if not self._size or steps == 0:
            return
        w, h = self._size
        self._scroll = max(
            0, min(self._scroll - steps * max(20, h // 24), self._max_scroll)
        )
        self._layout(w, h)

    def _iter_widgets(self):
        for action in ACTIONS:
            yield self.bind_rows[action]
            yield self.unbind_buttons[action]
        yield self.music_slider
        yield self.sfx_slider
        yield self.timer_toggle
        yield self.grid_toggle
        yield self.motion_toggle
        for button in self.difficulty_buttons:
            yield button
        yield self.display_row
        yield self.track_row
        yield self.back_btn
        yield self.reset_btn

    # --- State API -----------------------------------------------------------
    def handle_event(self, event):
        # Keybind rows first: a row in "press any key" mode consumes input.
        for action in ACTIONS:
            if self.bind_rows[action].handle_event(event):
                return
        if (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_ESCAPE
            and not any(row.waiting for row in self.bind_rows.values())
        ):
            self._back()
            return
        if event.type == pygame.MOUSEWHEEL and event.y:
            self._scroll_by(event.y)
            return
        if event.type == pygame.MOUSEMOTION and self._reset_confirm:
            # Moving off the reset button cancels the confirmation.
            if not self.reset_btn.rect.collidepoint(event.pos):
                self._reset_confirm = False
                self.reset_btn.label = "RESET TO DEFAULTS"
        for widget in self._iter_widgets():
            if widget.handle_event(event):
                return

    def update(self, dt):
        if self.bg is not None:
            self.bg.reduced_motion = bool(self.settings.get("reduced_motion", False))
            self.bg.update(dt)

    def draw(self, surface):
        w, h = surface.get_size()
        if self._size != (w, h):
            self._size = (w, h)
            self._layout(w, h)
        theme = get_theme()
        # City backdrop at a light dim so rows stay readable (Task 24).
        if self.bg is None or self.bg.size != (w, h):
            self.bg = CyberBackground(
                w, h, reduced_motion=bool(self.settings.get("reduced_motion", False))
            )
        self.bg.reduced_motion = bool(self.settings.get("reduced_motion", False))
        self.bg.draw(surface, dim=DIM_MENUS)

        draw_neon_text(
            surface,
            "SETTINGS",
            max(22, min(h // 12, 64)),
            theme["neon_cyan"],
            (w // 2, int(h * 0.065)),
            "center",
        )

        # Refresh cycling-row values from settings each frame.
        self.display_row.value_text = DISPLAY_LABELS.get(
            self.settings.get("display_mode", "borderless"), "BORDERLESS"
        )
        tracks = self.audio.scan_tracks()
        if not tracks:
            self.track_row.value_text = NO_TRACKS
        else:
            current = self.settings.get("current_track", "Auto")
            self.track_row.value_text = current if current in tracks else "Auto"

        # Clip the scrollable content so off-screen rows don't overlap headers.
        surface.set_clip(
            pygame.Rect(0, self._content_top, w, max(0, self._content_bottom - self._content_top))
        )
        for action in ACTIONS:
            self.bind_rows[action].draw(surface)
            self.unbind_buttons[action].draw(surface)

        label_size = max(12, int(self.music_slider.rect.h * 0.42))
        for slider, label in (
            (self.music_slider, "Music volume"),
            (self.sfx_slider, "SFX volume"),
        ):
            draw_text(
                surface,
                label,
                label_size,
                theme["text"],
                (self._slider_label_x, slider.rect.centery),
                "midleft",
            )
            draw_text(
                surface,
                "%d%%" % round(slider.value * 100),
                label_size * 0.9,
                theme["text_dim"],
                (slider.rect.x - 10, slider.rect.centery),
                "midright",
            )
            slider.draw(surface)

        self.timer_toggle.draw(surface)
        self.grid_toggle.draw(surface)
        self.motion_toggle.draw(surface)

        diff_level = self.settings["difficulty"]
        for level, button in zip(DIFFICULTY_ORDER, self.difficulty_buttons):
            button.active = diff_level == level
        draw_text(
            surface,
            "Difficulty",
            label_size,
            theme["text"],
            (self._difficulty_label_x, self.difficulty_buttons[0].rect.centery),
            "midleft",
        )
        for button in self.difficulty_buttons:
            button.draw(surface)

        self.display_row.draw(surface)
        self.track_row.draw(surface)

        draw_text(
            surface,
            "changes are saved automatically",
            max(10, h // 60),
            theme["text_dim"],
            (w // 2, self._hint_y),
            "center",
        )
        surface.set_clip(None)

        if self._max_scroll > 0:
            draw_text(
                surface,
                "scroll for more",
                max(9, h // 70),
                theme["text_dim"],
                (w // 2, self._content_bottom - max(8, h // 90)),
                "center",
            )
        self.back_btn.draw(surface)
        self.reset_btn.draw(surface)
