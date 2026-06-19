"""Batch and pipeline execution support for Geode.

Mirrors the Go reference (batch.go): a Statement pairs a GQL query with
optional bound parameters; batch_exec runs statements in a single
transaction with retry; pipeline_exec runs chunks concurrently.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Default number of statements per chunk in pipeline_exec (Go: DefaultChunkSize).
DEFAULT_CHUNK_SIZE = 100

# Default maximum number of concurrent chunk workers (Go: DefaultMaxWorkers).
DEFAULT_MAX_WORKERS = 8


@dataclass
class Statement:
    """A GQL query paired with its optional bound parameters."""

    query: str
    params: Optional[Dict[str, Any]] = None


def chunk_statements(
    statements: List[Statement], chunk_size: int
) -> List[List[Statement]]:
    """Split statements into contiguous chunks of at most chunk_size."""
    if chunk_size <= 0:
        chunk_size = DEFAULT_CHUNK_SIZE
    return [
        statements[i : i + chunk_size] for i in range(0, len(statements), chunk_size)
    ]
