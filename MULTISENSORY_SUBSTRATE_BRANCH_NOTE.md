# V5 Multisensory Substrate Prework

## Branch purpose

This branch is **documentation and pre-implementation design work only** for a future Verdant multisensory / embodied sensory substrate.

It exists so the work can be reopened later by William or by another LLM without relying on conversation history.

**Base branch:** `V5`

**Base V5 commit at branch creation:** `ec37dfd90f5b4a3c889a7105d7e855692a372b77`

**Branch:** `V5-Multisensory-Substrate-Prework`

## Why this branch exists

The immediate question that exposed the problem was simple: how should a future embodied Verdant receive pure binocular depth from two cameras without object boxes, semantic labels, or hand-authored world interpretation?

Reviewing the actual V5 sensory and perception implementation showed that the problem is broader than stereo depth. V5 currently has a strong evidence-preserving sensory gateway and strong higher developmental / cognitive machinery, but several assumptions in the current M10/M11 path are still shaped around one visual stream, one audio stream, and bounded media experiments.

Two eyes expose those assumptions immediately.

This branch therefore captures the design work for a **genuinely multisensor Verdant substrate** before physical camera, ear, proprioceptive, or motor hardware is attached.

## What is in scope

- multiple sensors of the same modality;
- binocular stereo as a pure nonsemantic sensory derivation;
- binaural / spatial audio implications;
- sensor identity versus stream/session identity;
- exact acquisition pairing and clock-domain handling;
- missing / invalid / unknown sensory states;
- dense derived sensory fields and provenance;
- moving-eye proprioception;
- M11 stream scoping and ego-motion implications;
- storage / archive scaling for continuous embodiment;
- compatibility with existing V5 checkpoints and stable IDs;
- a missing developmental bridge between dense sensation and concept-scoped P/Q learning;
- an adversarial test matrix that must pass before implementation is treated as trustworthy.

## What is explicitly NOT in scope yet

- production hardware drivers;
- real robot motor control;
- object detection;
- bounding boxes in the stereo stage;
- semantic labels such as `person`, `chair`, `near`, `far`, `safe`, or `reachable`;
- navigation logic;
- SLAM;
- hard-coded affordances;
- pretending a conventional stereo matcher is a semantic perception system;
- modifying V5 historical record semantics without a compatibility plan.

## Important status note

No multisensory runtime implementation is claimed to exist on this branch yet.

The documents under `docs/multisensory-substrate/` are a preserved engineering handoff and research specification. They are intended to be attacked, revised, prototyped, and tested before any implementation is considered part of the active Verdant architecture.

Start with:

- `docs/multisensory-substrate/README.md`
- `docs/multisensory-substrate/DESIGN_CONTRACT.md`
- `docs/multisensory-substrate/ADVERSARIAL_TEST_MATRIX.md`
- `docs/multisensory-substrate/LLM_HANDOFF.md`
