"""Evaluate whether emergent concept names are semantically coherent with their parents."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any



DOMAIN_CLUSTERS: dict[str, set[str]] = {
    "cognitive": {
        "attention",
        "awareness",
        "belief_revision",
        "cognition",
        "consciousness",
        "inference",
        "memory",
        "perception",
        "phenomenology",
        "qualia",
        "reasoning",
        "reflection",
        "selfhood",
        "subjective_experience",
    },
    "ethical": {
        "autonomy",
        "beneficence",
        "care",
        "ethics",
        "fairness",
        "freedom",
        "harm",
        "integrity",
        "justice",
        "moral_weight",
        "responsibility",
        "trust",
        "value_conflict",
    },
    "structural": {
        "abstraction",
        "boundary",
        "cascade",
        "coherence",
        "complexity",
        "constraint",
        "emergence",
        "emergence_from_interaction",
        "network",
        "order",
        "pattern",
        "phase_transition",
        "resonance",
        "self_organization",
        "structure",
        "synthesis",
        "threshold",
    },
    "temporal": {
        "anticipation",
        "change",
        "continuity",
        "decay",
        "experience_accumulation",
        "growth",
        "novelty",
        "persistence",
        "present_moment",
        "temporal_flow",
        "time",
        "transformation",
    },
    "relational": {
        "competition",
        "connection",
        "contradiction",
        "cooperation",
        "coupling",
        "dependency",
        "feedback",
        "hierarchy",
        "influence",
        "integration",
        "interference",
        "isolation",
        "relation",
        "translation",
    },
}

RATING_TO_SCORE = {"meaningful": 1.0, "partial": 0.5, "not_meaningful": 0.0}
SCORE_TO_RATING = ((0.6, "meaningful"), (0.3, "partial"), (0.0, "not_meaningful"))
_SUFFIXES = ("tion", "sion", "ment", "ness", "ity", "ing", "ence", "ance", "ism", "al", "ed", "ly", "es", "s")
_HEX_RE = re.compile(r"^[0-9a-f]{6,8}$")
_NUMERIC_RE = re.compile(r"^\d{1,4}$")


def clean_emergent_name(name: str) -> list[str]:
    text = name[len("Emergent_") :] if name.startswith("Emergent_") else name
    parts = [part for part in text.split("_") if part]
    if parts and (_HEX_RE.fullmatch(parts[-1]) or _NUMERIC_RE.fullmatch(parts[-1])):
        parts = parts[:-1]
    merged: list[str] = []
    idx = 0
    while idx < len(parts):
        if parts[idx] == "basin" and idx + 1 < len(parts) and parts[idx + 1].isdigit():
            merged.append(f"basin_{parts[idx + 1]}")
            idx += 2
            continue
        merged.append(parts[idx])
        idx += 1
    return merged


def clean_name_for_display(name: str) -> str:
    return " ".join(clean_emergent_name(name)).strip()


def _normalize_term(term: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", term.lower()).strip("_")


def _root(term: str) -> str:
    token = _normalize_term(term)
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def _explode_parent_tokens(parents: list[str]) -> set[str]:
    tokens: set[str] = set()
    for parent in parents:
        norm = _normalize_term(parent)
        if not norm:
            continue
        tokens.add(norm)
        tokens.update(part for part in norm.split("_") if part)
    return tokens


def _token_matches_parent(component: str, parent_tokens: set[str]) -> bool:
    norm_component = _normalize_term(component)
    component_root = _root(component)
    component_cluster = lookup_domain(component)
    for parent in parent_tokens:
        parent_root = _root(parent)
        if norm_component == parent or norm_component in parent or parent in norm_component:
            return True
        if component_root and parent_root and component_root == parent_root:
            return True
        if component_root and parent_root and len(component_root) >= 4 and len(parent_root) >= 4 and (
            component_root.startswith(parent_root[:4]) or parent_root.startswith(component_root[:4])
        ):
            return True
        if component_cluster is not None and component_cluster == lookup_domain(parent):
            return True
    return False


def lookup_domain(term: str) -> str | None:
    normalized = _normalize_term(term)
    pieces = {normalized, *_normalize_term(term).split("_")}
    for domain, vocabulary in DOMAIN_CLUSTERS.items():
        if pieces & vocabulary:
            return domain
    return None


def score_local_concept(concept: dict[str, Any]) -> dict[str, Any]:
    components = clean_emergent_name(str(concept.get("name", "")))
    parents = [str(parent) for parent in concept.get("parents", [])]
    parent_tokens = _explode_parent_tokens(parents)

    if components:
        matching_components = sum(1 for component in components if _token_matches_parent(component, parent_tokens))
        naming_match = (matching_components / len(components)) * 0.4
    else:
        matching_components = 0
        naming_match = 0.0

    matched_domains = {lookup_domain(parent) for parent in parents}
    matched_domains.discard(None)
    if len(matched_domains) == 1:
        parent_relatedness = 0.3
    elif len(matched_domains) == 2:
        parent_relatedness = 0.2
    elif len(matched_domains) >= 3:
        parent_relatedness = 0.1
    else:
        parent_relatedness = 0.0

    normalized_components = {_normalize_term(component) for component in components}
    if normalized_components and normalized_components <= parent_tokens:
        synthesis_plausibility = 0.3
    elif any(_token_matches_parent(component, parent_tokens) for component in components):
        synthesis_plausibility = 0.2
    else:
        synthesis_plausibility = 0.1 if parents else 0.0

    score = max(0.0, min(1.0, naming_match + parent_relatedness + synthesis_plausibility))
    rating = next(label for threshold, label in SCORE_TO_RATING if score >= threshold)
    return {
        "name": str(concept.get("name", "")),
        "name_cleaned": clean_name_for_display(str(concept.get("name", ""))),
        "parents": parents,
        "score": round(score, 4),
        "rating": rating,
        "explanation": None,
    }


class LLMJudge:
    def __init__(self, backend: str, model: str | None = None, temperature: float = 0.0) -> None:
        self.backend = backend.lower()
        self.model = model
        self.temperature = float(temperature)

    def evaluate(self, name: str, parents: list[str]) -> tuple[str, str | None]:
        prompt = (
            "Evaluate whether this emergent concept represents a meaningful\n"
            "synthesis of its parent concepts.\n\n"
            f"Emergent concept: {clean_name_for_display(name)}\n"
            f"Parent concepts: {', '.join(parents) if parents else 'none'}\n\n"
            "Rate the semantic coherence:\n"
            '- "meaningful": The emergent concept clearly synthesizes or bridges\n'
            "  the parent concepts in a way that makes intellectual sense.\n"
            '- "partial": There is some connection but it\'s weak or unclear.\n'
            '- "not_meaningful": The combination appears random or incoherent.\n\n'
            "Respond with ONLY one word: meaningful, partial, or not_meaningful"
        )
        raw = self._call_backend(prompt).strip().lower()
        if "not_meaningful" in raw:
            return "not_meaningful", raw
        if "meaningful" in raw and "not_meaningful" not in raw:
            return "meaningful", raw
        if "partial" in raw:
            return "partial", raw
        raise ValueError(f"Could not parse LLM rating from response: {raw!r}")

    def _call_backend(self, prompt: str) -> str:
        if self.backend == "groq":
            return self._call_groq(prompt)
        if self.backend == "anthropic":
            return self._call_anthropic(prompt)
        if self.backend == "mistral":
            return self._call_mistral(prompt)
        raise ValueError(f"Unsupported LLM backend: {self.backend}")

    def _call_groq(self, prompt: str) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        payload = {
            "model": self.model or "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }
        data = _post_json(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload=payload,
        )
        return str(data["choices"][0]["message"]["content"])

    def _call_anthropic(self, prompt: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        payload = {
            "model": self.model or "claude-3-5-haiku-latest",
            "max_tokens": 16,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = _post_json(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            payload=payload,
        )
        chunks = [block.get("text", "") for block in data.get("content", []) if isinstance(block, dict)]
        return "".join(chunks)

    def _call_mistral(self, prompt: str) -> str:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is not set")
        payload = {
            "model": self.model or "mistral-small-latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 16,
        }
        data = _post_json(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload=payload,
        )
        return str(data["choices"][0]["message"]["content"])



def _post_json(url: str, *, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc


def _summarize_scores(entries: list[dict[str, Any]]) -> dict[str, Any]:
    counts = defaultdict(int)
    total_score = 0.0
    for entry in entries:
        counts[str(entry["rating"])] += 1
        total_score += float(entry["score"])
    total = len(entries)
    return {
        "meaningful_count": counts["meaningful"],
        "partial_count": counts["partial"],
        "not_meaningful_count": counts["not_meaningful"],
        "meaningful_fraction": round(counts["meaningful"] / total, 4) if total else 0.0,
        "partial_fraction": round(counts["partial"] / total, 4) if total else 0.0,
        "not_meaningful_fraction": round(counts["not_meaningful"] / total, 4) if total else 0.0,
        "mean_score": round(total_score / total, 4) if total else 0.0,
    }


def evaluate_semantics(
    concepts_payload: dict[str, Any],
    *,
    mode: str = "local",
    backend: str | None = None,
    model: str | None = None,
    sleep_seconds: float = 1.0,
) -> dict[str, Any]:
    concepts = concepts_payload.get("concepts", []) if isinstance(concepts_payload, dict) else []
    if not isinstance(concepts, list):
        raise ValueError("Concept payload must include a list under 'concepts'")

    llm_judge = LLMJudge(backend or "", model=model) if mode == "llm" else None
    per_concept: list[dict[str, Any]] = []
    basin_scores: dict[str, list[float]] = defaultdict(list)

    for idx, concept in enumerate(concepts):
        if not isinstance(concept, dict):
            continue
        if mode == "local":
            evaluated = score_local_concept(concept)
        elif mode == "llm":
            assert llm_judge is not None
            rating, raw_response = llm_judge.evaluate(str(concept.get("name", "")), [str(parent) for parent in concept.get("parents", [])])
            evaluated = {
                "name": str(concept.get("name", "")),
                "name_cleaned": clean_name_for_display(str(concept.get("name", ""))),
                "parents": [str(parent) for parent in concept.get("parents", [])],
                "score": RATING_TO_SCORE[rating],
                "rating": rating,
                "explanation": raw_response,
            }
            if idx < len(concepts) - 1 and sleep_seconds > 0:
                time.sleep(sleep_seconds)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        evaluated["access_count"] = int(concept.get("access_count", 0) or 0)
        evaluated["connection_count"] = int(concept.get("connection_count", 0) or 0)
        evaluated["creation_time"] = concept.get("creation_time")
        evaluated["basin_id"] = concept.get("basin_id")
        per_concept.append(evaluated)
        if evaluated.get("basin_id") is not None:
            basin_scores[str(evaluated["basin_id"])].append(float(evaluated["score"]))

    by_basin = {
        basin_id: {"mean_score": round(sum(scores) / len(scores), 4), "count": len(scores)}
        for basin_id, scores in sorted(basin_scores.items())
    }

    return {
        "state_path": concepts_payload.get("state_path"),
        "mode": mode,
        "llm_backend": backend if mode == "llm" else None,
        "total_evaluated": len(per_concept),
        "scores": _summarize_scores(per_concept),
        "per_concept": per_concept,
        "by_basin": by_basin,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate semantic coherence of emergent concepts")
    parser.add_argument("--concepts", required=True)
    parser.add_argument("--mode", choices=["local", "llm"], default="local")
    parser.add_argument("--backend", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--outfile", required=True)
    parser.add_argument("--sleep-seconds", type=float, default=1.0, help="Delay between LLM requests")
    args = parser.parse_args()

    concepts_payload = json.loads(Path(args.concepts).read_text(encoding="utf-8"))
    result = evaluate_semantics(
        concepts_payload,
        mode=args.mode,
        backend=args.backend,
        model=args.model,
        sleep_seconds=args.sleep_seconds,
    )

    out_path = Path(args.outfile)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"outfile": str(out_path), "scores": result["scores"]}, indent=2))


if __name__ == "__main__":
    main()
