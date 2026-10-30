"""Game screen: countdown, play, HUD, timer, pause + game over overlays.

Supports three modes (Task 9-11): classic, speedrun (timer forced ON, hard
speed), time_attack (countdown timer + apple target scaled by difficulty).
Renders with smooth interpolated movement (Task 15), particles + screen
shake (Task 13) and a golden apple (Task 10).
"""

from __future__ import annotations

import random

import pygame

from game.ai import grid_metrics  # shared layout helper (also used by menu demo)
from game.apple import Apple, GoldenApple, spawn_free_cell
from game.background import DIM_PLAY, CyberBackground
from game.constants import (
    DIFFICULTY_TICKS,
    FPS,
    GAME_OVER,
    GOLDEN_CHANCE,
    GOLDEN_POINTS,
    GRID_SIZE,
    MODES,
    MODE_LABELS,
    NAME_TO_KEY,
    PAUSED,
    PLAYING,
    TIME_ATTACK_SPECS,
    format_time_ms,
    lerp_color,
)
from game.particles import ParticleSystem
from game.settings import save_settings
from game.snake import Snake
from game.stats import record_result, save_stats
from game.themes import get_theme
from game.ui import Button, draw_glow_rect, draw_neon_frame, draw_neon_text, draw_text

COUNTDOWN = "countdown"
PAUSE_KEYS = (pygame.K_ESCAPE, pygame.K_p)
TIME_ATTACK_DANGER_MS = 10000.0  # countdown turns red below 10 s


class PlayingState:
    """The whole game screen: countdown -> playing -> paused / game over."""

    def __init__(self, settings, audio, stats, on_menu, mode="classic"):
        self.settings = settings
        self.audio = audio
        self.stats = stats
        self.on_menu = on_menu
        self.mode = mode if mode in MODES else "classic"
        self.particles = ParticleSystem(
            reduced_motion=settings.get("reduced_motion", False)
        )
        self._size = None
        self._bg = None  # procedural cyber-city backdrop, built on first draw

        self.pause_resume_btn = Button(pygame.Rect(0, 0, 1, 1), "RESUME", self._resume)
        self.pause_restart_btn = Button(pygame.Rect(0, 0, 1, 1), "RESTART", self.reset)
        self.pause_menu_btn = Button(pygame.Rect(0, 0, 1, 1), "MENU", self._menu)
        self.over_play_btn = Button(
            pygame.Rect(0, 0, 1, 1), "PLAY AGAIN", self.reset, accent=True
        )
        self.over_menu_btn = Button(pygame.Rect(0, 0, 1, 1), "MENU", self._menu)

        self.reset()

    # --- Mode helpers --------------------------------------------------------
    def _show_timer(self):
        """Speedrun forces the timer on; classic honors the pref."""
        if self.mode == "speedrun":
            return True
        if self.mode == "time_attack":
            return True  # countdown is mandatory here
        return bool(self.settings.get("timer_enabled"))

    def _ticks_per_step(self):
        if self.mode == "speedrun":
            return DIFFICULTY_TICKS["hard"]
        return DIFFICULTY_TICKS.get(self.settings["difficulty"], 9)

    def _time_attack_spec(self):
        return TIME_ATTACK_SPECS.get(
            self.settings["difficulty"], TIME_ATTACK_SPECS["medium"]
        )

    # --- Lifecycle -----------------------------------------------------------
    def reset(self):
        """Fresh run: new snake, countdown from 3."""
        self.snake = Snake()
        self.apple = Apple()
        self.apple.respawn(self.snake.body)
        self.golden = None
        self.score = 0
        self.apples_eaten = 0  # red apples (Time Attack target)
        self.golden_eaten = 0
        self.phase = COUNTDOWN
        self.countdown_value = 3
        self.countdown_acc = 0.0
        self.audio.play_sfx("count_beep")  # F1-style: beep on "3"
        self.timer_ms = 0.0
        self.timer_running = False
        self.move_acc = 0.0
        self.won = False
        self.new_best_score = False
        self.new_best_time = False
        self._last_metrics = None  # set on first draw; used for particle pixels
        if self.mode == "time_attack":
            spec = self._time_attack_spec()
            self.target_apples = spec["apples"]
            self.time_limit_ms = spec["seconds"] * 1000.0
            self.remaining_ms = self.time_limit_ms
        else:
            self.target_apples = 0
            self.time_limit_ms = 0.0
            self.remaining_ms = 0.0
        # Fresh particles/shake for the new run.
        self.particles = ParticleSystem(
            reduced_motion=self.settings.get("reduced_motion", False)
        )

    def _menu(self):
        self.on_menu()

    def _pause(self):
        if self.phase == PLAYING:
            self.phase = PAUSED

    def _resume(self):
        if self.phase == PAUSED:
            self.phase = PLAYING

    # --- Update --------------------------------------------------------------
    def update(self, dt):
        dt = min(float(dt), 100.0)  # clamp long frames (window drag, lag)
        self.particles.update(dt)  # shake/particles decay in every phase
        if self._bg is not None:
            self._bg.update(dt)  # streaks/window flicker (off under reduced motion)
        if self.phase == COUNTDOWN:
            if self.timer_running:
                self.timer_ms += dt  # timer starts at GO
            self.countdown_acc += dt
            while self.countdown_acc >= 1000.0:
                self.countdown_acc -= 1000.0
                self.countdown_value -= 1
                if self.countdown_value == 0:
                    self.timer_running = True  # "GO!" beat
                    self.audio.play_sfx("start_beep")  # F1 lights-out (long)
                elif self.countdown_value in (1, 2):
                    self.audio.play_sfx("count_beep")  # beeps on 2 and 1
                elif self.countdown_value < 0:
                    self.phase = PLAYING
                    break
        elif self.phase == PLAYING:
            if self.timer_running:
                self.timer_ms += dt
            if self.mode == "time_attack":
                self.remaining_ms -= dt
                if self.remaining_ms <= 0.0:
                    self.remaining_ms = 0.0
                    self._finish(won=False)  # TIME'S UP
                    return
            if self.golden is not None and not self.golden.update(dt):
                self.golden = None  # lifetime expired: disappears
            step_ms = self._ticks_per_step() * (1000.0 / FPS)
            self.move_acc += dt
            while self.phase == PLAYING and self.move_acc >= step_ms:
                self.move_acc -= step_ms
                self._step()

    def _step(self):
        head = self.snake.step()
        col, row = head
        in_bounds = 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE
        if not in_bounds or head in self.snake.body[1:]:
            self._die(head)
            return
        if head == self.apple.pos:
            self._eat_red()
        elif self.golden is not None and head == self.golden.pos:
            self._eat_golden()

    def _eat_red(self):
        theme = get_theme()
        self.score += 1
        self.apples_eaten += 1
        self.snake.grow_by += 1
        self.audio.play_sfx("eat")
        self.particles.burst(*self._apple_pixel(self.apple.pos), theme["apple"], count=12)
        if not self.apple.respawn(self.snake.body):
            self._finish(won=True)  # board full -> win
            return
        # ~15% chance to also spawn the golden apple (one at a time).
        # Task 20: never spawns at all in Time Attack mode.
        if (
            self.mode != "time_attack"
            and self.golden is None
            and random.random() < GOLDEN_CHANCE
        ):
            cell = spawn_free_cell(set(self.snake.body) | {self.apple.pos})
            if cell is not None:
                self.golden = GoldenApple(cell)
        if self.mode == "time_attack" and self.apples_eaten >= self.target_apples:
            self._finish(won=True)  # target reached -> YOU WIN

    def _eat_golden(self):
        theme = get_theme()
        pos = self.golden.pos
        self.score += GOLDEN_POINTS
        self.golden_eaten += 1
        self.snake.grow_by += 1
        self.audio.play_sfx("eat")
        self.particles.burst(*self._apple_pixel(pos), theme["golden"], count=20)
        self.golden = None

    def _die(self, head):
        theme = get_theme()
        self.particles.shatter(*self._apple_pixel(head), theme["snake_head"], count=30)
        self.particles.add_shake()
        self.audio.play_sfx("death")
        self._finish(won=False)

    def _apple_pixel(self, pos):
        """Convert a grid cell to a pixel position for particle bursts.

        Uses the last-computed grid metrics; falls back to a 24px cell so
        particles still land sensibly if never drawn.
        """
        cell, origin_x, hud_h = self._last_metrics or (24, 0, 0)
        col, row = pos
        return (origin_x + col * cell + cell // 2, hud_h + row * cell + cell // 2)

    def _finish(self, won):
        if won:
            # Task 29: covers Time Attack wins and the board-full win; the
            # death path goes through _die() (death sfx) with won=False.
            self.audio.play_sfx("win")
        self.won = won
        self.phase = GAME_OVER
        self.timer_running = False

        settings = self.settings
        bests = settings.setdefault("bests", {})
        best = bests.setdefault(
            self.mode, {"best_score": 0, "best_time_ms": None}
        )

        # Best score (every mode).
        self.new_best_score = self.score > best.get("best_score", 0)
        if self.new_best_score:
            best["best_score"] = self.score

        if self.mode == "time_attack":
            # Fastest clear per difficulty (only on wins).
            if won:
                by = best.setdefault(
                    "by_difficulty", {"easy": None, "medium": None, "hard": None}
                )
                elapsed = int(self.timer_ms)
                fastest = by.get(self.settings["difficulty"])
                if fastest is None or elapsed < fastest:
                    by[self.settings["difficulty"]] = elapsed
                    self.new_best_time = True
        elif self._show_timer():
            fastest = best.get("best_time_ms")
            if fastest is None or self.timer_ms < fastest:
                best["best_time_ms"] = int(self.timer_ms)
                self.new_best_time = True

        save_settings(settings)
        record_result(
            self.stats,
            score=self.score,
            apples=self.apples_eaten,
            playtime_ms=int(self.timer_ms),
            won=won,
            golden_apples=self.golden_eaten,
        )
        save_stats(self.stats)

    # --- Events --------------------------------------------------------------
    def _overlay_widgets(self):
        if self.phase == PAUSED:
            return [self.pause_resume_btn, self.pause_restart_btn, self.pause_menu_btn]
        if self.phase == GAME_OVER:
            return [self.over_play_btn, self.over_menu_btn]
        return []

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.phase == PLAYING:
                if event.key in PAUSE_KEYS:
                    self._pause()
                    return
                for action, name in self.settings["keybinds"].items():
                    if name is None:
                        continue  # unbound action never fires (Task 22)
                    if NAME_TO_KEY.get(name) == event.key:
                        self.snake.on_action(action)
                        return
            elif self.phase == PAUSED and event.key in PAUSE_KEYS:
                self._resume()
                return
        elif event.type in (
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION,
        ):
            for widget in self._overlay_widgets():
                if widget.handle_event(event):
                    return

    # --- Layout --------------------------------------------------------------
    def _grid_metrics(self, w, h):
        """Cell size from screen height; grid centered horizontally."""
        return grid_metrics(w, h)

    # --- Draw ----------------------------------------------------------------
    def draw(self, surface):
        w, h = surface.get_size()
        cell, origin_x, hud_h = self._grid_metrics(w, h)
        if self._size != (w, h):
            self._size = (w, h)
        self._last_metrics = (cell, origin_x, hud_h)
        theme = get_theme()

        # Screen shake: decaying random offset of the grid drawing origin.
        shake_x, shake_y = self.particles.shake_offset()
        ox = origin_x + shake_x
        oy = hud_h + shake_y

        # Procedural neon skyline, heavily dimmed so the grid stays readable
        # (rebuilt only when the window size changes).
        if self._bg is None or self._bg.size != (w, h):
            self._bg = CyberBackground(
                w, h, reduced_motion=self.settings.get("reduced_motion", False)
            )
        self._bg.reduced_motion = bool(self.settings.get("reduced_motion", False))
        self._bg.draw(surface, dim=DIM_PLAY)

        grid_px = cell * GRID_SIZE
        if self.settings.get("grid_lines"):
            width = theme["grid_width"]
            for i in range(GRID_SIZE + 1):
                x = ox + i * cell
                pygame.draw.line(
                    surface, theme["grid_line"], (x, oy), (x, oy + grid_px), width
                )
                y = oy + i * cell
                pygame.draw.line(
                    surface, theme["grid_line"], (ox, y), (ox + grid_px, y), width
                )

        # Glowing neon border frame around the 25x25 play grid (Task 24).
        draw_neon_frame(surface, pygame.Rect(ox, oy, grid_px, grid_px))

        if self.golden is not None:
            self.golden.draw(surface, ox, oy, cell)
        self.apple.draw(surface, ox, oy, cell)
        # Interpolation alpha: 1 during countdown/pause, lerped while playing.
        if self.phase == PLAYING:
            step_ms = self._ticks_per_step() * (1000.0 / FPS)
            alpha = min(1.0, self.move_acc / step_ms)
        else:
            alpha = 1.0
        self.snake.draw(surface, ox, oy, cell, alpha=alpha)
        self.particles.draw(surface)
        self._draw_hud(surface, w, hud_h)

        if self.phase == COUNTDOWN:
            self._draw_countdown(surface, w, h, cell, origin_x, hud_h)
        elif self.phase == PAUSED:
            self._draw_pause_overlay(surface, w, h, cell)
        elif self.phase == GAME_OVER:
            self._draw_game_over_overlay(surface, w, h, cell)

    def _draw_hud(self, surface, w, hud_h):
        theme = get_theme()
        pygame.draw.rect(surface, theme["hud_bg"], pygame.Rect(0, 0, w, hud_h))
        # Neon underline: soft cyan glow with a crisp cyan line on top.
        glow_line = lerp_color(theme["neon_cyan"], theme["hud_bg"], 0.55)
        pygame.draw.line(surface, glow_line, (0, hud_h - 2), (w, hud_h - 2), 3)
        pygame.draw.line(surface, theme["neon_cyan"], (0, hud_h - 1), (w, hud_h - 1), 1)
        margin = max(10, hud_h // 4)
        font_size = max(14, int(hud_h * 0.42))
        draw_neon_text(
            surface,
            "SCORE  %d" % self.score,
            font_size,
            theme["neon_cyan"],
            (margin, hud_h // 2),
            "midleft",
            bg=theme["hud_bg"],
        )
        if self.mode == "time_attack":
            draw_neon_text(
                surface,
                "APPLES  %d/%d" % (self.apples_eaten, self.target_apples),
                font_size,
                theme["text"],
                (w // 2, hud_h // 2),
                "center",
                bg=theme["hud_bg"],
            )
            low = self.remaining_ms <= TIME_ATTACK_DANGER_MS
            draw_neon_text(
                surface,
                format_time_ms(self.remaining_ms),
                font_size,
                theme["danger"] if low else theme["text"],
                (w - margin, hud_h // 2),
                "midright",
                bg=theme["hud_bg"],
            )
        else:
            draw_neon_text(
                surface,
                MODE_LABELS[self.mode],
                font_size,
                theme["text_dim"],
                (w // 2, hud_h // 2),
                "center",
                bg=theme["hud_bg"],
            )
            if self._show_timer():
                draw_neon_text(
                    surface,
                    format_time_ms(self.timer_ms),
                    font_size,
                    theme["text"],
                    (w - margin, hud_h // 2),
                    "midright",
                    bg=theme["hud_bg"],
                )

    def _draw_countdown(self, surface, w, h, cell, origin_x, hud_h):
        theme = get_theme()
        grid_px = cell * GRID_SIZE
        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((*theme["overlay_dim"], 110))
        surface.blit(dim, (0, 0))
        text = "GO!" if self.countdown_value == 0 else str(max(1, self.countdown_value))
        draw_neon_text(
            surface,
            text,
            cell * 4,
            theme["neon_cyan"],
            (origin_x + grid_px // 2, hud_h + grid_px // 2),
            "center",
            bg=theme["overlay_dim"],
            spread=max(3, cell // 4),
        )

    def _draw_overlay(self, surface, w, h, cell, title, title_color, lines, buttons):
        theme = get_theme()
        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((*theme["overlay_dim"], 170))
        surface.blit(dim, (0, 0))

        gap = max(8, cell // 2)
        line_h = max(cell, 20)
        title_h = int(cell * 2.4)
        btn_h = max(28, int(cell * 1.5))
        panel_w = min(int(w * 0.6), max(340, cell * 16))
        panel_h = title_h + len(lines) * line_h + len(buttons) * (btn_h + gap) + gap * 2
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (w // 2, h // 2)

        radius = max(8, cell // 2)
        draw_glow_rect(surface, theme["neon_cyan"], panel, radius, alpha=55, grow=6)
        pygame.draw.rect(surface, theme["panel"], panel, border_radius=radius)
        pygame.draw.rect(
            surface, theme["neon_cyan"], panel, width=2, border_radius=radius
        )

        y = panel.y + gap
        draw_text(
            surface,
            title,
            title_h * 0.6,
            title_color,
            (panel.centerx, y + title_h // 2),
            "center",
            bold=True,
        )
        y += title_h
        for text, color in lines:
            draw_text(surface, text, line_h * 0.55, color, (panel.centerx, y + line_h // 2), "center")
            y += line_h
        y += gap
        btn_w = int(panel_w * 0.7)
        for button in buttons:
            button.rect = pygame.Rect(panel.centerx - btn_w // 2, y, btn_w, btn_h)
            button.draw(surface)
            y += btn_h + gap

    def _draw_pause_overlay(self, surface, w, h, cell):
        theme = get_theme()
        self._draw_overlay(
            surface,
            w,
            h,
            cell,
            "PAUSED",
            theme["warning"],
            [("take a breath", theme["text_dim"])],
            [self.pause_resume_btn, self.pause_restart_btn, self.pause_menu_btn],
        )

    def _draw_game_over_overlay(self, surface, w, h, cell):
        theme = get_theme()
        lines = []
        if self.mode == "time_attack":
            title = "YOU WIN" if self.won else "TIME'S UP"
            title_color = theme["accent"] if self.won else theme["danger"]
            lines.append(
                ("APPLES  %d/%d" % (self.apples_eaten, self.target_apples), theme["text"])
            )
            lines.append(("SCORE  %d" % self.score, theme["text"]))
            if self.won:
                left_text = "TIME LEFT  %s" % format_time_ms(self.remaining_ms)
                if self.new_best_time:
                    left_text += "  NEW BEST!"
                lines.append(
                    (left_text, theme["warning"] if self.new_best_time else theme["text"])
                )
            if self.new_best_score:
                lines.append(("NEW BEST SCORE!", theme["warning"]))
        else:
            title = "YOU WIN!" if self.won else "GAME OVER"
            title_color = theme["accent"] if self.won else theme["danger"]
            lines.append(("SCORE  %d" % self.score, theme["text"]))
            if self._show_timer():
                time_text = "TIME  %s" % format_time_ms(self.timer_ms)
                if self.new_best_time:
                    time_text += "  NEW BEST!"
                time_color = theme["warning"] if self.new_best_time else theme["text"]
                lines.append((time_text, time_color))
            if self.new_best_score:
                lines.append(("NEW BEST SCORE!", theme["warning"]))
            if self.won:
                lines.append(("the board is full - flawless!", theme["text_dim"]))
        lines.append(
            (
                "Games %d - Apples %d - Wins %d"
                % (
                    self.stats.get("games_played", 0),
                    self.stats.get("total_apples", 0),
                    self.stats.get("wins", 0),
                ),
                theme["text_dim"],
            )
        )
        self._draw_overlay(
            surface,
            w,
            h,
            cell,
            title,
            title_color,
            lines,
            [self.over_play_btn, self.over_menu_btn],
        )
