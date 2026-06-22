# Decisions Log

Append-only. Every time an approach is tried and rejected — by Piotr or after testing proves
it wrong — log it here with a one-line reason. Check this file before proposing a fix to a
recurring class of problem. Never propose something already rejected here.

Carried over from prior work (do not reintroduce):
- Subqueries in WHERE clauses — rejected on style grounds, use CTE reordering + JOIN instead.
- `FILTER (WHERE ...)` on aggregates — not supported in Snowflake, breaks in production even
  if it works in dev. Use `CASE WHEN ... THEN ... ELSE NULL END` inside the aggregate.

## dbt-agentic-engine

- Generic test config (`relationships: { to, field }`, `accepted_values: { values }`)
  written flat under the test key triggers `MissingArgumentsPropertyInGenericTestDeprecation`
  on dbt-core 1.11. Nest under `arguments:` instead — same behavior, no warning. Apply this
  to every schema.yml going forward in this project.

- `profiles.yml` used a relative duckdb path (`../warehouse/dbt_agentic_engine.duckdb`).
  dbt-duckdb resolves that relative to the process's CWD, not the project root — running
  `dbt build` from the repo root instead of `dbt/` silently created a second, wrong duckdb
  file one directory too high and then errored trying to reconnect to it. Fixed by hardcoding
  an absolute path in `profiles.yml` instead (safe to do since that file is gitignored and
  machine-local anyway, never meant to be portable). Confirmed fix works invoking from both
  the repo root and `dbt/`.

- Eval questions whose `question` text repeats numbers/dates that are themselves the first
  finding the agent is supposed to look up (e.g. quoting the exact MRR bridge figures, or
  the exact cancellation date from `fct_contract_events`, directly in the prompt) defeat the
  point of an investigation-tier question — the agent can answer part of it without calling
  any tool. Caught on self-review of `eval/questions.yml` (q10, q12) before the agent was
  built against it; rewritten so the question states only the observed *symptom*, never the
  underlying row data. Watch for this pattern in future eval-question drafts.

- Checking *all* mart models for failing tests (the literal spec example question) requires
  `list_models` (1 call) + `get_test_results` per mart (6 calls) = 7 calls, which exceeds the
  6-tool-call-per-question hard cap by design once there are more than 5 marts. Scoped q09
  down to 3 named marts so it fits cleanly as a 3-call investigation question. Worth revisiting
  in project 2 (the eval harness) as a deliberate "exceeds budget mid-investigation" test case
  instead of avoiding it — that's explicitly a behavior the spec wants validated, just not
  smuggled into this question set without Piotr signing off on it first.

- The agent's `run_query` tool runs against a DuckDB connection with no `search_path` set, so
  bare table names (`fct_mrr_monthly`) fail — DuckDB requires the schema-qualified name
  (`main_marts.fct_mrr_monthly`) by default. Neither the agent nor a human writing ad-hoc SQL
  would naturally qualify every table. Fixed by running
  `SET search_path = 'main_marts,main_intermediate,main_staging,main_raw'` once when the
  connection opens (`agent/tools.py::_connection`). Caught by actually calling `run_query` with
  realistic SQL during testing, not by inspection.

- `run_query` returned raw `datetime.date` / `decimal.Decimal` objects from DuckDB's cursor,
  which crashed `json.dumps` the moment the agent loop tried to serialize a tool result into a
  `tool_result` block. Caught on the first live run against the real Claude API, not in the
  tool-level smoke tests (which only printed results, never serialized them) — a reminder that
  printing a result and round-tripping it through the actual consumer are different tests.
  Fixed by stringifying non-JSON-native types at the source in `tools.py`, not with a
  `default=str` patch at each call site, so every future consumer (trace logging in particular)
  gets safe values automatically.

- Without a schema-check nudge in the system prompt, the agent frequently guesses plausible
  column names (`customer_name`, `mrr`, `notes`) instead of calling `get_model_columns` first,
  burning tool-call budget on `Binder Error` failures. Added an explicit instruction to check
  columns before querying unless already confirmed earlier in the conversation. This measurably
  helps but does not eliminate the behavior — across ~5 live runs of the same question, the
  agent ranged from a clean 6-call resolution with zero errors to exhausting the full budget on
  guesses. This is real model stochasticity, not a bug in the loop; don't try to prompt it away
  entirely, and don't be surprised if `eval/questions.yml`'s `expected_tool_calls` minimums run
  over in practice on a meaningful fraction of attempts. Worth a closer look in project 2.

- Pasted a real API key into `agent/.env.example` (the committed template) instead of
  `agent/.env` (gitignored) by mistake while testing live. Caught before committing by checking
  `git status` and `git check-ignore` on both files. Always verify which of a template/real-file
  pair actually received a secret before trusting "it's gitignored" — the gitignore protects the
  right file only if the secret landed in it.

- A local (untracked) `.git/hooks/pre-commit` runs `sqlfluff fix --dialect duckdb` on staged
  `.sql` files and re-stages them. With no `.sqlfluff` config in the repo, sqlfluff's default
  `LT04` policy is trailing commas — the opposite of this project's non-negotiable leading-comma
  rule — so the very first dbt commit silently rewrote every model to trailing commas on the way
  in. Caught immediately after committing by re-reading the diff the hook produced, not before.
  Fixed by adding `.sqlfluff` at the repo root with `line_position = leading` under
  `[sqlfluff:layout:type:comma]`, then re-running `sqlfluff fix` and committing the correction
  separately. Lesson: a pre-commit hook that auto-fixes is a second author with its own opinions
  — check its diff after every commit until a config file pins its behavior, not just before.

- CLAUDE.md was committed and pushed in the very first commit, before this project's work began,
  on a public GitHub repo. Caught when reviewing what gets pushed during Phase 4. Fixed by
  installing git-filter-repo and rewriting history to strip CLAUDE.md from every commit, then
  force-pushing — confirmed `git rev-list --objects --all | grep -i claude.md` returns nothing
  post-rewrite. Added CLAUDE.md to .gitignore so it can't be re-tracked; the file still exists
  locally as untracked instructions. `git filter-repo` requires a clean working tree and resets
  tracked files to HEAD before rewriting — it silently discarded uncommitted Phase 4 changes to
  agent_loop.py in the process. Recovered from a full repo backup taken immediately before
  running it. Always back up the whole repo before any history rewrite, not just the file being
  removed, and expect a clean-working-tree precondition to cost you anything uncommitted.

- Chose JSON Lines over a DuckDB table for trace storage (per docs/spec.md, justified in the
  README): the agent's tools enforce no write access to the project's own warehouse, full stop,
  so a writable DuckDB table for traces would mean a second writable connection for no real
  benefit. A flat append-only file needs no database, diffs cleanly when a sample is committed,
  and is readable by project 2's eval harness in any language without a DuckDB dependency.
  Verified queryable both ways: `jq` for ad-hoc filtering and DuckDB's own `read_json_auto`
  directly against the file, satisfying the spec's "queryable/exportable" requirement concretely
  rather than by assertion.
