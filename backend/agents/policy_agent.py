# =============================================================================
# Policy Knowledge And RAG Agent
#
# This agent gives ShiftIQ a grounded policy knowledge layer. The operational
# agents already know live schedule, labor, employee, and sales data; this file
# adds retrievable written guidance such as labor targets, shift-swap rules,
# approval policy, and weather staffing policy. Manager Chat can consult this
# layer before answering policy-sensitive questions so responses are grounded in
# an explicit knowledge base instead of model memory.
#
# Main responsibilities:
# - Load Markdown policy documents from data/knowledge.
# - Split documents into small searchable chunks.
# - Rank chunks with a deterministic keyword scorer that works offline.
# - Return citations with filenames and excerpts for Manager Chat, MCP tools,
#   and future Vertex AI Search/RAG integrations.
# - Log policy retrieval calls for auditability.
#
# This is intentionally lightweight for the MVP. The same tool boundary can be
# swapped later for Vertex AI Search, Agent Platform Search, or RAG Engine while
# keeping the rest of the app unchanged.
# =============================================================================

from __future__ import annotations

import re
from pathlib import Path

from agents.persistence_agent import log_audit


KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"
TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if len(token) > 2}


def _load_documents() -> list[dict]:
    docs = []
    if not KNOWLEDGE_DIR.exists():
        return docs
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8-sig").strip()
        if not text:
            continue
        docs.append({"source": path.name, "path": str(path), "text": text})
    return docs


def _chunk_document(doc: dict) -> list[dict]:
    sections = re.split(r"\n(?=##\s+)", doc["text"])
    chunks = []
    for index, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        heading = next((line.strip("# ").strip() for line in section.splitlines() if line.startswith("#")), "Policy")
        chunks.append(
            {
                "id": f"{doc['source']}:{index + 1}",
                "source": doc["source"],
                "heading": heading,
                "text": section,
                "tokens": _tokens(section),
            }
        )
    return chunks


def _all_chunks() -> list[dict]:
    chunks = []
    for doc in _load_documents():
        chunks.extend(_chunk_document(doc))
    return chunks


def search_policy_knowledge(query: str, limit: int = 4) -> dict:
    """Search ShiftIQ policy docs and return grounded excerpts with citations."""
    query_text = str(query or "").strip()
    query_tokens = _tokens(query_text)
    chunks = _all_chunks()
    if not query_tokens:
        return {"query": query_text, "results": [], "summary": "Ask a policy question to search the knowledge base."}

    scored = []
    for chunk in chunks:
        overlap = query_tokens & chunk["tokens"]
        if not overlap:
            continue
        heading_bonus = 2 if any(token in _tokens(chunk["heading"]) for token in query_tokens) else 0
        phrase_bonus = 0
        query_lower = query_text.lower()
        chunk_lower = chunk["text"].lower()
        if "48" in query_lower and "48" in chunk_lower:
            phrase_bonus += 6
        if "approval" in query_lower and "approval" in chunk_lower:
            phrase_bonus += 3
        if "within" in query_lower and "within" in chunk_lower:
            phrase_bonus += 2
        score = len(overlap) + heading_bonus + phrase_bonus
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, chunk in scored[: max(1, min(int(limit or 4), 8))]:
        excerpt = " ".join(line.strip("#- ").strip() for line in chunk["text"].splitlines() if line.strip())
        results.append(
            {
                "id": chunk["id"],
                "source": chunk["source"],
                "heading": chunk["heading"],
                "score": score,
                "excerpt": excerpt[:700],
            }
        )

    summary = (
        f"Found {len(results)} grounded policy matches for '{query_text}'."
        if results
        else f"No policy match found for '{query_text}'."
    )
    log_audit("rag", "policy_search", "ok", {"query": query_text, "results": len(results)}, actor="Policy Knowledge Agent")
    return {"query": query_text, "results": results, "summary": summary}


def policy_knowledge_overview() -> dict:
    """Return available policy documents and chunk count."""
    docs = _load_documents()
    return {
        "document_count": len(docs),
        "chunk_count": len(_all_chunks()),
        "documents": [{"source": doc["source"], "characters": len(doc["text"])} for doc in docs],
        "retrieval_mode": "local_keyword_rag",
        "upgrade_path": "Vertex AI Search or Agent Platform RAG Engine",
    }
