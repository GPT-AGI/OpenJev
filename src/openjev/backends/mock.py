"""Deterministic mock backend.

Useful for tests, demos and CI: no model download, sub-millisecond latency, and
stable outputs derived from a hash of (prompt, label). It exists so the REPL, the
server and the SDK-compat tests can run anywhere.
"""

from __future__ import annotations

import hashlib

from openjev.backends.base import Backend


class MockBackend(Backend):
    name = "openjev-mock"

    def score_options(self, prompt: str, labels: list[str]) -> tuple[list[float], int]:
        logits: list[float] = []
        for label in labels:
            h = hashlib.sha256((prompt + "\x00" + label).encode("utf-8")).digest()
            # map first 4 bytes to a logit in roughly [-3, 3]
            v = int.from_bytes(h[:4], "big") / 0xFFFFFFFF
            logits.append((v - 0.5) * 6.0)
        # crude token estimate: ~4 chars per token
        return logits, max(1, len(prompt) // 4)
