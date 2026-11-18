"""Tests guarding version single-sourcing across the package and setup.py."""

import re
from pathlib import Path

import geode_client

EXPECTED_VERSION = "0.5.1"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SETUP_PY = _REPO_ROOT / "setup.py"


def _setup_version() -> str:
    """Parse the ``version=`` string from setup.py without executing it."""
    source = _SETUP_PY.read_text(encoding="utf-8")
    match = re.search(r"""version\s*=\s*["']([^"']+)["']""", source)
    assert match is not None, "could not find version= in setup.py"
    return match.group(1)


class TestVersionConsistency:
    """Ensure __version__ and setup.py stay in lockstep."""

    def test_package_version_matches_setup_py(self):
        """__version__ must equal setup.py's version (guards future drift)."""
        assert geode_client.__version__ == _setup_version()

    def test_package_version_is_expected(self):
        """The declared package version is the released 0.5.1."""
        assert geode_client.__version__ == EXPECTED_VERSION

    def test_setup_version_is_expected(self):
        """setup.py declares the released 0.5.1."""
        assert _setup_version() == EXPECTED_VERSION
