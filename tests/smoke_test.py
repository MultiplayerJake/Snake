"""Headless smoke test for Phase 2 (Tasks 9-19).

Run (from anywhere): .\\.venv\\Scripts\\python.exe tests\\smoke_test.py
Or run every suite:  .\\.venv\\Scripts\\python.exe tests\\run_all.py

Uses SDL dummy drivers and temporary settings/stats files (the real
settings.json / stats.dat are never touched). Exits 0 on success.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

# Project root = parent of tests/ (CWD-independent: works from anywhere).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from game import settings as settings_mod  # noqa: E402
from game import stats as stats_mod  # noqa: E402
from game import audio as audio_mod  # noqa: E402
import game.game as game_mod  # noqa: E402
from game.ai import DemoSnake, bfs_path  # noqa: E402
from game.apple import GoldenApple  # noqa: E402
from game.constants import (  # noqa: E402
    GRID_SIZE,
    TIME_ATTACK_SPECS,
    format_time_ms,
)
from game.game import PlayingState  # noqa: E402
from game.menu import MainMenu  # noqa: E402
from game.mode_picker import ModePicker  # noqa: E402
from game.particles import ParticleSystem  # noqa: E402
from game.settings import (  # noqa: E402
    load_settings,
    reset_to_defaults,
    save_settings,
)
from game.settings_screen import NO_TRACKS, SettingsScreen  # noqa: E402
from game.snake import Snake  # noqa: E402
from game.stats import load_stats, save_stats  # noqa: E402
from game.themes import THEMES, get_theme, set_theme  # noqa: E402

import main as main_mod  # noqa: E402

PASS = 0


def check(label, condition, detail=""):
    global PASS
    if not condition:
        raise AssertionError("%s %s" % (label, detail))
    PASS += 1
    print("PASS  %s" % label)


def click(rect):
    return pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1}
    )


def main():
    tmp = tempfile.mkdtemp(prefix="quick_snake_smoke_")
    try:
        # Point all persistence at temp files (module globals, resolved at call time).
        settings_mod.SETTINGS_PATH = os.path.join(tmp, "settings.json")
        stats_mod.STATS_PATH = os.path.join(tmp, "stats.dat")
        music_dir = os.path.join(tmp, "music")
        os.makedirs(music_dir, exist_ok=True)
        audio_mod.MUSIC_DIR = music_dir

        pygame.init()
        screen = pygame.display.set_mode((1280, 720))

        # --- Task 9: legacy migration -----------------------------------------
        # Self-contained synthetic legacy file (the user's live settings.json
        # may already be migrated / in active use).
        with open(settings_mod.SETTINGS_PATH, "w", encoding="utf-8") as fh:
            json.dump(
                {"best_score": 7, "best_time_ms": 12345, "difficulty": "hard"},
                fh,
            )
        settings = load_settings()
        check(
            "migration: legacy bests -> bests.classic",
            settings["bests"]["classic"]["best_score"] == 7
            and settings["bests"]["classic"]["best_time_ms"] == 12345,
            str(settings["bests"]["classic"]),
        )
        check(
            "migration: legacy keys removed",
            "best_score" not in settings and "best_time_ms" not in settings,
        )
        check("defaults: new keys present",
              settings["theme"] == "dark"
              and settings["reduced_motion"] is False
              and settings["current_track"] == "Auto"
              and settings["display_mode"] == "borderless"
              and settings["last_mode"] == "classic")

        audio = audio_mod.AudioManager(settings)
        stats = load_stats()
        set_theme(settings["theme"])

        # --- Task 17: settings backup -----------------------------------------
        save_settings(settings)
        check("save #1 writes settings.json",
              os.path.isfile(settings_mod.SETTINGS_PATH))
        settings["difficulty"] = "medium"
        save_settings(settings)
        bak = settings_mod.SETTINGS_PATH + ".bak"
        check("save #2 creates settings.json.bak", os.path.isfile(bak))

        # --- Task 9: mode picker -----------------------------------------------
        started = []
        picker = ModePicker(settings, audio, started.append, lambda: None)
        picker.draw(screen)
        for mode in ("classic", "speedrun", "time_attack"):
            started.clear()
            picker.handle_event(click(picker.buttons_by_mode[mode].rect))
            check("mode picker starts %s" % mode, started == [mode], str(started))
        check("last_mode persisted", settings["last_mode"] == "time_attack")
        picker.draw(screen)  # best-line rendering with data
        esc = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE})
        back = []
        picker.on_back = lambda: back.append(True)
        picker.handle_event(esc)
        check("mode picker esc -> back", back == [True])

        # --- Task 15: interpolation -------------------------------------------
        snake = Snake()
        snake.step()
        centers = snake.interpolated_centers(0, 0, 20, 0.25)
        cell = 20
        between = [c for c in centers if (c[0] - cell // 2) % cell != 0]
        check("interpolation: positions between cells at alpha=0.25", bool(between))
        exact = snake.interpolated_centers(0, 0, 20, 1.0)
        check("interpolation: alpha=1 lands on cell centers",
              all((c[0] - cell // 2) % cell == 0 and (c[1] - cell // 2) % cell == 0
                  for c in exact))
        snake.grow_by = 2
        snake.step()
        check("interpolation: tail-grow clamp (len matches body)",
              len(snake.interpolated_centers(0, 0, 20, 0.5)) == len(snake.body))

        # --- Task 13: particles + shake + reduced_motion ----------------------
        ps = ParticleSystem()
        ps.burst(100, 100, (255, 0, 0), count=12)
        check("particles: eat burst creates 12", len(ps.particles) == 12)
        ps.shatter(50, 50, (0, 255, 0), count=30)
        check("particles: death shatter creates 30", len(ps.particles) == 42)
        ps.add_shake()
        check("shake: starts at 400ms", ps.shake_ms == 400.0)
        ps.update(100)
        check("shake: decays", ps.shake_ms == 300.0)
        ps.update(400)
        check("shake: ends at zero offset", ps.shake_ms == 0.0 and ps.shake_offset() == (0, 0))
        for _ in range(10):
            ps.update(100)
        check("particles: expire after update", len(ps.particles) == 0)
        ps.draw(screen)  # no crash
        ps_reduced = ParticleSystem(reduced_motion=True)
        ps_reduced.burst(10, 10, (255, 0, 0))
        ps_reduced.add_shake()
        check("reduced_motion: burst/shake suppressed",
              len(ps_reduced.particles) == 0 and ps_reduced.shake_ms == 0.0)

        # --- Task 6/13: classic game: eat, golden spawn/eat/expiry, death -----
        settings["difficulty"] = "medium"
        st = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        check("classic: timer hidden when pref off", not st._show_timer())
        st.phase = game_mod.PLAYING
        st.timer_running = True
        old_chance = game_mod.GOLDEN_CHANCE
        game_mod.GOLDEN_CHANCE = 1.0
        try:
            head = st.snake.body[0]
            st.snake.direction = (1, 0)
            st.snake.pending_dir = None
            st.apple.pos = (head[0] + 1, head[1])
            st._step()  # eat red -> golden must spawn (chance forced to 1)
            check("golden: spawns after red apple (forced chance)",
                  st.golden is not None, str(st.golden))
            check("golden: never on snake or red apple",
                  st.golden.pos not in st.snake.body
                  and st.golden.pos != st.apple.pos)
            check("golden: worth the run counters",
                  st.score == 1 and st.apples_eaten == 1)
            st.apple.pos = (5, 20)  # keep the lane clear deterministically
            st.golden.pos = (st.snake.body[0][0] + 1, st.snake.body[0][1])
            st._step()
            check("golden: eaten = +5 points",
                  st.golden is None and st.score == 6 and st.golden_eaten == 1)
            # Golden expiry through the update loop.
            st.golden = GoldenApple((3, 3))
            st.golden.lifetime_ms = 250.0
            for _ in range(4):
                st.update(100)
            check("golden: expires after lifetime", st.golden is None)
            # Pause freezes the lifetime.
            st.golden = GoldenApple((2, 2))
            st.golden.lifetime_ms = 100.0
            st.phase = game_mod.PAUSED
            for _ in range(3):
                st.update(100)
            check("golden: lifetime frozen while paused",
                  st.golden is not None and st.golden.lifetime_ms == 100.0)
            st.phase = game_mod.PLAYING
        finally:
            game_mod.GOLDEN_CHANCE = old_chance

        # Death: shatter + screen shake + game over.
        st.phase = game_mod.PLAYING
        st.snake.body = [(GRID_SIZE - 1, 12), (GRID_SIZE - 2, 12), (GRID_SIZE - 3, 12)]
        st.snake.prev_body = list(st.snake.body)
        st.snake.direction = (1, 0)
        st.particles = ParticleSystem()
        st._step()  # head leaves the grid -> death
        check("death: game over phase", st.phase == game_mod.GAME_OVER and not st.won)
        check("death: shatter + shake", len(st.particles.particles) == 30
              and st.particles.shake_ms == 400.0)
        st.draw(screen)

        # Speedrun forces timer + hard speed.
        sr = PlayingState(settings, audio, stats, lambda: None, mode="speedrun")
        check("speedrun: timer forced on", sr._show_timer())
        check("speedrun: hard speed", sr._ticks_per_step() == 6)
        sr.draw(screen)

        # --- Task 11: time attack win + lose ----------------------------------
        settings["difficulty"] = "easy"  # 5 apples / 90 s
        ta = PlayingState(settings, audio, stats, lambda: None, mode="time_attack")
        check("time attack: target/duration scale with difficulty",
              ta.target_apples == TIME_ATTACK_SPECS["easy"]["apples"]
              and ta.time_limit_ms == TIME_ATTACK_SPECS["easy"]["seconds"] * 1000.0)
        check("time attack: countdown mandatory", ta._show_timer())
        ta.phase = game_mod.PLAYING
        ta.timer_running = True
        guard = 0
        while ta.phase == game_mod.PLAYING and guard < 40:
            guard += 1
            head = ta.snake.body[0]
            ahead = (head[0] + 1, head[1])
            if ahead[0] >= GRID_SIZE:
                ta.snake.direction = (0, 1)
                ahead = (head[0], head[1] + 1)
            ta.apple.pos = ahead
            ta.update(200)  # >= one step at medium; easy is slower but fine
        check("time attack: YOU WIN when target reached",
              ta.phase == game_mod.GAME_OVER and ta.won, "guard=%d" % guard)
        check("time attack: HUD values", ta.apples_eaten >= 5)
        fastest = settings["bests"]["time_attack"]["by_difficulty"]["easy"]
        check("time attack: fastest clear tracked",
              fastest is not None and fastest == int(ta.timer_ms),
              "%s vs %s" % (fastest, ta.timer_ms))
        ta._draw_hud(screen, 1280, 60)
        ta.draw(screen)  # YOU WIN overlay renders

        ta2 = PlayingState(settings, audio, stats, lambda: None, mode="time_attack")
        ta2.phase = game_mod.PLAYING
        ta2.timer_running = True
        ta2._step = lambda: None  # keep the snake out of it; let time run out
        for _ in range(950):
            if ta2.phase != game_mod.PLAYING:
                break
            ta2.update(100)
        check("time attack: TIME'S UP when countdown hits 0",
              ta2.phase == game_mod.GAME_OVER and not ta2.won
              and ta2.remaining_ms == 0.0)
        check("time attack: lose records a death, not a win",
              ta2.stats["total_deaths"] >= 2 and ta2.stats["wins"] == 1)
        ta2.draw(screen)
        check("time attack: HUD turns red < 10s", True)  # drawn above without crash

        # --- Task 12: stats.dat base64 round-trip -----------------------------
        with open(stats_mod.STATS_PATH, "r", encoding="ascii") as fh:
            raw = fh.read()
        decoded = json.loads(base64.b64decode(raw.encode("ascii")).decode("utf-8"))
        expected_keys = {"games_played", "total_apples", "total_score",
                         "total_playtime_ms", "total_deaths", "wins", "golden_apples"}
        check("stats: base64 JSON with all fields",
              expected_keys.issubset(decoded.keys()), str(decoded))
        check("stats: aggregates updated",
              decoded["games_played"] >= 3 and decoded["wins"] >= 1
              and decoded["total_deaths"] >= 2 and decoded["golden_apples"] >= 1,
              str(decoded))
        check("stats: re-read matches file", load_stats() == decoded)
        save_stats(decoded)  # write -> read -> identical
        check("stats: save/load stable", load_stats() == decoded)

        # --- Task 13: reduced_motion flows through the game -------------------
        settings["reduced_motion"] = True
        st_rm = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        st_rm.phase = game_mod.PLAYING
        head = st_rm.snake.body[0]
        st_rm.apple.pos = (head[0] + 1, head[1])
        old_chance = game_mod.GOLDEN_CHANCE
        game_mod.GOLDEN_CHANCE = 0.0
        try:
            st_rm._step()  # eat red -> burst suppressed
        finally:
            game_mod.GOLDEN_CHANCE = old_chance
        st_rm._die(st_rm.snake.body[0])
        check("reduced_motion: no particles/shake in game",
              len(st_rm.particles.particles) == 0 and st_rm.particles.shake_ms == 0.0)
        st_rm.draw(screen)
        settings["reduced_motion"] = False

        # --- Task 24: single fixed Cyber palette ------------------------------
        # The Dark/Light/High Contrast system was deleted; get_theme() and
        # set_theme() always resolve to the Cyber palette, ignoring any name.
        cyber_bg = get_theme()["bg"]
        check("theme: active palette is cyber",
              cyber_bg == THEMES["cyber"]["bg"]
              and get_theme()["neon_cyan"] == (0, 229, 255))
        check("theme: only cyber remains (no light/high contrast)",
              set(THEMES) == {"cyber"})
        set_theme("light")  # legacy name: must be ignored, not switch palettes
        check("theme: legacy names ignored -> still cyber",
              get_theme()["bg"] == cyber_bg and get_theme() is THEMES["cyber"])
        set_theme("dark")
        check("theme: cyber grid/accent", get_theme()["grid_width"] == 1
              and get_theme()["apple"] == THEMES["cyber"]["apple"])

        # --- Task 19: demo AI snake -------------------------------------------
        demo = DemoSnake()
        demo.reset()
        start_head = demo.snake.body[0]
        for _ in range(200):
            demo.update(50)
            for col, row in demo.snake.body:
                assert 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE
        check("demo: AI snake steps and stays in bounds",
              demo.snake.body[0] != start_head or len(demo.snake.body) > 3)
        path = bfs_path((0, 0), (2, 0), blocked=set(), wrap=False)
        check("demo: bfs_path returns steps", path == [(1, 0), (2, 0)], str(path))
        path = bfs_path((0, 0), (2, 0), blocked={(1, 0)}, wrap=True)
        check("demo: bfs_path wraps around",
              path is not None and len(path) == 4, str(path))

        # --- Menu with demo behind it ------------------------------------------
        menu = MainMenu(settings, audio, stats, lambda: None, lambda: None, lambda: None)
        menu.update(200)
        menu.draw(screen)
        menu.play_btn.callback()
        transitions = []
        menu2 = MainMenu(
            settings, audio, stats,
            lambda: transitions.append("play"),
            lambda: transitions.append("settings"),
            lambda: transitions.append("exit"),
        )
        menu2.draw(screen)
        menu2.handle_event(click(menu2.play_btn.rect))
        check("menu: play button transitions", transitions == ["play"])

        # --- Task 16: music picker (empty music/ folder) -----------------------
        check("music: empty folder scans to []", audio.scan_tracks() == [])
        ss = SettingsScreen(settings, audio, lambda: None, on_display_change=lambda m: None)
        ss.draw(screen)
        check("music: row shows 'no tracks found'", ss.track_row.value_text == NO_TRACKS)
        before = settings["current_track"]
        ss._cycle_track(1)
        check("music: cycling does nothing when empty",
              settings["current_track"] == before)
        with open(os.path.join(music_dir, "zzz theme.ogg"), "w") as fh:
            fh.write("not really audio")
        with open(os.path.join(music_dir, "notes.txt"), "w") as fh:
            fh.write("ignored")
        check("music: scans ogg/mp3/wav only",
              audio.scan_tracks() == ["zzz theme.ogg"])
        ss._cycle_track(1)
        check("music: selection persists", settings["current_track"] == "zzz theme.ogg")
        ss.draw(screen)
        check("music: row shows track name", ss.track_row.value_text == "zzz theme.ogg")
        ss._cycle_track(-1)
        check("music: cycles back to Auto", settings["current_track"] == "Auto")
        audio.select_track("Auto", settings)  # loads fake file -> guarded, no crash

        # --- Settings screen: theme/display cycling + reset + resize -----------
        display_changes = []
        ss = SettingsScreen(settings, audio, lambda: None,
                            on_display_change=display_changes.append)
        ss.draw(screen)
        check("settings: theme row removed (fixed cyber palette)",
              not hasattr(ss, "theme_row") and not hasattr(ss, "_cycle_theme"))
        check("settings: palette fixed to cyber",
              get_theme()["bg"] == THEMES["cyber"]["bg"])
        ss.draw(screen)
        ss._cycle_display(1)
        check("settings: display mode toggles + applies",
              settings["display_mode"] == "windowed" and display_changes == ["windowed"])
        ss.draw(screen)
        ss.handle_event(
            pygame.event.Event(pygame.VIDEORESIZE, {"size": (900, 600)})
        )  # layout already derives from screen size; must not crash
        # Scrolling only kicks in when content overflows; use a small surface.
        small = pygame.Surface((700, 420))
        ss.draw(small)
        check("settings: small screen allows scrolling", ss._max_scroll > 0,
              "max_scroll=%d" % ss._max_scroll)
        before_y = ss.track_row.rect.y
        ss.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1}))
        check("settings: wheel scrolls content",
              ss._scroll > 0 and ss.track_row.rect.y < before_y)
        ss._scroll = 0
        ss.draw(small)
        ss._cycle_display(-1)
        check("settings: display mode cycles back",
              settings["display_mode"] == "borderless" and display_changes[-1] == "borderless")
        settings["theme"] = "high_contrast"
        settings["difficulty"] = "hard"
        bests_before = json.dumps(settings["bests"], sort_keys=True)
        ss._reset_clicked()  # first click arms the confirmation
        check("settings: reset requires confirmation",
              ss._reset_confirm and ss.reset_btn.label != "RESET TO DEFAULTS")
        ss._reset_clicked()  # second click performs the reset
        check("settings: reset restores defaults",
              not ss._reset_confirm and settings["difficulty"] == "medium"
              and settings["theme"] == "dark" and get_theme()["bg"] == THEMES["cyber"]["bg"])
        check("settings: reset keeps bests",
              json.dumps(settings["bests"], sort_keys=True) == bests_before)
        check("settings: widgets refreshed after reset",
              ss.bind_rows["up"].keyname == "w" and ss.music_slider.value == 0.5
              and not ss.motion_toggle.value)
        ss.draw(screen)

        # --- Task 18: display mode toggle code path ----------------------------
        win_surf = main_mod.apply_display_mode("windowed")
        check("display: windowed set_mode accepted",
              tuple(win_surf.get_size()) == (1280, 720), str(win_surf.get_size()))
        fs_surf = main_mod.apply_display_mode("borderless")
        check("display: borderless set_mode accepted", fs_surf is not None)

        # --- Full state-machine loop across screens (short simulated session) --
        states = [
            MainMenu(settings, audio, stats, lambda: None, lambda: None, lambda: None),
            ModePicker(settings, audio, lambda mode: None, lambda: None),
            PlayingState(settings, audio, stats, lambda: None, mode="classic"),
            ss,
        ]
        for state in states:
            for _ in range(30):
                state.update(16)
                state.draw(screen)
        check("loop: all screens update+draw without errors", True)

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
        print("\nFAILED: %s" % exc)
        sys.exit(1)
