import math

import pytest

from openjev.backends import get_backend
from openjev.core.primitives import (
    Choice,
    Noul,
    Score,
    SystemOneRequest,
    confidence_from_probs,
    softmax,
)


def test_softmax_sums_to_one():
    p = softmax([1.0, 2.0, 3.0])
    assert math.isclose(sum(p), 1.0, rel_tol=1e-9)
    assert p[2] > p[1] > p[0]


def test_confidence_bounds():
    assert confidence_from_probs([1.0, 0.0, 0.0]) == 1.0
    assert confidence_from_probs([1 / 3] * 3) == pytest.approx(0.0, abs=1e-9)


def test_choice_validation():
    with pytest.raises(ValueError):
        Choice(instructions="x", options=["only-one"])
    c = Choice(instructions="x", criteria={"a": "desc a", "b": "desc b"})
    assert c.option_keys() == ["a", "b"]


def test_score_validation():
    with pytest.raises(ValueError):
        Score(instructions="x", legend={"0": "only"})
    s = Score(instructions="x", legend={"2": "high", "0": "none", "1": "low"})
    assert s.levels() == [0, 1, 2]
    # official request form: ordered list of level descriptions
    s2 = Score(instructions="x", criteria=["calm", "annoyed", "furious"])
    assert s2.legend == {"0": "calm", "1": "annoyed", "2": "furious"}
    assert s2.levels() == [0, 1, 2]


def test_mock_backend_end_to_end():
    backend = get_backend("mock")
    req = SystemOneRequest(
        state={"ticket": "Stripe integration failed for 3 days, payments down"},
        questions={
            "dept": Choice(instructions="Which department?", options=["billing", "technical", "sales"]),
            "urgent": Noul(instructions="Is this urgent?"),
            "frustration": Score(
                instructions="Customer frustration?", legend={"0": "calm", "1": "annoyed", "2": "furious"}
            ),
        },
    )
    resp = backend.decide(req)
    assert set(resp.answers) == {"dept", "urgent", "frustration"}
    dept = resp.answers["dept"]
    assert dept.choice in {"billing", "technical", "sales"}
    assert math.isclose(sum(dept.probabilities.values()), 1.0, abs_tol=1e-3)
    assert 0.0 <= resp.answers["urgent"].noul <= 1.0
    assert 0.0 <= resp.answers["frustration"].score <= 2.0
    assert resp.usage.input_tokens > 0
    # response must be JSON serialisable in the /v1/systemone shape
    body = resp.model_dump()
    assert body["answers"]["dept"]["type"] == "choice"
    assert body["answers"]["urgent"]["type"] == "noul"
    assert body["answers"]["frustration"]["type"] == "score"
