# Snake

*A speedy little snake* — a borderless-fullscreen, neon-drenched arcade snake game: a 25×25 grid, three game modes, a procedurally drawn cyber-city skyline and synth sound effects. Pure Python + pygame, nothing extra to install.



https://github.com/user-attachments/assets/f0fb690b-2e29-4853-8fa7-6e949b678690



## Features

- **Borderless fullscreen** by default, with an optional 1280×720 windowed mode
- **25×25 neon grid** with smooth, interpolated snake movement at 60 FPS
- **Three game modes** — Classic, Speedrun and Time Attack
- **Cyber theme**: a fully procedural neon skyline (no image files), a glitching title and the "Cybork" snake — a neon-cyan crawler with an electronic visor and a magenta antenna
- **Red and golden apples**, particle bursts and screen shake
- **Sound effects synthesized on first run** with the Python standard library — no audio files to download
- **Bring your own music**: drop `.ogg` / `.mp3` / `.wav` files into `music/` and pick them in Settings
- **Rebindable controls** (with per-key unbind), volume sliders, difficulty levels and a reduced-motion accessibility option
- **Records saved automatically** — per-mode bests and lifetime stats
- **Countdown start** (3–2–1–GO!) and pause/restart on every run

---

## For Players

Written for someone who just wants to play. The easiest path is a single download; running from source is provided as an alternative below (macOS/Linux variants noted).

### Download the game (recommended, Windows)

1. **Download `QuickSnake.exe` (~13 MB)** from the [releases page](https://github.com/MultiplayerJake/Snake/releases) — or grab it with the [direct download link](https://github.com/MultiplayerJake/Snake/releases/download/Snake/QuickSnake.exe).
2. **Double-click it to play.** It's a single self-contained Windows file — no Python, no installation, nothing else needed.

On first run it creates its data files (settings, stats, sound effects, the `music/` folder) in the same folder as the exe — that's simply where your saves live.

> Windows may show a "Windows protected your PC" screen the first time you run a game you downloaded — that's a normal thing for downloaded apps: click **More info** → **Run anyway**.

### Or run from source

For players without Windows, or anyone who wants the source code. Get the code either by cloning it with git:

```bash
git clone https://github.com/MultiplayerJake/Snake.git
cd Snake
```

or without git: the [releases page](https://github.com/MultiplayerJake/Snake/releases) also offers GitHub's **Source code (zip)** / **(tar.gz)** buttons — download and unzip anywhere (the repo's green **Code** button → **Download ZIP** does the same).

#### 1. Install Python

Download Python from [python.org](https://www.python.org/downloads/) and run the installer.

- **Windows:** tick **"Add Python to PATH"** on the first installer screen before clicking *Install Now*.
- The game is tested on **Python 3.12**; anything from **3.10** up should work.

#### 2. Install the one dependency

Open a terminal (PowerShell on Windows) in the game folder and run:

```bash
pip install -r requirements.txt
```

That installs **pygame 2.6.1** — the only dependency. If your shell doesn't know `pip`, use `py -m pip install -r requirements.txt` (Windows) or `python3 -m pip install -r requirements.txt` (macOS/Linux).

#### 3. Play

```bash
python main.py
```

(macOS/Linux: `python3 main.py`.)

The game opens borderless fullscreen with the main menu: **Play**, **Settings**, **Exit**.

> **Optional — virtual environment:** if you prefer not to install pygame into your system Python:
>
> ```bash
> python -m venv .venv
> # Windows:   .\.venv\Scripts\python -m pip install -r requirements.txt
> #            .\.venv\Scripts\python main.py
> # macOS/Linux: source .venv/bin/activate, then the plain commands above
> ```

### Controls

| Key | Action |
| --- | --- |
| `W` `A` `S` `D` | Steer the snake (default — arrow keys and others can be bound in Settings) |
| `P` or `ESC` | Pause / resume during a run |
| `ESC` | Go back (in the mode picker and Settings) |
| Mouse | Everything else: menus, and the RESUME / RESTART / MENU and PLAY AGAIN buttons |

Turns are buffered, so a quick double-tap won't reverse you into yourself — 180° reversals are simply ignored. On the main menu, ESC does nothing (use the **Exit** button).

### Game modes

Pick a mode after pressing **Play**; your last choice is remembered.

**Classic** — eat apples, grow, don't crash. Hitting a wall or your own body ends the run (walls kill — there is no wrap-around). Chase a high score; an optional count-up timer can be enabled in Settings, and filling the entire board is a win.

**Speedrun** — same rules, but always at hard speed with the timer always running. The timer stops the moment you die; your fastest time is kept.

**Time Attack** — a countdown plus an apple target that scales with difficulty. Eat the target number of red apples before the clock hits zero:

| Difficulty | Target | Time limit |
| --- | --- | --- |
| Easy | 5 apples | 90 s |
| Medium | 8 apples | 75 s |
| Hard | 10 apples | 60 s |

Reach the target and you win (fastest clear per difficulty is recorded); run out of time and it's "TIME'S UP". Golden apples never appear in this mode.

### Apples

- **Red apple** — the everyday snack: +1 point, snake grows by one segment. Spawns on a random free cell.
- **Golden apple** — a bonus worth **5 points** that has roughly a **15% chance** of appearing right after you eat a red apple (only one at a time). It lasts just **5 seconds** — it visibly shrinks with a countdown ring, so grab it fast. Never spawns in Time Attack.

### Difficulty

Easy / Medium / Hard (set in Settings, default Medium) controls the snake's speed — how many frames pass between moves. It also sets your Time Attack target and timer. Speedrun ignores the setting and always runs at hard speed.

### Settings

- **Keybinds** — click a row and press a new key; each row also has a small **unbind (bin) button** if you want a direction to do nothing.
- **Music volume** and **SFX volume** sliders.
- **Speedrun timer** toggle — show the count-up timer in Classic (Speedrun and Time Attack always show their timers).
- **Grid lines** toggle and **Reduced motion** toggle (turns off screen shake, particles and background animations).
- **Difficulty** — EASY / MEDIUM / HARD buttons.
- **Display mode** — BORDERLESS (fullscreen) or WINDOWED (1280×720, resizable); the window is recreated instantly.
- **Music track** — cycle through "Auto" (plays the first file found, alphabetically) or a specific file from `music/`.
- **Reset to defaults** — click twice to confirm; your records are kept.

Everything saves immediately.

### Your own music

The `music/` folder sits next to `main.py` and is **created automatically** the first time you run the game. Drop any `.ogg`, `.mp3` or `.wav` file into it, then pick it under **Settings → Music track** — it loops at your music volume. No files there? The game just runs silently; nothing is required.

### Tips

- **Records save themselves.** Per-mode bests (best score, best times, Time Attack clears) live in `settings.json`; lifetime totals (games, apples, score, playtime, deaths, wins, golden apples) live in `stats.dat`. Both files are created next to the game automatically.
- Want a clean slate? Delete `settings.json` and `stats.dat` — settings go back to defaults and records reset. (`settings.json.bak` is just a backup of your previous settings.)
- A new personal best is called out on the game-over screen.

---

## For Programmers

### Requirements

- **Python 3.10+** — developed and tested on **3.12.6**
- **pygame 2.6.1** — pinned in `requirements.txt`, the only third-party package
- No other dependencies. The six sound effects are synthesized with the standard library (`wave` / `struct` / `math`) into `sfx/` on first run; **numpy is intentionally not used** (and no image assets exist — everything is code-drawn).

### Project structure

```
Snake/
├── main.py               # entry point: window creation, main loop, screen dispatch
├── .gitignore            # excludes caches, build output + per-machine user data
├── requirements.txt      # pygame==2.6.1 (the only dependency)
├── settings.json         # runtime: settings + per-mode bests (auto-created; never commit)
├── stats.dat             # runtime: lifetime stats, base64 JSON (auto-created; never commit)
├── music/                # your .ogg/.mp3/.wav files (auto-created)
├── sfx/                  # procedurally generated WAV sound effects (auto-created)
├── tests/                # headless test battery: run_all.py + 5 suites + TESTS.md
└── game/
    ├── __init__.py       # package marker
    ├── constants.py      # grid size, FPS, mode/difficulty tables, default settings, key-name maps
    ├── settings.py       # settings.json load/save: deep-merge defaults, sanitizing, .bak backups
    ├── stats.py          # lifetime stats: base64-encoded JSON in stats.dat
    ├── audio.py          # music + stdlib-synthesized SFX; degrades to silence when anything is missing
    ├── ui.py             # widgets (Button, Slider, Toggle, KeyBindRow, UnbindButton, CycleRow, GlitchTitle) + neon drawing helpers
    ├── themes.py         # the single fixed "Cyber" neon palette read by every draw path
    ├── background.py     # procedural neon city backdrop (cached statics + animated overlays)
    ├── menu.py           # main menu, with the AI demo snake playing behind it
    ├── mode_picker.py    # Classic / Speedrun / Time Attack selection + per-mode records
    ├── settings_screen.py# settings UI: keybinds, volumes, toggles, display, music, reset
    ├── game.py           # the run itself: countdown, movement, HUD, timers, pause/game-over, record saving
    ├── snake.py          # snake logic (grid step, buffered turn, growth) + "Cybork" rendering with interpolation
    ├── apple.py          # red/golden apple spawn logic + glow rendering (golden has a lifetime ring)
    ├── ai.py             # BFS menu demo snake (wraps walls, never dies) + shared grid layout helper
    └── particles.py      # particle bursts + screen shake (disabled under reduced motion)
```

### Architecture: a screen object per state

`main.py` does three things and nothing else:

1. **Window** — `apply_display_mode()` creates either borderless fullscreen (`FULLSCREEN | NOFRAME`, falling back gracefully) or a 1280×720 resizable window, and can recreate it at any time (the Settings display-mode row calls it live).
2. **One active screen object** — the variable `state` points at exactly one of four screen classes: `MainMenu` (menu.py), `ModePicker` (mode_picker.py), `SettingsScreen` (settings_screen.py) or `PlayingState` (game.py). Navigation is wired through closures defined in `main()` (`go_menu` / `go_mode_picker` / `go_game(mode)` / `go_settings`), so screens never import each other.
3. **The main loop** — a fixed **60 FPS** loop (`clock.tick(FPS)`, `FPS = 60` in constants.py; the frame delta `dt` is in milliseconds, no `time.sleep` anywhere). Every frame it dispatches `handle_event(event)` → `update(dt)` → `draw(screen)` to the active screen. The display surface is **re-fetched every frame** (`pygame.display.get_surface()`) because the display-mode toggle replaces it mid-run. A `QUIT` event ends the loop; the menu's **EXIT** button saves settings on the way out.

Inside a run, `PlayingState` (game.py) is a second, smaller state machine over the phase strings defined in `game/constants.py` (`MENU`, `SETTINGS`, `PLAYING`, `PAUSED`, `GAME_OVER`; `COUNTDOWN` lives in game.py):

```
COUNTDOWN (3-2-1-GO!; beeps on 2 and 1, long start beep at GO)
    ↓                     ↑
  PLAYING  ←——————————→  PAUSED   (P / ESC toggles)
    ↓
 GAME_OVER (records + stats saved here; RESUME is only from PAUSED)
```

**dt handling** — `PlayingState.update()` clamps every frame delta to **100 ms** (`dt = min(float(dt), 100.0)`) before using it, so a window drag or a system lag spike can never skip a snake move, a countdown beat or a golden-apple expiry; time-based features accumulate `dt` rather than counting frames (frame counts are only used for the difficulty-based move interval: 12/9/6 frames per move at easy/medium/hard).

### Rendering details

- **Interpolated (sub-frame) snake movement** — snake *logic* stays on the fixed grid tick, but *drawing* lerps between `Snake.prev_body` (a snapshot taken before each step) and the current body, using `alpha = tick_accum / ticks_per_step`. Segments glide across cells instead of hopping; a newly grown tail segment slides out of the old tail position (its previous index is clamped to the old last segment).
- **Cached procedural background** — `CyberBackground` (background.py) renders its static layers (sky gradient, buildings, window grids) **once into a cached surface** and only rebuilds that cache on resize. The animated overlay (falling neon streaks + window flicker) is drawn on top of the cache every frame — and is skipped entirely under **reduced motion**, whose `update()` is a no-op (the toggle can be flipped live without rebuilding the backdrop).
- **One palette** — every draw path (screen, widgets, snake, apples, background) reads colors through `themes.get_theme()`, which always resolves to the single fixed `CYBER` neon palette; there are zero hardcoded colors in draw code, and no image files anywhere.

### Persistence: settings.json and stats.dat

> ⚠️ **Both files are personal user data** (keybinds, volumes, records, lifetime stats). They are auto-created next to `main.py`, listed in `.gitignore`, and should never be committed or shipped.

**`settings.json`** — handled entirely by `game/settings.py`:

- **Load** (`load_settings`, never raises): the saved file is **deep-merged over `DEFAULT_SETTINGS`** (`_deep_merge`, recursing into dicts), so keys missing from an old file are simply filled in with defaults. Legacy flat `best_score` / `best_time_ms` keys are migrated into `bests.classic` on the way in. Then **`_sanitize()` coerces every single value** so game code can trust the dict: keybind names are validated against the key map (`null` is preserved as an explicitly unbound action, unknown strings fall back to the default key), volumes are clamped to `[0.0, 1.0]`, booleans must be booleans, difficulty/display-mode/last-mode must be known values, and `bests` is rebuilt into the full per-mode structure with non-negative int scores. A missing, corrupt or non-dict file just yields defaults.
- **Save** (`save_settings`): the existing file is copied to **`settings.json.bak`** (`shutil.copy2`) before every write, then dumped as indented JSON. Failures print a warning instead of crashing. Saved on every settings change and again on exit. `reset_to_defaults()` keeps the `bests` subtree intact.
- Per-mode bests live in the same file under `bests` (best score / best time per mode, plus Time Attack fastest clear per difficulty).

**`stats.dat`** — handled by `game/stats.py`; it holds *lifetime* aggregates (games, apples, score, playtime, deaths, wins, golden apples), kept separate from per-run bests:

- The payload is JSON that is **base64-encoded** so the file never looks like editable JSON. In `save_stats()` the encoding happens right here in `game/stats.py`:
  ```python
  payload = json.dumps(_sanitize(stats)).encode("utf-8")
  with open(STATS_PATH, "w", encoding="ascii") as handle:
      handle.write(base64.b64encode(payload).decode("ascii"))
  ```
  and `load_stats()` decodes it back with `base64.b64decode(..., validate=True)` → `json.loads`, merges over `STATS_DEFAULTS` and sanitizes every field to a non-negative int. Any error (missing file, bad base64, corrupt JSON, wrong root type) falls back to defaults — it never raises.
- `record_result()` applies one finished run to the dict (clamping negatives, wins and deaths mutually exclusive); the caller persists it.

### Input system

- Keybinds are stored in `settings.json` as **portable pygame key-name strings** (`"w"`, `"up"`, `"esc"`, `","`, ...), never as key codes. The name ↔ code mapping (`NAME_TO_KEY` / `KEY_TO_NAME`) is built at import time in `constants.py` by scanning every `pygame.K_*` constant and applying `_KEY_OVERRIDES` for readable names (arrow keys → `"up"`, Enter → `"enter"`, Shift → `"lshift"`, ...). `key_name()` / `key_label()` turn a code back into a string/label, with a safe fallback for unknown keys.
- **An unbound action is `null` in JSON** and stays `None` after sanitizing — the game simply ignores `None` bindings. The per-row **UnbindButton** in Settings sets this.
- Rebinding happens through `KeyBindRow` (ui.py): click a row → "press a key". Binding a key already used by another direction **swaps** the two rows instead of creating a conflict.
- **The P-arming warning**: `P` is the pause key, so assigning it to a direction needs a deliberate double-take — the first click only arms the row and shows the warning *"P is used for pause - click row again to force"* (`P_PAUSE_WARNING` in ui.py); a second click force-binds, while ESC or clicking elsewhere clears the armed state.
- Widgets never import audio: button clicks are routed through a module-level callback installed with `ui.set_click_sound()` (keeps ui.py audio-agnostic, avoids circular imports).

### Audio

- `AudioManager` (game/audio.py) owns everything: it scans `music/` for `.ogg` / `.mp3` / `.wav` files, loops the selected track (`"Auto"` = first found, alphabetically) via `pygame.mixer.music` at `music_volume`, and applies `sfx_volume` to every sound effect.
- The six SFX (`eat`, `death`, `win`, `click`, `count_beep`, `start_beep`) are **synthesized with only the standard library** (`wave` / `struct` / `math`) into `sfx/*.wav` on first run, from the declarative `SFX_RECIPES` table at **22050 Hz** (mono, 16-bit; recipes define per-tone frequencies, durations, wave shape and volume). Existing files are kept; delete one and it regenerates.
- **Silent-safe everywhere**: a missing/closed mixer, a missing `sfx/` or `music/` folder, or a corrupt WAV all degrade to silence — no code path crashes over audio, and the music-row cycling works even with no mixer at all.

### Extending the game

- **New main-menu item**: add a `ui.Button` in `MainMenu` (game/menu.py — buttons are created in `__init__` and laid out in the relayout code) plus a callback; follow the pattern of the existing PLAY / SETTINGS / EXIT buttons.
- **New game mode**: register it in game/constants.py — `MODES` tuple, `MODE_LABELS`, `MODE_BLURBS` (the `ModePicker` builds one button per `MODES` entry automatically) — then branch on `self.mode` inside `PlayingState` (game.py) for the behavior, and add a `DEFAULT_BESTS` entry if the mode keeps records (Time Attack additionally shows how per-difficulty tables next to `TIME_ATTACK_SPECS` work).
- **New settings row**: pick/create a widget in game/ui.py (`Slider`, `Toggle`, `CycleRow`, `KeyBindRow`, `UnbindButton`, `Button`), instantiate it in `SettingsScreen` (game/settings_screen.py), give it a rect in the relayout pass and (if it should scroll) yield it from the row iterator. Give the setting a default in `DEFAULT_SETTINGS` (constants.py) and a validation rule in `_sanitize` (settings.py) so it round-trips through a hand-edited file safely.

### Repo hygiene

A `.gitignore` is checked in: it excludes Python caches and virtualenvs, the build-output folders (`build/` and `dist/`), editor/OS noise, and — important — the **per-machine user data** (`settings.json`, `settings.json.bak`, `stats.dat`) and the **regenerated `sfx/` folder**. Never force-add those files.

### Building the Windows .exe

To ship the game to players who don't have Python, build a standalone executable with [PyInstaller](https://pyinstaller.org/).

**Prerequisites**

- **Windows.** PyInstaller builds natively for the host OS, so a Windows `.exe` must be built on Windows. (On macOS/Linux the same commands produce a native binary for that OS instead — there is no cross-compiling.)
- A `.venv` with the runtime dependency installed (`pip install -r requirements.txt`), then the build-only dependency (PyInstaller, pinned):

  ```powershell
  .\.venv\Scripts\pip.exe install -r requirements-build.txt
  ```

  (`requirements-build.txt` is build-time only — players never need it. `build.ps1` also installs it automatically if PyInstaller is missing from the venv, so this step is optional.)

**The one command**

From the project root:

```powershell
.\build.ps1
```

What the script does, step by step:

1. Checks that `.venv\Scripts\python.exe` exists (and tells you the exact `py -3.12 -m venv .venv` command if it doesn't).
2. Checks whether PyInstaller is available in the venv; if not, installs it from `requirements-build.txt`.
3. Generates `assets\icon.ico` with `tools\make_icon.py` (stdlib-only procedural pixel art) if the file is missing.
4. Deletes any previous `build\` and `dist\` folders — every build starts clean, so the script is idempotent; rerunning it always rebuilds from scratch.
5. Runs PyInstaller with the committed `QuickSnake.spec`.
6. Verifies `dist\QuickSnake.exe` was actually produced, then prints its path and size.

**Output**

`dist\QuickSnake.exe` — a single **onefile**, **windowed** (no console) executable with the icon embedded, roughly 13 MB. That one file is what you hand to players: they need nothing else — no Python, no pygame, no install step. (`build/` and `dist/` are both gitignored — they're build artifacts.)

**How the bundle is configured** (`QuickSnake.spec`)

- `onefile` — everything is packed into one executable (PyInstaller unpacks to a temp dir at startup); no folder of loose files to distribute.
- `console=False` — windowed app: launching the exe never flashes a terminal window.
- `datas=[]` — deliberately **nothing** is bundled: no `settings.json`, no `stats.dat`, no `music/`, no `sfx/`, no tests. User data must never ship inside the exe, and the sound effects are regenerated by the game itself.
- `excludes=["tests", "unittest", "pydoc_data"]` — test machinery and unused stdlib docs are stripped out of the bundle.
- `upx=False` — the binary stays vanilla; UPX-packed exes often trip antivirus scanners.
- `icon="assets/icon.ico"` — the generated icon is embedded in the exe.

Runtime consequence, by design: on first launch the exe synthesizes its six sound effects and creates `settings.json`, `stats.dat`, `music/` and `sfx/` in its own folder. All user data lives beside the exe — players can drop music files into `music/` and delete the settings files for a clean slate, exactly like running from source.

**Manual equivalent** — `build.ps1` is a thin wrapper; the underlying call is:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm QuickSnake.spec
```

### The icon generator (tools/make_icon.py)

`tools/make_icon.py` creates `assets/icon.ico` from scratch using **only the Python standard library** — no Pillow, no pygame, no image assets. It draws the game's icon (a coiled green snake with a red apple on a dark square) procedurally at **16, 32, 48 and 256 px** — one shared design, rendered at each size — and packs the four images as PNG entries into a single ICO container (`assets/` is created if missing).

```powershell
.\.venv\Scripts\python.exe tools\make_icon.py
```

(macOS/Linux: `python tools/make_icon.py` — stdlib-only, so any Python 3 interpreter works.)

You rarely need to run it by hand: `build.ps1` (step 3 above) already generates the icon automatically when `assets/icon.ico` is missing. Re-running it is always safe — the output path is fixed (no command-line arguments), and each run simply overwrites the file with a freshly generated one. The generated icon is **tracked in git** (not gitignored), so contributors don't strictly need to regenerate it.

### Running the tests

Everything lives in `tests/` (5 suites, all headless — no window, no audio hardware, safe for CI). **One command runs the whole battery:**

```powershell
.\.venv\Scripts\python.exe tests\run_all.py
```

(macOS/Linux: `.venv/bin/python tests/run_all.py`, or plain `python tests/run_all.py` if pygame is installed system-wide.)

What `run_all.py` guarantees:

- **Works from any CWD** — it derives `tests/` and the project root from `__file__`, not from where you launched it.
- **Forces `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy` itself**, so no suite can ever open a real window or touch an audio device, however it was invoked.
- **Runs each suite in its own subprocess** for full isolation (independent pygame init/quit and module-level path patches per suite), with a 600 s per-suite timeout.
- **Reports per-suite check counts + a grand total** (it parses each suite's `ALL N CHECKS PASSED` line) and **exits 0 only if every suite exits 0** — one command, one exit code, CI-ready.
- The live `settings.json` / `stats.dat` are never touched: every suite redirects persistence to a temp directory.

Latest run: **443 checks across 5 suites in ~2.5 s — ALL PASSED.**

```text
PASS  smoke_test.py            72 checks    0.7s
PASS  test_extra.py           105 checks    0.6s
PASS  test_cyber.py            53 checks    0.3s
PASS  test_gameplay3.py        84 checks    0.4s
PASS  test_phase35_gaps.py    129 checks    0.6s
GRAND TOTAL: 443 checks across 5 suites in 2.5s - ALL PASSED
```

#### Running a single suite

Direct invocation works and needs no manual environment setup — **each suite sets the SDL dummy drivers itself** at module top (before importing pygame), so a bare run is headless too, from any CWD:

```powershell
.\.venv\Scripts\python.exe tests\smoke_test.py
```

#### What each suite covers

| Suite | Checks | Covers |
| --- | ---: | --- |
| `smoke_test.py` | 72 | Core engine smoke test: legacy-settings migration, menu → mode picker → game navigation, snake stepping/growth, apple spawning, death/game-over, stats and settings round-trips, basic menu/settings-screen behavior. |
| `test_extra.py` | 105 | Phase-2 feature coverage gaps: mode picker, keybind-rebinding edge cases, board-full win, Time Attack pause, golden apple, music selection with a real tiny `.ogg`/`.wav` present, particles, themes-era checks, windowed resize relayout, demo-AI snake long-run stability, `settings.json`/`stats.dat` corruption recovery, reset-keeps-bests. |
| `test_cyber.py` | 53 | Design half: `CyberBackground` draw/rebuild at many sizes, streak & window-flicker spawning, reduced-motion suppression (incl. live toggle), `GlitchTitle` glitching, neon button outline/glow states, Cybork head pixels (visor, antenna node, halo), glowing apples, neon HUD/grid-frame pixels, theme replacement (single fixed CYBER palette). |
| `test_gameplay3.py` | 84 | Gameplay half + SFX wiring/spacing: golden-apple gating & exact 5000 ms lifetime, `UnbindButton` full behavior (incl. scrolling), the P-key force-bind warning flow, mode-picker identical buttons + exactly +10 px gap, stdlib WAV generation into a fresh `sfx/` (recipe-exact durations, regeneration, corrupt/missing guards), SFX hooks (eat/death/win/countdown, Button click, per-play volume). |
| `test_phase35_gaps.py` | 129 | Boundary/edge-case pass: live project `sfx/*.wav` vs recipes (frame count, mono/16-bit/22050 Hz, ±1 ms), golden apple dies **exactly** at the 5000 ms boundary, countdown lag-frame dt-clamp, mode-picker +10 px spacing at odd window sizes, unbind `null` JSON round-trip through save → load → fresh screen, unbind race conditions, settings scroll clamps, reduced-motion ↔ background live sync, background odd-size rebuild + min-size clamp, stats accumulation across game-over → PLAY AGAIN, volume-slider drag semantics, pure-function boundaries (`format_time_ms`, `lerp_color`, `key_name`/`key_label`, `record_result`, `spawn_free_cell`), and frozen-mode path assertions proving `settings.json` / `stats.dat` / `music/` / `sfx/` resolve next to the executable when `sys.frozen` is set (with dev-mode paths unchanged). |
| **GRAND TOTAL** | **443** | **~2.5 s, ALL PASSED** |

#### Testing conventions (follow these when contributing)

- **Every assertion goes through `check(label, condition)`** — a first failure raises `AssertionError` (suite exits 1 with the failing label); each pass prints `PASS <label>`. A finished suite prints **`ALL N CHECKS PASSED`** and exits 0; `run_all.py` reads exactly that line for its counts, so keep the wording.
- **CWD-independent bootstrap**: each suite computes `ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` (the project root, parent of `tests/`) and inserts it into `sys.path` before importing `game.*` — that's why suites run identically from the project root, from inside `tests/`, or by absolute path.
- **Persistence is always redirected**: suites reassign the module globals `settings.SETTINGS_PATH`, `stats.STATS_PATH`, `audio.MUSIC_DIR` (and `audio.SFX_DIR` where relevant) to a `tempfile.mkdtemp()` directory that's cleaned up afterwards — **the live `settings.json` / `stats.dat` are never read or written**. Keep it that way.
- **SDL dummy drivers**: `os.environ["SDL_VIDEODRIVER"] = "dummy"` and `os.environ["SDL_AUDIODRIVER"] = "dummy"` are set at module top before `import pygame` — no window or audio device is ever needed.
- `python -m py_compile main.py game/*.py tests/*.py` is the quick syntax gate used in this repo; run it alongside the battery when touching many files.

#### Adding a new test

1. **Create `tests/test_<name>.py`** following the same pattern — copy the bootstrap header (dummy-driver env vars, `ROOT` sys.path insert, temp persistence redirect, `check()` + `PASS` counter, `main()` that ends with `print("\nALL %d CHECKS PASSED" % PASS)` and exits 0/1). `tests/test_phase35_gaps.py` is the most recent, self-contained template.
2. **Register it in `tests/run_all.py`**: the runner does **not** discover files — the suites are a **hardcoded `SUITES` tuple** at the top of the file, in execution order. Append your filename there (with a one-line comment); the next battery run picks it up and includes its count in the grand total.
3. Refresh `TESTS.md` and append to `tests_log.md` (see below) — the battery's console output alone doesn't update them.

#### tests/TESTS.md and tests/tests_log.md

- **`tests/TESTS.md`** — snapshot of the **latest run only**: date, result, per-suite counts, plus notes on what was added and how the files are laid out.
- **`tests/tests_log.md`** — **cumulative history**: every run, every suite ever created, bugs found (and their status); the previous `TESTS.md` contents get archived here as entries.
- Both are **manually maintained** — `run_all.py` only prints to the console and writes no files. When you add or change tests, update `TESTS.md` to reflect the new latest run and append an entry to `tests_log.md`.

### Running from source

Same commands as the [For Players](#for-players) steps: `pip install -r requirements.txt` then `python main.py`. Edit code and just rerun — no build step.

### Music files

Same as for players: drop `.ogg` / `.mp3` / `.wav` into `music/` next to `main.py` and select the track in Settings ("Auto" picks the first file alphabetically). The folder is auto-created at startup and the game runs fine without it.

---

## License

Released under the MIT License — see [LICENSE](LICENSE) for the full text. Copyright (c) 2026 MultiplayerJake.
