#!/usr/bin/env python3
"""Stage 12: portable, offline AI memory backup and recovery (standard library only).

Never writes to the canonical memory file or GitHub. A ZIP archive is only a
potentially independent backup AFTER the user copies it outside this repository.
Self-contained hashes detect accidental corruption, not malicious replacement.
"""
import argparse
import copy
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from stage11_recover import reconstruct

FORMAT = "ai_memory_offline_backup_v1"
SOURCE_REPO = "SadnesstheMan/ai-memory-experiment"
ALLOWED = (
    "ai_memory.json",
    "tools/stage11_recover.py",
    "tools/stage12_backup.py",
    "manifest.json",
    "RESTORE_INSTRUCTIONS.txt",
)
MAX_FILE_BYTES = 10_000_000

INSTRUCTIONS = """STAGE 12 PORTABLE AI MEMORY BACKUP
This archive contains the full memory snapshot, recovery scripts and checksums.
It is not an independent backup until saved outside the primary GitHub repository.

Offline verification and recovery (requires Python 3.9+):
1. Extract the ZIP into a separate, empty directory.
2. From that directory run:
   python tools/stage12_backup.py verify --archive /path/to/original-backup.zip
   python tools/stage12_backup.py restore --archive /path/to/original-backup.zip --output recovered_stage12.json
3. Optionally run:
   python tools/stage11_recover.py recovered_stage12.json
4. Compare recovered revision and SHA-256 against your separately saved manifest.

The restore command never overwrites ai_memory.json or an existing output file.
Do NOT commit recovered data to main without an explicit user request and the
revision/SHA-safe restore procedure in MEMORY_PROTOCOL.md.
A manifest within the same ZIP is not a cryptographic signature or a trust root.
"""


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def validate_memory(raw):
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Memory file is too large")
    record = json.loads(raw.decode("utf-8"))
    reconstruct(record)
    return record


def make_backup(memory_path, verifier_path, tool_path, archive_path):
    memory_raw = Path(memory_path).read_bytes()
    record = validate_memory(memory_raw)
    payloads = {
        "ai_memory.json": memory_raw,
        "tools/stage11_recover.py": Path(verifier_path).read_bytes(),
        "tools/stage12_backup.py": Path(tool_path).read_bytes(),
        "RESTORE_INSTRUCTIONS.txt": INSTRUCTIONS.encode("utf-8"),
    }
    for name, raw in payloads.items():
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError("File too large: " + name)
    manifest = {
        "format": FORMAT,
        "source_repository": SOURCE_REPO,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "revision": record["revision"],
        "history_events": len(record["history"]),
        "memory_git_blob_sha": git_sha(memory_raw),
        "files": {name: {"sha256": sha256(raw), "size": len(raw)}
                  for name, raw in payloads.items()},
        "limitations": "Self-contained hashes detect accidental corruption; "
                       "copy archive outside GitHub for independent availability.",
    }
    payloads["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    target = Path(archive_path)
    if target.resolve() == Path(memory_path).resolve():
        raise ValueError("Refusing to replace the canonical memory")
    with ZipFile(target, "x", compression=ZIP_DEFLATED) as z:
        for name, raw in payloads.items():
            z.writestr(name, raw)
    return manifest


def read_backup(archive_path):
    with ZipFile(archive_path, "r") as z:
        names = z.namelist()
        if len(names) != len(ALLOWED) or set(names) != set(ALLOWED):
            raise ValueError("Backup contents do not match expected manifest")
        for info in z.infolist():
            if info.file_size > MAX_FILE_BYTES:
                raise ValueError("Archive member too large: " + info.filename)
        files = {name: z.read(name) for name in ALLOWED}
    manifest = json.loads(files["manifest.json"].decode("utf-8"))
    if manifest.get("format") != FORMAT or manifest.get("source_repository") != SOURCE_REPO:
        raise ValueError("Invalid backup format or source repository")
    if set(manifest.get("files", {})) != set(ALLOWED) - {"manifest.json"}:
        raise ValueError("Manifest file inventory mismatch")
    for name, spec in manifest["files"].items():
        if sha256(files[name]) != spec.get("sha256") or len(files[name]) != spec.get("size"):
            raise ValueError("Backup checksum mismatch: " + name)
    raw = files["ai_memory.json"]
    if git_sha(raw) != manifest.get("memory_git_blob_sha"):
        raise ValueError("Git blob checksum mismatch")
    record = validate_memory(raw)
    if record["revision"] != manifest.get("revision"):
        raise ValueError("Backup revision mismatch")
    if len(record["history"]) != manifest.get("history_events"):
        raise ValueError("Backup event count mismatch")
    return manifest, raw


def restore_backup(archive_path, output_path):
    manifest, raw = read_backup(archive_path)
    target = Path(output_path)
    if target.resolve() == Path("ai_memory.json").resolve() or target.name == "ai_memory.json":
        raise ValueError("Refusing to overwrite any canonical ai_memory.json")
    with target.open("xb") as stream:
        stream.write(raw)
    return manifest


def simulated_outage_test(memory_path, verifier_path, tool_path):
    with tempfile.TemporaryDirectory(prefix="stage12_fixture_") as temp:
        root = Path(temp)
        isolated = root / "isolated_memory.json"
        isolated.write_bytes(Path(memory_path).read_bytes())
        offline_zip = root / "offline_backup.zip"
        manifest = make_backup(isolated, verifier_path, tool_path, offline_zip)
        isolated.unlink()  # Simulates loss of a disposable primary copy only.
        confirmed, raw = read_backup(offline_zip)
        recovered = root / "recovered_fixture.json"
        restore_backup(offline_zip, recovered)
        if recovered.read_bytes() != raw:
            raise AssertionError("Restored file does not exactly match backup")
        if confirmed["memory_git_blob_sha"] != manifest["memory_git_blob_sha"]:
            raise AssertionError("Backup provenance mismatch")

        # Tamper with one copied file while retaining original checksum manifest.
        corrupted = root / "corrupted.zip"
        with ZipFile(offline_zip, "r") as src, ZipFile(corrupted, "x") as dst:
            for name in ALLOWED:
                payload = src.read(name)
                if name == "ai_memory.json":
                    payload = payload.replace(b'"stage": 12', b'"stage": 99', 1)
                    if payload == src.read(name):
                        payload = b"x" + payload[1:]
                dst.writestr(name, payload)
        try:
            read_backup(corrupted)
        except ValueError as exc:
            if "checksum mismatch" not in str(exc):
                raise
        else:
            raise AssertionError("Tampered memory backup was incorrectly accepted")
        print("Stage 12 isolated outage/recovery PASS; corrupted backup rejected")
        print("Restored revision", manifest["revision"], "without network or canonical source")


def main():
    parser = argparse.ArgumentParser(description="Offline backup and recovery for AI memory")
    sub = parser.add_subparsers(dest="command", required=True)
    exporter = sub.add_parser("export")
    exporter.add_argument("--memory", default="ai_memory.json")
    exporter.add_argument("--verifier", default="tools/stage11_recover.py")
    exporter.add_argument("--out", required=True)
    checker = sub.add_parser("verify")
    checker.add_argument("--archive", required=True)
    restorer = sub.add_parser("restore")
    restorer.add_argument("--archive", required=True)
    restorer.add_argument("--output", required=True)
    trial = sub.add_parser("self-test")
    trial.add_argument("--memory", default="ai_memory.json")
    trial.add_argument("--verifier", default="tools/stage11_recover.py")
    args = parser.parse_args()
    if args.command == "export":
        manifest = make_backup(args.memory, args.verifier, Path(__file__), args.out)
        print("Exported backup revision", manifest["revision"], "to", args.out)
        print("Copy it outside this GitHub repository for independent protection")
    elif args.command == "verify":
        manifest, _ = read_backup(args.archive)
        print("Verified backup revision", manifest["revision"],
              "SHA-256", manifest["files"]["ai_memory.json"]["sha256"])
    elif args.command == "restore":
        manifest = restore_backup(args.archive, args.output)
        print("Restored offline copy of revision", manifest["revision"], "to", args.output)
    else:
        simulated_outage_test(args.memory, args.verifier, Path(__file__))


if __name__ == "__main__":
    main()
