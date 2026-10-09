
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENESIS_HASH = "0" * 64


def canonical_json(data: dict[str, Any]) -> str:
    """Serialize data deterministically so hashes are reproducible."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def calculate_hash(record: dict[str, Any]) -> str:
    """Calculate the SHA-256 hash of a record, excluding its own hash."""
    payload = {key: value for key, value in record.items() if key != "hash"}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def append_event(
    log_path: str | Path,
    event: dict[str, Any],
) -> dict[str, Any]:
    """
    Append an event to a hash-chained JSONL audit log.

    Each record contains:
      - sequence: monotonically increasing record number
      - timestamp: UTC timestamp
      - previous_hash: hash of the preceding record
      - event: event details
      - hash: SHA-256 hash of this record's contents
    """
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    if path.exists():
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    records.append(json.loads(line))

    # Refuse to extend a log that already fails integrity verification.
    if records:
        result = verify_chain(path)
        if not result["valid"]:
            raise ValueError(
                f"Cannot append to invalid audit log: {result['error']}"
            )

    previous_hash = records[-1]["hash"] if records else GENESIS_HASH

    record = {
        "sequence": len(records) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "previous_hash": previous_hash,
        "event": event,
    }
    record["hash"] = calculate_hash(record)

    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(canonical_json(record) + "\n")

    return record


def verify_chain(log_path: str | Path) -> dict[str, Any]:
    """
    Verify record sequence, previous-hash links, and record hashes.

    Returns a result dictionary with valid, records_checked, and error.
    """
    path = Path(log_path)

    if not path.exists():
        return {
            "valid": False,
            "records_checked": 0,
            "error": "Audit log does not exist",
        }

    previous_hash = GENESIS_HASH
    records_checked = 0

    try:
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    return {
                        "valid": False,
                        "records_checked": records_checked,
                        "error": f"Invalid JSON on line {line_number}: {exc}",
                    }

                expected_sequence = records_checked + 1

                if record.get("sequence") != expected_sequence:
                    return {
                        "valid": False,
                        "records_checked": records_checked,
                        "error": (
                            f"Sequence mismatch on line {line_number}: "
                            f"expected {expected_sequence}, "
                            f"got {record.get('sequence')}"
                        ),
                    }

                if record.get("previous_hash") != previous_hash:
                    return {
                        "valid": False,
                        "records_checked": records_checked,
                        "error": f"Previous-hash mismatch on line {line_number}",
                    }

                expected_hash = calculate_hash(record)
                if record.get("hash") != expected_hash:
                    return {
                        "valid": False,
                        "records_checked": records_checked,
                        "error": f"Record hash mismatch on line {line_number}",
                    }

                previous_hash = record["hash"]
                records_checked += 1

    except OSError as exc:
        return {
            "valid": False,
            "records_checked": records_checked,
            "error": f"Could not read audit log: {exc}",
        }

    return {
        "valid": True,
        "records_checked": records_checked,
        "error": None,
    }


# ---------------------------------------------------------------- pipeline interface (section 10)
# pipeline.py calls chain.log(event, session_id, **fields) and chain.text_hash(); these map
# that contract onto append_event() so the app and eval share one hash-chain format.
import os
import threading

LOG = Path(os.environ.get("AEGIS_AUDIT", "logs/audit.jsonl"))
_lock = threading.Lock()          # the UI and eval may log from several threads


def log(event: str, session_id: str, **fields: Any) -> dict[str, Any]:
    """Append one pipeline event to LOG. Never pass raw secrets: hash or redact first."""
    payload = json.loads(json.dumps({"event": event, "session": session_id, **fields}, default=str))
    with _lock:
        return append_event(LOG, payload)


def text_hash(s: str) -> str:
    """Short sha256 used in audit records instead of raw user text or tool output."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]
