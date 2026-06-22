"""The four tools exposed to the agent, per docs/spec.md.

run_query is enforced SELECT-only at the connection level: it always executes
against a DuckDB connection opened with read_only=True. DuckDB itself raises
on any CREATE/INSERT/UPDATE/DELETE/DROP statement against a read-only
connection -- this is an engine-level guarantee, not a string check on the
SQL text, which is the bar docs/spec.md sets.
"""

import datetime
import decimal
import os
from pathlib import Path

import duckdb

import dbt_artifacts


def _json_safe(value):
    """DuckDB returns native date/Decimal/etc. objects that json.dumps can't
    serialize. Stringify anything that isn't already JSON-native, here at
    the source, so every consumer (the agent loop, trace logging) gets
    plain JSON-safe values without each needing its own encoder.
    """
    if isinstance(value, (datetime.date, datetime.datetime, decimal.Decimal)):
        return str(value)
    return value

WAREHOUSE_PATH = Path(
    os.environ.get(
        "DBT_AGENTIC_ENGINE_DB_PATH",
        Path(__file__).parent.parent / "warehouse" / "dbt_agentic_engine.duckdb",
    )
)

MAX_ROWS_RETURNED = 200

_read_only_con = None


def _connection() -> duckdb.DuckDBPyConnection:
    global _read_only_con
    if _read_only_con is None:
        _read_only_con = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
        # lets run_query and tool callers use bare model names (fct_mrr_monthly)
        # instead of schema-qualified ones (main_marts.fct_mrr_monthly)
        _read_only_con.execute(
            "SET search_path = 'main_marts,main_intermediate,main_staging,main_raw'"
        )
    return _read_only_con


def list_models() -> dict:
    """Returns dbt model names, layer, and one-line description."""
    models = dbt_artifacts.list_model_nodes()
    return {
        "models": [
            {"name": m["name"], "layer": m["layer"], "description": m["description"]}
            for m in models
        ]
    }


def get_model_columns(model_name: str) -> dict:
    """Returns column names, types, and descriptions for a given model."""
    node = dbt_artifacts.get_model_node(model_name)
    if node is None:
        return {"error": f"No model named '{model_name}'. Use list_models to see available models."}

    descriptions = dbt_artifacts.get_model_column_descriptions(model_name)

    con = _connection()
    rows = con.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
        """,
        [node["schema"], node["alias"]],
    ).fetchall()

    if not rows:
        return {
            "error": (
                f"Model '{model_name}' is defined in dbt but not found in the warehouse "
                f"at {node['schema']}.{node['alias']} -- has `dbt build` been run?"
            )
        }

    return {
        "model": model_name,
        "description": node["description"],
        "columns": [
            {
                "name": col_name,
                "type": data_type,
                "description": descriptions.get(col_name, ""),
            }
            for col_name, data_type in rows
        ],
    }


def run_query(sql: str) -> dict:
    """Executes a query against the DuckDB warehouse. Enforced SELECT-only
    at the connection level (read_only=True) -- any non-SELECT statement
    raises a duckdb.Error before any data is touched.
    """
    con = _connection()
    try:
        cursor = con.execute(sql)
    except duckdb.Error as e:
        return {"error": str(e)}

    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = cursor.fetchmany(MAX_ROWS_RETURNED + 1)
    truncated = len(rows) > MAX_ROWS_RETURNED
    rows = rows[:MAX_ROWS_RETURNED]

    return {
        "columns": columns,
        "rows": [[_json_safe(v) for v in row] for row in rows],
        "row_count": len(rows),
        "truncated": truncated,
    }


def get_test_results(model_name: str) -> dict:
    """Returns dbt test pass/fail status for a model, as of the last dbt build."""
    node = dbt_artifacts.get_model_node(model_name)
    if node is None:
        return {"error": f"No model named '{model_name}'. Use list_models to see available models."}

    tests = dbt_artifacts.get_tests_for_model(model_name)
    return {
        "model": model_name,
        "test_count": len(tests),
        "all_passing": all(t["status"] == "pass" for t in tests) if tests else True,
        "tests": tests,
    }
