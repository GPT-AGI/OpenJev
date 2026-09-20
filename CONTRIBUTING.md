# Contributing to OpenJev

Thanks for helping build an open System One decision engine.

## Setup

```bash
uv venv --python 3.11 && source .venv/bin/activate
uv pip install -e ".[dev]" prompt_toolkit
pytest -q && ruff check src tests
```

## Where to help

Look at the [Roadmap](README.md#roadmap). Good first issues:

- Multi-token label scoring (sum of log-probs) in `backends/hf.py`
- Shared-state prefill with KV-cache reuse across questions
- `openjev serve` (FastAPI, `POST /v1/systemone`)
- MLX backend for Apple Silicon
- Web Playground (side-by-side comparison)
- Eval harness on BoolQ / Banking77 with ECE

## Rules of thumb

- Keep the request/response schema identical to the Jev docs so the official SDKs keep working.
- Every backend implements exactly one method: `score_options(prompt, labels) -> (logits, n_input_tokens)`.
- No proprietary code, weights or data. This project reproduces an interface pattern, not TypeSafe's model.
- Be honest in benchmarks: report the model, revision, hardware and sample size.

## Style

`ruff format` + `ruff check`. Type hints everywhere. Tests for anything that touches the schema.
