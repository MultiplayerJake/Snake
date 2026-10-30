"""Extra headless tests for coverage gaps left by smoke_test.py.

Run (from anywhere): .\\.venv\\Scripts\\python.exe tests\\test_extra.py
Or run every suite:  .\\.venv\\Scripts\\python.exe tests\\run_all.py

Covers: keybind rebinding edge cases, board-full win, time-attack pause,
music selection with a real (tiny) .ogg/.wav present, windowed resize
relayout, demo AI snake long-run stability, stats.dat & settings.json
corruption recovery, reset-keeps-bests persistence. Uses SDL dummy drivers
and temp files only - the real settings.json / stats.dat are never touched.
Exits 0 on success.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
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
from game import settings as settings_mod  # noqa: E402
from game import stats as stats_mod  # noqa: E402
from game import audio as audio_mod  # noqa: E402
from game.ai import DEMO_RESET_LENGTH, DemoSnake  # noqa: E402
from game.constants import GRID_SIZE, NAME_TO_KEY, PAUSED, PLAYING  # noqa: E402
from game.constants import GAME_OVER  # noqa: E402
from game.game import COUNTDOWN, PlayingState  # noqa: E402
from game.menu import MainMenu  # noqa: E402
from game.settings import load_settings, reset_to_defaults, save_settings  # noqa: E402
from game.settings_screen import SettingsScreen  # noqa: E402
from game.stats import STATS_DEFAULTS, load_stats  # noqa: E402

import main as main_mod  # noqa: E402

PASS = 0
FAILURES = []


def check(label, condition, detail=""):
    global PASS
    if not condition:
        FAILURES.append("%s %s" % (label, detail))
        raise AssertionError("%s %s" % (label, detail))
    PASS += 1
    print("PASS  %s" % label)


def key(keycode):
    return pygame.event.Event(pygame.KEYDOWN, {"key": keycode})


def click(rect):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": rect.center, "button": 1})


def motion(pos):
    return pygame.event.Event(pygame.MOUSEMOTION, {"pos": pos})


def write_stats_file(payload_obj):
    """Write a valid-base64 stats.dat containing payload_obj (or raw string)."""
    if isinstance(payload_obj, (dict, list)):
        raw = json.dumps(payload_obj).encode("utf-8")
        text = base64.b64encode(raw).decode("ascii")
    else:
        text = str(payload_obj)
    with open(stats_mod.STATS_PATH, "w", encoding="ascii") as fh:
        fh.write(text)


def main():
    tmp = tempfile.mkdtemp(prefix="quick_snake_extra_")
    try:
        settings_mod.SETTINGS_PATH = os.path.join(tmp, "settings.json")
        stats_mod.STATS_PATH = os.path.join(tmp, "stats.dat")
        music_dir = os.path.join(tmp, "music")
        os.makedirs(music_dir, exist_ok=True)
        audio_mod.MUSIC_DIR = music_dir

        # Real (tiny but valid) wav tracks for the music picker tests.
        for name in ("a_first.wav", "b_second.wav"):
            with wave.open(os.path.join(music_dir, name), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(8000)
                wav.writeframes(b"\x00\x00" * 400)  # 50 ms of silence

        pygame.init()
        screen = pygame.display.set_mode((1280, 720))

        settings = load_settings()
        audio = audio_mod.AudioManager(settings)
        stats = load_stats()

        # =====================================================================
        # 1. Keybind rebinding edge cases
        # =====================================================================
        ss = SettingsScreen(settings, audio, lambda: None, on_display_change=lambda m: None)
        ss.draw(screen)  # lay out widget rects

        # 1a. Click row -> "press any key" -> new key applied + persisted.
        up_row = ss.bind_rows["up"]
        ss.handle_event(click(up_row.rect))
        check("rebind: click enters waiting mode", up_row.waiting)
        ss.handle_event(key(pygame.K_i))
        check("rebind: key press rebinds up -> i",
              settings["keybinds"]["up"] == "i" and not up_row.waiting)
        saved = json.load(open(settings_mod.SETTINGS_PATH, encoding="utf-8"))
        check("rebind: persisted immediately to disk",
              saved["keybinds"]["up"] == "i", str(saved["keybinds"]))

        # 1b. Conflict swap: bind up -> s (currently down's key).
        settings["keybinds"].update({"up": "w", "down": "s"})
        ss.bind_rows["up"].keyname = "w"
        ss.bind_rows["down"].keyname = "s"
        ss.handle_event(click(up_row.rect))
        ss.handle_event(key(pygame.K_s))
        check("rebind: conflict swaps down -> w",
              settings["keybinds"]["up"] == "s" and settings["keybinds"]["down"] == "w",
              str(settings["keybinds"]))
        check("rebind: swap reflected in the other row's widget",
              ss.bind_rows["down"].keyname == "w")

        # 1c. ESC cancels waiting without rebinding.
        ss.handle_event(click(up_row.rect))
        check("rebind: waiting again", up_row.waiting)
        ss.handle_event(key(pygame.K_ESCAPE))
        check("rebind: ESC cancels, binding unchanged",
              not up_row.waiting and settings["keybinds"]["up"] == "s")

        # 1d. Clicking elsewhere cancels waiting.
        ss.handle_event(click(up_row.rect))
        ss.handle_event(click(pygame.Rect(0, 0, 4, 4)))  # outside any widget
        check("rebind: click elsewhere cancels waiting", not up_row.waiting)

        # 1e. Special keys round-trip through the portable name map.
        ss.handle_event(click(up_row.rect))
        ss.handle_event(key(pygame.K_UP))
        check("rebind: arrow key stored as portable name 'up'",
              settings["keybinds"]["up"] == "up"
              and NAME_TO_KEY["up"] == pygame.K_UP)
        # Restore the post-swap state: up="s", down="w".
        ss._rebind("up", "s")

        # 1f. Rebinding to the same key is a no-op (no swap side effects).
        before = dict(settings["keybinds"])
        ss.handle_event(click(up_row.rect))
        ss.handle_event(key(pygame.K_s))
        check("rebind: same key is a no-op", settings["keybinds"] == before)

        # 1g. Rebound keys actually control the snake in-game.
        st = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        st.phase = PLAYING
        st.snake.direction = (1, 0)
        st.snake.pending_dir = None
        st.handle_event(key(pygame.K_s))  # rebound to "up" in 1b
        check("rebind: rebound key feeds snake input",
              st.snake.pending_dir == (0, -1), str(st.snake.pending_dir))
        ss._rebind("up", "up")  # bind up to the arrow key instead
        st.snake.pending_dir = None
        st.handle_event(key(pygame.K_UP))
        check("rebind: arrow key controls snake live",
              st.snake.pending_dir == (0, -1))
        st.snake.pending_dir = None
        st.handle_event(key(pygame.K_LEFT))  # 180-degree reversal ignored
        check("rebind: reversal still blocked after rebind",
              st.snake.pending_dir is None)

        # 1h. Documented limitation: 'p' can be bound but pause wins (ESC/P
        # is checked before movement). Must not crash or move the snake.
        ss._rebind("right", "p")
        st2 = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        st2.phase = PLAYING
        st2.handle_event(key(pygame.K_p))
        check("rebind: pause key takes precedence (documented)",
              st2.phase == PAUSED and st2.snake.pending_dir is None)
        ss._rebind("right", "d")  # restore defaults

        # 1i. Unknown key names in settings.json fall back to defaults.
        payload = json.load(open(settings_mod.SETTINGS_PATH, encoding="utf-8"))
        payload["keybinds"]["up"] = "not_a_real_key"
        with open(settings_mod.SETTINGS_PATH, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        reloaded = load_settings()
        check("rebind: unknown key name sanitized to default",
              reloaded["keybinds"]["up"] == "w", str(reloaded["keybinds"]))
        settings = reloaded

        # =====================================================================
        # 2. Board-full win condition
        # =====================================================================
        old_chance = game_mod.GOLDEN_CHANCE
        game_mod.GOLDEN_CHANCE = 0.0
        try:
            bf = PlayingState(settings, audio, stats, lambda: None, mode="classic")
            bf.phase = PLAYING
            bf.timer_running = True
            # 624 body cells covering every cell except head (0,0) and (1,0).
            head = (0, 0)
            ahead = (1, 0)
            rest = [(c, r) for c in range(GRID_SIZE) for r in range(GRID_SIZE)
                    if (c, r) not in (head, ahead)]
            bf.snake.body = [head] + rest  # 624 cells
            bf.snake.prev_body = list(bf.snake.body)
            bf.snake.direction = (1, 0)
            bf.snake.pending_dir = None
            bf.snake.grow_by = 1  # tail must not vacate a cell
            bf.apple.pos = ahead
            bf._step()  # eats last apple -> board full -> YOU WIN
            check("board full: win triggered", bf.phase == GAME_OVER and bf.won)
            check("board full: 625 unique cells", len(bf.snake.body) == GRID_SIZE ** 2
                  and len(set(bf.snake.body)) == GRID_SIZE ** 2)
            check("board full: best score recorded",
                  settings["bests"]["classic"]["best_score"] >= 1)
            bf.draw(screen)  # YOU WIN overlay renders
            check("board full: win overlay draws", True)

            # Same in time attack: board full also wins (and records a clear).
            settings["difficulty"] = "easy"
            ba = PlayingState(settings, audio, stats, lambda: None, mode="time_attack")
            ba.phase = PLAYING
            ba.timer_running = True
            ba.snake.body = [head] + rest
            ba.snake.prev_body = list(ba.snake.body)
            ba.snake.direction = (1, 0)
            ba.snake.pending_dir = None
            ba.snake.grow_by = 1
            ba.apple.pos = ahead
            ba._step()
            check("board full: time attack wins too",
                  ba.phase == GAME_OVER and ba.won)
            check("board full: time attack records fastest clear",
                  settings["bests"]["time_attack"]["by_difficulty"]["easy"] is not None)
            ba.draw(screen)
            settings["difficulty"] = "medium"
        finally:
            game_mod.GOLDEN_CHANCE = old_chance

        # =====================================================================
        # 3. Time attack pause
        # =====================================================================
        ta = PlayingState(settings, audio, stats, lambda: None, mode="time_attack")
        ta.phase = PLAYING
        ta.timer_running = True
        ta.update(100)
        remaining_before = ta.remaining_ms
        timer_before = ta.timer_ms
        check("ta pause: countdown ticks while playing",
              remaining_before < ta.time_limit_ms)
        ta.handle_event(key(pygame.K_ESCAPE))
        check("ta pause: ESC pauses", ta.phase == PAUSED)
        for _ in range(5):
            ta.update(100)
        check("ta pause: remaining time frozen",
              ta.remaining_ms == remaining_before, str(ta.remaining_ms))
        check("ta pause: run timer frozen too",
              ta.timer_ms == timer_before, str(ta.timer_ms))
        head_before = list(ta.snake.body)
        ta.handle_event(key(pygame.K_s))  # movement ignored while paused
        check("ta pause: movement ignored while paused",
              ta.snake.body == head_before and ta.snake.pending_dir is None)
        ta.handle_event(key(pygame.K_p))
        check("ta pause: P resumes", ta.phase == PLAYING)
        ta.update(100)
        check("ta pause: countdown resumes after unpause",
              ta.remaining_ms < remaining_before)

        # Pause is impossible during the countdown phase.
        cd = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        check("ta pause: countdown phase starts", cd.phase == COUNTDOWN)
        cd.handle_event(key(pygame.K_ESCAPE))
        check("ta pause: ESC ignored during countdown", cd.phase == COUNTDOWN)

        # Pause overlay buttons: RESUME / RESTART / MENU all work.
        ta.handle_event(key(pygame.K_ESCAPE))
        check("ta pause: paused again", ta.phase == PAUSED)
        ta.draw(screen)  # lays out overlay buttons
        ta.score = 5
        ta.handle_event(click(ta.pause_restart_btn.rect))
        check("ta pause: RESTART resets run",
              ta.phase == COUNTDOWN and ta.score == 0 and ta.remaining_ms == ta.time_limit_ms)
        ta.phase = PLAYING
        ta.handle_event(key(pygame.K_p))
        ta.draw(screen)
        ta.handle_event(click(ta.pause_resume_btn.rect))
        check("ta pause: RESUME button works", ta.phase == PLAYING)

        # Game over overlay buttons: PLAY AGAIN -> fresh countdown.
        st.phase = GAME_OVER
        st.draw(screen)
        st.score = 9
        st.handle_event(click(st.over_play_btn.rect))
        check("game over: PLAY AGAIN starts a fresh countdown",
              st.phase == COUNTDOWN and st.score == 0)

        # =====================================================================
        # 4. Music selection with real (tiny) wav files present
        # =====================================================================
        check("music+: scans both wavs (sorted)",
              audio.scan_tracks() == ["a_first.wav", "b_second.wav"],
              str(audio.scan_tracks()))
        if audio.available:
            check("music+: Auto starts first track",
                  audio.track_path("Auto") is not None
                  and audio.track_path("Auto").endswith("a_first.wav"))
            ok = audio.select_track("b_second.wav", settings)
            check("music+: selecting a real track loads it",
                  ok and audio.music_path is not None
                  and audio.music_path.endswith("b_second.wav"))
            check("music+: selection persisted",
                  settings["current_track"] == "b_second.wav")
            ok = audio.select_track("missing.wav", settings)
            check("music+: unknown name falls back to first track",
                  ok and audio.music_path.endswith("a_first.wav"))
            audio.select_track("Auto", settings)
        else:
            print("SKIP  music+: mixer unavailable, load paths skipped")

        ss2 = SettingsScreen(settings, audio, lambda: None, on_display_change=lambda m: None)
        ss2.draw(screen)
        ss2._cycle_track(1)  # Auto -> a_first.wav
        check("music+: settings row cycles real tracks",
              settings["current_track"] == "a_first.wav")
        ss2.draw(screen)
        check("music+: row shows current track",
              ss2.track_row.value_text == "a_first.wav")
        ss2._cycle_track(-1)
        check("music+: cycles back to Auto", settings["current_track"] == "Auto")

        # =====================================================================
        # 5. Windowed resize relayout
        # =====================================================================
        win = main_mod.apply_display_mode("windowed")
        check("resize: windowed mode 1280x720", tuple(win.get_size()) == (1280, 720))
        small = pygame.Surface((800, 600))  # simulated resized window
        st.phase = PLAYING
        st.draw(screen)  # establish full-size metrics first
        old_metrics = st._last_metrics
        st.phase = PLAYING
        st.draw(small)
        check("resize: playing grid metrics recomputed",
              st._last_metrics != old_metrics
              and st._last_metrics[0] < old_metrics[0],
              "%s vs %s" % (st._last_metrics, old_metrics))
        st.phase = PAUSED
        st.draw(small)  # overlay relayouts inside the smaller surface
        check("resize: pause overlay redraws on small surface", True)

        menu = MainMenu(settings, audio, stats, lambda: None, lambda: None, lambda: None)
        menu.draw(small)
        check("resize: menu buttons relayout inside small window",
              all(0 <= b.rect.x and b.rect.right <= 800 and b.rect.bottom <= 600
                  for b in menu.buttons))
        ss2.draw(small)
        check("resize: settings back/reset buttons inside small window",
              ss2.back_btn.rect.right <= 800 and ss2.reset_btn.rect.bottom <= 600
              and ss2.back_btn.rect.bottom <= 600)
        ss2.handle_event(pygame.event.Event(pygame.VIDEORESIZE, {"size": (800, 600)}))
        check("resize: VIDEORESIZE event harmless", True)
        # Resize back up: layout must follow the new size again.
        big = pygame.Surface((1280, 720))
        ss2.draw(big)
        check("resize: layout follows size back up",
              ss2._size == (1280, 720) and ss2.back_btn.rect.right <= 1280)
        main_mod.apply_display_mode("borderless")

        # =====================================================================
        # 6. Demo AI snake long-run stability
        # =====================================================================
        demo = DemoSnake()
        max_len = 3
        ate = False
        for i in range(2500):
            demo.update(160)
            if i % 250 == 0:
                body = demo.snake.body
                check("demo long-run: in bounds @ iter %d" % i,
                      all(0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE for c, r in body))
                check("demo long-run: unique cells @ iter %d" % i,
                      len(set(body)) == len(body))
                check("demo long-run: apple off snake @ iter %d" % i,
                      demo.apple.pos not in body)
            max_len = max(max_len, len(demo.snake.body))
            if len(demo.snake.body) > 3:
                ate = True
        check("demo long-run: survived 2500 updates without death/reset-lock",
              ate and max_len <= DEMO_RESET_LENGTH + 2,
              "max_len=%d ate=%s" % (max_len, ate))
        check("demo long-run: ate apples along the way", ate)
        demo.draw(screen, 0, 40, 20)  # rendering path with wrapped segments
        check("demo long-run: draw after long run OK", True)

        # =====================================================================
        # 7. stats.dat corruption recovery
        # =====================================================================
        write_stats_file("!!!definitely not base64!!!")
        check("stats corrupt: garbage falls back to defaults",
              load_stats() == STATS_DEFAULTS)
        write_stats_file(base64.b64encode(b"[1, 2, 3]").decode("ascii"))
        check("stats corrupt: non-dict root falls back to defaults",
              load_stats() == STATS_DEFAULTS)
        write_stats_file({"games_played": -5, "total_apples": 2.7, "wins": True,
                          "total_score": "lots", "mystery": 1})
        recovered = load_stats()
        check("stats corrupt: bad field types sanitized",
              recovered["games_played"] == 0 and recovered["total_apples"] == 2
              and recovered["wins"] == 0 and recovered["total_score"] == 0,
              str(recovered))
        check("stats corrupt: unknown keys dropped", "mystery" not in recovered)
        os.remove(stats_mod.STATS_PATH)
        check("stats corrupt: missing file -> defaults", load_stats() == STATS_DEFAULTS)
        write_stats_file({"games_played": 3, "total_apples": 12})
        partial = load_stats()
        check("stats corrupt: partial dict keeps provided values, fills defaults",
              partial["games_played"] == 3 and partial["wins"] == 0
              and set(partial) == set(STATS_DEFAULTS), str(partial))

        # =====================================================================
        # 8. settings.json corruption recovery
        # =====================================================================
        def write_settings_file(obj):
            with open(settings_mod.SETTINGS_PATH, "w", encoding="utf-8") as fh:
                if isinstance(obj, str):
                    fh.write(obj)
                else:
                    json.dump(obj, fh)

        write_settings_file("{ not json !!")
        check("settings corrupt: garbage -> defaults",
              load_settings()["difficulty"] == "medium"
              and load_settings()["theme"] == "dark")
        write_settings_file([1, 2, 3])
        check("settings corrupt: non-dict root -> defaults",
              load_settings()["keybinds"] == {"up": "w", "down": "s",
                                              "left": "a", "right": "d"})
        write_settings_file({"music_volume": 9, "sfx_volume": -3,
                             "difficulty": "impossible", "theme": "neon",
                             "display_mode": "hologram", "timer_enabled": "yes",
                             "last_mode": "battle royale",
                             "keybinds": {"up": "zzz", "left": 5},
                             "bests": "junk"})
        fixed = load_settings()
        check("settings corrupt: volumes clamped 0..1",
              fixed["music_volume"] == 1.0 and fixed["sfx_volume"] == 0.0)
        check("settings corrupt: invalid enums -> defaults",
              fixed["difficulty"] == "medium" and fixed["theme"] == "dark"
              and fixed["display_mode"] == "borderless"
              and fixed["last_mode"] == "classic")
        check("settings corrupt: non-bool toggle -> default",
              fixed["timer_enabled"] is False)
        check("settings corrupt: bad keybinds -> defaults",
              fixed["keybinds"] == {"up": "w", "down": "s",
                                    "left": "a", "right": "d"},
              str(fixed["keybinds"]))
        check("settings corrupt: junk bests -> default structure",
              fixed["bests"]["classic"]["best_score"] == 0
              and fixed["bests"]["time_attack"]["by_difficulty"] == {
                  "easy": None, "medium": None, "hard": None})
        os.remove(settings_mod.SETTINGS_PATH)
        check("settings corrupt: missing file -> defaults",
              load_settings() == settings_mod.DEFAULT_SETTINGS)

        # Legacy migration merge edge: legacy values override existing classic.
        write_settings_file({"best_score": 9,
                             "bests": {"classic": {"best_score": 3},
                                       "speedrun": {"best_score": 4}}})
        migrated = load_settings()
        check("settings corrupt: legacy migrates over classic entry",
              migrated["bests"]["classic"]["best_score"] == 9
              and migrated["bests"]["speedrun"]["best_score"] == 4
              and "best_score" not in migrated)
        # Legacy junk values are dropped, not merged.
        write_settings_file({"best_score": "twelve", "best_time_ms": -5})
        migrated = load_settings()
        check("settings corrupt: junk legacy bests dropped",
              migrated["bests"]["classic"]["best_score"] == 0
              and migrated["bests"]["classic"]["best_time_ms"] is None)

        # =====================================================================
        # 9. Reset to defaults keeps bests (end-to-end incl. disk + .bak)
        # =====================================================================
        write_settings_file({})
        settings = load_settings()
        settings["bests"]["classic"]["best_score"] = 42
        settings["bests"]["classic"]["best_time_ms"] = 123456
        settings["bests"]["time_attack"]["by_difficulty"]["hard"] = 55000
        settings["difficulty"] = "hard"
        settings["theme"] = "high_contrast"
        save_settings(settings)
        ss3 = SettingsScreen(settings, audio, lambda: None, on_display_change=lambda m: None)
        ss3.draw(screen)
        expected_bests = json.dumps(settings["bests"], sort_keys=True)
        ss3._reset_clicked()  # arm
        check("reset: armed state persists across frames",
              ss3._reset_confirm and ss3.reset_btn.label != "RESET TO DEFAULTS")
        # Moving off the button cancels the confirmation (plan pseudocode 20).
        ss3.handle_event(motion((1, 1)))
        check("reset: mouse leaving button cancels confirmation",
              not ss3._reset_confirm and ss3.reset_btn.label == "RESET TO DEFAULTS")
        ss3._reset_clicked()
        ss3._reset_clicked()  # confirm
        check("reset: defaults restored",
              settings["difficulty"] == "medium" and settings["theme"] == "dark")
        check("reset: all bests kept incl. per-difficulty",
              json.dumps(settings["bests"], sort_keys=True) == expected_bests,
              json.dumps(settings["bests"]))
        on_disk = json.load(open(settings_mod.SETTINGS_PATH, encoding="utf-8"))
        check("reset: kept bests persisted to disk",
              on_disk["bests"]["classic"]["best_score"] == 42
              and on_disk["bests"]["time_attack"]["by_difficulty"]["hard"] == 55000)
        bak = json.load(open(settings_mod.SETTINGS_PATH + ".bak", encoding="utf-8"))
        check("reset: .bak holds the pre-reset settings",
              bak["difficulty"] == "hard" and bak["theme"] == "high_contrast")
        # reset_to_defaults on a dict without bests must not crash.
        bare = {"difficulty": "hard"}
        reset_to_defaults(bare)
        check("reset: works on dict missing bests",
              bare["bests"]["classic"]["best_score"] == 0)

        # =====================================================================
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
