"""Append-only JSON Lines trace log, per docs/spec.md.

JSON Lines over a DuckDB table: the agent's tools enforce no write access to
the project's own warehouse, full stop (see docs/spec.md non-goals) -- a
writable DuckDB table for traces would mean introducing a second writable
connection for no real benefit here. A flat append-only file needs no
database, diffs cleanly when an example trace is committed as a sample, and
is readable by project 2's eval harness in any language without a DuckDB
dependency: `jq`, DuckDB's own `read_json_auto`, or plain `json.loads` per
line all work directly against it.
"""

import json
import os
from pathlib import Path

TRACE_LOG_PATH = Path(
    os.environ.get(
        "TRACE_LOG_PATH",
        Path(__file__).parent.parent / "traces" / "trace_log.jsonl",
    )
)


def write_trace_record(record: dict) -> None:
    TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACE_LOG_PATH, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")
