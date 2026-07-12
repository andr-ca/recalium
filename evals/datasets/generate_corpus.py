"""Deterministic, diverse synthetic corpus generator (GPT5.6 #20).

The committed golden set is four hand-tuned conversations, which makes headline
metrics non-diagnostic. This produces a configurable-size, topically diverse corpus
where every conversation carries a unique retrieval token, so a scale run can measure
retrieval precision/latency at volume against an objective ground truth — not a tiny
tuned fixture.

Pure and deterministic (seeded): the same (n, seed) always yields the same corpus, so
scale results are reproducible. This is synthetic data — it complements, and does not
replace, evaluation on real vendor exports.
"""
from __future__ import annotations

import random
from typing import Any

# (topic, subtopics) — breadth so retrieval is not trivially separable.
_TOPICS: list[tuple[str, list[str]]] = [
    ("python", ["asyncio", "dataclasses", "generators", "typing", "packaging"]),
    ("kubernetes", ["ingress", "statefulsets", "rbac", "autoscaling", "operators"]),
    ("postgres", ["indexes", "partitioning", "replication", "vacuum", "ctes"]),
    ("security", ["oauth", "csrf", "sandboxing", "secrets", "threat modeling"]),
    ("machine-learning", ["embeddings", "fine-tuning", "quantization", "eval harnesses"]),
    ("frontend", ["hydration", "bundling", "accessibility", "state management"]),
    ("networking", ["tls", "grpc", "load balancing", "dns", "quic"]),
    ("data-eng", ["batch jobs", "streaming", "schemas", "backfills", "lineage"]),
    ("observability", ["tracing", "metrics", "log sampling", "slos"]),
    ("rust", ["ownership", "async runtimes", "traits", "ffi"]),
    ("databases", ["isolation levels", "sharding", "wal", "connection pools"]),
    ("devops", ["ci pipelines", "blue-green", "rollbacks", "infra as code"]),
    ("mobile", ["offline sync", "push", "battery", "deep links"]),
    ("cryptography", ["kdf", "aead", "key rotation", "signatures"]),
    ("search", ["bm25", "reranking", "faceting", "typo tolerance"]),
    ("llmops", ["prompt caching", "routing", "guardrails", "cost tracking"]),
    ("storage", ["object stores", "erasure coding", "tiering", "compaction"]),
    ("scheduling", ["cron", "backpressure", "priority queues", "fairness"]),
    ("payments", ["idempotency keys", "reconciliation", "3ds", "chargebacks"]),
    ("graphics", ["shaders", "culling", "color spaces", "gpu buffers"]),
]

_ENTITIES = [
    "Aurora", "Basalt", "Cinder", "Dahlia", "Ember", "Frost", "Garnet", "Hollow",
    "Indigo", "Juniper", "Krypton", "Lumen", "Marble", "Nimbus", "Onyx", "Pyrite",
    "Quartz", "Rune", "Sable", "Talon", "Umbra", "Verdant", "Willow", "Xenon",
]


def _unique_token(i: int) -> str:
    """A per-conversation nonce word that appears nowhere else in the corpus."""
    return f"zephyrium{i:06d}"


def generate_corpus(n: int, seed: int = 0) -> dict[str, Any]:
    """Generate ``n`` diverse conversations with per-item retrieval ground truth.

    Returns::

        {
          "size": n, "seed": seed,
          "conversations": [
            {"id", "topic", "text", "query", "token"}, ...
          ],
        }

    ``query`` is the conversation's unique token — a keyword search for it should
    return that conversation and no other, giving an objective precision signal.
    """
    if n < 0:
        raise ValueError("corpus size must be non-negative")
    rng = random.Random(seed)
    conversations: list[dict[str, Any]] = []
    for i in range(n):
        topic, subtopics = _TOPICS[i % len(_TOPICS)]
        sub = rng.choice(subtopics)
        entity = rng.choice(_ENTITIES)
        token = _unique_token(i)
        turns = rng.randint(1, 3)
        lines = [
            f"User: How should I approach {sub} in {topic} for project {entity}?",
            f"Assistant: For {topic}, {sub} works best when you account for {entity}'s "
            f"constraints. Note the {token} setting is required before rollout.",
        ]
        for t in range(turns - 1):
            lines.append(f"User: And what about {rng.choice(subtopics)}?")
            lines.append(
                f"Assistant: Combine it with {sub}; keep the {token} setting consistent."
            )
        conversations.append(
            {
                "id": f"gen-{i:06d}",
                "topic": topic,
                "text": "\n".join(lines),
                "query": token,
                "token": token,
            }
        )
    return {"size": n, "seed": seed, "conversations": conversations}
