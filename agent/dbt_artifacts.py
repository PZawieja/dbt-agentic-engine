"""Read dbt's own build artifacts (manifest.json, run_results.json) and the
live DuckDB warehouse to answer metadata questions. No hand-parsed YAML --
dbt already computed this, and re-deriving it would drift from what `dbt
build` actually produced.
"""

import json
from pathlib import Path

DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt"
MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"
RUN_RESULTS_PATH = DBT_PROJECT_DIR / "target" / "run_results.json"

_manifest = None
_run_results = None


def _load_manifest() -> dict:
    global _manifest
    if _manifest is None:
        if not MANIFEST_PATH.exists():
            raise FileNotFoundError(
                f"{MANIFEST_PATH} not found -- run `dbt build` in {DBT_PROJECT_DIR} first."
            )
        with open(MANIFEST_PATH) as f:
            _manifest = json.load(f)
    return _manifest


def _load_run_results() -> dict:
    global _run_results
    if _run_results is None:
        if not RUN_RESULTS_PATH.exists():
            raise FileNotFoundError(
                f"{RUN_RESULTS_PATH} not found -- run `dbt build` in {DBT_PROJECT_DIR} first."
            )
        with open(RUN_RESULTS_PATH) as f:
            _run_results = json.load(f)
    return _run_results


def _model_nodes() -> dict:
    manifest = _load_manifest()
    return {
        node["name"]: node
        for node in manifest["nodes"].values()
        if node["resource_type"] == "model"
    }


def list_model_nodes() -> list[dict]:
    """One entry per dbt model: name, layer, description, unique_id, schema, alias."""
    nodes = []
    for node in _model_nodes().values():
        # fqn = [project_name, layer_dir, ..., model_name] -- layer_dir is staging/intermediate/marts
        layer = node["fqn"][1] if len(node["fqn"]) > 2 else "unknown"
        nodes.append(
            {
                "name": node["name"],
                "layer": layer,
                "description": node["description"],
                "unique_id": node["unique_id"],
                "schema": node["schema"],
                "alias": node.get("alias") or node["name"],
            }
        )
    return sorted(nodes, key=lambda n: (n["layer"], n["name"]))


def get_model_node(model_name: str) -> dict | None:
    return _model_nodes().get(model_name)


def get_model_column_descriptions(model_name: str) -> dict[str, str]:
    """column_name -> description, from the model's schema.yml docs."""
    node = get_model_node(model_name)
    if node is None:
        return {}
    return {col_name: col["description"] for col_name, col in node["columns"].items()}


def get_tests_for_model(model_name: str) -> list[dict]:
    """All generic/singular tests attached to this model, with their last run status."""
    node = get_model_node(model_name)
    if node is None:
        return []

    manifest = _load_manifest()
    run_results_by_id = {r["unique_id"]: r for r in _load_run_results()["results"]}

    tests = []
    for test_node in manifest["nodes"].values():
        if test_node["resource_type"] != "test":
            continue
        if test_node.get("attached_node") != node["unique_id"]:
            continue
        result = run_results_by_id.get(test_node["unique_id"])
        metadata = test_node.get("test_metadata") or {}
        tests.append(
            {
                "test_name": test_node["name"],
                "test_type": metadata.get("name", "singular"),
                "column_name": (metadata.get("kwargs") or {}).get("column_name"),
                "status": result["status"] if result else "not_run",
                "message": result["message"] if result else None,
            }
        )
    return sorted(tests, key=lambda t: t["test_name"])
