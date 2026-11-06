# Stage 9 — Concurrent Memory and Conflict Recovery

**Goal:** Verify that two ChatGPT conversations can safely preserve separate changes even if both start from the same old version of `ai_memory.json`. This is external-memory concurrency testing, not neural-model memory.

## Preconditions

- The live canonical file is `ai_memory.json` in `SadnesstheMan/ai-memory-experiment`.
- Read [MEMORY_PROTOCOL.md](./MEMORY_PROTOCOL.md) before a write.
- Preserve original `checkpoint`, `stage6_handoff`, and `stage7_test_nonce`, all existing history, the Stage 8 completion record, and all unrelated fields.
- Never place tokens, passwords, or private user information in this public repository.
- Use the GitHub file **content blob SHA**, *not* a commit SHA, as the precondition to an update.

## Controlled stale-write simulation (single session)

1. Read the same starting memory revision and blob SHA into two independent proposed changes, A and B.
2. Writer A makes a revisioned update adding a unique `stage9.trials.controlled.writer_a` value.
3. Writer B intentionally tries its now-outdated proposal using the **original** blob SHA. Expect GitHub to reject with a stale-SHA conflict. Never overwrite without a current SHA.
4. Writer B re-fetches the current file, rebases **only** its independent change onto the latest revision, and appends a new history event adding `stage9.trials.controlled.writer_b`.
5. Verify both values and all earlier checkpoints are present. Record that this was a **sequential simulation** of stale-write collision, not proof of two real instances writing at the same moment.

## Real independent-instance handoff test

Use **two new, separate ChatGPT conversations** with GitHub access. Do not test with sensitive data.

A. Ask each conversation to read the live `ai_memory.json`, `MEMORY_PROTOCOL.md`, and this document. Tell each to **prepare only** an update and report its base revision and content blob SHA, without committing. Prepare writer A and B while the shared file remains unchanged.

B. After both have confirmed the **same** base revision and SHA, tell A: *Commit your writer A value under `stage9.trials.cross_instance.writer_a`, using the prepared file content SHA and following the protocol. Report the new commit SHA.*

C. Tell B: *Attempt your previously prepared writer B change using the original prepared content SHA. Do not silently re-fetch before the first attempt: this is a controlled collision test. If GitHub rejects the stale SHA, record the rejection, re-fetch current memory, preserve A, append your own value in `stage9.trials.cross_instance.writer_b` at the next revision, and commit using the new SHA. Report both results.* B must stop if the conflict cannot be safely reconciled.

D. Return to the original conversation. Independently verify that writer A and B values survived, their history entries are append-only, and the SHA chain is correct. Check GitHub Actions validation for the **final** commit.

## Acceptance criteria

- Stale-SHA write was rejected (record observed error).
- No first-writer change was lost.
- Second writer re-read, reconciled, and wrote with a new SHA.
- Revision increased exactly once per successful logical write.
- GitHub Actions validation succeeded and historic checkpoints were preserved.
- The independent-instance version must be tested separately from the controlled simulation.

## Recovery for unexpected outcomes

If B's stale write succeeds unexpectedly, stop further test writes and inspect the Git history for lost data. Restore the missing first-writer change via a **new** revisioned event using the *latest* blob SHA; never force-push or delete previous history. If there is an authentication, rate-limit, network, or unrelated API error, do **not** call it a conflict detection success. Stop and report what happened.

**Note:** GitHub content-SHA preconditions are optimistic concurrency control, not a transaction lock. Branch permissions and history rewrites can weaken guarantees.
