"""Hugging Face Transformers backend.

One forward pass per (state, question). Logits are read at the last position and
only the first token of each label is compared, then softmaxed across labels so
nothing outside the option set can win.

Phase 1 will add: shared-state prefill with KV-cache reuse across questions, and
multi-token label scoring (sum of log-probs) for labels that are not single tokens.
"""

from __future__ import annotations

from openjev.backends.base import Backend


class HFBackend(Backend):
    def __init__(self, model_id: str = "Qwen/Qwen2.5-0.5B-Instruct", device: str | None = None):
        self.model_id = model_id
        self.name = f"openjev-hf/{model_id}"
        self.device = device
        self._model = None
        self._tok = None

    def load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as e:  # pragma: no cover
            raise ImportError("Install with: pip install 'openjev[hf]'") from e
        self._torch = torch
        self.device = self.device or (
            "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        )
        self._tok = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id, torch_dtype=torch.float32 if self.device == "cpu" else torch.bfloat16
        )
        self._model.to(self.device).eval()

    def _first_token_id(self, label: str) -> int:
        ids = self._tok.encode(label, add_special_tokens=False)
        return ids[0]

    def score_options(self, prompt: str, labels: list[str]) -> tuple[list[float], int]:
        self.load()
        torch = self._torch
        enc = self._tok(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self._model(**enc)
        last = out.logits[0, -1].float()
        ids = [self._first_token_id(label) for label in labels]
        logits = [float(last[i]) for i in ids]
        return logits, int(enc["input_ids"].shape[1])
