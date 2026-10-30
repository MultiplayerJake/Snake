"""Design-only tests for the Cyber redesign (Tasks 24, 25, 26 visual half).

Run (from anywhere): .\\.venv\\Scripts\\python.exe tests\\test_cyber.py
Or run every suite:  .\\.venv\\Scripts\\python.exe tests\\run_all.py

Covers: single fixed Cyber palette (multi-theme system removed), procedural
neon background — draw at many sizes, rebuild on resize, streak + window
flicker spawning, reduced_motion suppression (incl. live toggle) — GlitchTitle
glitch toggle, neon button outline/glow states, Cybork head rendering (visor,
antenna node, glow halo), glowing apples, neon HUD underline + neon grid frame
pixels, and reduced_motion syncing into menu widgets.

SDL dummy drivers and temp settings/stats files only — the real
settings.json / stats.dat are never touched. Exits 0 on success.

NOTE: gameplay tasks (golden-apple spawn gating, lifetime, unbind button,
mode-picker highlight, P-key warning) are covered by a follow-up agent's
suite — intentionally absent here.
"""

from __future__ import annotations

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

from game import audio as audio_mod  # noqa: E402
from game import settings as settings_mod  # noqa: E402
from game import stats as stats_mod  # noqa: E402
from game.ai import grid_metrics  # noqa: E402
from game.apple import Apple, GoldenApple  # noqa: E402
from game.background import DIM_MENUS, DIM_PLAY, CyberBackground  # noqa: E402
from game.constants import PLAYING, lerp_color  # noqa: E402
from game.game import PlayingState  # noqa: E402
from game.menu import MainMenu  # noqa: E402
from game.settings import load_settings  # noqa: E402
from game.settings_screen import SettingsScreen  # noqa: E402
from game.snake import Snake  # noqa: E402
from game.stats import load_stats  # noqa: E402
from game.themes import CYBER, THEMES, get_theme, set_theme  # noqa: E402
from game.ui import Button, GlitchTitle  # noqa: E402

PASS = 0
BG_KNOWN = (80, 0, 0)  # sentinel fill so glow/blends are detectable


def check(label, condition, detail=""):
    global PASS
    if not condition:
        raise AssertionError("%s %s" % (label, detail))
    PASS += 1
    print("PASS  %s" % label)


def scan_colors(surface, rect):
    """Distinct RGB colors inside rect (clipped to the surface)."""
    bounds = surface.get_rect().clip(rect)
    colors = set()
    for y in range(bounds.y, bounds.bottom):
        for x in range(bounds.x, bounds.right):
            colors.add(surface.get_at((x, y))[:3])
    return colors


def main():
    tmp = tempfile.mkdtemp(prefix="quick_snake_cyber_")
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
        # 1. Theme replacement: single fixed Cyber palette (Task 24)
        # =====================================================================
        check("theme: only 'cyber' remains", set(THEMES) == {"cyber"}, str(set(THEMES)))
        check("theme: get_theme() returns the CYBER dict",
              get_theme() is CYBER and get_theme("light") is CYBER
              and get_theme("high_contrast") is CYBER)
        check("theme: set_theme ignores legacy names",
              set_theme("light") is CYBER and set_theme("dark") is CYBER)
        check("theme: spec accent colors",
              theme["neon_cyan"] == (0, 229, 255)
              and theme["neon_magenta"] == (255, 46, 166)
              and theme["bg"] == (10, 10, 26)
              and theme["apple"] == (255, 46, 166)
              and theme["snake_head"] == (140, 250, 255))
        check("theme: play dim heavier than menu dim", DIM_PLAY > DIM_MENUS)

        ss = SettingsScreen(settings, audio, lambda: None,
                            on_display_change=lambda m: None)
        ss.draw(screen)
        check("settings: no theme CycleRow / no _cycle_theme",
              not hasattr(ss, "theme_row") and not hasattr(ss, "_cycle_theme"))
        settings["theme"] = "light"  # legacy value: must pass through untouched
        ss.draw(screen)
        check("settings: legacy theme value ignored, not rewritten",
              settings["theme"] == "light" and get_theme() is CYBER)
        settings["theme"] = "dark"

        # =====================================================================
        # 2. Procedural background (Task 24)
        # =====================================================================
        bg = CyberBackground(1280, 720, seed=42)
        check("bg: static layer built at requested size",
              bg.size == (1280, 720) and bg.static.get_size() == (1280, 720))
        big = pygame.Surface((1280, 720))
        bg.draw(big, dim=DIM_MENUS)
        check("bg: draws full-size (dim menus)", True)

        # Resize rebuild: static layer must be rebuilt for the new geometry.
        old_static = bg.static
        small = pygame.Surface((800, 600))
        bg.draw(small, dim=DIM_PLAY)
        check("bg: rebuilds on resize",
              bg.size == (800, 600) and bg.static.get_size() == (800, 600)
              and bg.static is not old_static,
              str(bg.size))

        # Draw + update at many sizes without error.
        for size in ((640, 480), (1920, 1080), (500, 900), (320, 240), (100, 100)):
            surf = pygame.Surface(size)
            bg.draw(surf, dim=DIM_PLAY)
            bg.update(16)
        check("bg: draws + updates across many resolutions", True)

        # Streak spawn when the timer hits zero.
        bg._streak_in = 0.0
        bg.update(16)
        check("bg: shooting streak spawns when timer hits zero",
              len(bg.streaks) >= 1, str(len(bg.streaks)))
        bg.draw(small, dim=DIM_MENUS)  # streak overlay render path
        check("bg: streaks render without error", True)

        # Window flicker when its timer hits zero.
        check("bg: flicker candidates sampled from lit windows",
              len(bg.flicker_windows) > 0, str(len(bg.flicker_windows)))
        bg._flicker_in = 0.0
        bg.update(16)
        check("bg: window flicker toggles when timer hits zero",
              len(bg.flicker_off) >= 1, str(bg.flicker_off))
        bg.draw(small, dim=DIM_MENUS)
        # Deterministic expiry: one entry with 50 ms left, no new spawns.
        bg.flicker_off = {0: 50.0}
        bg._flicker_in = 999999.0
        bg.update(100)
        check("bg: flicker window lights back up after its beat",
              len(bg.flicker_off) == 0, str(bg.flicker_off))

        # reduced_motion: streaks/flicker never spawn, background still draws.
        bg_rm = CyberBackground(640, 480, reduced_motion=True, seed=7)
        bg_rm._streak_in = 0.0
        bg_rm._flicker_in = 0.0
        for _ in range(5):
            bg_rm.update(100)
        check("reduced_motion: no streaks ever spawn", bg_rm.streaks == [])
        check("reduced_motion: no window flicker ever toggles", bg_rm.flicker_off == {})
        rm_surf = pygame.Surface((640, 480))
        bg_rm.draw(rm_surf, dim=DIM_PLAY)
        check("reduced_motion: background still draws", True)
        # Live accessibility toggle in both directions.
        bg_rm.reduced_motion = False
        bg_rm._streak_in = 0.0
        bg_rm.update(16)
        check("bg: live toggle re-enables motion", len(bg_rm.streaks) >= 1)
        bg_rm.reduced_motion = True
        bg_rm.update(16)
        check("bg: live toggle re-suppresses motion",
              bg_rm.streaks == [] and bg_rm.flicker_off == {})

        # =====================================================================
        # 3. Glitch title (Task 26 visual)
        # =====================================================================
        title = GlitchTitle("QUICK SNAKE")
        title.update(16)
        check("glitch: quiet on a normal update", title.glitch_ms == 0.0)
        title._until_glitch = 0.0  # force the next update to fire a glitch
        title.update(16)
        check("glitch: forced trigger enters glitch state",
              title.glitch_ms == GlitchTitle.GLITCH_MS, str(title.glitch_ms))
        t_surf = pygame.Surface((900, 300))
        t_surf.fill(BG_KNOWN)
        rect = title.draw(t_surf, 72, theme["neon_cyan"], (450, 150))
        check("glitch: renders during a glitch beat",
              rect is not None and rect.center == (450, 150))
        title.update(200)  # longer than the 120 ms beat -> back to clean
        check("glitch: beat decays back to clean",
              title.glitch_ms == 0.0, str(title.glitch_ms))
        title.draw(t_surf, 72, theme["neon_cyan"], (450, 150))
        check("glitch: clean render works", True)

        quiet = GlitchTitle("QUICK SNAKE", reduced_motion=True)
        quiet._until_glitch = 0.0
        quiet.update(5000)
        check("reduced_motion: glitch suppressed", quiet.glitch_ms == 0.0)
        quiet.draw(t_surf, 72, theme["neon_cyan"], (450, 150))
        check("reduced_motion: glitch title still draws", True)
        quiet.reduced_motion = False  # accessibility toggle off -> glitch allowed
        quiet._until_glitch = 0.0
        quiet.update(16)
        check("glitch: live reduced_motion toggle re-enables glitch",
              quiet.glitch_ms > 0.0, str(quiet.glitch_ms))

        # =====================================================================
        # 4. Neon buttons (Task 26 visual): outline + hover glow
        # =====================================================================
        btn = Button(pygame.Rect(50, 50, 160, 40), "TEST", lambda: None)
        b_surf = pygame.Surface((300, 150))
        b_surf.fill(BG_KNOWN)
        real_get_pos = pygame.mouse.get_pos
        try:
            pygame.mouse.get_pos = lambda: (500, 500)  # outside -> no hover
            btn.draw(b_surf)
            rest_top = b_surf.get_at((130, 50))[:3]
            rest_third = b_surf.get_at((130, 52))[:3]
            rest_outside = b_surf.get_at((130, 45))[:3]

            pygame.mouse.get_pos = lambda: (130, 70)  # inside -> hover
            btn.draw(b_surf)
            hot_top = b_surf.get_at((130, 50))[:3]
            hot_third = b_surf.get_at((130, 52))[:3]
            hot_outside = b_surf.get_at((130, 45))[:3]
        finally:
            pygame.mouse.get_pos = real_get_pos

        check("button: cyan neon outline at rest",
              rest_top == theme["neon_cyan"], str(rest_top))
        check("button: rest outline is 2px (row 3 is fill)",
              rest_third == theme["button"], str(rest_third))
        check("button: no glow outside at rest",
              rest_outside == BG_KNOWN, str(rest_outside))
        check("button: hover keeps the outline",
              hot_top == theme["neon_cyan"], str(hot_top))
        check("button: hover thickens outline to 3px",
              hot_third == theme["neon_cyan"], str(hot_third))
        check("button: hover casts a glow outside the rect",
              hot_outside != BG_KNOWN, str(hot_outside))

        # =====================================================================
        # 5. Cybork snake + glowing apples (Task 25)
        # =====================================================================
        snake = Snake()  # body: (12,12) head, (11,12), (10,12) tail
        s_surf = pygame.Surface((600, 600))
        s_surf.fill(BG_KNOWN)
        cell = 40
        snake.draw(s_surf, 0, 0, cell, alpha=1.0)
        check("cybork: bright head block pixel",
              s_surf.get_at((490, 490))[:3] == theme["snake_head"],
              str(s_surf.get_at((490, 490))[:3]))
        check("cybork: dark electronic visor strip",
              s_surf.get_at((502, 496))[:3] == theme["eye"],
              str(s_surf.get_at((502, 496))[:3]))
        check("cybork: magenta antenna node on the back corner",
              s_surf.get_at((486, 512))[:3] == theme["neon_magenta"],
              str(s_surf.get_at((486, 512))[:3]))
        check("cybork: glow halo extends past the head edge",
              s_surf.get_at((500, 519))[:3] != BG_KNOWN,
              str(s_surf.get_at((500, 519))[:3]))
        tail_colors = scan_colors(s_surf, pygame.Rect(404, 484, 33, 33))
        check("cybork: body fades toward snake_tail",
              theme["snake_tail"] in tail_colors, str(sorted(tail_colors)))
        mid_colors = scan_colors(s_surf, pygame.Rect(444, 484, 33, 33))
        check("cybork: mid body is neon cyan (snake_body -> snake_tail lerp)",
              lerp_color(theme["snake_body"], theme["snake_tail"], 0.5) in mid_colors,
              str(sorted(mid_colors)))

        # Apples: magenta glow halo + pulsing core; gold keeps its glow style.
        a_surf = pygame.Surface((700, 700))
        a_surf.fill(BG_KNOWN)
        apple = Apple()
        apple.pos = (5, 5)
        apple.draw(a_surf, 0, 0, cell)
        golden = GoldenApple((15, 15))
        golden.draw(a_surf, 0, 0, cell)

        apple_colors = scan_colors(a_surf, pygame.Rect(204, 204, 33, 33))
        check("apple: bright magenta core", theme["apple"] in apple_colors,
              str(sorted(apple_colors)))
        check("apple: glow halo beyond the core",
              a_surf.get_at((220, 250))[:3] != BG_KNOWN,
              str(a_surf.get_at((220, 250))[:3]))

        golden_colors = scan_colors(a_surf, pygame.Rect(604, 604, 33, 33))
        check("golden apple: gold core keeps its color",
              theme["golden"] in golden_colors, str(sorted(golden_colors)))
        check("golden apple: gains the glow halo style",
              a_surf.get_at((650, 620))[:3] != BG_KNOWN,
              str(a_surf.get_at((650, 620))[:3]))

        # =====================================================================
        # 6. Neon HUD + neon grid frame pixels (Tasks 24/26)
        # =====================================================================
        st = PlayingState(settings, audio, stats, lambda: None, mode="classic")
        st.phase = PLAYING  # no countdown dim over the HUD
        p_surf = pygame.Surface((1280, 720))
        st.draw(p_surf)
        check("play screen: city backdrop built", st._bg is not None
              and st._bg.size == (1280, 720), str(getattr(st, "_bg", None)))

        _cell, origin_x, hud_h = grid_metrics(1280, 720)
        expected_glow = lerp_color(theme["neon_cyan"], theme["hud_bg"], 0.55)
        check("hud: crisp cyan underline",
              p_surf.get_at((10, hud_h - 1))[:3] == theme["neon_cyan"],
              str(p_surf.get_at((10, hud_h - 1))[:3]))
        check("hud: glow line above the underline",
              p_surf.get_at((10, hud_h - 2))[:3] == expected_glow,
              str(p_surf.get_at((10, hud_h - 2))[:3]))

        grid_px = _cell * 25
        check("frame: magenta outer edge of the play grid",
              p_surf.get_at((origin_x, hud_h + grid_px // 2))[:3]
              == theme["neon_magenta"],
              str(p_surf.get_at((origin_x, hud_h + grid_px // 2))[:3]))
        check("frame: cyan inner edge of the play grid",
              p_surf.get_at((origin_x + 2, hud_h + grid_px // 2))[:3]
              == theme["neon_cyan"],
              str(p_surf.get_at((origin_x + 2, hud_h + grid_px // 2))[:3]))
        st.update(16)  # background animation ticks alongside the game loop
        st.draw(p_surf)
        check("play screen: update + draw loop stable", True)

        # =====================================================================
        # 7. reduced_motion flows into menu widgets
        # =====================================================================
        settings["reduced_motion"] = True
        menu = MainMenu(settings, audio, stats, lambda: None, lambda: None,
                        lambda: None)
        menu.draw(screen)  # builds the background from settings
        menu.update(16)
        menu.draw(screen)
        check("menu: reduced_motion reaches background + glitch title",
              menu.bg is not None and menu.bg.reduced_motion
              and menu.title.reduced_motion,
              "%s / %s" % (getattr(menu.bg, "reduced_motion", None),
                           menu.title.reduced_motion))
        settings["reduced_motion"] = False
        menu.update(16)
        check("menu: toggle flows back off live",
              not menu.bg.reduced_motion and not menu.title.reduced_motion)

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
