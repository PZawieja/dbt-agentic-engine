"""Standard tool-use loop against the Claude API: model proposes a tool
call, we execute it, feed the result back, repeat until a final answer or
the hard tool-call cap (per docs/spec.md) is hit.

No cross-question memory in v1 -- every call to run_question starts a fresh
message history.
"""

import json
import time
import uuid
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

import tools
import trace_log

load_dotenv()

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MAX_TOOL_CALLS = 6

SYSTEM_PROMPT = """You are an analytics agent answering questions about a B2B SaaS \
subscription revenue dbt project running on DuckDB.

The project follows medallion layering: staging (stg_) models are 1:1 with raw \
sources, intermediate (int_) models hold business logic and joins, and marts \
(dim_/fct_) are the final tables analysts and stakeholders query. Investigate by \
querying marts first; drop down to intermediate or staging models only when a mart \
doesn't have what you need.

You have four tools: list_models, get_model_columns, run_query, and \
get_test_results. run_query only accepts read-only SELECT statements -- it cannot \
write data under any circumstance.

Check a model's exact column names with get_model_columns before writing SQL \
against it unless you already confirmed them earlier in this conversation. A \
query that fails because you guessed a column name still counts against your \
tool-call budget -- it's cheaper to check first.

If a question requires data, an entity, or a capability this project's models \
don't have (e.g. sales pipeline, account ownership, support tickets -- anything \
outside subscriptions, invoices, and contract events), say so plainly and explain \
what's missing. Do not estimate, guess, or fabricate a plausible-sounding answer \
for something the data doesn't track. A small number of verification tool calls \
before declining is good practice; declining without checking when you could \
reasonably check is not.

You have a hard budget of 6 tool calls for this question. Work efficiently -- \
check mart-level data first, and don't make a tool call you don't need.

Write plain prose. No emoji, no decorative tables or headers for a short answer, \
no exclamation points. State what the data shows, then the caveat, then what's \
unconfirmed -- in that order, as sentences, not a slide deck."""

TOOL_SCHEMAS = [
    {
        "name": "list_models",
        "description": (
            "List all dbt models in the project with their layer "
            "(staging/intermediate/marts) and one-line description."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_model_columns",
        "description": "Get column names, types, and descriptions for a given dbt model.",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": "The dbt model name, e.g. 'fct_mrr_monthly'.",
                }
            },
            "required": ["model_name"],
        },
    },
    {
        "name": "run_query",
        "description": (
            "Run a read-only SQL SELECT query against the warehouse. "
            "Any non-SELECT statement is rejected by the database connection."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A SQL SELECT statement."}
            },
            "required": ["sql"],
        },
    },
    {
        "name": "get_test_results",
        "description": "Get dbt test pass/fail status for a given model, as of the last dbt build.",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": "The dbt model name, e.g. 'fct_mrr_bridge_monthly'.",
                }
            },
            "required": ["model_name"],
        },
    },
]

TOOL_FUNCTIONS = {
    "list_models": tools.list_models,
    "get_model_columns": tools.get_model_columns,
    "run_query": tools.run_query,
    "get_test_results": tools.get_test_results,
}

client = anthropic.Anthropic()


def _execute_tool(name: str, tool_input: dict) -> dict:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"Unknown tool '{name}'."}
    try:
        return fn(**tool_input)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def _result(run_id, question_id, question, final_answer, trace, hit_cap, stop_reason, total_usage, started_at) -> dict:
    completed_at = datetime.now(timezone.utc).isoformat()
    summary_record = {
        "record_type": "summary",
        "run_id": run_id,
        "question_id": question_id,
        "question": question,
        "final_answer": final_answer,
        "tool_calls_made": len(trace),
        "hit_cap": hit_cap,
        "stop_reason": stop_reason,
        "total_input_tokens": total_usage["input_tokens"],
        "total_output_tokens": total_usage["output_tokens"],
        "started_at": started_at,
        "completed_at": completed_at,
    }
    trace_log.write_trace_record(summary_record)
    return {
        "run_id": run_id,
        "question_id": question_id,
        "question": question,
        "final_answer": final_answer,
        "trace": trace,
        "tool_calls_made": len(trace),
        "hit_cap": hit_cap,
        "stop_reason": stop_reason,
        "total_usage": total_usage,
    }


def run_question(question: str, question_id: str = "adhoc", max_tool_calls: int = MAX_TOOL_CALLS) -> dict:
    run_id = uuid.uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    messages = [{"role": "user", "content": question}]
    trace = []
    tool_calls_made = 0
    total_usage = {"input_tokens": 0, "output_tokens": 0}

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        total_usage["input_tokens"] += usage["input_tokens"]
        total_usage["output_tokens"] += usage["output_tokens"]

        if response.stop_reason != "tool_use":
            final_text = "".join(b.text for b in response.content if b.type == "text")
            return _result(
                run_id, question_id, question, final_text, trace, False,
                response.stop_reason, total_usage, started_at,
            )

        if tool_calls_made >= max_tool_calls:
            return _result(
                run_id,
                question_id,
                question,
                f"Could not complete within the {max_tool_calls}-tool-call budget. "
                f"Returning partial findings from the {len(trace)} tool call(s) made so far.",
                trace,
                True,
                "tool_call_budget_exceeded",
                total_usage,
                started_at,
            )

        messages.append({"role": "assistant", "content": response.content})
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        tool_results = []

        for block in tool_use_blocks:
            if tool_calls_made >= max_tool_calls:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Tool-call budget exhausted for this question.",
                        "is_error": True,
                    }
                )
                continue

            tool_calls_made += 1
            start = time.monotonic()
            result = _execute_tool(block.name, block.input)
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            is_error = isinstance(result, dict) and "error" in result

            record = {
                "record_type": "tool_call",
                "run_id": run_id,
                "step": tool_calls_made,
                "question_id": question_id,
                "tool_name": block.name,
                "input": block.input,
                "output": None if is_error else result,
                "error": result.get("error") if is_error else None,
                "latency_ms": latency_ms,
                "usage": usage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            trace.append(record)
            trace_log.write_trace_record(record)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                    "is_error": is_error,
                }
            )

        messages.append({"role": "user", "content": tool_results})
