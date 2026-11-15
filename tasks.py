#!/usr/bin/env python3
"""Cross-platform task runner.

The Makefile works on the Pi; this works everywhere, including the Windows box
this repo is usually edited on, which has no `make`. Same targets, same
meanings - use whichever your machine has.

    python tasks.py test      unit tests
    python tasks.py check     validate the machine description
    python tasks.py gen       regenerate derived files
    python tasks.py verify    fail if a generated file is stale
    python tasks.py lint      ruff, if installed
    python tasks.py all       verify + lint + test   <- before committing

Stdlib only, and it puts `tools/` and `ui/` on `sys.path` itself rather than
relying on PYTHONPATH, whose separator differs by platform and fails with a
confusing "No module named machinegen".
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for extra in ("tools", "ui"):
    path = str(ROOT / extra)
    if path not in sys.path:
        sys.path.insert(0, path)


def _run(args: list[str], *, optional: bool = False) -> int:
    print(f"$ {' '.join(args)}")
    try:
        return subprocess.call(args, cwd=ROOT)
    except FileNotFoundError:
        if optional:
            print(f"  (skipped - {args[0]} not installed)")
            return 0
        raise


def _pytest(*extra: str) -> int:
    return _run([sys.executable, "-m", "pytest", *extra])


def _machinegen(command: str) -> int:
    from machinegen.cli import main  # noqa: PLC0415 - needs sys.path set above

    print(f"$ machinegen {command}")
    return main([command])


def task_test() -> int:
    return _pytest("tests/unit")


def task_check() -> int:
    return _machinegen("check")


def task_gen() -> int:
    return _machinegen("generate")


def task_verify() -> int:
    return _machinegen("verify")


def task_lint() -> int:
    return _run([sys.executable, "-m", "ruff", "check", "."], optional=True)


def task_integration() -> int:
    return _pytest("tests/integration", "-m", "integration")


def task_hardware() -> int:
    """Deliberately not part of `all` - this moves the machine."""
    print("This runs tests that MOVE THE MACHINE.")
    print("Read docs/commissioning/README.md first. Hand on the E-stop.")
    if input("Type 'yes' to continue: ").strip().lower() != "yes":
        print("aborted")
        return 1
    return _pytest("tests/hardware", "-m", "hardware")


def task_all() -> int:
    for task in (task_verify, task_lint, task_test):
        code = task()
        if code != 0:
            print(f"\nFAILED at {task.__name__.removeprefix('task_')}")
            return code
    print("\nall green")
    return 0


TASKS = {
    name.removeprefix("task_"): fn
    for name, fn in sorted(globals().items())
    if name.startswith("task_")
}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in TASKS:
        print(__doc__)
        print("targets:", ", ".join(sorted(TASKS)))
        return 2
    return TASKS[argv[0]]()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
