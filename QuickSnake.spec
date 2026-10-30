# -*- mode: python ; coding: utf-8 -*-
"""Quick Snake - PyInstaller spec: ONE single-file windowed exe, NO data files.

Rebuild (one command, from the project root):   .\\build.ps1
Direct PyInstaller invocation (equivalent):     .\\.venv\\Scripts\\python.exe -m PyInstaller --noconfirm QuickSnake.spec

BUNDLE RULES (see REPORT / project docs for rationale):
  * NEVER bundled: settings.json, stats.dat, settings.json.bak, music/,
    tests/, .venv/, plan & changelog docs. `datas` is intentionally empty.
  * sfx/ is intentionally NOT bundled: the six WAVs are auto-generated at
    startup by game/audio.generate_sfx() (guarded - missing/unwritable only
    means silence, never a crash), so bundling them would be dead weight.
  * Data-file paths (SETTINGS_PATH / STATS_PATH / MUSIC_DIR / SFX_DIR) are
    derived from game/constants.py PROJECT_ROOT (based on __file__). NOTE:
    when frozen, __file__ points inside PyInstaller's _MEIPASS temp dir, so
    today the game reads/writes its data there, NOT next to the exe. A
    one-line frozen-aware fix to PROJECT_ROOT is recommended (resolving it
    against sys.executable when getattr(sys, "frozen", False)); this spec is
    deliberately kept compatible with both the current and the fixed code.
"""

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],  # no data files: user data (settings/stats/music) must never be bundled
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", "unittest", "pydoc_data"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="QuickSnake",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX often trips AV scanners; keep the binary vanilla
    runtime_tmpdir=None,
    console=False,  # windowed app (game); the src says --noconsole
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)
