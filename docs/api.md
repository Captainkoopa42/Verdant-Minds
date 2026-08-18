# V5 interface reference

V5 has four user-facing interface layers: root commands, Python engine packages, persistent artifact formats, and the Workbench HTTP/WebSocket API.

## Root commands

| Entry point | Interface |
| --- | --- |
| `run_verdant_workbench.py` | `--host`, `--port`, `--home`, `--open-browser`, `--check` |
| `run_verdant_media.py` | Media gateway CLI; see `python run_verdant_media.py --help` |
| `run_verdant_cultivation.py` | Interactive cultivation shell |
| `run_ethomorphism_benchmark.py` | `--output`, `--seed`, `--state-dim`, `--noise-concepts` |
| `verify_release.py` | `--with-proofs` optionally adds WB-08/WB-09 proofs |

## Canonical kernel

```python
from verdant_kernel import VerdantKernel

kernel = VerdantKernel(seed=42)
snapshot = kernel.snapshot()
fingerprint = kernel.fingerprint()
semantic_fingerprint = kernel.semantic_fingerprint()
metrics = kernel.metrics()
```

Important kernel interfaces include:

- `apply_experience(command)`;
- `ensure_concept(...)`, `propose_relation(...)`, `register_claim(...)`;
- `current_belief(...)`, `claim_history(...)`, `neighbors(...)`;
- pure `inspect_resonance(...)` plus `commit_resonance(...)`;
- report validation/commit methods for sensory, perception, workspace, plasticity, structures, interaction, hierarchy, refolding, governance, shards, and objects;
- policy-update and subsystem fingerprint methods;
- explicit P/Q availability changes for causal ablation/restoration.

Most users should prefer the subsystem pipelines instead of calling low-level commit methods directly.

## Experience and development

```python
from verdant_development import DevelopmentalCycleConfig, VerdantDevelopmentPipeline
from verdant_kernel import ExperienceCommand

result = VerdantDevelopmentPipeline().advance(kernel, command)
```

`ExperienceCommand` requires:

- `event_key`;
- `source_ref`;
- `modality`;
- lowercase `payload_sha256`;
- nonempty finite `feature_vector`.

It may include explicit labels and typed concept/relation/claim proposals, confidence, evidence kind/details, and metadata.

## Subsystem packages

| Package | Primary class or function | Responsibility |
| --- | --- | --- |
| `cognitive_chunk_v2` | `CognitiveChunkV2`, `PipelineOrchestrator`, archive/resources | Typed multimodal compatibility plumbing |
| `verdant_language` | `VerdantLanguagePipeline` | Teach rules/lexemes and learn evidence-backed sentences |
| `verdant_claims` | `ClaimLearningPipeline` | Record typed claims and localize contradiction/revision |
| `verdant_ecwf` | `VerdantECWFPipeline` | Text-to-field inspection and evidence-bounded resonance commitment |
| `verdant_governance` | `VerdantGovernancePipeline` | Proposal, Three Kings inspection, Council commitment, outcomes |
| `verdant_shards` | `VerdantShardPipeline` | Governed shard formation and grounded routing |
| `verdant_sensory` | `VerdantSensoryPipeline` | Native translation, sample ingestion, temporal-event assembly |
| `verdant_media` | `VerdantMediaGateway` | File preservation, decoding, run inspection/continue/branch/package |
| `verdant_perception` | `VerdantPerceptionPipeline` | Nonsemantic temporal-region binding |
| `verdant_objects` | `VerdantObjectPipeline` | Object evidence accumulation and governed proto-object promotion |
| `verdant_workspace` | `VerdantWorkspacePipeline` | Bounded admission, commitment, and explicit writeback |
| `verdant_plasticity` | `VerdantPlasticityPipeline` | Bounded nonsemantic association updates |
| `verdant_structures` | `VerdantStructurePipeline` | P observation, candidate tracking, governed promotion |
| `verdant_compilation` | `VerdantCompilationPipeline` | P reconstruction probe and ablation/restoration |
| `verdant_interaction` | `VerdantStructureInteractionPipeline` | Continuous retrieval plus symbolic verification |
| `verdant_hierarchy` | `VerdantHierarchyPipeline` | Q observation/promotion/probe and availability control |
| `verdant_refolding` | `VerdantRefoldingPipeline` | Structural challenge and stable/revise/split/unresolved commitment |
| `verdant_benchmarks` | `EthomorphismBenchmarkHarness` | Current oracle-free A/B/C/D evaluation |

## Checkpoints

```python
from pathlib import Path
from verdant_kernel import load_checkpoint, save_checkpoint

sha256 = save_checkpoint(Path("organism.vdk"), kernel.state)
state = load_checkpoint(Path("organism.vdk"))
restored = VerdantKernel.from_state(state)
```

`save_checkpoint()` writes atomically through a temporary file and `os.replace()`. The archive contains `state.json` and `manifest.json` with fixed format name, byte length, and state SHA-256.

## Media gateway

```python
from pathlib import Path
from verdant_media import ImportOptions, VerdantMediaGateway

gateway = VerdantMediaGateway()
result = gateway.import_path(
    kernel,
    Path("input.png"),
    output_dir=Path("media_run"),
    options=ImportOptions(),
)
```

Key methods are `classify`, `import_path`, `import_many`, `inspect_run`, `load_run`, and `write_run_package`.

## Workbench Python service

The backend package is importable when `workbench/backend` is on `PYTHONPATH`:

```python
from verdant_workbench import DurableRunService, OrganismConfig

service = DurableRunService("my-lab")
project = service.create_project("experiment")
run = service.create_run(project.project_id, OrganismConfig())
```

`DurableRunService` owns project/run/checkpoint persistence, queue execution, engine-worker interaction, curricula, forensic/living views, experiments, provider captures, plugins, integrity, and branching.

## Workbench HTTP/WebSocket API

All operational routes use `/api/v1` except `/health`.

| Route group | Representative operations |
| --- | --- |
| Projects/runs | list/create projects and runs; status; close/reopen; ancestry |
| Queue/control | queue teach/probe; start; pause; step; stop |
| Checkpoints/events | save/list checkpoints; branch; event pagination; WebSocket event stream |
| Snapshot | summary or debug snapshot projection |
| Curricula | templates; compile/seal; pack compile/seal; list/detail; queue |
| Grammar | status; preview; teach rule, lexeme, or sentence |
| Structures | list/detail/graph/replay; promote; ablate; restore; interact; challenge; refold; causal compare |
| Explorer | frame and timeline projections |
| Hierarchy | observe and promote candidates |
| Experiments | template; author/seal; run; verify; fork; download packages |
| Providers | configure; capture paste; n4ã[h‘éì¶»§q«^t^Y\ŠŠˆ8 %›İ\‹X\›HÛÛ›ÛYÛÛ\\š\ÛÛˆ[™Ø]\Ø[ÛÛ›ÛË‚Kˆ
Š•ÛÜšØ™[˜Ú^Y\ŠŠˆ8 %ØØ[TKÕRK\œÚ\İ[˜ÙKİ\œšXİ[K^Ü™\œË^\š[Y[Ë›İšY\œËYÚ[œË[™[™Ú[™Y\š[™ÈXYÛ›ÜİXÜË‚ŒLˆ
Š”Üİ\™[X\ÙH]™[ÜY[^Y\ŠŠˆ8 %Ğ‹LLHİ\œšXİ[[HXÚÜËÛÜšÙ\ˆ[Y[İ]ÛÜœ™Xİ[Û‹Ü˜XÛKYœ™YHLNH™\XÙ[Y[[™[˜[Y][ÛˆÛÜšÙ›İÜË‚‚ˆÈÈZ[\İÛ™H[X™\š[™Â‚“Z[\İÛ™\Èx $ÍÈ\™H›ÛİÙYHZ[\İÛ™HKˆZ[\İÛ™HØ\È[X™\˜][H™[[İ™Y[™]È[X™\ˆØ\È›İ™]\ÙYˆZ[\İÛ™\ÈL8 $ÌNHÛÛ[YHœ›ÛHÛÜšÜÜXÙH›İYÚÙ[œÛÜK]™[ÜY[İXİ\™H›Ü›X][Û‹Y\˜\˜ÚK™Y›Û[™Ë[™™[˜ÚX\šÚ[™Ë‚‚”ÙYHÛZ[\İÛ™KZ[™^›YJZ[\İÛ™KZ[™^›Y
H›ÜˆH^XİXÚØYÙKÜ™\ÜØ\Y˜XİX\‚‚ˆÈÈ\İÜšXØ[Øİ[Y[][Ûˆ™Z]š[Ü‚‚‘^\İ[™È™\ÜÈ™\Ù\™HÚ]Ø\ÈÛZ[YY[™YX\İ\™Y]Z\ˆ^Y\‚‚‹H[™]šYX[RSTÕÓ‘WÊ—Ô‘TÔ•›Yš[\È\ØÜšX™HH[™Ú[™IÜÈİYÙYÛÛœİXİ[ÛÂ‹HÓÔ’Ğ‘SÒÕĞŠ—Ô‘TÔ•›Yš[\È\ØÜšX™HHÛÛ›Û\[™H›ØYX\Â‹HÓÔ’Ğ‘SÒÌWÌÑ’SSÔ‘TÔ•›Y[™‘SPTÑWÓPS’Q‘TÕšœÛÛ˜\ØÜšX™HHL]\İÛÜšØ™[˜ÚKŒŒH™[X\ÙHİ]NÂ‹HĞ‹LLH[™ÛÜšÙ\‹][Y[İ]š[\È\ØÜšX™H]\ˆÛÜšØ™[˜Ú]™[ÜY[Â‹HRSTÕÓ‘WÌNWÓÔPÓWÔ‘USQUSÓ‹›YÛÜœ™XİÈHÜšYÚ[˜[LNH›Ü›X][Ûˆ›İØÛÛ[™™XÛÜ™ÈH]\ˆN]\İ˜[Y][Û‹‚‚•HX\›Y\ˆØİ[Y[ÈÚİ[›İ™HÚ[[H™]Üš][ˆÈXZÙH[HÛÚÈ\ÈYˆ^H[Ø^\ÈÛÛZ[™YH]\ˆÛÜœ™Xİ[Û‹ˆHİ\œ™[İ]\ËÜ™\›ÙXÚXš[]HØÜÈ[œİXY[H™XY\ˆÚXÚ^Y\ˆ™[XZ[œÈ]]Üš]]]™H›ÜˆXXÚÛZ[K‚‚ˆÈÈXZ›Üˆ\ØÛÛ[Z]Hœ›ÛHX\›Y\ˆ™\™[Ù[™\˜][ÛœÂ‚•H\È[ˆ[™\[™[ÛX[‹\›ÛÛH™XZ[›İ[ˆ[˜Ü™[Y[[XÚØYÚ[™ÈÙˆHÛ\ˆŒ‹ÕŒËÕÜ˜\YÜ›İİİXÚËˆHHœ˜[˜Ú™[[İ™YH™]š[İ\È]Û[ÜœXØİ[]˜][Û˜[˜[\Ú\ØÛÛX‹[™Œˆ\İ™Y\È[™™\XÙY[HÚ]‚‚‹HÛ™HØ[›ÛšXØ[Ù\›™[İ]XÂ‹H^XÚ]\Y]šY[˜ÙH[™Ù[X[XÈØ]\ÎÂ‹H[œÜXİİ˜[Y]KØÛÛ[Z]›İ[™\šY\ÎÂ‹H]\›Z[š\İXÈÚXÚÜÚ[[™È[™[™XYÙNÂ‹H˜]]™HÙ[œÛÜKÜ\˜Ù\X[™XÛÜ™ÎÂ‹H›İ[™YØØ[\İXÚ]NÂ‹HÜ\]YHX\›™YÔHİXİ\™H™XÛÜ™ÎÂ‹HØ]\Ø[X›][Û‹Ü™\İÜ˜][ÛÂ‹HHØØ[X›Ü˜]ÜHÛÛ›Û[™K‚‚•HÛÛİ\˜ÙH™[XZ[œÈœ›İÜØX›H[ˆ]ÈİÛˆ™\œÚ[Ûˆœ˜[˜Ú\ËˆHØİ[Y[][ÛˆÚİ[^Z[ˆH]Ù[ˆ˜]\ˆ[ˆØ\œZ[™È›ÜØ\™ØœÛÛ]H[\Ü]ÈÜˆÛÛ˜Û\Ú[ÛœË‚‚ˆÈÈLNHÛÜœ™Xİ[Ûˆ^Y\‚‚•HÜšYÚ[˜[LNH™[˜ÚX\šÈ\ÙY]˜[X]ÜˆÜ›İ[™]ÈÙ[Xİ›Û[İ[Ûˆ\™Ù]ËˆH]\ˆÜ˜XÛKYœ™YH\›™\ÜÈÚ[™ÙYH›Ü›X][Ûˆ›İ[™\HÛÈ]™\H˜]]™[H[YÚX›HØ[™Y]H™XÙZ]™\ÈHØ[YHÜÜ[š]H[™]˜[X]ÜˆX\[™ÈØØİ\œÈÛ›HY\ˆ›Ü›X][Û‹‚‚•\™Y›Ü™N‚‚‹H\ÙHHÜšYÚ[˜[LNH™\ÜØ\Y˜XİÈ[™\œİ[™H\İÜšXØ[^\š[Y[[\ÚYÛˆ[™H›]ÎÂ‹H\ÙHRSTÕÓ‘WÌNWÓÔPÓWÔ‘USQUSÓ‹›YHÜ˜XÛKYœ™YHÛİ\˜ÙKİ\İË[™Hœ™\ÚŒ—ÛÜ˜XÛWÙœ™YX™\İ[›Üˆİ\œ™[Ù[Xİ[ÛˆÛZ[\ÎÂ‹HÈ›İ›[™HÜšYÚ[˜[˜XÚÙY”ÓÓˆÚ]HÛÜœ™XİY›Ü›X][Ûˆ[\œ™]][Û‹‚‚ˆÈÈÛÜšØ™[˜Ú™[X\ÙH™\œİ\ÈÛÛ[Z[™Èœ˜[˜Ú‚•HÛÜšØ™[˜ÚKŒŒHØİ[Y[È™XÛÜ™ŒHÛÜšØ™[˜Ú\İÈ[™LÛÛXš[™Y\İËˆHÛÛ[Z[™ÈHœ˜[˜Ú]\ˆYYÚ^ÛÜšØ™[˜Ú\İÈ[™ÛÈ[™Ú[™H™[˜ÚX\šÈ\İË™XXÚ[™ÈN‚‚•Hİ\œ™[™\šYWÜ™[X\ÙKœXÚ]È™]ÙY[ˆÜÙH^Y\œÎˆ][˜[ZXØ[HÛÛXİÈ[NLHİ\œ™[[™Ú[™H\İÈ]İ[^XÚ]H\İÈÛ›HHÛ\ˆŒHÛÜšØ™[˜Ú\İËˆH[\İZ]HÛÜšÙ›İÈ\ÈHÛÛ\]Hİ\œ™[\ØÛİ™\H›İ]K‚‚ˆÈÈØİ[Y[][ÛˆYYH\È\ÜÂ‚•Hİ\œ™[Ü›ÜÜË\Ş\İ[HØİ[Y[ÈÙ\™HYYİ]ÚYHHZ[ZY[]H]Ëˆ›È^\İ[™ÈX\šÙİÛˆØ\ÈY]Yˆ\È™\Ù\™\È[š[Üˆ™\ÙX\˜Ú™XÛÜ™È[™ÙY\È[™Ú[™KÕÛÜšØ™[˜ÚÛÛ[\Ú\È[˜Ú[™ÙYÚ[HÚ]š[™È™XY\œÈHİ\œ™[X\›İYÚ[K‚