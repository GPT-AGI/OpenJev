"""System One primitives: Choice, Score, Noul.

These models mirror the request / response shape of TypeSafe's ``POST /v1/systemone``
endpoint so that the official SDKs work against OpenJev by changing only the base URL.

OpenJev reproduces the *interface pattern*, not TypeSafe's undisclosed model or training.
"""

from __future__ import annotations

import math
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, model_validator

# --------------------------------------------------------------------------------------
# Questions (request side)
# --------------------------------------------------------------------------------------


class Choice(BaseModel):
    """Pick exactly one option from a runtime-defined set (2..255 options)."""

    type: Literal["choice"] = "choice"
    instructions: str
    options: list[str] | None = None
    criteria: dict[str, str] | None = None

    @model_validator(mode="after")
    def _check_options(self) -> Choice:
        keys = self.option_keys()
        if len(keys) < 2:
            raise ValueError("Choice needs at least 2 options (use `options` or `criteria`).")
        if len(keys) > 255:
            raise ValueError("Choice supports at most 255 options.")
        return self

    def option_keys(self) -> list[str]:
        if self.criteria:
            return list(self.criteria.keys())
        return list(self.options or [])


class Score(BaseModel):
    """Grade the state on an ordered legend (2..10 levels). Returns a probability-weighted score."""

    type: Literal["score"] = "score"
    instructions: str
    legend: dict[str, str]  # {"0": "none", "1": "low", "2": "high"}

    @model_validator(mode="after")
    def _check_legend(self) -> Score:
        if not (2 <= len(self.legend) <= 10):
            raise ValueError("Score legend needs between 2 and 10 levels.")
        for k in self.legend:
            int(k)  # raises if not numeric
        return self

    def levels(self) -> list[int]:
        return sorted(int(k) for k in self.legend)


class Noul(BaseModel):
    """A yes/no judgement. Returns P(true) in [0, 1]."""

    type: Literal["noul"] = "noul"
    instructions: str


Question = Union[Choice, Score, Noul]


class SystemOneRequest(BaseModel):
    """Body of ``POST /v1/systemone``."""

    state: Any
    questions: dict[str, Question]
    model: str = "openjev-latest"


# --------------------------------------------------------------------------------------
# Answers (response side)
# --------------------------------------------------------------------------------------


class ChoiceAnswer(BaseModel):
    type: Literal["choice"] = "choice"
    choice: str
    probabilities: dict[str, float]
    confidence: float


class ScoreAnswer(BaseModel):
    type: Literal["score"] = "score"
    score: float
    legend: dict[str, str]
    probabilities: dict[str, float]
    confidence: float


class NoulAnswer(BaseModel):
    type: Literal["noul"] = "noul"
    noul: float


Answer = Union[ChoiceAnswer, ScoreAnswer, NoulAnswer]


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class SystemOneResponse(BaseModel):
    model: str
    answers: dict[str, Answer]
    usage: Usage = Field(default_factory=Usage)
    latency_ms: float | None = None


# --------------------------------------------------------------------------------------
# Helpers shared by every backend
# --------------------------------------------------------------------------------------


def softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    if temperature <= 0:
        raise ValueError("temperature must be > 0")
    scaled = [x / temperature for x in logits]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def confidence_from_probs(probs: list[float]) -> float:
    """Confidence in [0, 1] as 1 - normalized entropy.

    TypeSafe does not publish its confidence formula. This is an interpretable
    approximation: 1.0 when all mass is on one option, 0.0 when uniform.
    """
    n = len(probs)
    if n <= 1:
        return 1.0
    ent = -sum(p * math.log(p) for p in probs if p > 0)
    return max(0.0, min(1.0, 1.0 - ent / math.log(n)))


def build_choice_answer(
    question: Choice, option_logits: list[float], temperature: float = 1.0
) -> ChoiceAnswer:
    keys = question.option_keys()
    probs = softmax(option_logits, temperature)
    dist = {k: round(p, 4) for k, p in zip(keys, probs)}
    best = keys[max(range(len(keys)), key=lambda i: probs[i])]
    return ChoiceAnswer(choice=best, probabilities=dist, confidence=round(confidence_from_probs(probs), 4))


def build_score_answer(question: Score, level_logits: list[float], temperature: float = 1.0) -> ScoreAnswer:
    levels = question.levels()
    probs = softmax(level_logits, temperature)
    expectation = sum(l * p for l, p in zip(levels, probs))
    dist = {str(l): round(p, 4) for l, p in zip(levels, probs)}
    return ScoreAnswer(
        score=round(expectation, 4),
        legend=question.legend,
        probabilities=dist,
        confidence=round(confidence_from_probs(probs), 4),
    )


def build_noul_answer(yes_logit: float, no_logit: float, temperature: float = 1.0) -> NoulAnswer:
    p_yes, _ = softmax([yes_logit, no_logit], temperature)
    return NoulAnswer(noul=round(p_yes, 4))
