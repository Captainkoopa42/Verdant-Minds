# VPC-1 architecture freeze policy

## Purpose

VPC-1 exists to characterize the architecture already built. The publication campaign cannot distinguish measurement from invention if cognitive mechanisms change while outcomes are being collected.

## Changes permitted during the campaign

- Evaluation harnesses and external case generators
- Result schemas, validators, and analysis scripts
- Logging, provenance, hashing, and reproducibility infrastructure
- Documentation and packaging
- Portability fixes that do not change cognitive dispositions
- Correctness fixes, provided their behavioral impact is tested and disclosed

## Changes not permitted under the same candidate

- New cognitive stages, memories, folds, routing mechanisms, or governance mechanisms
- Changes to P or Q promotion semantics
- Changes to structure-selection or fallback semantics
- Post-result threshold tuning
- Adding evaluator family labels or expected answers to Verdant state
- Deleting or rewriting failed raw trials
- Pooling results from behaviorally different candidate commits without disclosure

## Change classification

Every campaign commit must be classified as one of:

1. `measurement` - evaluator, schema, instrumentation, or analysis only;
2. `documentation` - prose or packaging only;
3. `portability` - environment compatibility with no intended cognitive change;
4. `correctness` - repairs behavior that contradicts an existing invariant;
5. `architecture` - changes cognitive behavior or introduces a new mechanism.

An `architecture` change retires VPC-1. A `correctness` or `portability` change requires the full preflight suite and a before/after disposition comparison. If behavior changes, the candidate version increments and confirmatory results restart.

## Locked-test rule

The locked test manifest is generated and hashed in Phase 3. After its outcomes are opened:

- no threshold, evaluator, generator, or analysis rule may be tuned against those outcomes;
- any necessary change creates a recorded deviation;
- any change affecting scientific dispositions creates a new candidate and new locked campaign;
- old results remain archived and are never silently replaced.

## Authority and record

William Adams is the scientific authority for accepting a candidate or campaign restart. AI-assisted changes must be reviewed by him. Every exception is appended to `protocol/protocol_deviations.jsonl` before affected cases are rerun.

