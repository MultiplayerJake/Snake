# TESTS.md — Quick Snake test battery (snapshot: LATEST RUN ONLY)

**Last run**: 2026-10-30 · **Result**: ALL PASSED · **Grand total**: 443 checks across 5 suites (~2.5s)
**One command**: `.\.venv\Scripts\python.exe tests\run_all.py` (works from any CWD)

## Layout (all test material lives in `tests/`)

```
tests/
  run_all.py            # single entry point: runs every suite headless, per-suite
                        # counts + grand total, exit 0 only if everything passes
  smoke_test.py         # Phase 2 (Tasks 9-19)
  test_extra.py         # Phase 2 coverage gaps
  test_cyber.py         # Phase 3 design half (Tasks 24-26 visual)
  test_gameplay3.py     # Phase 3 gameplay half + Phase 3.5 (Tasks 27-29)
  test_phase35_gaps.py  # NEW: fresh edge-case pass over the Phase 3.5 features
  TESTS.md              # this file — snapshot of the latest run only
  tests_log.md          # cumulative history of every run
```

Each suite sets `SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy` itself and
redirects settings.json / stats.dat / music / to temp directories — the live
files are never touched (verified: mtimes unchanged after a full run). Path
bootstrap is `__file__`-based (`ROOT = parent of tests/`), so every suite and
the runner work from the project root, from inside `tests/`, or via absolute
path.

## Results (latest run)

| Suite                  | Checks | Result | Time  |
|------------------------|-------:|--------|------:|
| smoke_test.py          |     72 | PASS   |  0.7s |
| test_extra.py          |    105 | PASS   |  0.6s |
| test_cyber.py          |     53 | PASS   |  0.3s |
| test_gameplay3.py      |     84 | PASS   |  0.4s |
| test_phase35_gaps.py   |    129 | PASS   |  0.6s |
| **GRAND TOTAL**        | **443** | **ALL PASSED** | **2.5s** |

All four legacy suites (314 checks) pass unchanged from their new location;
both from the project root AND from inside `tests/` (CWD-independence
verified for every suite individually).

## New tests added this run: `tests/test_phase35_gaps.py` (129 checks)

1. **Live project sfx/ vs recipes** — the six real `sfx/*.wav` files exist and
   match `SFX_RECIPES` exactly (frame count, mono/16-bit/22050Hz, ±1ms
   duration). Read-only.
2. **Golden apple 5000ms boundary** — alive at 4999ms, dead exactly at 5000ms
   (and on an overshooting frame); urgency clamps at 0.0/1.0; expiry through
   the real game loop at the exact deadline; expiry never scores or counts.
3. **Countdown dt-clamp** — a 10s lag frame advances the countdown by at most
   100ms (beats can never be skipped), the next real second still beeps "2".
4. **Mode picker +10px spacing at odd sizes** (777x513, 1023x767, 641x481) —
   equal step, exactly +10px over base gap, centered, blurbs clear BACK;
   layout idempotent.
5. **Unbind through a real save→load→fresh-screen cycle** — JSON holds
   `null`, `load_settings()` keeps None, a brand-new SettingsScreen renders
   `[ unbound ]`, and a game built from the reloaded dict ignores the old key.
6. **Unbind race conditions** — unbind click beats "press any key" waiting;
   unbind clears a P-armed warning; UnbindButton does not fire the global
   click SFX (characterization).
7. **Settings scroll clamps with unbind buttons present** — clamps exactly at
   `_max_scroll`, unbind buttons stay in-bounds and remain clickable when
   scrolled, wheel-up clamps at 0, no-op without overflow; ESC ladder (first
   ESC cancels waiting, second ESC leaves the screen).
8. **Play-screen reduced_motion ↔ background live interaction** — built with
   reduced_motion, live toggle re-enables/re-suppresses without rebuilding
   the backdrop object, in-flight streaks cleared, resize rebuilds through
   the game loop.
9. **Background rebuild at odd sizes** (777x513, 1001x499, 333x777) + the
   sub-40px min-size clamp (40x40 static layer, never crashes).
10. **game-over → PLAY AGAIN → second game-over stats accumulation** —
    1→2→3 games and 2 deaths/1 win accumulate across runs, disk matches
    memory after each finish, a lower second score never regresses the best,
    the overlay redraws.
11. **Volume slider drag** — value from x-position, clamps past both edges,
    live audio update, persisted on release.
12. **Pure-function boundaries** — `format_time_ms` (0, negative, 59999.9,
    exact minute rollover, >1h), `lerp_color` t-clamping, `key_name`/
    `key_label` unknown-key fallback, `record_result` negative clamps and
    win/death exclusivity, `spawn_free_cell`/`Apple.respawn` on a full board.
13. **Frozen (PyInstaller) path resolution (Task 31)** — in a subprocess
    that simulates PyInstaller's runtime (`sys.frozen = True`,
    `sys.executable = <fake dir>QuickSnake.exe`) BEFORE importing the game,
    `PROJECT_ROOT` AND the final path strings `STATS_PATH` (`stats.dat`),
    `SETTINGS_PATH` (`settings.json`), `MUSIC_DIR` (`music/`) and `SFX_DIR`
    (`sfx/`) all resolve INSIDE the fake exe folder (which stays empty —
    pure path assertions); a second dev-mode subprocess asserts every path
    still resolves to the real project root (non-frozen semantics
    byte-identical), plus an in-interpreter check that the suite's own
    `game.constants` is un-frozen. 14 checks.

## Game bugs found

None. All 443 checks pass; no game-source defect was observed. Minor
observation (not a failure, characterized in tests): only `Button` presses
fire the global click SFX — `UnbindButton`, `CycleRow` arrows, sliders and
toggles are silent by design.

## Docs-reference mismatch (reported, NOT edited)

`changelog.md` still references `smoke_test.py` at the project root (Phase 2
entry). The file now lives at `tests/smoke_test.py`. Per task constraints
changelog.md/plan.md were not modified; this reference mismatch is
intentional and accepted.

## Deviations from the task

- Kept the original suite filenames (smoke_test.py, test_extra.py,
  test_cyber.py, test_gameplay3.py) instead of renaming to a uniform
  `test_*.py` convention, to match the requested layout exactly; the runner
  makes the naming moot for discoverability.
- Also removed 4 stale `__pycache__\*.pyc` artifacts of the moved test files
  from the project root (build artifacts, not sources).
- `Tests/TESTS.md` + `Tests/tests_log.md` were requested by the agent-level
  conventions; on Windows `tests/` is the same folder, so they live inside
  `tests/` next to the suites.
