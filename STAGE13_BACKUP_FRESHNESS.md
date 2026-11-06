# Stage 13 — Backup Freshness, Rotation, and Recovery Drills

**Status at creation:** prepared; not yet verified on independent storage.

## Why Stage 13

Stage 12 demonstrated checksum verification and offline restoration from a ZIP in a separate folder on the user's computer. That is a genuine offline recovery test, but **not** redundancy against computer or disk loss. Stage 12 is therefore closed **with an outstanding independent-storage limitation**, not misrepresented as fully redundant.

Stage 13 makes backup health measurable and repeatable:
- detect when an offline backup is behind the canonical GitHub memory revision;
- identify when a backup is too old even if its revision matches;
- periodically create fresh copies to independent durable storage;
- restore a saved backup in an isolated folder and verify its contents;
- record observed versus user-reported evidence accurately.

## Components

- Canonical GitHub file: `ai_memory.json`.
- Backup creator/verifier: `tools/stage12_backup.py`.
- Backup freshness auditor: `tools/stage13_backup_audit.py`.
- Offline memory replay verifier: `tools/stage11_recover.py`.
- This plan: `STAGE13_BACKUP_FRESHNESS.md`.

**No recurring export, monitor, notification, or independent external destination is installed or enabled by committing these files.** A script placed in the same GitHub repository does not create genuine redundancy.

## Basic test on Windows

Download/extract the latest repository again after a canonical update, so the local `ai_memory.json` is not stale. Then in the root folder:

```bat
python tools\stage12_backup.py export --out stage13-revision-XX.zip
python tools\stage12_backup.py verify --archive stage13-revision-XX.zip
python tools\stage13_backup_audit.py --archive stage13-revision-XX.zip --current ai_memory.json --max-age-hours 168 --max-revision-lag 0
```

Replace XX with the revision reported by the export command. By default, the audit fails for a revision mismatch, an old archive, an invalid backup, or a memory record that fails replay validation. It cannot know the current *live* GitHub revision without a **freshly retrieved** canonical file. Running it while offline can establish freshness relative to your last downloaded file, not to unseen GitHub commits.

To check an older Stage 12 backup against a newer Stage 13 repository extract, use the same command with the older ZIP; a nonzero revision lag is expected. Do not overwrite an existing ZIP; `export` uses exclusive creation.

## Restore drill from independently stored copy

1. Copy the latest ZIP to a USB drive, external drive, or separately administered cloud provider that remains accessible without the primary GitHub account.
2. Disable network access or block GitHub.
3. Retrieve the ZIP **from that destination**, extract it into an isolated directory, and run:
   ```bat
   python tools\stage12_backup.py verify --archive ..\backup.zip
   python tools\stage12_backup.py restore --archive ..\backup.zip --output recovered_drill.json
   python tools\stage11_recover.py recovered_drill.json
   ```
4. Verify the ZIP's revision and SHA-256 against a trusted independently saved baseline.
5. Do not overwrite `ai_memory.json` in GitHub or in the repository folder.

## Proposed automation, not yet configured

A user-controlled Windows Task Scheduler job can periodically refresh an extracted checkout, export to a **separate target** and run the audit. A scheduled job should fail clearly when the USB drive is missing or when the source was not refreshed. Periodic manual exercises are still needed. Do not claim automatic replication or offsite protection until a real independent destination and successful scheduled runs are observed.

## Acceptance checks

- **13A:** Auditor accepts intact and current ZIP, reports accurate revision and checksums.
- **13B:** Auditor flags stale revision and stale export timestamp.
- **13C:** At least two backup generations are kept without overwriting the earlier one.
- **13D:** A backup reaches a genuinely independent destination, not only a folder on the same drive.
- **13E:** Offline restoration from that destination matches the expected revision and checksum.
- **13F:** Recurring freshness audit and periodic recovery drill are demonstrated and recorded with evidence.
- **13G:** Canonical GitHub memory retains all earlier checkpoints, events, Stage 11 replay integrity, and passing GitHub Actions.

This stage can only be marked complete when the required independent destination and recurring checks actually exist. A committed guide is **setup**, not a passed Stage 13 test.

## Data protection

This is a public experiment. Do not store private data, secrets, recovery credentials, or sensitive conversation contents in backups. ZIP-internal SHA-256 checksums detect accidental errors, not a forged ZIP plus manifest. For tamper-resistant authenticity, keep an expected hash or signature in a separately trusted location.

## Suggested next chat

> Read `ai_memory.json`, `MEMORY_PROTOCOL.md`, `STAGE11_RECOVERY_PROTOCOL.md`, and `STAGE13_BACKUP_FRESHNESS.md` in `SadnesstheMan/ai-memory-experiment`. Confirm Stage 13 setup and test its backup freshness auditor using isolated fixtures. Do not modify canonical memory without an explicit request.
