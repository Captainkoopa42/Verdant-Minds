# Verdant publication status

This is the first file to open at the beginning of every publication work session.

## Current state

- **Program:** Verdant Publication Evidence Program v1.0
- **Candidate:** Verdant Publication Candidate 1 (VPC-1)
- **Phase:** Phase 0 - Freeze and inventory
- **Status:** Local Phase 0 gate passed; external synchronization pending
- **Active experiment:** None; confirmatory testing has not started
- **Frozen primary Q threshold:** `0.985`
- **Candidate branch:** `wb11-worker-response-sync-fix`
- **Architecture baseline commit:** `b0f73a1`
- **Candidate reference:** `verdant-publication-candidate-v1`
- **External synchronization:** Pending; local branch is ahead of its remote tracking branch

## Current gate

Phase 0 is complete only when:

- the candidate checkout is clean;
- the full current preflight suite passes;
- the environment and candidate hashes are recorded;
- the architecture-freeze policy is committed;
- the verified candidate is tagged;
- the candidate branch and tag are synchronized to the public remote.

## Work completed

- [x] Publication master plan written and committed.
- [x] Repository, test, release, and existing-artifact inventory started.
- [x] Isolated Python environment created from `requirements-lock.txt`.
- [x] Verification script expanded from the older release boundary to all current test files.
- [x] Publication control directory and evidence-ledger skeleton created.
- [x] Full 267-test preflight suite passed locally.
- [x] Candidate hashes and Linux environment snapshot recorded.
- [x] Phase 0 controls prepared for the candidate commit.
- [x] Local VPC-1 tag is created after the clean committed preflight.
- [ ] Candidate branch and tag pushed to the remote.

## Blockers

- Pushing the branch and tag is an external publication action and is not performed silently.

## Exactly one next action

Synchronize the verified candidate branch and annotated tag to the remote, then begin Phase 1 protocol and generator validation.
