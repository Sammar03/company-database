"""Retrieval + Groq generation with a strict grounding prompt and citations."""
from __future__ import annotations

import json
import time

from groq import Groq, RateLimitError

from .config import get_settings
from .embeddings import embed_query
from .models import ChatTurn, Source
from .vectorstore import Retrieved, query

# Minimum cosine similarity for a chunk to count as relevant context.
RELEVANCE_THRESHOLD = 0.30

# How many candidates to pull from the vector store before reranking down to top_k.
RERANK_CANDIDATES = 15

# Auto-retry a rate-limited generation only if the wait is this short (per-minute
# limits). Longer waits (daily limits) are surfaced to the user instead of blocking.
MAX_AUTORETRY_WAIT_S = 10


class RateLimited(Exception):
    """Groq rate limit we couldn't auto-clear; carries seconds until reset (if known)."""

    def __init__(self, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__("rate limited")


def _retry_after_seconds(err: RateLimitError) -> float | None:
    try:
        ra = err.response.headers.get("retry-after")
        return float(ra) if ra is not None else None
    except Exception:  # noqa: BLE001 — best-effort header parse
        return None

SYSTEM_PROMPT = (
    "You are a company knowledge assistant. Answer the user's question using ONLY the "
    "numbered context blocks below, which are drawn from the company's documents. Each "
    "block starts with a reference number like [1] or [2].\n\n"
    "Rules:\n"
    "- Use only facts present in the context. Do not use outside knowledge.\n"
    "- Cite every claim with the reference number(s) of the block(s) it came from, e.g. "
    "[1] or [2]. Place the number right after the claim.\n"
    "- Reuse the same number whenever you refer to the same block again.\n"
    "- Only use reference numbers that appear in the context. Never invent a number.\n"
    "- If the answer is not in the context, reply exactly: "
    '"I couldn\'t find that in the documents."\n'
    "- Be concise. If the context only partially answers, answer what you can and note "
    "what is missing."
)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def _select_by_ids(
    ids: list[object], candidates: list[Retrieved], top_k: int
) -> list[Retrieved]:
    """Map 1-based ids from the reranker back to candidates: dedupe, range-check, cap."""
    picked: list[Retrieved] = []
    seen: set[int] = set()
    for i in ids:
        if isinstance(i, int) and 1 <= i <= len(candidates) and i not in seen:
            picked.append(candidates[i - 1])
            seen.add(i)
            if len(picked) >= top_k:
                break
    return picked


def _rerank(message: str, candidates: list[Retrieved], top_k: int) -> list[Retrieved]:
    """Ask Groq to pick the most relevant candidates. Best-effort: on any failure,
    fall back to the vector-similarity order (candidates[:top_k])."""
    if len(candidates) <= top_k:
        return candidates

    settings = get_settings()
    listing = "\n\n".join(
        f"[{i}] {c.text[:500]}" for i, c in enumerate(candidates, start=1)
    )
    prompt = (
        "You are ranking document snippets by how well they help answer a question.\n"
        f"Question: {message}\n\n"
        f"Snippets:\n{listing}\n\n"
        f'Return JSON {{"relevant": [ids]}} listing up to {top_k} snippet ids, most '
        "relevant first. Only include ids that genuinely help answer the question."
    )
    try:
        completion = _get_client().chat.completions.create(
            model=settings.gen_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        ids = json.loads(completion.choices[0].message.content or "{}").get("relevant", [])
        picked = _select_by_ids(ids, candidates, top_k)
        return picked or candidates[:top_k]
    except Exception:  # noqa: BLE001 — reranker is best-effort; never block answering
        return candidates[:top_k]


def _generate(messages: list[dict[str, str]], model: str) -> str:
    """Call Groq once; on a short per-minute rate limit, wait and retry once.
    On a persistent or long limit, raise RateLimited with the seconds to wait."""
    client = _get_client()
    kwargs = dict(model=model, messages=messages, temperature=0.2, max_tokens=1024)
    try:
        return client.chat.completions.create(**kwargs).choices[0].message.content or ""
    except RateLimitError as err:
        wait = _retry_after_seconds(err)
        if wait is not None and wait <= MAX_AUTORETRY_WAIT_S:
            time.sleep(wait + 0.5)
            try:
                return client.chat.completions.create(**kwargs).choices[0].message.content or ""
            except RateLimitError as err2:
                raise RateLimited(_retry_after_seconds(err2)) from err2
        raise RateLimited(wait) from err


def _build_context_block(chunks: list[Retrieved]) -> str:
    """Number each block [1], [2], … so the model can cite by number."""
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(f"[{i}] {c.filename} (p.{c.page})\n{c.text}")
    return "\n\n---\n\n".join(parts)


def answer_question(
    message: str, history: list[ChatTurn], top_k: int
) -> tuple[str, list[Source], bool]:
    query_embedding = embed_query(message)
    # Pull a wider candidate set, then let Groq rerank down to the best top_k.
    retrieved = query(query_embedding, max(top_k * 3, RERANK_CANDIDATES))
    candidates = [r for r in retrieved if r.score >= RELEVANCE_THRESHOLD]

    if not candidates:
        return ("I couldn't find that in the documents.", [], False)

    relevant = _rerank(message, candidates, top_k)

    settings = get_settings()
    context_block = _build_context_block(relevant)

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Recent conversation turns, trimmed to stay within limits.
    for turn in history[-settings.max_history_turns :]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append(
        {
            "role": "user",
            "content": f"Context:\n{context_block}\n\nQuestion: {message}",
        }
    )

    answer = _generate(messages, settings.gen_model)

    grounded = "couldn't find that in the documents" not in answer.lower()
    # Don't attach citations to a refusal — the answer isn't actually drawn from them.
    sources = (
        [
            Source(
                id=i,
                filename=r.filename,
                page=r.page,
                snippet=(r.text[:600] + ("…" if len(r.text) > 600 else "")),
                score=r.score,
            )
            for i, r in enumerate(relevant, start=1)
        ]
        if grounded
        else []
    )
    return (answer, sources, grounded)
