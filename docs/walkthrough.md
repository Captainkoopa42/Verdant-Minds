# V5 execution walkthrough

This walkthrough follows the current source tree while keeping the engine, artifacts, and Workbench control plane distinct.

## 1. Prepare the source tree

Follow [../INSTALL.md](../INSTALL.md). V5 is run from the repository root rather than installed as one Python distribution.

```bash
source .venv/bin/activate
export PYTHONPATH=.:workbench/backend
python run_verdant_workbench.py --check
```

The diagnostic creates or opens a Workbench home, recovers stale run metadata, discovers providers/plugins, computes build identity, and verifies indexed artifacts. Use a disposable `--home` during audits.

## 2. Create a kernel and submit evidence

```python
import hashlib

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel

text = "care supports trust"
kernel = VerdantKernel(seed=42)
command = ExperienceCommand(
    event_key="walkthrough-0001",
    source_ref="walkthrough:text",
    modality="text",
    payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
    feature_vector=(1.0, 0.0, 0.0, 0.0),
    concept_labels=("care", "trust"),
    confidence=1.0,
    semantic_evidence_kind=EvidenceKind.TESTIMONY,
    semantic_evidence_details={"source": "walkthrough"},
)
result = VerdantDevelopmentPipeline().advance(kernel, command)
print(result.semantic_firewall_held)
print(kernel.metrics())
```

The event key makes replay detectable. Reusing the same key with identical content is idempotent; conflicting reuse is rejected.

## 3. What one developmental cycle does

The pipeline stages a copy of the current kernel, then:

1. records exact observation/translation evidence and any explicitly supported semantic proposals;
2. computes a pure ECWF resonance report scoped to eligible concepts;
3. commits bounded attention candidates from that report;
4. builds workspace candidates from current evidence, resonance, learned local recall, available P structures, and contradictions;
5. admits a bounded foreground according to resource and persistence policies;
6. updates nonsemantic local plasticity from workspace co-presence;
7. observes potential P structures;
8. verifies that downstream stages did not create semantic state;
9. replaces the caller's kernel only if the entire staged cycle succeeds.

This is transactional behavior at the in-memory state level: a downstream failure does not leave a half-committed experience.

## 4. Save and restore canonical state

```python
from pathlib import Path
from verdant_kernel import load_checkpoint, save_checkpoint

path = Path("walkthrough.vdk")
digest = save_checkpoint(path, kernel.state)
restored_state = load_checkpoint(path)
restored = VerdantKernel.from_state(restored_state)
assert restored.fingerprint() == kernel.fingerprint()
print(digest)
```

A `.vdk` is a deterministic stored ZIP containing canonical `state.json` and a manifest with state length and SHA-256. Loading rejects unsupported formats, hash mismatches, and length mismatches.

## 5. Import native media

```bash
python run_verdant_media.py \
  --input "path/to/photo.png" \
  --output-dir "media_run"
```

The media gateway first preserves the original bytes. If a supported translator succeeds, it creates bounded native samples, temporal records, perceptual bindings, and candidate/object reports without automatically installing a semantic object category.

Typical output includes:

- `.vmi.zip` exact-source archive;
- `.vsa.zip` translated native sample archive;
- `current_run.vdk` canonical checkpoint;
- `current_run.vrun.zip` portable run package;
- `media_import_summary.json` report.

Use `--inspect-only` for classification without ingestion or `--archive-only` to preserve without decoding. Continue/branch behavior is documented in [../USER_MEDIA_IMPORT_GUIDE.md](../USER_MEDIA_IMPORT_GUIDE.md).

## 6. Cultivate P and Q structures manually

```bash
python run_verdant_cultivation.py
```

The interactive shell supports teaching/probing, candidate inspection, P promotion/compilation, cross-symbolic interaction, Q observation/promotion/probing, refolding, save, and export. These operations use the same engine pipelines and canonical records as tests and Workbench.

The rough structural progression is:

```text
repeated bounded co-presence
→ competitive local traces
→ selective P candidate
→ independent promotion gates + Council
→ opaque P operand
→ continuous retrieval + symbolic verification
→ repeated verified P-family interaction
→ Q candidate + Council
→ opaque Q operand
→ evidence-grounded challenge and lineage-preserving refolding
```

Promotion does not assign a human semantic name or create unsupported canonical relations.

## 7. Launch Workbench

```bash
PYTHONPATH=.:workbench/backend python run_verdant_workbench.py \
  --home ./my-verdant-lab \
  --open-browser
```

Inside Workbench:

1. create a project and organism/run;
2. add explicit teaching records or compile a curriculum pack;
3. queue items, then run, pause, or step;
4. inspect current state, evidence, structures, and the recorded timeline;
5. save a checkpoint before changing experimental conditions;
6. branch from a checkpoint when testing an alternate curriculum;
7. use causal compare/ablation/restoration for structure claims;
8. package experiments and verify result artifacts against declared build identity.

The Workbench database indexes this laboratory activity. A verified `.vdk` remains the canonical organism state.

## 8. Run the current M19 benchmark

```bash
python run_ethomorphism_benchmark.py \
  --output /tmp/verdant-v5-oracle-free.json \
  --seed 1901 \
  --state-dim 16 \
  --noise-concepts 16
```

The current runner imports the oracle-free harness. Formation/promotion completes before evaluator mapping. Inspect the result for:

```json
{"schema": "verdant.ethomorphism_benchmark.v2_oracle_free"}
```

The tracked `artifacts/milestone_19_benchmark_summary.json` has the older `v1` schema and belongs to the invalid oracle-assisted formation path. Do not overwrite it casually or cite it as autonomous selection evidence; see [reproducibility.md](reproducibility.md).

## 9. Verify the current branch

Run the two-step procedure in [../TESTING.md](../TESTING.md). Plain `pytest -q` covers only the engine. The current `verify_release.py` covers 252 tests and omits six later Workbench tests; complete current validation is 258.

## 10. Interpret results narrowly

V5 provides executable evidence for its typed state, integrity, causality, bounded developmental mechanisms, structural reuse, oracle separation, and local laboratory behavior under controlled protocols.

It does not by itself establish consciousness, general intelligence, unrestricted transfer, production security, or safe autonomous embodiment.
