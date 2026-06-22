# Project Spec — dbt-Native Analytics Agent

## What this project is for

Portfolio project #1 in a four-project series demonstrating AI + Analytics Engineering
skill, to be published at github.com/PZawieja and linked from goldlayer.dev. Series order:

1. **This project** — agentic tool-use over a dbt project (multi-step, not template-filling)
2. LLMOps cost & eval harness — runs a fixed eval set against this agent, scores accuracy,
   tracks token cost/latency, gates on regressions
3. Semantic layer agent — NL resolves to dbt-defined metrics (MetricFlow / semantic layer),
   never to ad-hoc SQL synthesis
4. Multi-tenant cost guardrails capstone — per-user budget caps, caching, kill-switch on
   warehouse credit spend

This spec covers project 1 only. Don't build ahead into 2–4; reference them only to keep
interfaces compatible (e.g. the trace log format from this project will be consumed by
project 2's eval harness, so keep it structured/parseable).

## The gap this closes

An earlier project (`revenue-intelligence-agent`) already demonstrates governed AI:
intent classification → fills a pre-approved query template. That's the right instinct but
it's one-shot — the LLM picks a template, doesn't reason across steps. This project is the
explicit next level: an agent that can chain multiple tool calls to answer a question that
requires investigation, e.g. "why did NRR drop in March" requires checking several models
and comparing values, not filling one template.

The deliverable that matters most here is the **execution trace**, not the demo. A working
agent answering one question well is not differentiating; a visible, structured log of
*how* it got there (which tools, in what order, what each one returned, what it cost) is
what shows engineering maturity to a hiring manager skimming GitHub.

## Functional requirements

### Sample dbt project (build this first)
A small but realistic dbt project on DuckDB modeling subscription revenue — reuse the
pattern from the existing `gtm-revenue-analytics` repo's staging/intermediate/mart structure
rather than inventing a new domain. Needs enough models and history that "why did metric X
move" questions have real, non-trivial answers (e.g. a contract transfer or plan change
event that affects MoM but not YoY, similar to known real patterns in this person's work —
don't fabricate an unrealistic dataset, make it look like genuine messy SaaS data).

### Toolbelt
Expose exactly these tools to the agent, no more for v1:

- `list_models()` — returns dbt model names, layer (staging/intermediate/mart), and
  one-line description from schema.yml
- `get_model_columns(model_name)` — returns column names, types, and descriptions for a
  given model
- `run_query(sql)` — executes a query against the DuckDB warehouse. **Must be enforced
  SELECT-only at the connection level** (separate read-only connection/role, not a prompt
  instruction or regex check on the SQL string — those are bypassable)
- `get_test_results(model_name)` — returns dbt test pass/fail status for a model

### Agent loop
- Standard tool-use loop against the Claude API: model proposes a tool call, you execute it,
  feed the result back, repeat until the model returns a final answer.
- **Hard cap: 6 tool calls per user question.** If the cap is hit without a final answer,
  return the partial trace and a clear "could not complete within tool-call budget" message
  — don't silently truncate or guess.
- No memory/state across separate questions in v1 — each question starts a fresh trace.

### Trace logging
Every tool call recorded as structured data (JSON lines or a DuckDB table — pick one and
justify it briefly in the README), each record containing: timestamp, question_id, step
number, tool name, input, output (or error), latency_ms, and token usage for that turn if
available from the API response. The trace must be queryable/exportable, not just printed
to stdout — project 2 will consume it.

### Interface
Simple — a CLI or minimal Streamlit input box is enough, consistent with the Streamlit
pattern already used in other repos on goldlayer.dev. Don't over-invest in UI polish; the
trace output is the product.

## Eval question set (write before the agent exists)

Draft 10–15 realistic analytics questions against the sample dbt project now, before
building the agent, so grading isn't done after the fact. Mix of:
- Lookup questions answerable in 1–2 tool calls ("what columns does the MRR mart have")
- Investigation questions requiring 3–5 tool calls and cross-referencing ("which mart
  models currently have failing tests and what do they feed downstream")
- At least 2–3 questions designed to be unanswerable with the given toolbelt, to verify the
  agent says so rather than fabricating an answer

Store these in `eval/questions.yml` or similar with the question text and, where feasible, a
known-good expected answer or SQL result — project 2 will score against this file directly.

## Explicit non-goals for v1

- No multi-tenant anything (project 4)
- No semantic layer / MetricFlow integration (project 3)
- No automated cost/eval scoring loop (project 2) — this project just needs to *produce*
  the trace data that project 2 will later consume
- No write access of any kind from the agent — read-only, full stop

## Definition of done

- Sample dbt project runs clean (`dbt build` passes, tests pass)
- Agent answers at least 80% of the lookup-tier eval questions correctly and correctly
  declines the unanswerable ones (don't grade this formally yet — that's project 2 — but
  sanity-check it manually before calling v1 done)
- Trace log exists, is structured, and one example trace is committed to the repo as a
  sample (for the GitHub README to show directly, since the trace is the differentiator)
- README explains the gap this closes relative to `revenue-intelligence-agent` in 2–3
  sentences — don't make a reader infer it
- `docs/decisions.md` exists, even if just noting "no rejected approaches yet"
