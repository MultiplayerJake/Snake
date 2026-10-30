"""Fresh edge-case pass over the Phase 3.5 features (Tasks 20-29).

Run (from anywhere): .\\.venv\\Scripts\\python.exe tests\\test_phase35_gaps.py
Or run every suite:  .\\.venv\\Scripts\\python.exe tests\\run_all.py

This suite deliberately targets boundaries the older suites do NOT cover:
  1. the LIVE project sfx/ files match their recipes exactly (read-only),
  2. golden-apple lifetime dies EXACTLY at the 5000ms boundary (+ urgency
     clamps, expiry leaves score untouched),
  3. a huge lag frame can never skip a countdown beat (dt clamp),
  4. mode-picker +10px spacing at odd window sizes + idempotent layout,
  5. unbind persistence through a real save -> load -> fresh-screen cycle,
  6. unbind clicks beating "press any key" waiting / P-armed states,
  7. settings scroll clamping with the unbind buttons present + ESC ladder,
  8. play-screen reduced_motion <-> background live interaction (no rebuild),
  9. background rebuild at odd sizes + sub-40px min-size clamp,
 10. game-over -> PLAY AGAIN -> second game-over stats accumulation
     (incl. disk round-trip and bests never regressing),
 11. volume slider drag semantics (live update, clamping, commit on release),
 12. small pure-function boundaries (format_time_ms, lerp_color, key_name,
     record_result clamps, spawn_free_cell on a full board),
 13. frozen (PyInstaller) path resolution (Task 31): with sys.frozen set,
     PROJECT_ROOT + stats.dat + settings.json + music/ + sfx/ all resolve
     NEXT TO THE EXE (subprocess simulation), dev-mode paths unchanged.

SDL dummy drivers and temp settings/stats files only - the real
settings.json / stats.dat are never touched. Exits 0 on success.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

# Project root = parent of tests/ (CWD-independent: works from anywhere).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import game.game as game_mod  # noqa: E402
from game import audio as audio_mod  # noqa: E402
from game import constants as constants_mod  # noqa: E402
from game import settings as settings_mod  # noqa: E402
from game import stats as stats_mod  # noqa: E402
from game.apple import Apple, GoldenApple, spawn_free_cell  # noqa: E402
from game.background import CyberBackground, DIM_PLAY  # noqa: E402
from game.constants import (  # noqa: E402
    GOLDEN_LIFETIME_MS,
    GRID_SIZE,
    format_time_ms,
    key_label,
    key_name,
    lerp_color,
)
from game.game import COUNTDOWN, PlayingState  # noqa: E402
from game.mode_picker import ModePicker  # noqa: E402
from game.settings import load_settings, save_settings  # noqa: E402
from game.settings_screen import SettingsScreen  # noqa: E402
from game.stats import STATS_DEFAULTS, load_stats, record_result  # noqa: E402
from game import ui as ui_mod  # noqa: E402
from game.ui import P_PAUSE_WARNING  # noqa: E402

PASS = 0


def check(label, condition, detail=""):
    global PASS
    if not condition:
        raise AssertionError("%s %s" % (label, detail))
    PASS += 1
    print("PASS  %s" % label)


def key(keycode):
    return pygame.event.Event(pygame.KEYDOWN, {"key": keycode})


def click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1})


def click_at(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1})


DEFAULT_BINDS = {"up": "w", "down": "s", "left": "a", "right": "d"}

# --- Frozen-mode path resolution child (Task 31) -----------------------------
# Imports game.constants in a fresh interpreter; with QS_FROZEN=1 it first
# fakes PyInstaller's runtime (sys.frozen + sys.executable = <fake dir>EXE)
# and prints every derived path as JSON. Pure path assertions only: the child
# imports game.constants + game.stats, which do no file I/O at import time,
# so nothing is ever written to the fake exe dir or to live user data.
FROZEN_CHILD = r"""
import json, os, sys
if os.environ.get("QS_FROZEN") == "1":
    sys.frozen = True
    sys.executable = os.path.join(os.environ["QS_FAKE_DIR"], "QuickSnake.exe")
sys.path.insert(0, os.environ["QS_ROOT"])
from game.constants import PROJECT_ROOT, SETTINGS_PATH, MUSIC_DIR, SFX_DIR
from game.stats import STATS_PATH
print(json.dumps({
    "project_root": PROJECT_ROOT,
    "settings": SETTINGS_PATH,
    "music": MUSIC_DIR,
    "sfx": SFX_DIR,
    "stats": STATS_PATH,
}))
"""


def resolve_paths_like(frozen, fake_dir=None):
    """Run the path-resolving child interpreter; returns its dict."""
    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["QS_ROOT"] = ROOT
    if frozen:
        env["QS_FROZEN"] = "1"
        env["QS_FAKE_DIR"] = fake_dir
    proc = subprocess.run(
        [sys.executable, "-c", FROZEN_CHILD],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    check(
        "frozen paths: child interpreter exited 0 (%s)"
        % ("frozen" if frozen else "dev"),
        proc.returncode == 0,
        "rc=%s stderr=%s" % (proc.returncode, proc.stderr[-300:]),
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main():
    tmp = tempfile.mkdtemp(prefix="quick_snake_gaps_")
    try:
        # Point all persistence at temp files (live settings/stats untouched).
        settings_mod.SETTINGS_PATH = os.path.join(tmp, "settings.json")
        stats_mod.STATS_PATH = os.path.join(tmp, "stats.dat")
        music_dir = os.path.join(tmp, "music")
        os.makedirs(music_dir, exist_ok=True)
        audio_mod.MUSIC_DIR = music_dir

        pygame.init()
        screen = pygame.display.set_mode((1280, 720))

        settings = load_settings()
        audio = audio_mod.AudioManager(settings)
        stats = load_stats()

        # =====================================================================
        # 1. LIVE project sfx/ files match the recipes exactly (read-only)
        # =====================================================================
        project_sfx = audio_mod.SFX_DIR
        for name, recipe in sorted(audio_mod.SFX_RECIPES.items()):
            path = os.path.join(project_sfx, name)
            check("live sfx: %s exists in the project sfx/" % name,
                  os.path.isfile(path), path)
            want_frames = sum(
                int(audio_mod.SAMPLE_RATE * ms / 1000)
                for ms in recipe["durations_ms"]
            )
            want_ms = float(sum(recipe["durations_ms"]))
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
            check("live sfx: %s frame count matches the recipe" % name,
                  frames == want_frames, "%d vs %d" % (frames, want_frames))
            check("live sfx: %s format is mono/16-bit/22050Hz" % name,
                  channels == 1 and sampwidth == 2 and rate == audio_mod.SAMPLE_RATE,
                  "%d ch / %d bit / %d Hz"
                  % (channels, sampwidth * 8, rate))
            got_ms = frames * 1000.0 / rate
            check("live sfx: %s duration ~%dms (±1ms rounding)" % (name, int(want_ms)),
                  abs(got_ms - want_ms) <= 1.0, "%.3fms" % got_ms)

        # =====================================================================
        # 2. Golden apple: dies EXACTLY at the 5000ms boundary
        # =====================================================================
        check("golden boundary: lifetime constant is 5000.0",
              GOLDEN_LIFETIME_MS == 5000.0)
        g = GoldenApple((3, 3))
        check("golden boundary: alive with 1ms to spare",
              g.update(4999.0) is True and g.lifetime_ms == 1.0,
              str(g.lifetime_ms))
        check("golden boundary: dead exactly at 5000ms elapsed",
              g.update(1.0) is False and g.lifetime_ms == 0.0,
              str(g.lifetime_ms))
        g = GoldenApple((3, 3))
        check("golden boundary: an overshooting frame dies too (5100ms)",
              g.update(5100.0) is False and g.lifetime_ms < 0.0)

        # Urgency clamps at both ends.
        g = GoldenApple((1, 1))
        g.lifetime_ms = GOLDEN_LIFETIME_MS / 2
        check("golden boundary: urgency is 0.5 at half life", g.urgency == 0.5)
        g.lifetime_ms = -50.0
        check("golden boundary: urgency clamps to 0.0 after death",
              g.urgency == 0.0)
        g.lifetime_ms = 999999.0
        check("golden boundary: urgency clamps to 1.0 beyond full life",
              g.urgency == 1.0)

        # Through the real update loop: dies on the exact 100ms deadline.
        st = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        st.phase = game_mod.PLAYING
        st.golden = GoldenApple((3, 3))
        st.golden.lifetime_ms = 100.0
        st.update(99.0)
        check("golden boundary: alive at 99ms in the game loop",
              st.golden is not None and st.golden.lifetime_ms == 1.0,
              str(getattr(st.golden, "lifetime_ms", None)))
        st.update(1.0)
        check("golden boundary: gone on the 100th ms in the game loop",
              st.golden is None)

        # An expiry is not an eat: score and counters stay untouched.
        st = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        st.phase = game_mod.PLAYING
        st.golden = GoldenApple((3, 3))
        st.golden.lifetime_ms = 50.0
        score_before, apples_before, gold_before = (
            st.score, st.apples_eaten, st.golden_eaten,
        )
        st.update(50.0)  # 50ms < one medium step (150ms): no snake movement
        check("golden boundary: expiry never scores or counts",
              st.golden is None
              and st.score == score_before
              and st.apples_eaten == apples_before
              and st.golden_eaten == gold_before)

        # =====================================================================
        # 3. Countdown: a huge lag frame can never skip a beat (dt clamp)
        # =====================================================================
        spy = []
        audio.play_sfx = lambda name: spy.append(name)  # instance-level spy
        cd = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        check("countdown clamp: beep on 3 at reset", spy == ["count_beep"],
              str(spy))
        cd.update(10000.0)  # 10s stall (window drag): clamped to 100ms
        check("countdown clamp: 10s lag frame advances at most 100ms",
              cd.countdown_value == 3 and cd.countdown_acc == 100.0
              and spy == ["count_beep"],
              "%s / %s / %s" % (cd.countdown_value, cd.countdown_acc, spy))
        for _ in range(9):  # 9 more clamped 100ms frames -> exactly one second
            cd.update(100.0)
        check("countdown clamp: the real second still beeps 2",
              cd.countdown_value == 2 and cd.countdown_acc == 0.0
              and spy == ["count_beep", "count_beep"],
              "%s / %s" % (cd.countdown_value, spy))
        del audio.play_sfx  # restore the real manager method

        # =====================================================================
        # 4. Mode picker +10px spacing at ODD window sizes + idempotent layout
        # =====================================================================
        started = []
        picker = ModePicker(settings, audio, started.append, lambda: None)
        for size in ((777, 513), (1023, 767), (641, 481)):
            picker._layout(*size)
            buttons = picker.mode_buttons
            step_a = buttons[1].rect.y - buttons[0].rect.y
            step_b = buttons[2].rect.y - buttons[1].rect.y
            btn_h = buttons[0].rect.h
            base_gap = max(18, btn_h)
            check("odd spacing: equal step on %dx%d" % size, step_a == step_b,
                  "%d / %d" % (step_a, step_b))
            check("odd spacing: exactly +10px on %dx%d" % size,
                  step_a - (base_gap + btn_h) == 10,
                  "step=%d base=%d btn_h=%d" % (step_a, base_gap, btn_h))
            check("odd spacing: centered on %dx%d" % size,
                  all(b.rect.centerx == size[0] // 2 for b in buttons))
            blurb_size = max(11, min(btn_h // 3, 20))
            blurb_end = (buttons[-1].rect.bottom + max(8, blurb_size)
                         + 2 * blurb_size + blurb_size)
            check("odd spacing: stack clears BACK on %dx%d" % size,
                  blurb_end < picker.back_btn.rect.top,
                  "%d vs %d" % (blurb_end, picker.back_btn.rect.top))
        # Laying out the same size twice yields identical rects (pure layout).
        picker._layout(777, 513)
        first = [tuple(b.rect) for b in picker.mode_buttons] + [tuple(picker.back_btn.rect)]
        picker._layout(777, 513)
        second = [tuple(b.rect) for b in picker.mode_buttons] + [tuple(picker.back_btn.rect)]
        check("odd spacing: layout is idempotent", first == second)
        picker._layout(*screen.get_size())

        # =====================================================================
        # 5. Unbind persistence through a REAL save -> load -> fresh screen
        # =====================================================================
        settings["keybinds"] = dict(DEFAULT_BINDS)
        save_settings(settings)
        ss = SettingsScreen(settings, audio, lambda: None,
                            on_display_change=lambda m: None)
        ss.draw(screen)
        ss.handle_event(click(ss.unbind_buttons["left"].rect))
        check("unbind cycle: left unbound in memory",
              settings["keybinds"]["left"] is None, str(settings["keybinds"]))
        on_disk = json.load(open(settings_mod.SETTINGS_PATH, encoding="utf-8"))
        check("unbind cycle: JSON on disk literally holds null",
              on_disk["keybinds"]["left"] is None, str(on_disk["keybinds"]))
        reloaded = load_settings()
        check("unbind cycle: None survives a full settings reload",
              reloaded["keybinds"]["left"] is None
              and reloaded["keybinds"] == dict(DEFAULT_BINDS, left=None),
              str(reloaded["keybinds"]))
        # A screen built ONLY from the reloaded dict shows the unbound row.
        ss2 = SettingsScreen(reloaded, audio, lambda: None,
                             on_display_change=lambda m: None)
        ss2.draw(screen)
        left_row = ss2.bind_rows["left"]
        check("unbind cycle: fresh screen renders '[ unbound ]'",
              left_row.keyname is None and left_row.prompt_text() == "[ unbound ]",
              left_row.prompt_text())
        # And a game built from the reloaded settings ignores the old key.
        st2 = PlayingState(reloaded, audio, stats, lambda: None, mode="classic")
        st2.phase = game_mod.PLAYING
        st2.snake.direction = (0, -1)  # moving up: "left" would be a legal turn
        st2.snake.pending_dir = None
        st2.handle_event(key(pygame.K_a))
        check("unbind cycle: reloaded game ignores the unbound key",
              st2.snake.pending_dir is None, str(st2.snake.pending_dir))
        st2.handle_event(key(pygame.K_d))  # right still bound
        check("unbind cycle: bound keys still fire after reload",
              st2.snake.pending_dir == (1, 0), str(st2.snake.pending_dir))
        settings = reloaded  # carry the unbound-left state forward

        # =====================================================================
        # 6. Unbind clicks beat waiting mode and P-armed warnings
        # =====================================================================
        settings["keybinds"] = dict(DEFAULT_BINDS)
        save_settings(settings)
        ss3 = SettingsScreen(settings, audio, lambda: None,
                             on_display_change=lambda m: None)
        ss3.draw(screen)
        up_row = ss3.bind_rows["up"]
        up_unbind = ss3.unbind_buttons["up"]

        ss3.handle_event(click(up_row.rect))
        check("unbind race: row is waiting", up_row.waiting)
        ss3.handle_event(click(up_unbind.rect))
        check("unbind race: unbind wins over waiting mode",
              settings["keybinds"]["up"] is None and not up_row.waiting,
              str(settings["keybinds"]))

        # P-armed row: unbind clears the binding AND the armed warning.
        ss3._rebind("up", "w")
        ss3.handle_event(click(up_row.rect))
        ss3.handle_event(key(pygame.K_p))
        check("unbind race: P arms the row", up_row.armed
              and up_row.warning == P_PAUSE_WARNING and not up_row.waiting)
        ss3.handle_event(click(up_unbind.rect))
        check("unbind race: unbind disarms + clears the warning",
              not up_row.armed and up_row.warning == ""
              and settings["keybinds"]["up"] is None,
              "%s / %s" % (up_row.armed, up_row.warning))
        # Unbind buttons never play the global click sound (current behavior:
        # only Button presses fire it) - characterization check.
        click_spy = []
        ui_mod.set_click_sound(lambda: click_spy.append("click"))
        ss3.handle_event(click(ss3.unbind_buttons["down"].rect))
        check("unbind race: unbind button is not a Button (no click SFX)",
              click_spy == [] and settings["keybinds"]["down"] is None,
              str(click_spy))
        ui_mod.set_click_sound(None)
        settings["keybinds"] = dict(DEFAULT_BINDS)
        save_settings(settings)

        # =====================================================================
        # 7. Settings scroll clamps with unbind buttons present + ESC ladder
        # =====================================================================
        small = pygame.Surface((700, 420))
        ss4 = SettingsScreen(settings, audio, lambda: None,
                             on_display_change=lambda m: None)
        ss4.draw(small)
        check("scroll: small screen allows scrolling", ss4._max_scroll > 0,
              "max_scroll=%d" % ss4._max_scroll)
        for _ in range(60):
            ss4.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1}))
        check("scroll: clamps exactly at max scroll",
              ss4._scroll == ss4._max_scroll,
              "%d vs %d" % (ss4._scroll, ss4._max_scroll))
        check("scroll: unbind buttons stay inside the surface width",
              all(b.rect.right <= 700 for b in ss4.unbind_buttons.values()),
              str([tuple(b.rect) for b in ss4.unbind_buttons.values()]))
        down_unbind = ss4.unbind_buttons["down"]
        check("scroll: down's unbind button is on-screen after scrolling",
              0 <= down_unbind.rect.y and down_unbind.rect.bottom <= 420,
              str(tuple(down_unbind.rect)))
        ss4.handle_event(click(down_unbind.rect))
        check("scroll: scrolled-away unbind button still works",
              settings["keybinds"]["down"] is None, str(settings["keybinds"]))
        for _ in range(60):
            ss4.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1}))
        check("scroll: wheel-up past the top clamps at 0", ss4._scroll == 0)

        # Big screen: no overflow -> wheel events are a no-op.
        ss5 = SettingsScreen(settings, audio, lambda: None,
                             on_display_change=lambda m: None)
        ss5.draw(screen)
        check("scroll: no overflow on 1280x720", ss5._max_scroll == 0,
              "max_scroll=%d" % ss5._max_scroll)
        ss5.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1}))
        check("scroll: wheel is a no-op without overflow", ss5._scroll == 0)

        # ESC ladder: first ESC cancels waiting, second ESC leaves the screen.
        backs = []
        ss6 = SettingsScreen(settings, audio, lambda: backs.append("back"),
                             on_display_change=lambda m: None)
        ss6.draw(screen)
        row = ss6.bind_rows["right"]
        ss6.handle_event(click(row.rect))
        ss6.handle_event(key(pygame.K_ESCAPE))
        check("scroll: first ESC only cancels waiting",
              backs == [] and not row.waiting, str(backs))
        ss6.handle_event(key(pygame.K_ESCAPE))
        check("scroll: second ESC goes back", backs == ["back"], str(backs))
        settings["keybinds"] = dict(DEFAULT_BINDS)
        save_settings(settings)

        # =====================================================================
        # 8. Play-screen reduced_motion <-> background live interaction
        # =====================================================================
        settings["reduced_motion"] = True
        play = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        play.phase = game_mod.PLAYING
        play.draw(screen)
        check("play bg: built with reduced_motion from settings",
              play._bg is not None and play._bg.reduced_motion)
        bg_obj = play._bg
        bg_obj._streak_in = 0.0
        play.update(16)
        check("play bg: no streaks spawn under reduced motion",
              bg_obj.streaks == [], str(len(bg_obj.streaks)))
        # Toggle OFF live: same object re-enabled on the next draw.
        settings["reduced_motion"] = False
        play.draw(screen)
        check("play bg: live toggle re-enables motion (no rebuild)",
              play._bg is bg_obj and not bg_obj.reduced_motion)
        bg_obj._streak_in = 0.0
        play.update(16)
        check("play bg: streaks spawn again after the live toggle",
              len(bg_obj.streaks) >= 1, str(len(bg_obj.streaks)))
        # Toggle back ON live: in-flight animation is cleared on update.
        settings["reduced_motion"] = True
        play.draw(screen)
        play.update(16)
        check("play bg: live toggle back on clears in-flight streaks",
              bg_obj.streaks == [] and play._bg is bg_obj)
        settings["reduced_motion"] = False
        # Resize rebuilds the backdrop through the game loop too.
        play.draw(small)
        check("play bg: rebuilds when the game surface resizes",
              play._bg.size == (700, 420) and play._bg is not bg_obj,
              str(play._bg.size))
        play.draw(screen)
        check("play bg: and back to full size", play._bg.size == (1280, 720))

        # =====================================================================
        # 9. Background rebuild at odd sizes + sub-40px min-size clamp
        # =====================================================================
        bg = CyberBackground(1280, 720, seed=1)
        for size in ((777, 513), (1001, 499), (333, 777)):
            surf = pygame.Surface(size)
            bg.draw(surf, dim=DIM_PLAY)
            check("bg odd: rebuilds exactly to %dx%d" % size,
                  bg.size == size and bg.static.get_size() == size,
                  str(bg.size))
            bg.update(16)  # animated overlay keeps working after the rebuild
        check("bg odd: update after odd rebuilds stays stable", True)
        tiny = pygame.Surface((10, 10))
        bg.draw(tiny, dim=DIM_PLAY)  # must not crash on a tiny surface
        check("bg odd: sub-40px surface clamps the static layer to 40x40",
              bg.size == (40, 40), str(bg.size))

        # =====================================================================
        # 10. game-over -> PLAY AGAIN -> second game-over stats accumulation
        # =====================================================================
        stats_fresh = load_stats()  # temp stats.dat -> pristine defaults
        check("accum: fresh stats are defaults", stats_fresh == STATS_DEFAULTS)
        run1 = PlayingState(settings, audio, stats_fresh, lambda: None,
                            mode="classic")
        run1.phase = game_mod.PLAYING
        run1.timer_running = True
        run1.score = 3
        run1.apples_eaten = 3
        run1.snake.body = [(GRID_SIZE - 1, 8), (GRID_SIZE - 2, 8),
                           (GRID_SIZE - 3, 8)]
        run1.snake.prev_body = list(run1.snake.body)
        run1.snake.direction = (1, 0)
        run1.snake.pending_dir = None
        run1._step()  # head leaves the grid -> death
        check("accum: first game over recorded",
              run1.phase == game_mod.GAME_OVER and not run1.won)
        check("accum: 1 game / 1 death / 0 wins after the first loss",
              stats_fresh["games_played"] == 1 and stats_fresh["total_deaths"] == 1
              and stats_fresh["wins"] == 0, str(stats_fresh))
        check("accum: first run sets the classic best",
              settings["bests"]["classic"]["best_score"] == 3
              and run1.new_best_score,
              str(settings["bests"]["classic"]))

        # Restart through the REAL overlay button.
        run1.draw(screen)  # lays out the PLAY AGAIN button
        run1.handle_event(click(run1.over_play_btn.rect))
        check("accum: PLAY AGAIN starts a fresh countdown",
              run1.phase == COUNTDOWN and run1.score == 0
              and run1.apples_eaten == 0 and run1.golden is None
              and len(run1.snake.body) == 3)

        run1.phase = game_mod.PLAYING
        run1.timer_running = True
        run1.score = 1
        run1.apples_eaten = 1
        run1.snake.body = [(GRID_SIZE - 1, 8), (GRID_SIZE - 2, 8),
                           (GRID_SIZE - 3, 8)]
        run1.snake.prev_body = list(run1.snake.body)
        run1.snake.direction = (1, 0)
        run1._step()  # second death
        check("accum: second loss ACCUMULATES (2 games / 2 deaths)",
              stats_fresh["games_played"] == 2 and stats_fresh["total_deaths"] == 2
              and stats_fresh["wins"] == 0
              and stats_fresh["total_apples"] == 4
              and stats_fresh["total_score"] == 4,
              str(stats_fresh))
        check("accum: lower second score never regresses the best",
              settings["bests"]["classic"]["best_score"] == 3
              and not run1.new_best_score,
              str(settings["bests"]["classic"]))
        check("accum: stats persisted to disk match memory",
              load_stats() == stats_fresh, str(load_stats()))
        run1.draw(screen)  # second game-over overlay renders
        check("accum: second game-over overlay draws", True)

        # A later WIN appends wins without erasing the death history.
        settings["difficulty"] = "easy"
        ta = PlayingState(settings, audio, stats_fresh, lambda: None,
                          mode="time_attack")
        ta.phase = game_mod.PLAYING
        ta.timer_running = True
        ta.target_apples = 1
        ta.apples_eaten = 0
        ta.apple.pos = (ta.snake.body[0][0] + 1, ta.snake.body[0][1])
        ta._step()  # eat -> target reached -> YOU WIN
        check("accum: win flags the run", ta.won and ta.phase == game_mod.GAME_OVER)
        check("accum: win appends (3 games / 2 deaths / 1 win)",
              stats_fresh["games_played"] == 3 and stats_fresh["total_deaths"] == 2
              and stats_fresh["wins"] == 1, str(stats_fresh))
        check("accum: disk matches memory after the win",
              load_stats() == stats_fresh)

        # =====================================================================
        # 11. Volume slider drag: live update, clamping, commit on release
        # =====================================================================
        ss7 = SettingsScreen(settings, audio, lambda: None,
                             on_display_change=lambda m: None)
        ss7.draw(screen)
        slider = ss7.music_slider
        target_x = slider.rect.right - 2
        ss7.handle_event(click_at((target_x, slider.rect.centery)))
        expected = (target_x - slider.rect.x) / slider.rect.w
        check("slider: click sets the value from x",
              abs(settings["music_volume"] - expected) < 1e-9
              and abs(slider.value - expected) < 1e-9,
              "%s vs %s" % (settings["music_volume"], expected))
        ss7.handle_event(
            pygame.event.Event(pygame.MOUSEMOTION,
                               {"pos": (slider.rect.right + 500,
                                        slider.rect.centery)}))
        check("slider: dragging past the track clamps to 1.0",
              settings["music_volume"] == 1.0 and slider.dragging)
        ss7.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP,
                               {"pos": (slider.rect.right + 500,
                                        slider.rect.centery), "button": 1}))
        on_disk = json.load(open(settings_mod.SETTINGS_PATH, encoding="utf-8"))
        check("slider: release commits the volume to disk",
              on_disk["music_volume"] == 1.0, str(on_disk["music_volume"]))
        check("slider: audio manager received the live volume",
              audio.music_volume == 1.0, str(audio.music_volume))
        # A click exactly on the track's left edge clamps to 0.0.
        settings["music_volume"] = 0.5
        save_settings(settings)
        ss7.handle_event(click_at((slider.rect.x, slider.rect.centery)))
        check("slider: far-left click clamps to 0.0",
              settings["music_volume"] == 0.0, str(settings["music_volume"]))
        ss7.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP,
                               {"pos": (slider.rect.x, slider.rect.centery),
                                "button": 1}))
        settings["music_volume"] = 0.5
        save_settings(settings)

        # =====================================================================
        # 12. Small pure-function boundaries
        # =====================================================================
        check("fmt: zero", format_time_ms(0) == "00:00.000")
        check("fmt: negative clamps to zero", format_time_ms(-500) == "00:00.000")
        check("fmt: 59999.9 truncates to 59.999",
              format_time_ms(59999.9) == "00:59.999")
        check("fmt: exact minute rollover", format_time_ms(60000) == "01:00.000")
        check("fmt: over an hour stays minutes",
              format_time_ms(3661001) == "61:01.001")
        check("lerp: t below 0 clamps to a",
              lerp_color((0, 0, 0), (100, 100, 100), -5) == (0, 0, 0))
        check("lerp: t above 1 clamps to b",
              lerp_color((0, 0, 0), (100, 100, 100), 5) == (100, 100, 100))
        check("lerp: midpoint is exact",
              lerp_color((10, 20, 30), (30, 40, 50), 0.5) == (20, 30, 40))
        check("keys: known key name", key_name(pygame.K_w) == "w")
        check("keys: unknown key gets a portable fallback name",
              key_name(10 ** 6) == "key1000000", key_name(10 ** 6))
        check("keys: unknown key label matches the fallback",
              key_label(10 ** 6) == "key1000000", key_label(10 ** 6))

        s = dict(STATS_DEFAULTS)
        record_result(s, score=-5, apples=-1, playtime_ms=-2, won=False,
                      golden_apples=-3)
        check("record: negatives clamp to zero, death counted",
              s["games_played"] == 1 and s["total_deaths"] == 1 and s["wins"] == 0
              and s["total_apples"] == 0 and s["total_score"] == 0
              and s["total_playtime_ms"] == 0 and s["golden_apples"] == 0,
              str(s))
        record_result(s, score=2, apples=3, playtime_ms=1000, won=True,
                      golden_apples=1)
        check("record: win and death are mutually exclusive",
              s["wins"] == 1 and s["total_deaths"] == 1 and s["games_played"] == 2
              and s["total_apples"] == 3 and s["golden_apples"] == 1, str(s))

        occupied = {(c, r) for c in range(GRID_SIZE) for r in range(GRID_SIZE)}
        check("spawn: full board has no free cell",
              spawn_free_cell(occupied) is None)
        ap = Apple()
        check("spawn: respawn on a full board returns False (win trigger)",
              ap.respawn(occupied) is False and ap.pos is None)

        # =====================================================================
        # 13. Frozen path resolution (Task 31): ALL runtime-writable paths
        #     (settings, stats, music, sfx) resolve NEXT TO THE EXE when
        #     sys.frozen is set; dev-mode semantics stay byte-identical.
        #     Derivation chain verified in source: stats.STATS_PATH joins
        #     PROJECT_ROOT (stats.py), settings.SETTINGS_PATH and audio's
        #     MUSIC_DIR/SFX_DIR are exported from constants — everything
        #     flows from the single PROJECT_ROOT fix.
        # =====================================================================
        fake_dir = os.path.join(tmp, "dist")
        os.makedirs(fake_dir)
        frozen_paths = resolve_paths_like(True, fake_dir)
        check("frozen paths: PROJECT_ROOT is the exe's folder",
              frozen_paths["project_root"] == os.path.abspath(fake_dir),
              frozen_paths["project_root"])
        check("frozen paths: stats.dat resolves INSIDE the exe dir",
              frozen_paths["stats"] == os.path.join(fake_dir, "stats.dat"),
              frozen_paths["stats"])
        check("frozen paths: settings.json resolves INSIDE the exe dir",
              frozen_paths["settings"] == os.path.join(fake_dir, "settings.json"),
              frozen_paths["settings"])
        check("frozen paths: music/ resolves INSIDE the exe dir",
              frozen_paths["music"] == os.path.join(fake_dir, "music"),
              frozen_paths["music"])
        check("frozen paths: sfx/ resolves INSIDE the exe dir",
              frozen_paths["sfx"] == os.path.join(fake_dir, "sfx"),
              frozen_paths["sfx"])
        check("frozen paths: child wrote nothing into the fake exe dir",
              os.listdir(fake_dir) == [], str(os.listdir(fake_dir)))

        dev_paths = resolve_paths_like(False)
        check("dev paths: PROJECT_ROOT is the real project root",
              dev_paths["project_root"] == ROOT, dev_paths["project_root"])
        check("dev paths: stats.dat stays in the project root",
              dev_paths["stats"] == os.path.join(ROOT, "stats.dat"),
              dev_paths["stats"])
        check("dev paths: settings.json stays in the project root",
              dev_paths["settings"] == os.path.join(ROOT, "settings.json"),
              dev_paths["settings"])
        check("dev paths: music/ stays in the project root",
              dev_paths["music"] == os.path.join(ROOT, "music"),
              dev_paths["music"])
        check("dev paths: sfx/ stays in the project root",
              dev_paths["sfx"] == os.path.join(ROOT, "sfx"),
              dev_paths["sfx"])

        # THIS (dev, unpatched) interpreter: constants must also be un-frozen.
        check("dev paths: live game.constants is un-frozen (no sys.frozen)",
              not getattr(sys, "frozen", False)
              and constants_mod.PROJECT_ROOT == ROOT,
              constants_mod.PROJECT_ROOT)

        print("\nALL %d CHECKS PASSED" % PASS)
        return 0
    finally:
        try:
            pygame.quit()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print("\nFAILED after %d passes: %s" % (PASS, exc))
        sys.exit(1)
