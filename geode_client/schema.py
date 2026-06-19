"""Schema file parsing for Geode (mirrors Go schema.go ParseSchemaFS).

Reads ``*.gql`` files from a directory, strips blank lines, line comments
(``//`` and ``--``), and lines that do not begin with a recognised GQL
keyword (CREATE, MERGE, MATCH, DELETE), then splits the surviving lines on
``;`` into individual statements.
"""

import os
from typing import List, Union

from .batch import Statement

_GQL_PREFIXES = ("CREATE", "MERGE", "MATCH", "DELETE")


def parse_schema_fs(path: Union[str, "os.PathLike[str]"]) -> List[Statement]:
    """Read all ``.gql`` files directly under ``path`` and return Statements.

    Subdirectories are not traversed; only direct children matching
    ``*.gql`` are read. Raises OSError if the directory cannot be read.
    """
    statements: List[Statement] = []
    entries = sorted(os.listdir(path))
    for name in entries:
        full = os.path.join(path, name)
        if os.path.isdir(full) or not name.endswith(".gql"):
            continue
        with open(full, encoding="utf-8") as handle:
            content = handle.read()
        for line in content.split("\n"):
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("//") or trimmed.startswith("--"):
                continue
            upper = trimmed.upper()
            if not upper.startswith(_GQL_PREFIXES):
                continue
            for part in trimmed.split(";"):
                part = part.strip()
                if part:
                    statements.append(Statement(query=part))
    return statements
