"""Run the backend suite and fail the build on any NEW failure.

This exists because the `backend-test` job in `.github/workflows/ci.yml`
carried `continue-on-error: true` at both the job and the step level, so a
failing pytest run could not fail the workflow. 21 tests were red for the
whole life of the tree and every PR stayed green.

Rather than flipping that flag and turning main permanently red, this script
gates against `backend/ci_known_failures.txt`:

  * a test that fails and is NOT in the baseline  ->  exit 1 (build fails)
  * a test in the baseline                         ->  tolerated, reported
  * a baseline test that now passes                ->  reported as STALE,
    because the entry should be deleted

The baseline is a ratchet, not a permanent allowlist. `check_baseline()` fails
the build if an entry was added without a written reason, so the list can only
shrink without someone consciously justifying each addition. That is the
specific failure mode this card is about: the "pre-existing, ignore it"
framing is what let the suite rot while CI stayed green.

Usage (from backend/):
    python scripts/ci_backend_gate.py

Exit codes:
    0  no new failures
    1  new failures, or the baseline file is malformed
    2  pytest itself could not run (collection error, missing deps)
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
BASELINE = BACKEND / "ci_known_failures.txt"

# "FAILED tests/foo.py::Class::test - SomeError: msg"
FAILED_RE = re.compile(r"^FAILED\s+(\S+)")


def parse_baseline(path: Path) -> tuple[set[str], set[str]]:
    """Return (test_ids, ids_with_a_written_reason).

    An entry is "documented" when the comment block above it carries a reason.
    A reason block applies to every entry that follows it until the next reason
    block, so a single comment can cover a group of related tests. Requiring an
    explicit reason is what stops the list from quietly growing.
    """
    if not path.exists():
        return set(), set()

    tests: set[str] = set()
    documented: set[str] = set()
    # A reason block covers entries until a BLANK line or a new marker block
    # ends it. Without the reset, a bare entry appended to the end of the file
    # would silently inherit the last group's reason and pass the check.
    group_documented = False

    # Marker words that make a comment block count as a written reason.
    markers = (
        "---",
        "owner:",
        "because",
        "predates",
        "dead",
        "deliberately",
        "masking",
        "moved",
        "asserts",
    )

    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            # A blank line ends the current reason block.
            group_documented = False
            continue
        if line.startswith("#"):
            # A marker starts (or continues) a reason block covering the
            # entries that follow it.
            if any(word in line.lower() for word in markers):
                group_documented = True
            continue

        if "::" in line:
            tests.add(line)
            if group_documented:
                documented.add(line)

    return tests, documented


def run_pytest() -> tuple[int, set[str]]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--tb=no", "-q"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    output = proc.stdout + proc.stderr

    failures = set()
    for line in output.splitlines():
        m = FAILED_RE.match(line.strip())
        if m:
            failures.add(m.group(1))

    return proc.returncode, failures


def main() -> int:
    baseline, documented = parse_baseline(BASELINE)

    rc, failures = run_pytest()

    # A collection error means pytest never ran the tests. That is an
    # environment problem (missing dependency, bad import) and must not be
    # mistaken for "no new failures".
    if rc not in (0, 1):
        print("=" * 70)
        print("ERROR: pytest did not complete (exit %d)." % rc)
        print("This is usually a collection error or a missing dependency.")
        print("The gate cannot verify anything in this state, so it fails.")
        print("=" * 70)
        return 2

    new_failures = sorted(failures - baseline)
    stale = sorted(baseline - failures)

    print("=" * 70)
    print("Backend gate — %d failing, %d in baseline, %d NEW"
          % (len(failures), len(failures & baseline), len(new_failures)))
    print("=" * 70)

    if stale:
        print("\nSTALE baseline entries (these tests now PASS — delete them):")
        for test in stale:
            print("  - %s" % test)
        print(
            "\nThis is not a failure, but each of these is a line item to\n"
            "remove from %s." % BASELINE.name
        )

    if new_failures:
        print("\nNEW failures (not in the baseline) — build FAILS:")
        for test in new_failures:
            print("  - %s" % test)
        print(
            "\nIf a new failure is a genuine pre-existing defect rather than a\n"
            "regression, it may be added to %s ONLY with a written reason\n"
            "above the entry. Silent additions are what this gate exists to\n"
            "prevent." % BASELINE.name
        )
        return 1

    # Every entry must carry a reason. A bare list is how the rot started.
    undocumented = sorted(baseline - documented)
    if undocumented:
        print("\nBaseline entries with no written reason — build FAILS:")
        for test in undocumented:
            print("  - %s" % test)
        print(
            "\nEach entry needs a comment above it explaining why the test is\n"
            "expected to fail. See the existing entries for the format."
        )
        return 1

    print("\nNo new failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
