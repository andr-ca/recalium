"""Sensitivity gate — classifies content before any external provider call.

TWO-PASS ARCHITECTURE:
  Pass 1: Keyword heuristics (sync, <1ms) — fast path for obvious personal/relationship content
  Pass 2: CrossEncoder NLI (CPU-bound, ~50-200ms) — handles novel patterns

SECURITY CONTRACT (PIPE-03, PRIV-04, PRIV-05):
  - Gate MUST run before any external API call
  - personal_profile → blocked=True
  - relationship → blocked=True
  - unclassified → blocked=True (unknown content is not allowed by default)
  - general → blocked=False (explicitly safe to send to external provider)
  - Gate decision MUST be recorded in audit trail (caller's responsibility)

USAGE:
  gate = SensitivityGate()
  decision = gate.classify(text)  # sync, uses heuristics; safe for quick check
  # or
  decision = await gate.classify_async(text)  # wraps NLI in asyncio.to_thread()
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Keyword lists ─────────────────────────────────────────────────────────────

_PERSONAL_PROFILE_KEYWORDS = frozenset([
    "my name is", "i was born", "birthday", "born on", "date of birth",
    "home address", "i live at", "my address", "phone number", "my phone",
    "social security", "passport number", "driver's license",
    "my age is", "years old", "my email is",
])

_RELATIONSHIP_KEYWORDS = frozenset([
    "my wife", "my husband", "my partner", "my girlfriend", "my boyfriend",
    "my kids", "my children", "my son", "my daughter", "my mom", "my dad",
    "my parents", "my sibling", "my brother", "my sister",
    "my best friend", "my friend", "my family",
])

# ── CrossEncoder NLI config ───────────────────────────────────────────────────

_NLI_MODEL_NAME = "cross-encoder/nli-MiniLM2-L6-H768"
_NLI_LABELS = [
    "personal profile information",  # index 0 → personal_profile
    "relationship information",       # index 1 → relationship
    "general topic",                  # index 2 → general
]
_NLI_CONFIDENCE_THRESHOLD = 0.6
_NLI_ENTAILMENT_COLUMN = 2  # NLI score matrix column: 0=contradiction, 1=neutral, 2=entailment

_gate_model = None  # CrossEncoder, loaded lazily


def _get_gate_model():
    """Load CrossEncoder model on first use.

    NOT thread-safe for concurrent first-loads (acceptable: personal-scale worker
    processes one job at a time via Semaphore(1)).
    """
    global _gate_model
    if _gate_model is None:
        try:
            from sentence_transformers import CrossEncoder  # noqa: PLC0415
            _gate_model = CrossEncoder(_NLI_MODEL_NAME)
            logger.info("Loaded sensitivity gate model: %s", _NLI_MODEL_NAME)
        except Exception as e:
            logger.error("Failed to load sensitivity gate model: %s", e)
            raise
    return _gate_model


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class SensitivityDecision:
    """Result of sensitivity gate classification.

    category: "personal_profile" | "relationship" | "unclassified" | "general"
    confidence: float in [0, 1] — how confident the classifier is
    blocked: True if content must NOT be sent to external provider
    method: "heuristic" | "nli" — which pass made the decision
    """
    category: str
    confidence: float
    blocked: bool
    method: str = "heuristic"

    @property
    def is_allowed(self) -> bool:
        """True if content is safe to send to external provider."""
        return not self.blocked


# ── Gate implementation ───────────────────────────────────────────────────────

class SensitivityGate:
    """Content sensitivity classifier.

    classify() is synchronous and uses keyword heuristics only (fast path).
    For full two-pass classification including NLI, use classify_async().
    """

    def _keyword_check(self, text: str) -> SensitivityDecision | None:
        """Pass 1: fast keyword heuristics. Returns decision or None if inconclusive."""
        text_lower = text.lower()

        for keyword in _PERSONAL_PROFILE_KEYWORDS:
            if keyword in text_lower:
                return SensitivityDecision(
                    category="personal_profile",
                    confidence=1.0,
                    blocked=True,
                    method="heuristic",
                )

        for keyword in _RELATIONSHIP_KEYWORDS:
            if keyword in text_lower:
                return SensitivityDecision(
                    category="relationship",
                    confidence=1.0,
                    blocked=True,
                    method="heuristic",
                )

        return None  # inconclusive — proceed to NLI

    def _nli_classify(self, text: str) -> SensitivityDecision:
        """Pass 2: CrossEncoder NLI classification. Runs synchronously (call from to_thread)."""
        model = _get_gate_model()
        pairs = [(text, label) for label in _NLI_LABELS]
        # scores shape: (num_pairs, 3) — columns: contradiction, neutral, entailment
        scores = model.predict(pairs)
        entailment_scores = scores[:, _NLI_ENTAILMENT_COLUMN]
        best_idx = int(entailment_scores.argmax())
        confidence = float(entailment_scores[best_idx])

        label_to_category = {
            0: "personal_profile",
            1: "relationship",
            2: "general",
        }

        if confidence < _NLI_CONFIDENCE_THRESHOLD:
            category = "unclassified"
        else:
            category = label_to_category[best_idx]

        blocked = category in ("personal_profile", "relationship", "unclassified")

        return SensitivityDecision(
            category=category,
            confidence=confidence,
            blocked=blocked,
            method="nli",
        )

    def classify(self, text: str) -> SensitivityDecision:
        """Classify text sensitivity synchronously.

        Uses keyword heuristics only (fast path). For full NLI pass, use classify_async().
        This method is safe to call from sync context; does NOT load the NLI model.

        Returns SensitivityDecision with category, confidence, blocked, method.
        If heuristics are inconclusive, returns unclassified (blocked=True) by default.
        """
        # Pass 1: keyword heuristics
        heuristic_result = self._keyword_check(text)
        if heuristic_result is not None:
            return heuristic_result

        # If heuristics are inconclusive, return unclassified (blocked by default).
        # Full NLI classification requires classify_async().
        return SensitivityDecision(
            category="unclassified",
            confidence=0.0,
            blocked=True,
            method="heuristic",
        )

    async def classify_async(self, text: str) -> SensitivityDecision:
        """Classify text sensitivity with full NLI pass via asyncio.to_thread().

        Use from worker loop — avoids blocking the event loop during model inference.
        Keyword heuristics still run first; NLI only runs if heuristics are inconclusive.
        """
        # Pass 1: keyword heuristics (sync, instant)
        heuristic_result = self._keyword_check(text)
        if heuristic_result is not None:
            return heuristic_result

        # Pass 2: NLI model inference in thread pool (CPU-bound — must not block event loop)
        try:
            return await asyncio.to_thread(self._nli_classify, text)
        except Exception as e:
            logger.error(
                "NLI classification failed: %s — defaulting to unclassified (blocked)", e
            )
            return SensitivityDecision(
                category="unclassified",
                confidence=0.0,
                blocked=True,
                method="heuristic",
            )
