"""Music + SFX manager that degrades gracefully when audio is unavailable.

Phase 2: scans music/ for ALL playable files and supports picking a specific
track ("Auto" = first found) from the settings screen.

Phase 3.5 (Tasks 28/29): the six short SFX are synthesized with the Python
STDLIB only (`wave`/`struct`/`math` — numpy is NOT installed) into sfx/*.wav
at first run, then loaded as pygame Sounds. Button clicks are routed through
a module-level callback on game.ui so widgets stay audio-agnostic (no circular
imports). Everything stays guarded: missing files, a corrupt WAV, a missing
mixer or a missing folder only mean silence — the game never crashes.
"""

from __future__ import annotations

import math
import os
import struct
import wave

import pygame

from game.constants import MUSIC_DIR, SFX_DIR

MUSIC_EXTENSIONS = (".ogg", ".mp3", ".wav")
TRACK_AUTO = "Auto"

# --- Procedural SFX generation (pseudocode §33: stdlib only, no numpy) -------

SAMPLE_RATE = 22050

# name -> synth() kwargs; parallel freq/duration arrays play tone after tone.
SFX_RECIPES = {
    "eat.wav": dict(
        freqs=[880, 1320], durations_ms=[40, 40], wave_shape="square", volume=0.35
    ),
    "death.wav": dict(
        freqs=[320, 90], durations_ms=[150, 200], wave_shape="saw", volume=0.40
    ),
    "win.wav": dict(
        freqs=[523, 659, 784, 1047],
        durations_ms=[100, 100, 100, 100],
        wave_shape="square",
        volume=0.35,
    ),
    "click.wav": dict(
        freqs=[1000], durations_ms=[25], wave_shape="square", volume=0.30
    ),
    "count_beep.wav": dict(
        freqs=[800], durations_ms=[200], wave_shape="square", volume=0.40,
        decay=False,
    ),
    "start_beep.wav": dict(
        freqs=[1300], durations_ms=[700], wave_shape="square", volume=0.45,
        decay=False,
    ),
}


def synth(freqs, durations_ms, wave_shape="square", volume=0.5, decay=True):
    """Float samples for consecutive tones (freqs/durations are parallel)."""
    samples = []
    for freq, ms in zip(freqs, durations_ms):
        n = max(1, int(SAMPLE_RATE * ms / 1000))
        for i in range(n):
            t = i / SAMPLE_RATE
            if wave_shape == "square":
                v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            elif wave_shape == "saw":
                v = 2.0 * ((freq * t) % 1.0) - 1.0
            else:
                v = math.sin(2 * math.pi * freq * t)
            if decay:
                v *= 1.0 - (i / n)  # linear fade within each tone
            samples.append(v * volume)
    return samples


def write_wav(path, samples):
    """Mono 16-bit PCM WAV from floats clamped to [-1, 1]."""
    with wave.open(str(path), "w") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(SAMPLE_RATE)
        writer.writeframes(
            b"".join(
                struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767))
                for s in samples
            )
        )


def generate_sfx(sfx_dir=None):
    """Write every missing sfx/*.wav; returns paths created. Never raises.

    `sfx_dir` defaults to the module-level SFX_DIR (resolved at call time so
    tests can redirect it). Existing files are left untouched — deleting one
    regenerates it on the next run.
    """
    if sfx_dir is None:
        sfx_dir = SFX_DIR
    written = []
    try:
        os.makedirs(sfx_dir, exist_ok=True)
    except OSError as exc:
        print("[audio] Could not create sfx folder: %s" % exc)
        return written
    for name, recipe in SFX_RECIPES.items():
        path = os.path.join(sfx_dir, name)
        if os.path.exists(path):
            continue
        try:
            write_wav(path, synth(**recipe))
            written.append(path)
        except Exception as exc:
            print("[audio] Could not generate '%s': %s" % (path, exc))
    return written


class AudioManager:
    """Plays looping background music from music/ and generated SFX."""

    def __init__(self, settings):
        self.settings = settings
        self.available = False
        self.music_path = None
        self.current_track = TRACK_AUTO
        self.tracks = []
        self.sounds = {}
        self.music_volume = float(settings.get("music_volume", 0.5))
        self.sfx_volume = float(settings.get("sfx_volume", 0.5))

        # Task 29: every ui.Button press plays click.wav. Registered through a
        # module-level hook so game.ui never imports game.audio (no cycles).
        self._register_click_hook()

        try:
            os.makedirs(MUSIC_DIR, exist_ok=True)
        except OSError as exc:
            print("[audio] Could not create music folder: %s" % exc)

        # Track list works even without a mixer (settings row still cycles).
        self.tracks = self.scan_tracks()

        # Task 28: synthesize missing WAVs first — this needs no mixer, so the
        # assets exist even on a machine where audio hardware is unavailable.
        try:
            generate_sfx()
        except Exception as exc:
            print("[audio] SFX generation failed (%s); running silently." % exc)

        try:
            pygame.mixer.init()
            self.available = True
        except Exception as exc:
            print("[audio] Mixer unavailable (%s); running silently." % exc)
            return

        self._load_sfx()
        self._start_music(settings)

    def _register_click_hook(self):
        """Central click hook for all buttons (menu/picker/settings/overlays)."""
        try:
            from game.ui import set_click_sound

            set_click_sound(lambda: self.play_sfx("click"))
        except Exception as exc:
            print("[audio] Button click hook unavailable: %s" % exc)

    # --- Music ---------------------------------------------------------------
    def scan_tracks(self):
        """Sorted list of playable file names in music/ (never raises)."""
        try:
            entries = sorted(os.listdir(MUSIC_DIR))
        except OSError:
            return []
        return [name for name in entries if name.lower().endswith(MUSIC_EXTENSIONS)]

    def track_path(self, name):
        """Full path for a track name ("Auto" -> first found). None if none."""
        tracks = self.tracks or self.scan_tracks()
        if not tracks:
            return None
        if name == TRACK_AUTO or name not in tracks:
            name = tracks[0]
        return os.path.join(MUSIC_DIR, name)

    def select_track(self, name, settings=None):
        """Load+loop the named track (or 'Auto') at the current volume."""
        if settings is not None:
            settings["current_track"] = name
        self.current_track = name
        if not self.available:
            return False
        path = self.track_path(name)
        if not path:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            self.music_path = None
            return False
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1)
            self.music_path = path
            print("[audio] Playing music: %s" % path)
            return True
        except Exception as exc:
            print("[audio] Could not play music file '%s': %s" % (path, exc))
            self.music_path = None
            return False

    def _start_music(self, settings):
        wanted = settings.get("current_track", TRACK_AUTO)
        if not self.tracks:
            print(
                "[audio] No music file found in '%s'. "
                "Drop an .ogg/.mp3/.wav there to enable music (game runs fine silently)."
                % MUSIC_DIR
            )
            self.current_track = wanted
            return
        self.select_track(wanted, settings)

    # --- SFX -----------------------------------------------------------------
    def _load_sfx(self):
        """Load every sfx/*.wav into a Sound keyed by its file stem (Task 29).

        Broken/missing files are skipped individually — one bad WAV never
        silences the rest and never crashes.
        """
        try:
            entries = sorted(os.listdir(SFX_DIR))
        except OSError as exc:
            print("[audio] Could not read sfx folder: %s" % exc)
            return
        loaded = 0
        for name in entries:
            if not name.lower().endswith(".wav"):
                continue
            path = os.path.join(SFX_DIR, name)
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(self.sfx_volume)
                self.sounds[os.path.splitext(name)[0]] = sound
                loaded += 1
            except Exception as exc:
                print("[audio] Skipping broken SFX '%s': %s" % (name, exc))
        if not loaded:
            print("[audio] No playable SFX in '%s'; game runs fine silently." % SFX_DIR)

    # --- Public API ----------------------------------------------------------
    def set_music_volume(self, volume):
        self.music_volume = min(1.0, max(0.0, float(volume)))
        if not self.available:
            return
        try:
            pygame.mixer.music.set_volume(self.music_volume)
        except Exception:
            pass

    def set_sfx_volume(self, volume):
        self.sfx_volume = min(1.0, max(0.0, float(volume)))
        for sound in self.sounds.values():
            try:
                sound.set_volume(self.sfx_volume)
            except Exception:
                pass

    def _live_sfx_volume(self):
        """settings["sfx_volume"] clamped to 0..1 (source of truth per play)."""
        try:
            value = float(self.settings.get("sfx_volume", self.sfx_volume))
        except (AttributeError, TypeError, ValueError):
            value = self.sfx_volume
        return min(1.0, max(0.0, value))

    def play_sfx(self, name):
        if not self.available:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        try:
            # Volume re-read from settings on every play (Task 29).
            sound.set_volume(self._live_sfx_volume())
            sound.play()
        except Exception:
            pass
