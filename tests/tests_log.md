# tests_log.md — cumulative test history for Quick Snake

Every test-suite run, every test file ever created, every bug discovered
(and its status). `TESTS.md` in this folder always holds ONLY the latest
run; its previous contents are archived as entries below.

---

## Run #1 — 2026-10-30 · suite reorganization + fresh Phase 3.5 edge-case pass

**Agent**: test subagent (reorg + test task). **Result**: ALL PASSED —
429 checks / 5 suites / ~2.4s (`.\.venv\Scripts\python.exe tests\run_all.py`).

### Workspace changes
- Created `tests/`; MOVED the four root-level suites into it:
  `smoke_test.py` (72), `test_extra.py` (105), `test_cyber.py` (53),
  `test_gameplay3.py` (84) — 314 legacy checks, all still passing.
- Fixed each suite's path bootstrap: `ROOT` is now the parent of `tests/`
  (`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`), so the
  suites run correctly from ANY working directory (verified from project
  root AND from inside `tests/`). Test logic untouched.
- Added `tests/run_all.py`: single headless entry point (forces SDL dummy
  drivers, one subprocess per suite, per-suite check counts + grand total,
  exit 0 only if all pass).
- Removed 4 stale root `__pycache__\*.pyc` artifacts of the moved suites.
- Verified `py_compile` on all 23 project .py files (root + game/ + tests/).
- Live `settings.json` / `stats.dat` / `settings.json.bak` confirmed
  untouched (all suites use temp paths; mtimes predate the runs).

### New suite created
- `tests/test_phase35_gaps.py` — 115 checks, fresh edge cases not restating
  existing ones (see TESTS.md for the full 12-section breakdown): live sfx/
  files vs recipes, golden-apple 5000ms exact boundary, countdown dt-clamp,
  mode-picker +10px spacing at odd sizes, unbind full load/save cycle,
  unbind-vs-waiting/P-armed races, scroll clamps with unbind buttons,
  play-screen reduced_motion ↔ background live sync, background odd-size
  rebuild + sub-40px clamp, game-over → restart → second game-over stats
  accumulation, slider drag semantics, pure-function boundaries.

### Results per suite (latest run)
| Suite                 | Checks | Result |
|-----------------------|-------:|--------|
| smoke_test.py         |     72 | PASS   |
| test_extra.py         |    105 | PASS   |
| test_cyber.py         |     53 | PASS   |
| test_gameplay3.py     |     84 | PASS   |
| test_phase35_gaps.py  |    115 | PASS   |
| **GRAND TOTAL**       | **429** | **ALL PASSED** |

### Bugs discovered
- **Game bugs: NONE.** All 429 checks pass; no game-source defect found.
- Observation (characterized, not a bug): only `ui.Button` presses fire the
  global click SFX; `UnbindButton` and `CycleRow` arrows are silent.
- Docs mismatch (reported, files NOT edited per constraints):
  `changelog.md` references `smoke_test.py` at the project root; it now
  lives at `tests/smoke_test.py`.

### Fixed bugs
- (none pending from earlier runs — this is the first entry)

### Re-run history
- 2026-10-30 (final verification): `tests\run_all.py` re-run after docs were
  written — identical result: 429 checks / 5 suites / ~2.4s — ALL PASSED,
  exit 0. (TESTS.md snapshot above still accurate; no changes since.)

---
*(No prior TESTS.md existed before this run, so there is nothing to archive.)*

---

## Run #2 — 2026-10-30 · Phase 4 Task 31: frozen path resolution

**Agent**: implementation subagent (Task 31). **Result**: ALL PASSED —
443 checks / 5 suites / ~2.5s (`.\.venv\Scripts\python.exe tests\run_all.py`).

### Workspace changes
- `game/constants.py`: `PROJECT_ROOT` now resolves NEXT TO THE EXE when
  PyInstaller freezes the game (`sys.frozen` → `os.path.dirname(
  os.path.abspath(sys.executable))`); the dev-mode `__file__`-based
  expression is preserved verbatim in the else-branch, so all 429 previous
  dev-mode checks still pass unchanged. `sys` imported. SETTINGS_PATH /
  MUSIC_DIR / SFX_DIR (constants) and stats.STATS_PATH all derive from
  PROJECT_ROOT, so settings.json, stats.dat, music/ and sfx/ now persist
  next to the exe when frozen (before: everything resolved into the
  `_MEIxxxx` temp extraction dir — the exe "never saved your stats" bug).
- `tests/test_phase35_gaps.py`: +14 checks (section 13) — frozen-mode
  simulation in a subprocess (`sys.frozen`/`sys.executable` faked BEFORE
  importing `game.constants`/`game.stats`) asserting the FINAL path strings
  PROJECT_ROOT, stats.dat, settings.json, music/, sfx/ all land inside the
  fake exe dir (pure path assertions, nothing written); dev-mode subprocess
  asserting paths still equal the real project root; in-interpreter check
  that the suite's own constants are un-frozen. `subprocess` imported; suite
  docstring extended with section 13.

### Results per suite (latest run)
| Suite                 | Checks | Result |
|-----------------------|-------:|--------|
| smoke_test.py         |     72 | PASS   |
| test_extra.py         |    105 | PASS   |
| test_cyber.py         |     53 | PASS   |
| test_gameplay3.py     |     84 | PASS   |
| test_phase35_gaps.py  |    129 | PASS   |
| **GRAND TOTAL**       | **443** | **ALL PASSED** |

### Bugs discovered / fixed
- **FIXED (user-reported)**: frozen exe never persisted user data —
  `PROJECT_ROOT` derived from `__file__` pointed into PyInstaller's `_MEI`
  temp dir, so settings.json/stats.dat died on exit and music//sfx/
  resolved to throwaway temp. Verified end-to-end after rebuild (see below):
  dist\sfx\ now gets its 6 generated WAVs, dist\music\ is auto-created, and
  dist\settings.json was written next to the exe during a live run; a
  throwaway frozen probe exe built from the real `game.stats`/`game.settings`
  save APIs confirmed stats.dat + settings.json are created beside the exe
  (not in _MEIPASS, not in the project). Live project settings.json /
  stats.dat byte-identical (SHA256 + mtime) before and after.
- Game logic bugs: NONE. 443 checks pass.
