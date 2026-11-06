# Stage 11 — Self-contained recovery using an embedded checkpoint and replayable history

## Scope and limits

The canonical `ai_memory.json` contains:
- `recovery.anchor_snapshot`: **one complete, preserved revision-14 snapshot**, saved in the same file.
- `recovery.anchor_revision`: 14.
- `recovery.anchor_blob_sha`: the Git blob SHA of the serialized anchor snapshot.
- `recovery.format`: `anchored_top_level_patch_v1`.
- Every history event **after revision 14**: `replay_ops` with the machine-readable changes needed to reconstruct that revision from the immediately preceding one.

Because the anchor is from revision 14, the experiment can recover **revision 14 and later** without fetching intermediate Git commits. It does **not** reconstruct revisions 1–13 from their summary-only events; their final values and events are preserved inside the anchor. No model weights or internal memory are modified. The embedded anchor means the document grows; it is not a separate durable backup or protection from whole-file deletion or malicious rewriting.

## How to verify recovery offline

Download `ai_memory.json` and `tools/stage11_recover.py` into the same directory and run:

```bash
python tools/stage11_recover.py ai_memory.json --output recovered_local.json
```

Pyodide can execute this with standard-library Python and local files. It doesn't need network access. The validator checks the anchor's Git blob hash, history sequencing, old checkpoints, replay integrity, and full JSON object equality with the record being validated. The output file is a **local recovered copy**, never an automatic GitHub write.

## REQUIRED for every future canonical-memory write

Continue to follow [MEMORY_PROTOCOL.md](./MEMORY_PROTOCOL.md). Before updating, re-fetch the live memory file, its content blob SHA and this Stage 11 guide.

1. Make a deep copy of current memory to construct the intended next state; preserve `recovery` **byte-for-byte in meaning** and all unrelated fields. Never mutate `recovery.anchor_snapshot`.
2. Increment `revision` once. Update `last_updated` and `updated_by`, and append the standard single history event (timestamp, actor, summary, previous blob SHA).
3. Add a **non-empty** `replay_ops` array to the new history event. It must represent **every changed top-level root field except `history` and `recovery`**. Use the following schema:
   ```json
   {"op": "set", "field": "stage11", "value": {"status": "running"}}
   ```
   Or `{"op":"delete","field":"obsolete_field"}` to remove a top-level field. Never patch `history` or `recovery`, never use two operations for the same field, and never include event-log instructions as executable code. The event itself is appended by the replay algorithm.
4. At minimum, normal updates require operations to set new `revision`, `last_updated`, and `updated_by`. Add a `set` operation for any other changed root field such as `stage`, `status`, or the entire updated `stage11` object. Setting the whole nested object is intentionally simple but can increase file size.
5. **Test in an isolated copy before committing:** running `tools/stage11_recover.py` on the proposed new JSON must exactly recreate the entire proposed JSON from `recovery.anchor_snapshot` and its embedded replay ops. The validator also checks each replay event's `previous_blob_sha` against the serialized predecessor (except the first event, which points to the original anchor).
6. Commit the full JSON to GitHub using the original SHA read in step 1 (optimistic concurrency). If rejected because the SHA is stale, fetch current state, reconcile, rebuild your ops against the **new** current record, revalidate, and only then retry.
7. Re-fetch the committed record and confirm the new revision and all checkpoints; ensure GitHub Actions validation passes.

The JSON format uses two-space indentation and a trailing newline. A change to serialization format can affect the reconstructed Git blob SHA chain; do not silently reformat the file.

## Stage 11 tests

- **11A — Anchor integrity:** confirm the embedded snapshot equals actual revision 14 and its stored Git blob SHA. No intermediate historical Git snapshots are needed for later replay.
- **11B — Replay:** reconstruct the updated canonical record from the **single current file** (anchor + replay ops) and compare it to the actual document.
- **11C — Corruption detection:** in isolated copies, change a patch value or remove a patch; validator must reject. The real canonical file is never deliberately damaged.
- **11D — Continuation:** perform a second SHA-safe revision with replay ops and verify a two-step replay.
- **11E — CI:** GitHub Actions executes the offline replay verifier and succeeds on the resulting commit.

Successful testing proves reconstruction of the post-anchor data **when the current file and anchor are intact**. It does not prove recovery from loss of the whole GitHub repository, nor reconstruction from summaries alone.
