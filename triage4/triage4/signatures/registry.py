from __future__ import annotations

from typing import Any, Callable


class SignatureRegistry:
    """Simple registry for signature extractors.

    Each extractor exposes an `extract(**context)` method returning a dict.
    The registry runs all registered extractors on the same context and
    returns a merged mapping of {name: result}.
    """

    def __init__(self) -> None:
        self.extractors: dict[str, Any] = {}

    def register(self, name: str, extractor: Any) -> None:
        self.extractors[name] = extractor

    def run_all(self, context: dict) -> dict:
        outputs: dict[str, Any] = {}
        for name, extractor in self.extractors.items():
            call: Callable[..., Any] = extractor.extract
            outputs[name] = call(**context)
        return outputs
