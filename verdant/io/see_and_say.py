from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_session(teaching_list_path: str | Path, query_interface: Any) -> dict[str, Any]:
    teaching_list = _load_json(teaching_list_path)
    session = dict(teaching_list.get("see_and_say_session", {}))
    cloze_ids = list(session.get("cloze_items", []))

    sentences_path = Path(teaching_list_path).resolve().parents[1] / "sentences" / "teaching_sentences_physical_world.json"
    sentences = _load_json(sentences_path)
    cloze_map: dict[str, dict[str, Any]] = {}
    for item in sentences:
        for cloze in item.get("see_and_say_variants", []):
            cloze_map[str(cloze.get("cloze_id"))] = cloze

    results = []
    pass_count = 0
    weakness: dict[str, int] = {}

    for cid in cloze_ids:
        c = cloze_map.get(cid)
        if not c:
            continue
        target = str(c.get("target_word", ""))
        masked = str(c.get("masked_sentence", ""))
        options = [str(x) for x in c.get("distractor_options", [])]

        target_text = masked.replace("___", target, 1)
        target_score = 0.0
        target_diff = query_interface.diff(masked, target_text)
        if target_diff.get("activation_delta"):
            target_score = float(sum(abs(float(x.get("delta", 0.0))) for x in target_diff["activation_delta"][:5]))

        distractor_scores = []
        for opt in options:
            if opt == target:
                continue
            cand_text = masked.replace("___", opt, 1)
            d = query_interface.diff(masked, cand_text)
            score = float(sum(abs(float(x.get("delta", 0.0))) for x in d.get("activation_delta", [])[:5]))
            distractor_scores.append({"option": opt, "score": score, "delta": d.get("activation_delta", [])[:5]})

        max_dist = max([x["score"] for x in distractor_scores], default=0.0)
        passed = target_score > max_dist
        if passed:
            pass_count += 1
        else:
            weakness[target] = weakness.get(target, 0) + 1

        results.append({
            "cloze_id": cid,
            "masked_sentence": masked,
            "target": target,
            "target_score": target_score,
            "max_distractor_score": max_dist,
            "passed": passed,
            "distractors": distractor_scores,
            "evidence": target_diff.get("activation_delta", [])[:10],
        })

    total = len(results)
    pass_rate = (pass_count / total) if total else 0.0
    out = {
        "session_id": session.get("session_id", "sas_unknown"),
        "pass_threshold": session.get("pass_threshold", 0.8),
        "total_items": total,
        "passed_items": pass_count,
        "pass_rate": pass_rate,
        "weakest_concepts": sorted(weakness.items(), key=lambda x: x[1], reverse=True)[:10],
        "results": results,
    }

    results_dir = Path("corpus/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / f"{out['session_id']}_results.json"
    results_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"See and Say Session: {out['session_id']}")
    print(f"Pass rate: {pass_count}/{total} = {pass_rate:.2%}")
    if out["weakest_concepts"]:
        print("Weakest concepts:", ", ".join([f"{c}({n})" for c, n in out["weakest_concepts"]]))
    print(f"Results written: {results_path}")
    return out
