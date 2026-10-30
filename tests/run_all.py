"""Single entry point: run every Quick Snake test suite headless.

Usage (from the project root or anywhere):
    .\\.venv\\Scripts\\python.exe tests\\run_all.py

Each suite runs in its own subprocess for full isolation (pygame init/quit
and module-level settings/stats/music/SFX path patches per suite). SDL dummy
video/audio drivers are forced HERE as well, so no suite can ever open a
real window or touch an audio device, no matter how it is invoked.

Reports per-suite check counts and a grand total. Exits 0 only if every
suite exits 0. The live settings.json / stats.dat are never touched (each
suite redirects persistence to a temp directory).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

# Suites in execution order; all live next to this runner in tests/.
SUITES = (
    "smoke_test.py",       # Phase 2 (Tasks 9-19)
    "test_extra.py",       # Phase 2 coverage gaps
    "test_cyber.py",       # Phase 3 design half (Tasks 24-26 visual)
    "test_gameplay3.py",   # Phase 3 gameplay half + Phase 3.5 (T27-29)
    "test_phase35_gaps.py",  # Fresh edge-case pass over the Phase 3.5 features
)

CHECKS_RE = re.compile(r"ALL (\d+) CHECKS PASSED")


def run_suite(name):
    """Run one suite as a subprocess; returns (returncode, checks, seconds,
    stdout, stderr)."""
    path = os.path.join(TESTS_DIR, name)
    started = time.time()
    proc = subprocess.run(
        [sys.executable, path],
        cwd=PROJECT_ROOT,  # suites are CWD-independent; root is a sane default
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=600,
    )
    elapsed = time.time() - started
    match = CHECKS_RE.search(proc.stdout or "")
    checks = int(match.group(1)) if match else 0
    return proc.returncode, checks, elapsed, proc.stdout or "", proc.stderr or ""


def tail(text, lines=15):
    return "\n".join(text.strip().splitlines()[-lines:])


def main():
    print("=== Quick Snake test battery (headless, SDL dummy drivers) ===")
    print("python: %s" % sys.executable)
    print("suites: %s" % ", ".join(SUITES))
    print("")

    grand_total = 0
    failures = []
    started = time.time()
    for name in SUITES:
        code, checks, elapsed, out, err = run_suite(name)
        grand_total += checks
        status = "PASS" if code == 0 else "FAIL"
        print("%-4s  %-22s %4d checks  %5.1fs" % (status, name, checks, elapsed))
        if code != 0:
            failures.append(name)
            print("      --- last output ---")
            print("      " + tail(out).replace("\n", "\n      "))
            if err.strip():
                print("      --- stderr ---")
                print("      " + tail(err, 8).replace("\n", "\n      "))
            print("")

    total_elapsed = time.time() - started
    print("")
    print("-" * 60)
    if failures:
        print("GRAND TOTAL: %d checks across %d suites in %.1fs - FAILED (%s)"
              % (grand_total, len(SUITES), total_elapsed, ", ".join(failures)))
        return 1
    print("GRAND TOTAL: %d checks across %d suites in %.1fs - ALL PASSED"
          % (grand_total, len(SUITES), total_elapsed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
