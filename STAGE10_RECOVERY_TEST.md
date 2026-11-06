# Stage 10 — Memory Recovery and Integrity Resilience

**Status:** Prepared, not tested. Begin only after confirming the live `ai_memory.json` reflects Stage 10 and Stage 9 is completed.

## Objective

Test whether external shared AI memory can detect damaged or incomplete data and reconstruct a valid state from Git history **without losing prior checkpoints, revision history, or later valid updates**.

This remains an experiment in external storage and retrieval, not a change to a model's internal memory.

## Safety boundaries

- **Never intentionally corrupt, truncate, delete, force-push, or reset the canonical `ai_memory.json`.**
- Run all destructive tests on an **isolated temporary copy** (such as a local browser editor test fixture or a dedicated experimental branch), not on the main branch file.
- Read `MEMORY_PROTOCOL.md` and fetch current `ai_memory.json` from the default branch before any official memory update.
- Do not publish secrets or personal conversation content in the public repository.
- All commits to the real canonical record remain append-only, use the latest content blob SHA as a precondition, and increment root `revision` exactly once per logical update.

## Tests

### 10A — Snapshot recovery (read-only)

1. Fetch the live canonical memory, noting its commit hash, blob SHA, revision, and event count.
2. Fetch two earlier snapshots using known Git commit SHAs, including the Stage 9 completion commit.
3. Verify those earlier snapshots contain the expected historical stage, revision, and checkpoints. Demonstrate that an old state can be read independently of the latest JSON.
4. **Do not restore an earlier snapshot over main.**

### 10B — Corruption detection on an isolated copy

1. Copy the canonical JSON to a temporary test fixture, **not** `ai_memory.json` on main.
2. In separate test attempts, deliberately introduce malformed JSON, a missing checkpoint, and an invalid `history`/`revision` mismatch.
3. Run a validator (either in a browser Python editor or Node/JavaScript environment) that checks JSON parse, schema version, incrementing history revisions, unique IDs, preservation of core checkpoints, timestamp validity, and previous-blob-SHA format.
4. Expect every damaged fixture to be rejected and the original to pass.

### 10C — Safe replay and recovery on a separate fixture

1. Obtain an earlier valid Git snapshot as a recovery base.
2. Replay subsequent valid logical changes onto a **new test copy**, preserving original checkpoints and earlier history entries, using successive revision numbers.
3. Compare the reconstructed fixture with the current live canonical record for required preserved fields and event IDs. Note any non-reproducible fields or information not represented in the event log.
4. Do not claim a full deterministic reconstruction if the event log lacks complete data patches; note which fields require Git snapshot diffs.

### 10D — Optional canonical restore workflow (only when explicitly authorized)

If the user later requests a genuine restore, first read the latest record and blob SHA, inspect the target commit, and propose a change that restores **specific named fields** while preserving the full history. Append one `restore_previous_snapshot` event with `restored_from_commit`, then commit using the latest SHA. Never reset the branch or silently overwrite intervening updates.

## Acceptance criteria

- Read-only retrieval of earlier Git snapshots succeeds.
- Isolated corruptions are detected with clear failure messages, with no canonical file damage.
- A fixture recovery preserves key checkpoints, the Stage 8 and 9 completion records, and all observed history events.
- If a Git commit is made for a non-destructive recovery marker, GitHub Actions validation passes.
- All results are recorded with observed-versus-user-reported evidence labels, and any limitations of event-log replay are documented.

## How to start

In a new ChatGPT conversation with GitHub access, ask:

> Read `MEMORY_PROTOCOL.md`, `ai_memory.json`, and `STAGE10_RECOVERY_TEST.md` from `SadnesstheMan/ai-memory-experiment`. Prepare the Stage 10 snapshot-recovery and integrity-validation tests without modifying the canonical memory. Show the baseline revision, relevant commit SHAs, and the safety boundaries. Do not commit anything until explicitly requested.

After reviewing the plan, carry out tests 10A and 10B using only read-only Git retrieval and an isolated temporary fixture. Return to the original chat to record results with version-safe updates.
