# Stage 12 — Redundant Backup and Disaster Recovery

**Status at creation:** prepared, awaiting independent backup placement and a genuine restore from an independently stored copy.

## Objective

Reduce the single-point-of-failure risk in the external memory experiment. Earlier stages demonstrated versioned GitHub storage, collision rejection, validation, and self-contained replay from an anchor included in `ai_memory.json`. Stage 12 tests **survival after losing access to the primary GitHub repository** by keeping a portable, independently stored recovery package.

> An extra copy in this same GitHub repository, a Git branch, GitHub Pages, or a second GitHub repository is **not** an independent failure domain against a GitHub-wide outage or loss of GitHub credentials. A ZIP generated in a GitHub Actions runner is also ephemeral unless someone exports it to separately controlled durable storage.

## Components

- `tools/stage12_backup.py`: Python 3.9+ standard-library export, checksum verification, safe offline restore and isolated loss/corruption simulation.
- `tools/stage11_recover.py`: verifies self-contained recovery from the embedded revision-14 anchor and later replayable events.
- `ai_memory.json`: authoritative live source on GitHub.
- `STAGE12_DISASTER_RECOVERY.md`: this procedure.

The ZIP contains the entire current memory, both Python tools, a SHA-256 integrity manifest, a Git blob SHA, a record of revision and history length, and offline restore instructions.

## Create the off-repository backup

From an up-to-date checkout or a directory holding **the latest** `ai_memory.json` and both scripts:

```bash
python tools/stage12_backup.py export --memory ai_memory.json --out stage12-revision-XX.zip
python tools/stage12_backup.py verify --archive stage12-revision-XX.zip
```

Replace XX with the verified revision, then **copy the ZIP** to a location not dependent on access to the original GitHub account or service. Options include local removable storage, an offline encrypted drive, or a separately administered cloud-storage provider. A local file in this chat or an export in the repository workspace alone is not long-term off-site protection.

For genuine resilience keep at least two independent backups (e.g. one local offline copy plus one other provider). Protect private data accordingly, though this experiment's canonical repository is currently public.

## Verify offline recovery

On a machine with Python 3.9+ and **without GitHub access**:

1. Copy the backed-up ZIP to an isolated folder. Extract it there.
2. Run:
   ```bash
   python tools/stage12_backup.py verify --archive /path/to/stage12-revision-XX.zip
   python tools/stage12_backup.py restore --archive /path/to/stage12-revision-XX.zip --output recovered_stage12.json
   python tools/stage11_recover.py recovered_stage12.json
   ```
3. Compare the recovered file's bytes, revision, and SHA-256 with your manifest / saved baseline. Check `checkpoint`, `stage6_handoff`, and `stage7_test_nonce`; preserve the entire history and embedded anchor.
4. Never overwrite `ai_memory.json` on the default branch as part of this test.

The backup script refuses to restore to a path named `ai_memory.json` or overwrite an existing output.

## Automated, non-destructive simulation (tests the machinery, not backup independence)

```bash
python tools/stage12_backup.py self-test --memory ai_memory.json
```

The test creates a **temporary disposable memory copy**, exports it, deletes only that disposable copy, recovers exactly from the temporary archive, and rejects a deliberately corrupted temporary archive. The canonical file is never deleted or overwritten. GitHub Actions runs this test as a guard.

## Acceptance checklist

- **12A — Portable export:** backup archive contains full memory, scripts, integrity manifest and the correct latest revision, with no canonical write.
- **12B — Verification:** SHA-256 hashes and Stage 11 replay validator accept intact backup; corruption is rejected.
- **12C — Simulated disaster:** delete only the disposable test source; restore identical bytes from archive without re-reading canonical memory.
- **12D — Independent placement:** user confirms one backup has been copied to a genuinely independently accessible durable store (not just the GitHub repository, CI runner, or a transient chat attachment).
- **12E — Real offline recovery:** test from that independent store with no GitHub access and verify checksums/checkpoints and revision. Record whether observed or user-reported.
- **12F — Integrity automation:** CI runs backup self-test and Stage 11 validator successfully.

A stage must not be marked **fully complete** while independent placement/recovery has not been verified. Repeat exports after important updates: this tool is **not** automatic background replication, and a backup only captures its own revision.

## Security and scope

- In-archive SHA-256 validates internal consistency and unintentional corruption, **not authenticity against a deliberate attacker** who can replace both memory and manifest. For adversarial threats, save the expected SHA-256 in a second trusted location or digitally sign the manifest with a separately protected key.
- If the entire repository is lost, restoring locally from the independently stored ZIP is feasible. Restoring to GitHub requires explicit user authorization and the versioned protocol; never push blindly to overwrite newer live changes.
- The embedded Stage 11 anchor reconstructs **revision 14 onward**. Earlier intermediate snapshots require Git history.
- A successful local simulation is not proof of true independent availability in a GitHub outage.

## Suggested new-chat test

> Read `ai_memory.json`, `MEMORY_PROTOCOL.md`, `STAGE11_RECOVERY_PROTOCOL.md` and `STAGE12_DISASTER_RECOVERY.md` from `SadnesstheMan/ai-memory-experiment`. Verify Stage 12's latest status. Export and validate a portable backup without modifying the canonical memory; perform only an isolated dry-run restore. Report its SHA-256, revision, and checks. Do not record completion of independent backup placement unless an off-GitHub backup is actually stored and recovered.
