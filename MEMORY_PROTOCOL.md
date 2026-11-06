# AI Memory Experiment — Stage 7 Protocol

This repository contains **external shared memory** for an AI experiment. It does not change model weights, create automatic recall, or grant access without authorized retrieval.

## Canonical record
- File: `ai_memory.json` on the default branch.
- `schema_version`: structure version, currently 1.
- `revision`: increments exactly once per successful logical update.
- `history`: an array of events; append only, do not silently delete or rewrite.
- `stage`: the experiment milestone, not a per-session counter.
- `checkpoint` and `stage6_handoff`: preserve the original Stage 5 and Stage 6 values.
- `last_updated`: UTC ISO-8601 timestamp.
- `updated_by`: descriptive name of the writer.

## Update procedure (optimistic concurrency)
1. Fetch the latest `ai_memory.json` and record its **GitHub content blob SHA**.
2. Validate JSON, `schema_version=1`, integer `revision>=1`, and `history` array whose last entry has the same revision as the root.
3. Preserve all unrelated fields. Make only the intended changes.
4. Set `revision = old revision + 1`. Append one event to `history` containing:
   - `revision`: new revision number
   - `event_id`: an identifier unique within the event history
   - `timestamp`: UTC ISO-8601 time
   - `actor`: name of the updating instance
   - `action`: concise machine-readable event type
   - `summary`: human-readable description
   - `previous_blob_sha`: blob SHA from the initial fetch
5. Update root `last_updated`, `updated_by`, and other intended fields.
6. Commit the complete JSON to GitHub using the **original content blob SHA**. Do not issue concurrent writes to the same path.
7. If the update fails because the SHA is stale, **do not force overwrite**. Re-fetch, reconcile any intervening changes, rebase the event on the newest revision and blob SHA, and retry only when safe.
8. Re-fetch after committing and verify the new revision, appended event, and preserved checkpoint fields.

This is optimistic concurrency control: it detects certain collisions, but it is not a transaction lock or tamper-proof history. GitHub commits provide historical snapshots. Owners with write access may rewrite branch history.

## Recovery
To inspect an older revision, fetch the file at an earlier Git commit. To restore old values, **make a new revision** and append an event with `action: restore_previous_snapshot` and `restored_from_commit`. Do not silently drop newer history entries or force-reset the public history.

## Stage 7 cross-instance test
Open an independent ChatGPT conversation with GitHub access, then ask:

> Read `MEMORY_PROTOCOL.md` and `ai_memory.json` from `SadnesstheMan/ai-memory-experiment`. Follow the update procedure. Preserve the original `checkpoint` and `stage6_handoff`. Generate a unique unpredictable `stage7_test_nonce`, add it to the memory, increment `revision` by one, append an event with `action: stage7_cross_instance_test`, and commit with the current content blob SHA. Re-fetch to verify and report the commit SHA and revision.

Then open the original conversation and ask it to fetch `ai_memory.json` independently and verify the nonce, history event, revision, and preserved checkpoint fields.

**Privacy:** This is a public repository. Never store passwords, API tokens, personal secrets, or sensitive conversation content in it.

## Stage 11 replay requirement (applies after revision 14)

**Mandatory for all revisions 15 and later:** Before editing `ai_memory.json`, read [STAGE11_RECOVERY_PROTOCOL.md](./STAGE11_RECOVERY_PROTOCOL.md) and the offline verifier [tools/stage11_recover.py](./tools/stage11_recover.py). In addition to the SHA-safe update procedure above:

- Treat `recovery.anchor_snapshot`, `recovery.anchor_revision`, `recovery.anchor_blob_sha`, and `recovery.format` as immutable. The embedded revision-14 anchor is a checkpoint, not a mutable log.
- Each new history event MUST include `replay_ops`, a non-empty list of `{"op":"set","field":"top_level_field","value":...}` and optional `{"op":"delete","field":"top_level_field"}`, covering **every changed top-level root field except `history` and `recovery`**. Never change those excluded fields using replay operations; the event is appended automatically during replay.
- Always include updates for `revision`, `last_updated`, and `updated_by` in `replay_ops`, plus each additionally modified top-level field.
- Verify that `tools/stage11_recover.py ai_memory.json` reconstructs the entire proposed record using the embedded anchor and replay changes **before committing**. Treat a validation failure as a blocker.
- A valid update must also pass the GitHub Actions replay check. If SHA conflict occurs, discard stale patch operations and build them again after fetching current state.

This new requirement supplements, not replaces, the earlier append-only history and GitHub-SHA collision procedure. The anchor and event patches support **reconstruction from the current file after revision 14**, without retrieving intermediate Git snapshots. They cannot recover data when the whole current file is lost, and do not reconstruct all earlier historical intermediate records.
