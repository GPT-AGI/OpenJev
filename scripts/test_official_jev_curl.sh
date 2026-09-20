#!/usr/bin/env bash
# Raw HTTP smoke test against the official TypeSafe / Jev API (no SDK).
# Usage:
#   export TYPESAFE_API_KEY=sk-...
#   bash scripts/test_official_jev_curl.sh
set -euo pipefail

: "${TYPESAFE_API_KEY:?TYPESAFE_API_KEY is not set. Run: export TYPESAFE_API_KEY=sk-...}"

curl -sS -w '\n\nHTTP %{http_code}  time %{time_total}s\n' \
  -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'EOF'
{
  "state": "Hi, I've been trying to connect my Stripe account for 3 days and the integration keeps failing. I'm losing sales. Please help ASAP.",
  "model": "jev-latest",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "Which team should handle this",
      "criteria": {
        "billing": "Payment or subscription issues",
        "technical": "Bugs or integration problems",
        "sales": "Pricing or account questions"
      }
    },
    "frustration": {
      "type": "score",
      "instructions": "How frustrated the customer appears",
      "criteria": ["Calm, just stating facts", "Frustrated but civil", "Very angry, strong language"]
    },
    "is_urgent": {
      "type": "noul",
      "instructions": "The message conveys urgency or time-sensitivity"
    }
  }
}
EOF
