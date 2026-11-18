"""SONNY-6723: declared dependency floors must satisfy the generated stubs.

The generated gRPC stub raises at import when grpcio is older than
``GRPC_GENERATED_VERSION``, and the protobuf gencode refuses runtimes older
than the version it validates. If setup.py/requirements.txt declare floors
below those, an environment that satisfies the declared range cannot import
``geode_client``. These checks read the files statically (no network); the
end-to-end proof is ``scripts/check_min_deps.py`` (CI job ``test:min-deps``).
"""

import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROTO_DIR = _REPO_ROOT / "geode_client" / "proto"


def _version_tuple(version: str) -> tuple:
    return tuple(int(part) for part in version.split("."))


def _setup_requires() -> dict:
    tree = ast.parse((_REPO_ROOT / "setup.py").read_text(encoding="utf-8"))
    reqs: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in (
            "install_requires",
            "extras_require",
        ):
            value = ast.literal_eval(node.value)
            items = value if isinstance(value, list) else sum(value.values(), [])
            for req in items:
                name = re.split(r"[<>=!~ ]", req, maxsplit=1)[0].lower()
                reqs.setdefault(name, req)
    return reqs


def _requirements_txt() -> dict:
    reqs = {}
    text = (_REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            reqs[re.split(r"[<>=!~ ]", line, maxsplit=1)[0].lower()] = line
    return reqs


def _floor(req: str) -> tuple:
    match = re.search(r">=\s*([0-9.]+)", req)
    assert match is not None, f"{req!r} declares no >= floor"
    return _version_tuple(match.group(1))


def _grpc_generated_version() -> tuple:
    source = (_PROTO_DIR / "geode_pb2_grpc.py").read_text(encoding="utf-8")
    match = re.search(r"GRPC_GENERATED_VERSION = '([0-9.]+)'", source)
    assert match is not None
    return _version_tuple(match.group(1))


def _protobuf_gencode_version() -> tuple:
    source = (_PROTO_DIR / "geode_pb2.py").read_text(encoding="utf-8")
    match = re.search(
        r"ValidateProtobufRuntimeVersion\(\s*_runtime_version\.Domain\.PUBLIC,"
        r"\s*(\d+),\s*(\d+),\s*(\d+),",
        source,
    )
    assert match is not None
    return tuple(int(g) for g in match.groups())


class TestGrpcFloor:
    def test_setup_py_grpcio_floor_satisfies_stub_guard(self):
        assert _floor(_setup_requires()["grpcio"]) >= _grpc_generated_version()

    def test_requirements_txt_grpcio_floor_matches_setup_py(self):
        assert _floor(_requirements_txt()["grpcio"]) == _floor(
            _setup_requires()["grpcio"]
        )

    def test_grpcio_tools_floor_matches_generator(self):
        """Regenerating with an older grpcio-tools would lower the guard."""
        assert _floor(_setup_requires()["grpcio-tools"]) >= _grpc_generated_version()


class TestProtobufRange:
    def test_setup_py_protobuf_floor_satisfies_gencode(self):
        assert _floor(_setup_requires()["protobuf"]) >= _protobuf_gencode_version()

    def test_requirements_txt_protobuf_floor_matches_setup_py(self):
        assert _floor(_requirements_txt()["protobuf"]) == _floor(
            _setup_requires()["protobuf"]
        )


class TestFloorsConsistent:
    def test_every_runtime_floor_matches_requirements_txt(self):
        """setup.py and requirements.txt must not drift (SONNY-6723)."""
        tree = ast.parse((_REPO_ROOT / "setup.py").read_text(encoding="utf-8"))
        install_requires = next(
            ast.literal_eval(node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.keyword) and node.arg == "install_requires"
        )
        pinned = _requirements_txt()
        for req in install_requires:
            name = re.split(r"[<>=!~ ]", req, maxsplit=1)[0].lower()
            assert name in pinned, f"requirements.txt is missing {name}"
            assert _floor(pinned[name]) == _floor(req), (req, pinned[name])
