"""CLI entry point for project 2 (llmops-eval-harness) to shell out to this
agent per question, without importing this repo's modules directly. Prints
the same result dict run_question() already returns, as one JSON object on
stdout -- the trace itself is still appended to traces/trace_log.jsonl by
run_question() exactly as it is for the Streamlit app.
"""

import argparse
import json

import agent_loop


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    parser.add_argument("--question-id", default="cli-adhoc")
    args = parser.parse_args()

    result = agent_loop.run_question(args.question, question_id=args.question_id)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
