"""Backend interface.

A backend turns ``(state, question)`` pairs into option logits. Every backend must
implement :meth:`score_options`, which is the single primitive the rest of OpenJev
builds on. Choice / Score / Noul are all expressed as "score these labels given this
prompt", which is exactly one forward pass on any causal LM.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any

from openjev.core.primitives import (
    Answer,
    Choice,
    Noul,
    Score,
    SystemOneRequest,
    SystemOneResponse,
    Usage,
    build_choice_answer,
    build_noul_answer,
    build_score_answer,
)

NOUL_LABELS = ["yes", "no"]


def render_state(state: Any) -> str:
    if isinstance(state, str):
        return state
    return json.dumps(state, ensure_ascii=False, indent=2)


def render_prompt(state: Any, instructions: str, labels: list[str]) -> str:
    """Chat-style prompt whose next token is expected to be one of ``labels``."""
    options = "\n".join(f"- {label}" for label in labels)
    return (
        "You are a decision engine. Read the state, then answer the question by replying "
        "with exactly one of the allowed labels and nothing else.\n\n"
        f"### State\n{render_state(state)}\n\n"
        f"### Question\n{instructions}\n\n"
        f"### Allowed labels\n{options}\n\n"
        "### Answer\n"
    )


class Backend(ABC):
    name: str = "base"

    @abstractmethod
    def score_options(self, prompt: str, labels: list[str]) -> tuple[list[float], int]:
        """Return one logit per label plus the number of input tokens consumed."""

    def load(self) -> None:  # optional warm-up
        return None

    def decide(self, request: SystemOneRequest, temperature: float = 1.0) -> SystemOneResponse:
        t0 = time.perf_counter()
        answers: dict[str, Answer] = {}
        usage = Usage()
        for qid, q in request.questions.items():
            if isinstance(q, Choice):
                labels = q.option_keys()
                logits, n_in = self.score_options(
                    render_prompt(request.state, q.instructions, labels), labels
                )
                answers[qid] = build_choice_answer(q, logits, temperature)
            elif isinstance(q, Score):
                labels = [f"{lvl} ({q.legend[str(lvl)]})" for lvl in q.levels()]
                logits, n_in = self.score_options(
                    render_prompt(request.state, q.instructions, labels), labels
                )
                answers[qid] = build_score_answer(q, logits, temperature)
            elif isinstance(q, Noul):
                logits, n_in = self.score_options(
                    render_prompt(request.state, q.instructions, NOUL_LABELS), NOUL_LABELS
                )
                answers[qid] = build_noul_answer(logits[0], logits[1], temperature)
            else:  # pragma: no cover
                raise TypeError(f"Unknown question type: {type(q)!r}")
            usage.input_tokens += n_in
            usage.output_tokens += len(labels) if not isinstance(q, Noul) else 2
        latency_ms = (time.perf_counter() - t0) * 1000
        return SystemOneResponse(
            model=self.name, answers=answers, usage=usage, latency_ms=round(latency_ms, 2)
        )
