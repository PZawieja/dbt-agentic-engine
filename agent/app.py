"""Minimal Streamlit demo for the agent, per docs/spec.md ("Interface" section).

Local-only by design: this reads ANTHROPIC_API_KEY from .env (gitignored) and
is never deployed anywhere a third party could spend that key's budget -- see
docs/decisions.md. The trace panel, not the chat UI, is the point: it's the
one piece of this app that isn't already standard chatbot UX.
"""

from pathlib import Path

import streamlit as st
import yaml

import agent_loop

EVAL_QUESTIONS_PATH = Path(__file__).parent.parent / "eval" / "questions.yml"

TIER_LABELS = {
    "lookup": "Lookup",
    "investigation": "Investigation",
    "unanswerable": "Unanswerable",
}


@st.cache_data
def load_eval_questions() -> list[dict]:
    with open(EVAL_QUESTIONS_PATH) as f:
        return yaml.safe_load(f)["questions"]


def ask(question: str, question_id: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.spinner("Agent is investigating (up to 6 tool calls)..."):
        result = agent_loop.run_question(question, question_id=question_id)
    st.session_state.messages.append({"role": "assistant", "content": result["final_answer"], "result": result})


st.set_page_config(page_title="dbt Agentic Engine", page_icon=":bar_chart:", layout="centered")

if "messages" not in st.session_state:
    st.session_state.messages = []

eval_questions = load_eval_questions()

with st.sidebar:
    st.header("Try a question")
    st.caption("Pick an example below, or type your own in the chat box.")
    for tier in ("lookup", "investigation", "unanswerable"):
        tier_questions = [q for q in eval_questions if q["tier"] == tier]
        with st.expander(TIER_LABELS[tier], expanded=False):
            for q in tier_questions:
                if st.button(q["question"].strip(), key=f"preset-{q['id']}", use_container_width=True):
                    ask(q["question"].strip(), q["id"])

    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Instructions")
    st.caption(
        "Ask a question about subscriptions, MRR, invoices, or contract events in "
        "this dbt project. The agent chains tool calls — list_models, "
        "get_model_columns, run_query, get_test_results — capped at 6 calls per "
        "question, and every call is logged as a structured trace under its answer. "
        "Questions outside this project's data (sales pipeline, support tickets, "
        "account ownership) should be declined rather than guessed."
    )

st.title("dbt Agentic Engine")
st.caption(
    "Agentic tool-use over a dbt subscription-revenue project — the model chains "
    "multiple tool calls to investigate a question, not just fill one query template."
)
st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        result = msg.get("result")
        if result is None:
            continue

        if result["hit_cap"]:
            st.warning("Hit the tool-call budget before finishing — answer above is partial.")

        m1, m2, m3 = st.columns(3)
        m1.metric("Tool calls", result["tool_calls_made"])
        m2.metric("Input tokens", result["total_usage"]["input_tokens"])
        m3.metric("Output tokens", result["total_usage"]["output_tokens"])

        with st.expander(f"Execution trace · {len(result['trace'])} step(s)"):
            for record in result["trace"]:
                status = "error" if record["error"] else "ok"
                with st.container(border=True):
                    st.markdown(
                        f"**Step {record['step']} — `{record['tool_name']}`**"
                        f"&nbsp;&nbsp;·&nbsp;&nbsp;{status}"
                        f"&nbsp;&nbsp;·&nbsp;&nbsp;{record['latency_ms']} ms"
                    )
                    st.markdown("**Input**")
                    st.json(record["input"])
                    if record["error"]:
                        st.markdown("**Error**")
                        st.error(record["error"])
                    else:
                        st.markdown("**Output**")
                        st.json(record["output"])

        st.caption(f"Full trace also appended to traces/trace_log.jsonl (run_id: {result['run_id']})")

custom_question = st.chat_input("Ask about subscriptions, MRR, invoices, or contract events...")
if custom_question:
    ask(custom_question, "ui-adhoc")
    st.rerun()
