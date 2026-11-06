#!/usr/bin/env python3
"""Stage 13: check integrity, revision freshness, and age of a portable backup.

Offline only. Uses the most recently supplied --current file, NOT live GitHub.
Does not create or overwrite the canonical memory file.
"""
import argparse
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from stage12_backup import make_backup, read_backup


def utc_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing backup export timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Backup timestamp lacks timezone")
    return parsed.astimezone(timezone.utc)


def revision_lag_issue(backup_revision, current_revision, max_revision_lag):
    gap = current_revision - backup_revision
    if gap > max_revision_lag:
        return "backup lags source by {} revisions".format(gap)
    if gap < 0:
        return "backup revision exceeds supplied source revision"
    return None


def audit(archive, current=None, max_age_hours=168, max_revision_lag=0,
          now=None):
    if max_age_hours < 0 or max_revision_lag < 0:
        raise ValueError("Freshness limits must not be negative")
    manifest, raw = read_backup(archive)
    backup_revision = manifest["revision"]
    exported = utc_timestamp(manifest["exported_at"])
    reference = now or datetime.now(timezone.utc)
    age_hours = (reference - exported).total_seconds() / 3600
    problems = []
    if age_hours < -0.0834:
        problems.append("backup timestamp is more than five minutes in the future")
    if age_hours > max_age_hours:
        problems.append("backup is too old ({:.1f} hours)".format(age_hours))
    current_revision = None
    if current is not None:
        # The independent file must be validated too; a stale or corrupted local
        # canonical copy must not be silently treated as trusted current state.
        from stage11_recover import reconstruct
        record = json.loads(Path(current).read_text(encoding="utf-8"))
        reconstruct(record)
        current_revision = record["revision"]
        revision_warning = revision_lag_issue(backup_revision, current_revision,
                                              max_revision_lag)
        if revision_warning:
            problems.append(revision_warning)
    return {
        "passed": not problems,
        "backup_revision": backup_revision,
        "current_revision": current_revision,
        "age_hours": round(age_hours, 2),
        "max_age_hours": max_age_hours,
        "max_revision_lag": max_revision_lag,
        "memory_sha256": manifest["files"]["ai_memory.json"]["sha256"],
        "memory_git_blob_sha": manifest["memory_git_blob_sha"],
        "source_is_fresh_live_github": False,
        "issues": problems,
    }


def self_test(memory, verifier, tool):
    with tempfile.TemporaryDirectory(prefix="stage13_fixture_") as folder:
        base = Path(folder)
        archived = base / "backup.zip"
        make_backup(memory, verifier, tool, archived)
        from stage11_recover import reconstruct
        live = json.loads(Path(memory).read_text(encoding="utf-8"))
        reconstruct(live)
        report = audit(archived, current=memory)
        if not report["passed"]:
            raise AssertionError("Fresh backup was rejected")
        manifest, _ = read_backup(archived)
        created_at = utc_timestamp(manifest["exported_at"])
        age_test = audit(archived, current=memory, max_age_hours=48,
                         now=created_at + timedelta(days=4))
        if age_test["passed"] or not any("too old" in x for x in age_test["issues"]):
            raise AssertionError("Stale timestamp went undetected")
        # Exercise the same pure revision-lag rule against a synthetic newer
        # revision; don't mutate or spoof the validated canonical JSON file.
        lag_warning = revision_lag_issue(report["backup_revision"],
                                         live["revision"] + 1, 0)
        if lag_warning != "backup lags source by 1 revisions":
            raise AssertionError("Stale revision went undetected")
        print("STAGE 13 SELF-TEST PASS: valid backup, stale time and revision lag")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Audit portable backup freshness")
    parser.add_argument("--archive", help="Previously exported backup ZIP")
    parser.add_argument("--current", help="Latest locally fetched ai_memory.json")
    parser.add_argument("--max-age-hours", type=float, default=168)
    parser.add_argument("--max-revision-lag", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="Run isolated backup audit fixtures")
    parser.add_argument("--memory", default="ai_memory.json")
    parser.add_argument("--verifier", default="tools/stage11_recover.py")
    args = parser.parse_args()
    if args.self_test:
        return self_test(args.memory, args.verifier,
                         "tools/stage12_backup.py")
    if not args.archive:
        parser.error("--archive is required unless using --self-test")
    output = audit(args.archive, current=args.current,
                   max_age_hours=args.max_age_hours,
                   max_revision_lag=args.max_revision_lag)
    print(json.dumps(output, indent=2))
    return 0 if output["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
