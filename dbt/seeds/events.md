# Seed Events — Ground Truth

This file documents the business events deliberately baked into the seed data. It is the
ground truth used to (1) write eval questions with known-correct answers, and (2)
sanity-check the agent's answers later. If a mart shows a different effect than documented
here, the mart is wrong — not the doc.

All months below are `2025-MM-01` (first of month), matching `month_date` /
`invoice_month` / `recognized_month` grain in the seeds.

## Event 1 — Plan upgrade (Acme Co, April 2025)

- **subscription_id**: `S001`, **customer**: `C001` Acme Co
- Growth ($800/mo) → Enterprise ($2,400/mo), effective **2025-04-01**
- `raw_contract_events.event_id = E001`
- **Expected mart effect**:
  - `fct_mrr_monthly`: Acme's contracted MRR jumps from $800 to $2,400 in April (+$1,600),
    and stays at $2,400 through December.
  - `fct_mrr_bridge_monthly`: April shows +$1,600 of **expansion MRR** attributed to C001.
  - `fct_customer_logo_monthly`: **no change** — Acme is active before and after, same
    logo. Logo count for April should NOT reflect this event at all.

## Event 2 — Contract transfer (Initech LLC → Globex Corp, July 2025)

- **subscription_id**: `S003` (same subscription throughout — never canceled or recreated)
- **old_customer_id**: `C003` Initech LLC, **new_customer_id**: `C004` Globex Corp
- Initech LLC was acquired by Globex Corp. The contract transferred at unchanged terms
  (Growth plan, $900/mo), effective **2025-07-01**.
- `raw_contract_events.event_id = E002`
- **Expected mart effect**:
  - `fct_mrr_monthly`: total MRR contribution of S003 is flat at $900/mo across June → July
    — no dip, no spike — just a change in which `customer_id` it's attributed to.
  - `fct_customer_logo_monthly`: Initech (C003) shows as a churned logo in July; Globex
    (C004) shows as a new logo in July. **This is not real churn or real new business** —
    it's the same contract continuing under a new legal entity. Any answer that calls this
    "churn" or "expansion" without flagging the transfer is wrong.
  - `fct_mrr_bridge_monthly`: a naive bridge (built only from line-item deltas, without
    joining `fct_contract_events`) will show this as churned MRR for C003 and new MRR for
    C004 in July. Cross-referencing `fct_contract_events` is required to correctly explain
    it as a contract transfer, not real churn/expansion. This is intentional — it's the
    multi-step investigation case.

## Event 3 — Delayed invoice (Brightline Inc, September 2025)

- **subscription_id**: `S002`, **customer**: `C002` Brightline Inc
- September 2025 invoice was processed late; revenue was recognized in October instead of
  September. Contracted MRR for S002 never changes ($450/mo all year).
- `raw_contract_events.event_id = E003`
- **Expected mart effect**:
  - `fct_mrr_monthly`: flat at $450/mo for Brightline every month, including September and
    October — contracted MRR is unaffected by invoice timing.
  - `fct_revenue_recognized_monthly`: Brightline's recognized revenue is **$0 in
    September** (dipped from the usual $450) and **$900 in October** (spiked — September's
    delayed $450 plus October's normal $450).
  - A question like "why did recognized revenue dip in September" requires checking
    `fct_mrr_monthly` first (flat, rules out a real subscription/usage problem), then
    `fct_revenue_recognized_monthly` (shows the dip), then `fct_contract_events` (explains
    why) — a genuine 3-model investigation.

## Supporting events (not headline cases, but feed the bridge/logo marts)

- **E004 — New logo, Vandelay Industries (`C007`, `S006`)**: Starter plan, $420/mo,
  effective **2025-02-01**. First line item is Feb 2025; no Jan row exists for this
  subscription. Logo count should rise by 1 in February; bridge shows +$420 new MRR.
- **E005 — New logo, Pied Piper (`C011`, `S010`)**: Starter plan, $400/mo, effective
  **2025-05-01**. Logo count rises by 1 in May; bridge shows +$400 new MRR.
- **E006 — Cancellation, Dunder Mifflin (`C012`, `S011`)**: Starter plan, $400/mo,
  canceled effective **2025-08-31**. Last line item is Aug 2025; no Sep row. Logo count
  drops by 1 in September; bridge shows -$400 churned MRR in September. This is **real**
  churn — contrast against Event 2, which looks like churn but isn't.

## Reference: full customer/subscription/plan map

| Customer | Segment | Subscription | Plan history |
|---|---|---|---|
| C001 Acme Co | MidMarket | S001 | Growth $800 (Jan–Mar) → Enterprise $2,400 (Apr–Dec) |
| C002 Brightline Inc | SMB | S002 | Starter $450 flat, Jan–Dec |
| C003 Initech LLC | MidMarket | S003 | Growth $900 flat, Jan–Jun (transferred to C004 in Jul) |
| C004 Globex Corp | Enterprise | S003 (inherited) | Growth $900 flat, Jul–Dec |
| C005 Northwind Traders | SMB | S004 | Starter $400 flat, Jan–Dec |
| C006 Hooli | Enterprise | S005 | Enterprise $3,200 flat, Jan–Dec |
| C007 Vandelay Industries | SMB | S006 | Starter $420 flat, Feb–Dec (new logo) |
| C008 Soylent Corp | MidMarket | S007 | Growth $850 flat, Jan–Dec |
| C009 Stark Industries | Enterprise | S008 | Enterprise $2,600 flat, Jan–Dec |
| C010 Wayne Enterprises | Enterprise | S009 | Enterprise $2,800 flat, Jan–Dec |
| C011 Pied Piper | SMB | S010 | Starter $400 flat, May–Dec (new logo) |
| C012 Dunder Mifflin | SMB | S011 | Starter $400 flat, Jan–Aug (canceled, real churn) |
