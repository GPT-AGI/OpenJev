# OpenJev design notes

## Positioning

The "read option logits in one forward pass" trick is now well understood and has half a dozen
open implementations. OpenJev does not try to win on that axis. It wins on **developer
experience and interoperability**:

1. A terminal you can watch decisions happen in (Claude Code style REPL, streaming bars).
2. Byte-for-byte compatible request/response with `POST /v1/systemone` so the official
   `typesafe-sdk` / `@typesafe-ai/sdk` work by changing `base_url`.
3. A side-by-side playground that makes the *speed and calibration story* visible, the same
   way TypeSafe's own launch GIF did.
4. Pluggable backends so the same UX runs on a laptop (MLX / HF), a GPU box (vLLM) or the
   real Jev API (reference mode) for honest comparison.

## Primitives

| Primitive | Input | Readout | Output |
|---|---|---|---|
| Choice | 2..255 options (or `criteria` map) | logits of each option's label token | `choice`, `probabilities`, `confidence` |
| Score | ordered legend, 2..10 levels | logits of each level label | probability-weighted `score`, `legend`, `probabilities`, `confidence` |
| Noul | question | logits of `yes` / `no` | `noul` = P(true) |

`confidence = 1 - H(p) / log(n)`. TypeSafe's formula is unpublished; ours is transparent and
monotonic in peakedness. Calibration (temperature scaling) is applied on top when a profile is
available.

## Backend contract

```python
class Backend:
    def score_options(self, prompt: str, labels: list[str]) -> tuple[list[float], int]: ...
```

That is the only thing a backend must do. `Backend.decide()` turns a `SystemOneRequest` into a
`SystemOneResponse` on top of it. Everything else (KV-cache sharing, batching, multi-token
labels) is an optimisation inside a specific backend.

### Planned optimisations

- **Shared-state prefill**: encode `state` once, fork the KV cache per question (daseinlabs
  approach). This is what makes "adding a question barely changes latency" true.
- **Multi-token labels**: sum of log-probs over the label's tokens, length-normalised
  (`mean`) or PMI-corrected, for labels that are not a single token.
- **Packed mode** (ikermoel approach): all questions in one sequence, read logits at each
  answer slot. Fastest, small interference risk; `separate` mode stays the exact baseline.
- **vLLM**: `prompt_logprobs` for packed, `allowed_token_ids` for separate.

## Phases

### Phase 0 (shipped)
Core primitives, mock + HF backends, REPL, demo GIFs, CI.

### Phase 1: API compatibility
- `openjev serve --backend hf --model ...` -> FastAPI on :8000
- `POST /v1/systemone`, `GET /v1/models`, error codes 401/422/429 aligned with docs
- Contract test that runs the official Python SDK against the server
- Shared-state prefill + multi-token labels in HF backend
- `/session save|load`, `/history` in REPL

### Phase 2: Show, don't tell
- `web/` playground: state + questions on the left; three columns on the right (OpenJev local,
  Jev via user key, generic LLM JSON mode) with probability bars, p50 latency, cost estimate
- `/compare` in the REPL producing the same table
- `openjev eval --dataset boolq|banking77 --n 500` -> accuracy, ECE, reliability diagram
- `openjev calibrate --data labelled.jsonl` -> temperature stored in a model profile

### Phase 3: Backends and agent glue
- MLX backend (Apple Silicon), vLLM backend, TypeSafe / OpenRouter reference backend
- Middlewares: tool-call guardrail (Noul), model router (Choice), RAG reranker (Score)
- `skills/openjev/SKILL.md` so Claude Code / Clawd-Code can call it as a slash command

### Phase 4: From interface to model
- Train a small decision head (Qwen3-0.6B base) with CE / Brier losses on synthetic +
  public decision data; publish weights on Hugging Face
- Docker image, one-click deploy, hosted playground

## Non-goals

- Reproducing TypeSafe's proprietary architecture, sampler or RLCD training.
- Text generation of any kind. If you need a value extracted from free text, generate
  candidates elsewhere and let OpenJev pick.
