"""Headless tests for the Phase 3 gameplay half (Tasks 20, 21, 22, 23, 26-logic)
+ Phase 3.5 (Tasks 27, 28, 29).

Run (from anywhere): .\\.venv\\Scripts\\python.exe tests\\test_gameplay3.py
Or run every suite:  .\\.venv\\Scripts\\python.exe tests\\run_all.py

Covers: golden apple never spawns in Time Attack (forced spawn rolls) but
does in Classic, GOLDEN_LIFETIME_MS == 5000, UnbindButton (sets keybind to
None + persists + "[ unbound ]" label + action inert in game + rebind works
after + scrolls with its row), conflict-swap with unbound slots, mode picker
renders all three buttons identically (no last_mode highlight, pixel-compared),
the P-key force-bind warning (first press warns without binding, second
press binds, ESC cancels, click-elsewhere/other key clears armed state),
mode picker gap is exactly base+10px (Task 27), procedural stdlib WAV
generation into a fresh sfx/ with recipe-exact durations + regeneration +
corrupt/missing file guards (Task 28), and SFX wiring: eat/death/win/countdown
hooks, Button click SFX, per-play settings volume (Task 29).

SDL dummy drivers and temp settings/stats files only — the real
settings.json / stats.dat are never touched. Exits 0 on success.
"""

from __future__ import annotations

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
from game import audio as audio_mod  # noqa: E402
from game import settings as settings_mod  # noqa: E402
from game import stats as stats_mod  # noqa: E402
from game.apple import GoldenApple  # noqa: E402
from game.constants import (  # noqa: E402
    GOLDEN_LIFETIME_MS,
    GOLDEN_POINTS,
    GAME_OVER,
    MODES,
    PAUSED,
    PLAYING,
)
from game.game import PlayingState  # noqa: E402
from game.mode_picker import ModePicker  # noqa: E402
from game.settings import load_settings  # noqa: E402
from game.settings_screen import SettingsScreen  # noqa: E402
from game.stats import load_stats  # noqa: E402
from game.themes import get_theme  # noqa: E402
from game.ui import P_PAUSE_WARNING, Button, UnbindButton  # noqa: E402
from game import ui as ui_mod  # noqa: E402

PASS = 0
BG_KNOWN = (80, 0, 0)  # sentinel fill so blends are detectable


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


def has_color(surface, rect, color):
    """Any pixel inside rect (clipped to the surface) exactly matches color."""
    bounds = surface.get_rect().clip(rect)
    for y in range(bounds.y, bounds.bottom):
        for x in range(bounds.x, bounds.right):
            if surface.get_at((x, y))[:3] == color:
                return True
    return False


def main():
    tmp = tempfile.mkdtemp(prefix="quick_snake_gameplay3_")
    try:
        # Point all persistence at temp files (live settings/stats untouched).
        settings_mod.SETTINGS_PATH = os.path.join(tmp, "settings.json")
        stats_mod.STATS_PATH = os.path.join(tmp, "stats.dat")
        music_dir = os.path.join(tmp, "music")
        os.makedirs(music_dir, exist_ok=True)
        audio_mod.MUSIC_DIR = music_dir

        pygame.init()
        screen = pygame.display.set_mode((1280, 720))
        theme = get_theme()

        settings = load_settings()
        audio = audio_mod.AudioManager(settings)
        stats = load_stats()

        # =====================================================================
        # 1. Golden apple: Task 21 lifetime + Task 20 Time Attack gating
        # =====================================================================
        check("golden: GOLDEN_LIFETIME_MS is 5000", GOLDEN_LIFETIME_MS == 5000.0,
              str(GOLDEN_LIFETIME_MS))
        g = GoldenApple((1, 1))
        check("golden: fresh lifetime is 5000", g.lifetime_ms == 5000.0,
              str(g.lifetime_ms))
        check("golden: urgency starts at 1.0", g.urgency == 1.0)
        g.update(1000)
        check("golden: lifetime counts down", g.lifetime_ms == 4000.0,
              str(g.lifetime_ms))

        settings["difficulty"] = "easy"
        old_chance = game_mod.GOLDEN_CHANCE
        game_mod.GOLDEN_CHANCE = 1.0  # every roll must produce a golden apple
        try:
            # Time Attack: 30 forced rolls -> the golden apple never spawns.
            ta = PlayingState(settings, audio, stats, lambda: None, mode="time_attack")
            ta.phase = PLAYING
            for i in range(30):
                ta.snake.body = [(5, 5), (4, 5), (3, 5)]
                ta.snake.prev_body = list(ta.snake.body)
                ta.snake.direction = (1, 0)
                ta.snake.pending_dir = None
                ta.snake.grow_by = 0
                ta.apples_eaten = 0  # keep the win target out of the way
                ta.golden = None
                ta.apple.pos = (6, 5)
                ta._step()  # eats the red apple -> spawn roll happens
                if ta.golden is not None:
                    raise AssertionError(
                        "time attack: golden spawned on roll %d" % i)
            check("time attack: golden never spawns (30 forced rolls)", True)
            check("time attack: red apples still eaten normally",
                  ta.apples_eaten == 1 and ta.score == 30, str(ta.score))

            # Defensive: a golden apple already present is still edible.
            ta.snake.body = [(5, 5), (4, 5), (3, 5)]
            ta.snake.prev_body = list(ta.snake.body)
            ta.snake.direction = (1, 0)
            ta.snake.pending_dir = None
            ta.apple.pos = (0, 0)  # keep the red apple off the head's path
            ta.golden = GoldenApple((6, 5))
            score_before = ta.score
            ta._step()
            check("time attack: pre-existing golden still edible (defensive)",
                  ta.golden is None and ta.score == score_before + GOLDEN_POINTS)

            # Classic: same forced rolls -> spawns every time.
            st = PlayingState(settings, audio, stats, lambda: None, mode="classic")
            st.phase = PLAYING
            spawns = 0
            for _ in range(30):
                st.snake.body = [(5, 5), (4, 5), (3, 5)]
                st.snake.prev_body = list(st.snake.body)
                st.snake.direction = (1, 0)
                st.snake.pending_dir = None
                st.snake.grow_by = 0
                st.golden = None
                st.apple.pos = (6, 5)
                st._step()
                if st.golden is not None:
                    spawns += 1
            check("classic: golden spawns on every forced roll",
                  spawns == 30, str(spawns))
        finally:
            game_mod.GOLDEN_CHANCE = old_chance

        # =====================================================================
        # 2. Task 22: Unbind button — None binding, persistence, inert, rebind
        # =====================================================================
        ss = SettingsScreen(settings, audio, lambda: None,
                            on_display_change=lambda m: None)
        ss.draw(screen)  # lay out widget rects

        up_row = ss.bind_rows["up"]
        up_unbind = ss.unbind_buttons["up"]
        check("unbind: button exists next to every keybind row",
              set(ss.unbind_buttons) == set(ss.bind_rows)
              and all(isinstance(b, UnbindButton) for b in ss.unbind_buttons.values()))
        check("unbind: square button right of its row",
              up_unbind.rect.w == up_row.rect.h
              and up_unbind.rect.x >= up_row.rect.right
              and up_unbind.rect.x - up_row.rect.right <= 12,
              "%s vs %s" % (up_unbind.rect, up_row.rect))

        ss.handle_event(click(up_unbind.rect))
        check("unbind: click sets the binding to None",
              settings["keybinds"]["up"] is None, str(settings["keybinds"]))
        check("unbind: row widget follows the None binding",
              up_row.keyname is None and not up_row.waiting)
        on_disk = json.load(open(settings_mod.SETTINGS_PATH, encoding="utf-8"))
        check("unbind: None persisted to disk", on_disk["keybinds"]["up"] is None,
              str(on_disk["keybinds"]))
        check("unbind: None survives a settings reload",
              load_settings()["keybinds"]["up"] is None)
        check("unbind: row renders '[ unbound ]' text",
              up_row.prompt_text() == "[ unbound ]",
              up_row.prompt_text())
        u_surf = pygame.Surface((1280, 720))
        ss.draw(u_surf)  # renders the "[ unbound ]" row without error
        check("unbind: settings screen draws with unbound rows", True)

        # Unbound action is inert in game; other actions still work.
        st2 = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        st2.phase = PLAYING
        st2.snake.direction = (1, 0)
        st2.snake.pending_dir = None
        st2.handle_event(key(pygame.K_w))  # up is unbound -> must do nothing
        check("unbind: unbound action never fires in game",
              st2.snake.pending_dir is None, str(st2.snake.pending_dir))
        st2.handle_event(key(pygame.K_s))  # down still bound to "s"
        check("unbind: other actions still fire",
              st2.snake.pending_dir == (0, 1), str(st2.snake.pending_dir))

        # Rebinding still works after an unbind.
        ss.handle_event(click(up_row.rect))
        check("unbind: clicking the row still enters waiting mode", up_row.waiting)
        ss.handle_event(key(pygame.K_u))
        check("unbind: rebind works after unbind",
              settings["keybinds"]["up"] == "u" and up_row.keyname == "u"
              and up_row.prompt_text() == "U",
              str(settings["keybinds"]["up"]))

        # The unbind button scrolls with its row.
        small = pygame.Surface((700, 420))
        ss.draw(small)
        check("unbind: small screen allows scrolling", ss._max_scroll > 0,
              "max_scroll=%d" % ss._max_scroll)
        before_gap_y = up_unbind.rect.y - up_row.rect.y
        before_gap_x = up_unbind.rect.x - up_row.rect.right
        ss.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1}))
        check("unbind: button scrolls together with its row",
              up_unbind.rect.y - up_row.rect.y == before_gap_y
              and up_unbind.rect.x - up_row.rect.right == before_gap_x)
        ss._scroll = 0
        ss.draw(screen)

        # =====================================================================
        # 3. Conflict-swap with unbound slots
        # =====================================================================
        settings["keybinds"].update({"up": "w", "down": None, "left": "a", "right": "d"})
        for action, name in settings["keybinds"].items():
            ss.bind_rows[action].keyname = name
        ss.draw(screen)
        down_row = ss.bind_rows["down"]
        ss.handle_event(click(down_row.rect))
        ss.handle_event(key(pygame.K_w))  # w belongs to (unbound-able) up
        check("swap: binding over a bound slot swaps the old key in",
              settings["keybinds"]["down"] == "w"
              and settings["keybinds"]["up"] is None,
              str(settings["keybinds"]))
        check("swap: unbound slot reflected in the other row's widget",
              up_row.keyname is None and down_row.keyname == "w")
        # Binding into an unbound slot with no conflict just overwrites.
        ss.handle_event(click(down_row.rect))
        ss.handle_event(key(pygame.K_x))
        check("swap: unbound slot accepts a free key directly",
              settings["keybinds"]["down"] == "x"
              and settings["keybinds"]["up"] is None,
              str(settings["keybinds"]))

        # =====================================================================
        # 4. Task 23: mode picker — all buttons render identically
        # =====================================================================
        settings["last_mode"] = "speedrun"  # must not color any button
        started = []
        picker = ModePicker(settings, audio, started.append, lambda: None)
        picker.draw(screen)
        check("mode picker: no accent/active flags on any button",
              all(b.accent is False and b.active is False
                  for b in picker.mode_buttons))

        samples = []
        real_get_pos = pygame.mouse.get_pos
        try:
            pygame.mouse.get_pos = lambda: (0, 0)  # no hover anywhere
            for button in picker.mode_buttons:
                button.rect = pygame.Rect(20, 20, 200, 50)
                b_surf = pygame.Surface((240, 90))
                b_surf.fill(BG_KNOWN)
                button.draw(b_surf)
                samples.append((
                    b_surf.get_at((120, 20))[:3],  # top border center
                    b_surf.get_at((120, 26))[:3],  # interior fill
                    b_surf.get_at((30, 45))[:3],   # interior fill, off text
                ))
        finally:
            pygame.mouse.get_pos = real_get_pos
        check("mode picker: identical pixels across all three buttons",
              samples[0] == samples[1] == samples[2], str(samples))
        check("mode picker: uniform cyan border + button fill (no accent)",
              all(s[0] == theme["neon_cyan"] and s[1] == theme["button"]
                  and s[2] == theme["button"] for s in samples),
              str(samples))

        # Hover state identical too: 3px cyan outline for every button.
        hot_samples = []
        try:
            pygame.mouse.get_pos = lambda: (120, 45)  # inside every button
            for button in picker.mode_buttons:
                b_surf = pygame.Surface((240, 90))
                b_surf.fill(BG_KNOWN)
                button.draw(b_surf)
                hot_samples.append((
                    b_surf.get_at((120, 20))[:3],
                    b_surf.get_at((120, 22))[:3],
                ))
        finally:
            pygame.mouse.get_pos = real_get_pos
        check("mode picker: identical hover rendering for all three",
              hot_samples[0] == hot_samples[1] == hot_samples[2]
              and all(s[0] == theme["neon_cyan"] and s[1] == theme["neon_cyan"]
                      for s in hot_samples),
              str(hot_samples))

        # last_mode is still stored (just no visual difference).
        picker._layout(*screen.get_size())  # rects were moved for pixel sampling
        picker.handle_event(click(picker.buttons_by_mode["time_attack"].rect))
        check("mode picker: last_mode still stored on start",
              started == ["time_attack"] and settings["last_mode"] == "time_attack",
              str(settings["last_mode"]))

        # =====================================================================
        # 5. Task 26 logic: P-key force-bind warning in KeyBindRow
        # =====================================================================
        settings["keybinds"].update({"up": "w", "down": "s", "left": "a", "right": "d"})
        for action, name in settings["keybinds"].items():
            ss.bind_rows[action].keyname = name
        ss.draw(screen)
        up_row = ss.bind_rows["up"]

        ss.handle_event(click(up_row.rect))
        check("p warning: row is waiting", up_row.waiting)
        ss.handle_event(key(pygame.K_p))
        check("p warning: first P press does NOT bind",
              settings["keybinds"]["up"] == "w", str(settings["keybinds"]))
        check("p warning: first P press arms + sets the warning",
              up_row.armed and up_row.warning == P_PAUSE_WARNING
              and not up_row.waiting,
              "%s / %s" % (up_row.armed, up_row.warning))

        # The inline warning renders (warning-colored text in the label area).
        w_surf = pygame.Surface((1280, 720))
        ss.draw(w_surf)
        label_zone = pygame.Rect(
            up_row.rect.x + 6, up_row.rect.centery - 8,
            int(up_row.rect.w * 0.5), 16,
        )
        check("p warning: inline warning text is drawn in warning color",
              has_color(w_surf, label_zone, theme["warning"]))

        # Click the row again, press P a second time -> force-bind applies.
        ss.handle_event(click(up_row.rect))
        check("p warning: re-click keeps armed state and waits again",
              up_row.waiting and up_row.armed)
        ss.handle_event(key(pygame.K_p))
        check("p warning: second P press force-binds",
              settings["keybinds"]["up"] == "p" and up_row.keyname == "p",
              str(settings["keybinds"]))
        check("p warning: binding clears armed + warning",
              not up_row.armed and up_row.warning == "" and not up_row.waiting)
        on_disk = json.load(open(settings_mod.SETTINGS_PATH, encoding="utf-8"))
        check("p warning: force-bind persisted", on_disk["keybinds"]["up"] == "p")

        # ESC cancels waiting and disarms without binding.
        ss._rebind("up", "w")  # restore
        ss.handle_event(click(up_row.rect))
        ss.handle_event(key(pygame.K_p))  # arm
        ss.handle_event(key(pygame.K_ESCAPE))
        check("p warning: ESC cancels waiting and disarms",
              not up_row.waiting and not up_row.armed and up_row.warning == ""
              and settings["keybinds"]["up"] == "w",
              str(settings["keybinds"]))

        # Plain ESC still cancels waiting without any P involved.
        ss.handle_event(click(up_row.rect))
        ss.handle_event(key(pygame.K_ESCAPE))
        check("p warning: plain ESC still cancels waiting", not up_row.waiting)

        # Clicking elsewhere clears armed + warning.
        ss.handle_event(click(up_row.rect))
        ss.handle_event(key(pygame.K_p))  # arm
        ss.handle_event(click(pygame.Rect(0, 0, 4, 4)))  # outside any widget
        check("p warning: click elsewhere clears armed + warning",
              not up_row.waiting and not up_row.armed and up_row.warning == "")

        # Binding a different key applies it and clears armed + warning.
        ss.handle_event(click(up_row.rect))
        ss.handle_event(key(pygame.K_p))  # arm
        ss.handle_event(click(up_row.rect))  # back into waiting, still armed
        ss.handle_event(key(pygame.K_j))  # any other key binds immediately
        check("p warning: binding another key clears armed + warning",
              settings["keybinds"]["up"] == "j" and not up_row.armed
              and up_row.warning == "" and not up_row.waiting,
              str(settings["keybinds"]))

        # P binding still loses to pause in game (documented precedence).
        st3 = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        st3.phase = PLAYING
        st3.handle_event(key(pygame.K_p))
        check("p warning: P bound to a direction still pauses first",
              st3.phase == PAUSED and st3.snake.pending_dir is None)

        # =====================================================================
        # 6. Phase 3.5 Task 27: mode picker gap + exactly 10px, still centered
        # =====================================================================
        for size in ((1280, 720), (800, 600)):
            picker._layout(*size)
            buttons = picker.mode_buttons
            step_a = buttons[1].rect.y - buttons[0].rect.y
            step_b = buttons[2].rect.y - buttons[1].rect.y
            btn_h = buttons[0].rect.h
            base_gap = max(18, btn_h)
            check("spacing: equal step on %dx%d" % size, step_a == step_b,
                  "%d / %d" % (step_a, step_b))
            check("spacing: step grew by exactly +10px on %dx%d" % size,
                  step_a - (base_gap + btn_h) == 10,
                  "step=%d base=%d btn_h=%d" % (step_a, base_gap, btn_h))
            check("spacing: buttons still centered on %dx%d" % size,
                  all(b.rect.centerx == size[0] // 2 for b in buttons),
                  str([b.rect.centerx for b in buttons]))
            # Blurbs under the buttons must still clear the BACK button.
            blurb_size = max(11, min(btn_h // 3, 20))
            blurb_end = (buttons[-1].rect.bottom + max(8, blurb_size)
                         + 2 * blurb_size + blurb_size)
            check("spacing: stack clears the back button on %dx%d" % size,
                  blurb_end < picker.back_btn.rect.top,
                  "%d vs %d" % (blurb_end, picker.back_btn.rect.top))
        picker._layout(*screen.get_size())  # restore the real layout

        # =====================================================================
        # 7. Task 28: procedural stdlib WAVs (wave/struct/math, no numpy)
        # =====================================================================
        expected_wavs = {
            "eat.wav", "death.wav", "win.wav",
            "click.wav", "count_beep.wav", "start_beep.wav",
        }
        check("sfx: exactly the six recipe files",
              set(audio_mod.SFX_RECIPES) == expected_wavs,
              str(sorted(audio_mod.SFX_RECIPES)))
        with open(audio_mod.__file__, encoding="utf-8") as fh:
            audio_src = fh.read()
        check("sfx: generator is stdlib-only (no numpy import)",
              "import numpy" not in audio_src and "sndarray" not in audio_src)

        default_sfx_dir = audio_mod.SFX_DIR  # project-root sfx/
        fresh = os.path.join(tmp, "fresh_sfx")
        audio_mod.SFX_DIR = fresh
        try:
            fresh_audio = audio_mod.AudioManager(settings)  # generates on init
            check("sfx: fresh sfx/ gets all six WAVs",
                  set(os.listdir(fresh)) == expected_wavs,
                  str(sorted(os.listdir(fresh))))

            stems = {os.path.splitext(name)[0] for name in expected_wavs}
            if fresh_audio.available:
                check("sfx: AudioManager loads all six WAVs as Sounds",
                      set(fresh_audio.sounds) == stems,
                      str(sorted(fresh_audio.sounds)))
            else:
                check("sfx: no mixer -> empty sounds, no crash",
                      fresh_audio.sounds == {}, str(sorted(fresh_audio.sounds)))

            # Durations / format match the recipes exactly.
            bad = []
            for name, recipe in audio_mod.SFX_RECIPES.items():
                want = sum(
                    int(audio_mod.SAMPLE_RATE * ms / 1000)
                    for ms in recipe["durations_ms"]
                )
                with wave.open(os.path.join(fresh, name), "rb") as wf:
                    if (wf.getnframes() != want
                            or wf.getframerate() != audio_mod.SAMPLE_RATE
                            or wf.getnchannels() != 1
                            or wf.getsampwidth() != 2):
                        bad.append(name)
            check("sfx: WAV durations/rate/channels match the recipes",
                  not bad, str(bad))

            # Deleting a file regenerates it; existing files stay untouched.
            eat_path = os.path.join(fresh, "eat.wav")
            eat_before = open(eat_path, "rb").read()
            os.remove(os.path.join(fresh, "click.wav"))
            audio_mod.generate_sfx(fresh)
            check("sfx: deleted WAV regenerates on next run",
                  os.path.exists(os.path.join(fresh, "click.wav")))
            check("sfx: existing WAVs are never overwritten",
                  open(eat_path, "rb").read() == eat_before)
        finally:
            audio_mod.SFX_DIR = default_sfx_dir
        audio_mod.generate_sfx(default_sfx_dir)  # project sfx/ populated too
        check("sfx: project sfx/ holds all six WAVs",
              expected_wavs <= set(os.listdir(default_sfx_dir)),
              str(sorted(os.listdir(default_sfx_dir))))

        # A folder that cannot be created is a silent no-op (never raises).
        blocker = os.path.join(tmp, "blocker_file")
        with open(blocker, "w", encoding="utf-8") as fh:
            fh.write("a file where a folder should be")
        blocked = audio_mod.generate_sfx(os.path.join(blocker, "sfx"))
        check("sfx: uncreatable folder is a silent no-op", blocked == [],
              str(blocked))

        # Corrupt WAV: init survives, that one sound is skipped, rest loads.
        corrupt = os.path.join(tmp, "corrupt_sfx")
        os.makedirs(corrupt, exist_ok=True)
        for name in expected_wavs - {"eat.wav"}:
            shutil.copy(os.path.join(fresh, name), os.path.join(corrupt, name))
        with open(os.path.join(corrupt, "eat.wav"), "wb") as fh:
            fh.write(b"definitely not a RIFF/WAVE header")
        audio_mod.SFX_DIR = corrupt
        try:
            broken_audio = audio_mod.AudioManager(settings)  # must not raise
            check("sfx: corrupt WAV never crashes init", True)
            if broken_audio.available:
                check("sfx: corrupt WAV skipped, healthy ones load",
                      "eat" not in broken_audio.sounds
                      and "win" in broken_audio.sounds,
                      str(sorted(broken_audio.sounds)))
            else:
                check("sfx: no mixer with corrupt files -> no crash", True)
            broken_audio.play_sfx("eat")
            broken_audio.play_sfx("win")
            check("sfx: play_sfx over corrupt sound is a no-op", True)
        finally:
            audio_mod.SFX_DIR = default_sfx_dir

        # =====================================================================
        # 8. Task 29: volume per play + eat/death/win/countdown/click hooks
        # =====================================================================
        class FakeSound:
            def __init__(self):
                self.volumes = []
                self.plays = 0

            def set_volume(self, value):
                self.volumes.append(value)

            def play(self):
                self.plays += 1

        fake = FakeSound()
        real_eat = fresh_audio.sounds.get("eat")
        fresh_audio.sounds["eat"] = fake
        was_available = fresh_audio.available
        fresh_audio.available = True
        orig_volume = settings["sfx_volume"]
        settings["sfx_volume"] = 0.25
        fresh_audio.play_sfx("eat")
        check("sfx: play applies settings[sfx_volume]",
              fake.volumes == [0.25] and fake.plays == 1, str(fake.volumes))
        settings["sfx_volume"] = 0.9
        fresh_audio.play_sfx("eat")
        check("sfx: volume re-read from settings on every play",
              fake.volumes[-1] == 0.9 and fake.plays == 2, str(fake.volumes))
        fresh_audio.play_sfx("not_a_sound")
        check("sfx: unknown sound name is a no-op", fake.plays == 2,
              str(fake.plays))
        fresh_audio.available = False
        fresh_audio.play_sfx("eat")
        check("sfx: play without mixer is a no-op", fake.plays == 2,
              str(fake.plays))
        fresh_audio.available = was_available
        if real_eat is not None:
            fresh_audio.sounds["eat"] = real_eat
        else:
            del fresh_audio.sounds["eat"]
        settings["sfx_volume"] = orig_volume

        spy = []
        audio.play_sfx = lambda name: spy.append(name)  # instance-level spy

        # Countdown: 3 (reset), 2, 1 -> count_beep; GO -> start_beep; then quiet.
        cd = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        check("countdown: beep on 3 at reset", spy == ["count_beep"], str(spy))
        for _ in range(10):
            cd.update(100.0)  # 1000ms -> value 2 (dt is clamped to 100ms)
        check("countdown: beep on 2",
              spy[-1] == "count_beep" and cd.countdown_value == 2,
              "%s / %s" % (spy, cd.countdown_value))
        for _ in range(10):
            cd.update(100.0)
        check("countdown: beep on 1",
              spy[-1] == "count_beep" and cd.countdown_value == 1,
              "%s / %s" % (spy, cd.countdown_value))
        for _ in range(10):
            cd.update(100.0)
        check("countdown: long start beep on GO",
              spy[-1] == "start_beep" and cd.countdown_value == 0
              and cd.timer_running,
              "%s / %s" % (spy, cd.countdown_value))
        for _ in range(10):
            cd.update(100.0)
        check("countdown: play starts with no further sound",
              cd.phase == PLAYING and cd.countdown_value == -1
              and spy[-1] == "start_beep",
              "%s / %s" % (cd.phase, spy))
        check("countdown: exact 3-2-1-GO order",
              spy == ["count_beep", "count_beep", "count_beep", "start_beep"],
              str(spy))

        def fresh_state(mode="classic"):
            """PlayingState mid-run: playing, 3-long snake facing right."""
            state = PlayingState(settings, audio, stats, lambda: None, mode=mode)
            state.phase = PLAYING
            state.snake.body = [(5, 5), (4, 5), (3, 5)]
            state.snake.prev_body = list(state.snake.body)
            state.snake.direction = (1, 0)
            state.snake.pending_dir = None
            state.snake.grow_by = 0
            state.golden = None
            return state

        # Red apple -> eat.
        eater = fresh_state()
        eater.apple.pos = (6, 5)
        spy.clear()
        eater._step()
        check("hook: red apple eaten -> eat", spy == ["eat"], str(spy))

        # Golden apple -> eat (same sound).
        golden_eater = fresh_state()
        golden_eater.apple.pos = (0, 0)  # off the head's path
        golden_eater.golden = GoldenApple((6, 5))
        spy.clear()
        golden_eater._step()
        check("hook: golden apple eaten -> eat",
              spy == ["eat"] and golden_eater.golden is None, str(spy))

        # Wall death -> death (and never a win).
        wall = fresh_state()
        wall.snake.body = [(0, 0), (1, 0), (2, 0)]
        wall.snake.prev_body = list(wall.snake.body)
        wall.snake.direction = (-1, 0)
        spy.clear()
        wall._step()
        check("hook: wall death -> death", spy == ["death"], str(spy))
        check("hook: death ends the run without a win",
              wall.won is False and wall.phase == GAME_OVER,
              "%s / %s" % (wall.won, wall.phase))

        # Self-collision -> death too.
        self_hit = fresh_state()
        self_hit.snake.body = [(5, 5), (6, 5), (6, 6), (5, 6), (4, 6)]
        self_hit.snake.prev_body = list(self_hit.snake.body)
        spy.clear()
        self_hit._step()
        check("hook: self-collision -> death", spy == ["death"], str(spy))

        # Time Attack target reached -> eat + win.
        ta_win = fresh_state(mode="time_attack")
        ta_win.target_apples = 1
        ta_win.apples_eaten = 0
        ta_win.apple.pos = (6, 5)
        spy.clear()
        ta_win._step()
        check("hook: Time Attack win -> eat + win", spy == ["eat", "win"],
              str(spy))
        check("hook: Time Attack win flagged", ta_win.won is True)

        # Board-full win -> eat + win.
        full = fresh_state()
        full.apple.pos = (6, 5)
        full.apple.respawn = lambda body: False  # board is "full"
        spy.clear()
        full._step()
        check("hook: board-full win -> eat + win", spy == ["eat", "win"],
              str(spy))

        # Centralized click SFX: every Button press fires it (before callback).
        click_spy = []
        ui_mod.set_click_sound(lambda: click_spy.append("click"))
        probe = Button(pygame.Rect(10, 10, 140, 44), "PROBE",
                       lambda: click_spy.append("cb"))
        probe.handle_event(click(probe.rect))
        check("hook: Button press fires the click SFX",
              click_spy == ["click", "cb"], str(click_spy))
        probe.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                               {"pos": (900, 500), "button": 1})
        )
        check("hook: click outside a button stays silent",
              click_spy == ["click", "cb"], str(click_spy))

        # A fresh AudioManager registers itself as the global click sound.
        route = []
        route_audio = audio_mod.AudioManager(settings)
        route_audio.play_sfx = lambda name: route.append(name)
        probe.handle_event(click(probe.rect))
        check("hook: AudioManager auto-registers as button click sound",
              route == ["click"], str(route))
        ui_mod.set_click_sound(None)  # clean teardown

        del audio.play_sfx  # drop the instance-level spy
        fresh_audio.play_sfx("eat")  # real manager still fine after tests

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
