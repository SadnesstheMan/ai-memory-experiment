#!/usr/bin/env python3
"""Stage 11: replay embedded recovery snapshot and structured history patches.

Works offline using Python's standard library, including Pyodide.
Never writes to GitHub. By default, only reads ai_memory.json.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def serialized(document):
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def git_blob_sha(document):
    raw = serialized(document)
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_history(record):
    require(isinstance(record, dict), "Memory must be a JSON object")
    require(record.get("schema_version") == 1, "Unsupported memory schema")
    revision = record.get("revision")
    require(type(revision) is int and revision >= 1, "Invalid revision")
    events = record.get("history")
    require(isinstance(events, list) and len(events) == revision, "History/revision mismatch")
    seen = set()
    for expected, event in enumerate(events, start=1):
        require(isinstance(event, dict) and event.get("revision") == expected,
                "History event revision out of sequence")
        eid = event.get("event_id")
        require(isinstance(eid, str) and eid and eid not in seen, "Invalid or duplicate event ID")
        seen.add(eid)
    require(record.get("checkpoint", "").startswith("STAGE5_"), "Missing Stage 5 checkpoint")
    require(record.get("stage6_handoff", "").startswith("STAGE6_HANDOFF_"), "Missing Stage 6 handoff")
    require(bool(record.get("stage7_test_nonce")), "Missing Stage 7 nonce")


def reconstruct(record):
    validate_history(record)
    recovery = record.get("recovery")
    require(isinstance(recovery, dict), "No Stage 11 embedded recovery anchor")
    require(recovery.get("format") == "anchored_top_level_patch_v1", "Unsupported recovery format")
    anchor_revision = recovery.get("anchor_revision")
    require(type(anchor_revision) is int and anchor_revision >= 1, "Invalid anchor revision")
    anchor = copy.deepcopy(recovery.get("anchor_snapshot"))
    require(isinstance(anchor, dict), "Missing recovery anchor snapshot")
    validate_history(anchor)
    require(anchor["revision"] == anchor_revision, "Anchor revision mismatch")
    require("recovery" not in anchor, "Anchor must precede recovery bootstrap")
    anchor_sha = recovery.get("anchor_blob_sha")
    require(git_blob_sha(anchor) == anchor_sha, "Anchor SHA mismatch")
    require(record["history"][:anchor_revision] == anchor["history"],
            "Historical events differ from anchor")
    restored = copy.deepcopy(anchor)
    # Recovery metadata is immutable across replay events and stored in the same record.
    restored["recovery"] = copy.deepcopy(recovery)
    last_blob_sha = anchor_sha
    for event in record["history"][anchor_revision:]:
        require(event.get("previous_blob_sha") == last_blob_sha,
                "History blob SHA chain mismatch at revision {}".format(event.get("revision")))
        operations = event.get("replay_ops")
        require(isinstance(operations, list) and operations, "Missing replay operations")
        changed = set()
        for op in operations:
            require(isinstance(op, dict) and op.get("op") in ("set", "delete"),
                    "Unsupported replay operation")
            key = op.get("field")
            require(isinstance(key, str) and key and key not in ("history", "recovery"),
                    "Forbidden replay field")
            require(key not in changed, "Duplicate replay field")
            changed.add(key)
            if op["op"] == "set":
                require("value" in op, "Missing set value")
                restored[key] = copy.deepcopy(op["value"])
            else:
                require(key in restored, "Cannot delete absent field")
                del restored[key]
        restored["history"].append(copy.deepcopy(event))
        require(restored["revision"] == event["revision"], "Replay revision mismatch")
        require(restored["last_updated"] == event["timestamp"], "Replay timestamp mismatch")
        last_blob_sha = git_blob_sha(restored)
    validate_history(restored)
    require(restored == record, "Reconstructed memory does not match canonical memory")
    return restored


def main():
    parser = argparse.ArgumentParser(description="Verify self-contained Stage 11 recovery")
    parser.add_argument("memory", nargs="?", default="ai_memory.json")
    parser.add_argument("--output", help="Optional local reconstructed JSON output")
    parser.add_argument("--self-test", action="store_true", help="Run isolated corruption-detection fixtures")
    args = parser.parse_args()
    original = json.loads(Path(args.memory).read_text(encoding="utf-8"))
    result = reconstruct(original)
    if args.self_test:
        examples = []
        changed_patch = copy.deepcopy(original)
        for op in changed_patch["history"][-1]["replay_ops"]:
            if op.get("field") == "status" and op.get("op") == "set":
                op["value"] = "TAMPERED_FIXTURE_VALUE"
                break
        examples.append(("changed_replay_value", changed_patch))
        missing_patch = copy.deepcopy(original)
        missing_patch["history"][-1].pop("replay_ops", None)
        examples.append(("missing_replay_patch", missing_patch))
        damaged_anchor = copy.deepcopy(original)
        damaged_anchor["recovery"]["anchor_snapshot"]["checkpoint"] = "CORRUPTED"
        examples.append(("tampered_anchor", damaged_anchor))
        for name, fixture in examples:
            try:
                reconstruct(fixture)
            except ValueError:
                print("REJECTED isolated corruption fixture:", name)
            else:
                raise AssertionError("Corrupted fixture passed validation: " + name)
        print("ISOLATED CORRUPTION TESTS PASS:", len(examples), "of", len(examples))
    if args.output:
        Path(args.output).write_bytes(serialized(result))
    print("STAGE 11 REPLAY PASS: restored revision", result["revision"],
          "from embedded revision", result["recovery"]["anchor_revision"],
          "with", result["revision"] - result["recovery"]["anchor_revision"], "patch events")


if __name__ == "__main__":
    main()
