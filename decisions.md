# Decisions Log

Append-only. Every time an approach is tried and rejected — by Piotr or after testing proves
it wrong — log it here with a one-line reason. Check this file before proposing a fix to a
recurring class of problem. Never propose something already rejected here.

Carried over from prior work (do not reintroduce):
- Subqueries in WHERE clauses — rejected on style grounds, use CTE reordering + JOIN instead.
- `FILTER (WHERE ...)` on aggregates — not supported in Snowflake, breaks in production even
  if it works in dev. Use `CASE WHEN ... THEN ... ELSE NULL END` inside the aggregate.

(No project-specific decisions yet.)
