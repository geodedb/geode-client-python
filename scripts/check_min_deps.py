#!/usr/bin/env python3
"""Prove the package imports with its declared MINIMUM dependency versions.

SONNY-6723: setup.py declared ``grpcio>=1.50.0`` while the generated gRPC
stubs refuse to import below the grpcio that generated them, so an
environment that satisfied the declared range could not ``import
geode_client``. This script:

1. reads the runtime ``install_requires`` floors from setup.py (via ``ast``,
   without executing it) and checks requirements.txt declares the same floors;
2. creates a clean virtual environment;
3. installs the package with every runtime dependency constrained to exactly
   its declared floor (``pip install --constraint``, wheels only);
4. imports ``geode_client`` (and the gRPC stubs) from outside the source tree
   and checks the installed versions are the floors.

It exits non-zero on any failure. Standard library only.

Usage: python scripts/check_min_deps.py [--venv DIR] [--python PYTHON]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SETUP_PY = REPO_ROOT / "setup.py"
REQUIREMENTS_TXT = REPO_ROOT / "requirements.txt"

_REQ_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$")
_FLOOR_RE = re.compile(r">=\s*([0-9][0-9A-Za-z.]*)")


def normalize(name: str) -> str:
    """PEP 503 project-name normalization."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirement(req: str) -> tuple[str, str | None]:
    """Return (normalized name, ``>=`` floor or None) for a requirement."""
    match = _REQ_RE.match(req.split(";", 1)[0])
    if match is None:
        raise ValueError(f"unparseable requirement: {req!r}")
    floor = _FLOOR_RE.search(match.group(2))
    return normalize(match.group(1)), floor.group(1) if floor else None


def setup_install_requires() -> list[str]:
    """Extract the literal ``install_requires`` list from setup.py."""
    tree = ast.parse(SETUP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "install_requires":
            return list(ast.literal_eval(node.value))
    raise SystemExit("setup.py: install_requires not found")


def requirements_floors() -> dict[str, str | None]:
    floors: dict[str, str | None] = {}
    for line in REQUIREMENTS_TXT.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, floor = parse_requirement(line)
            floors[name] = floor
    return floors


def run(cmd: list[str], **kwargs) -> None:
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def check_metadata(errors: list[str]) -> dict[str, str]:
    """Validate the declared floors; return {name: floor} for runtime deps.

    Problems are appended to ``errors`` so the install/import proof still runs.
    """
    floors: dict[str, str] = {}
    for req in setup_install_requires():
        name, floor = parse_requirement(req)
        if floor is None:
            errors.append(f"setup.py: {req!r} declares no >= floor")
            continue
        floors[name] = floor

    pinned = requirements_floors()
    for name, floor in floors.items():
        if name not in pinned:
            errors.append(f"requirements.txt: missing runtime dependency {name}")
        elif pinned[name] != floor:
            errors.append(
                f"floor mismatch for {name}: setup.py >={floor}, "
                f"requirements.txt >={pinned[name]}"
            )

    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    return floors


_IMPORT_PROBE = """
import importlib.metadata as md, json, sys
import geode_client
from geode_client.proto import geode_pb2, geode_pb2_grpc  # noqa: F401
assert geode_client.__file__ and "site-packages" in geode_client.__file__, (
    "imported geode_client from the source tree, not the installed package: "
    + str(geode_client.__file__)
)
names = json.loads(sys.argv[1])
print(json.dumps({n: md.version(n) for n in names}))
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--venv", help="venv directory (default: a temp dir)")
    parser.add_argument(
        "--python", default=sys.executable, help="interpreter to build the venv"
    )
    args = parser.parse_args()

    errors: list[str] = []
    floors = check_metadata(errors)
    print(
        "Declared runtime floors: " + ", ".join(f"{n}>={v}" for n, v in floors.items())
    )

    with tempfile.TemporaryDirectory(prefix="geode-min-deps-") as tmp:
        venv = Path(args.venv) if args.venv else Path(tmp) / "venv"
        run([args.python, "-m", "venv", "--clear", str(venv)])
        py = str(venv / "bin" / "python")

        constraints = Path(tmp) / "constraints.txt"
        constraints.write_text(
            "".join(f"{n}=={v}\n" for n, v in floors.items()), encoding="utf-8"
        )
        print(constraints.read_text(encoding="utf-8"), end="")

        run([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
        # Wheels only for the runtime deps; the package itself is built locally.
        binary_flags = [f"--only-binary={n}" for n in floors]
        try:
            run(
                [
                    py,
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    *binary_flags,
                    "--constraint",
                    str(constraints),
                    str(REPO_ROOT),
                ]
            )
        except subprocess.CalledProcessError:
            print(
                "FAIL: the declared minimum versions are not installable",
                file=sys.stderr,
            )
            return 1

        # Run from an unrelated cwd in isolated mode so the source tree is not
        # on sys.path and the installed distribution is what gets imported.
        result = subprocess.run(
            [py, "-I", "-c", _IMPORT_PROBE, json.dumps(sorted(floors))],
            cwd=tmp,
            capture_output=True,
            text=True,
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode != 0:
            print(
                "FAIL: `import geode_client` fails at the declared minimum versions",
                file=sys.stderr,
            )
            return 1

        installed = json.loads(result.stdout.strip().splitlines()[-1])
        drift = {n: v for n, v in installed.items() if v != floors[n]}
        if drift:
            print(
                f"FAIL: installed versions are not the floors: {drift}", file=sys.stderr
            )
            return 1

    if errors:
        print("FAIL: declared dependency metadata is inconsistent", file=sys.stderr)
        return 1
    print("PASS: geode_client imports with every runtime dependency at its floor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
