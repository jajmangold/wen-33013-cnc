"""Command line entry point.

    python -m machinegen check      validate the machine description only
    python -m machinegen generate   write every generated file
    python -m machinegen verify     fail if any generated file is stale

`verify` is what CI and the pre-commit hook run. It is the mechanism that
stops a generated file drifting away from machine/wen33013.toml.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .constraints import Severity, check_machine, errors
from .emit import fingerprint, generate_all
from .model import MachineConfigError, default_machine_path, load_machine


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _report(violations) -> None:
    for v in violations:
        stream = sys.stderr if v.severity is Severity.ERROR else sys.stdout
        print(v, file=stream)


def cmd_check(args: argparse.Namespace) -> int:
    machine = load_machine(args.machine)
    violations = check_machine(machine)
    _report(violations)
    fatal = errors(violations)
    if fatal:
        print(f"\n{len(fatal)} error(s) - refusing to generate.", file=sys.stderr)
        return 1
    print(f"machine OK: {machine.name} ({len(violations)} warning(s))")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    machine = load_machine(args.machine)
    violations = check_machine(machine)
    _report(violations)
    if errors(violations):
        print("\nrefusing to generate from an invalid machine.", file=sys.stderr)
        return 1

    fp = fingerprint(args.machine)
    for path, content in generate_all(machine, _repo_root(), fp).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(_repo_root())}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    machine = load_machine(args.machine)
    fp = fingerprint(args.machine)
    root = _repo_root()
    stale: list[Path] = []
    for path, expected in generate_all(machine, root, fp).items():
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual != expected:
            stale.append(path)
    if stale:
        print("stale generated file(s):", file=sys.stderr)
        for path in stale:
            print(f"  {path.relative_to(root)}", file=sys.stderr)
        print("\nRun: python -m machinegen generate", file=sys.stderr)
        return 1
    print("all generated files are current")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="machinegen", description=__doc__)
    parser.add_argument(
        "--machine",
        type=Path,
        default=default_machine_path(),
        help="path to the machine description (default: machine/wen33013.toml)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate only").set_defaults(func=cmd_check)
    sub.add_parser("generate", help="write generated files").set_defaults(func=cmd_generate)
    sub.add_parser("verify", help="fail if generated files are stale").set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except MachineConfigError as exc:
        print(f"machine description invalid: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
