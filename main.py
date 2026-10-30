"""Quick Snake - entry point: window, main loop, state dispatch."""

from __future__ import annotations

import pygame

from game.audio import AudioManager
from game.game import PlayingState
from game.menu import MainMenu
from game.mode_picker import ModePicker
from game.settings import load_settings, save_settings
from game.settings_screen import SettingsScreen
from game.stats import load_stats
from game.themes import set_theme

from game.constants import FPS

WINDOWED_SIZE = (1280, 720)


def apply_display_mode(mode):
    """Create the window for the given display mode; returns the surface.

    borderless = fullscreen without frame; windowed = 1280x720 resizable.
    True Exclusive Fullscreen is intentionally out of scope.
    """
    if mode == "windowed":
        try:
            return pygame.display.set_mode(WINDOWED_SIZE, pygame.RESIZABLE)
        except pygame.error:
            return pygame.display.set_mode(WINDOWED_SIZE)
    info = pygame.display.Info()
    size = (info.current_w, info.current_h)
    try:
        return pygame.display.set_mode(size, pygame.FULLSCREEN | pygame.NOFRAME)
    except pygame.error:
        try:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error:
            return pygame.display.set_mode(size)


def main():
    pygame.init()
    try:
        settings = load_settings()
        set_theme(settings["theme"])
        apply_display_mode(settings["display_mode"])
        pygame.display.set_caption("Quick Snake")

        audio = AudioManager(settings)
        stats = load_stats()
        clock = pygame.time.Clock()

        state = None

        def go_mode_picker():
            nonlocal state
            state = ModePicker(settings, audio, go_game, go_menu)

        def go_game(mode):
            nonlocal state
            state = PlayingState(settings, audio, stats, go_menu, mode)

        def go_settings():
            nonlocal state
            state = SettingsScreen(settings, audio, go_menu, apply_display_mode)

        def quit_game():
            nonlocal running
            save_settings(settings)
            running = False

        def go_menu():
            nonlocal state
            state = MainMenu(settings, audio, stats, go_mode_picker, go_settings, quit_game)

        running = True
        go_menu()

        while running:
            dt = clock.tick(FPS)  # ms since last frame; no time.sleep anywhere
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                state.handle_event(event)
            state.update(dt)
            # Re-fetch each frame: the display-mode toggle recreates the surface.
            screen = pygame.display.get_surface()
            state.draw(screen)
            pygame.display.flip()
    finally:
        try:
            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
