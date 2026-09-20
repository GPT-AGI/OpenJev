"""Quick smoke test against the official TypeSafe / Jev API.

Usage:
    export TYPESAFE_API_KEY=sk-...
    .venv/bin/python scripts/test_official_jev.py            # SDK test (default sample)
    .venv/bin/python scripts/test_official_jev.py --raw      # also dump raw JSON response
    .venv/bin/python scripts/test_official_jev.py --state "your text here"

Reads TYPESAFE_API_KEY from the environment (never hardcode it).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from typesafe_sdk import (
    Choice,
    Noul,
    Score,
    TypeSafeAuthenticationError,
    TypeSafeClient,
    TypeSafeError,
)

DEFAULT_STATE = (
    "Hi, I've been trying to connect my Stripe account for 3 days and the "
    "integration keeps failing. I'm losing sales. Please help ASAP."
)

QUESTIONS = {
    "department": Choice(
        instructions="Which team should handle this",
        criteria={
            "billing": "Payment or subscription issues",
            "technical": "Bugs or integration problems",
            "sales": "Pricing or account questions",
        },
    ),
    "frustration": Score(
        instructions="How frustrated the customer appears",
        criteria=[
            "Calm, just stating facts",
            "Frustrated but civil",
            "Very angry, strong language",
        ],
    ),
    "is_urgent": Noul(
        instructions="The message conveys urgency or time-sensitivity",
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--state", default=DEFAULT_STATE, help="text to evaluate")
    parser.add_argument("--model", default="jev-latest", help="model alias or id (default: jev-latest)")
    parser.add_argument("--raw", action="store_true", help="print raw response JSON")
    parser.add_argument("--list-models", action="store_true", help="list available models and exit")
    args = parser.parse_args()

    if not os.environ.get("TYPESAFE_API_KEY"):
        print("ERROR: TYPESAFE_API_KEY is not set. Run:  export TYPESAFE_API_KEY=sk-...", file=sys.stderr)
        return 2

    try:
        with TypeSafeClient() as client:
            if args.list_models:
                models = client.models.list()
                print(json.dumps(models.model_dump(mode="json"), indent=2, ensure_ascii=False))
                return 0

            print(f"model    : {args.model}")
            print(f"state    : {args.state[:120]}{'...' if len(args.state) > 120 else ''}")
            print(f"questions: {list(QUESTIONS)}")
            print("-" * 60)

            t0 = time.perf_counter()
            resp = client.system_one(state=args.state, model=args.model, questions=QUESTIONS)
            dt = (time.perf_counter() - t0) * 1000

            print(f"served by: {resp.model}   latency: {dt:.0f} ms")
            if resp.usage:
                print(f"usage    : in={resp.usage.input_tokens} out={resp.usage.output_tokens}")
            print("-" * 60)

            d = resp.answers["department"]
            f = resp.answers["frustration"]
            u = resp.answers["is_urgent"]
            print(f"department  -> {d.choice!r:14} conf={d.confidence:.2f} probs={_fmt(d.probabilities)}")
            print(f"frustration -> {f.score!r:14} conf={f.confidence:.2f} probs={_fmt(f.probabilities)}")
            print(f"is_urgent   -> noul={u.noul:.3f}")

            if args.raw:
                print("-" * 60)
                print(json.dumps(resp.model_dump(mode="json"), indent=2, ensure_ascii=False))
            return 0

    except TypeSafeAuthenticationError as e:
        print(f"AUTH ERROR (check TYPESAFE_API_KEY): {e}", file=sys.stderr)
        return 1
    except TypeSafeError as e:
        print(f"API ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


def _fmt(probs) -> str:
    return "{" + ", ".join(f"{k}: {v:.2f}" for k, v in probs.items()) + "}"


if __name__ == "__main__":
    raise SystemExit(main())
