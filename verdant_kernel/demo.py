from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from .checkpoint import save_checkpoint
from .kernel import VerdantKernel
from .models import ExperienceCommand, RelationProposal


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(output_dir: Path = Path("artifacts")) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(
        seed=7741,
        state_dim=64,
        run_label="milestone-1-demo",
    )
    sentence = "Gravity pulls objects downward."
    features = tuple(float(value) for value in np.linspace(0.0, 1.0, 64))
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key="physics-0001",
            source_ref="handwritten_physics_curriculum",
            modality="text",
            payload_sha256=_sha(sentence),
            feature_vector=features,
            concept_labels=("gravity", "objects", "downward"),
            relation_proposals=(
                RelationProposal(
                    source_label="gravity",
                    target_label="objects",
                    relation_type="acts_on",
                    weight=0.7,
                    confidence=0.75,
                ),
                RelationProposal(
                    source_label="gravity",
                    target_label="downward",
                    relation_type="directional_effect",
                    weight=0.65,
                    confidence=0.7,
                ),
            ),
            metadata={
                "curriculum_stage": "controlled_demo",
                "sentence": sentence,
            },
        )
    )
    checkpoint_path = output_dir / "canonical_kernel_demo.vdk"
    checkpoint_sha256 = save_checkpoint(checkpoint_path, kernel.snapshot())
    summary = {
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "kernel_fingerprint": kernel.fingerprint(),
        "semantic_fingerprint": kernel.semantic_fingerprint(),
        "experience_result": result.__dict__,
        "metrics": kernel.metrics(),
    }
    (output_dir / "canonical_kernel_demo_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
