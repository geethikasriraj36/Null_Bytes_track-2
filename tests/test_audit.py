
import json

import pytest

from aegis.audit.chain import append_event, verify_chain


def test_empty_log_is_valid(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text("", encoding="utf-8")

    result = verify_chain(log)

    assert result["valid"] is True
    assert result["records_checked"] == 0


def test_appending_events_creates_valid_chain(tmp_path):
    log = tmp_path / "audit.jsonl"

    first = append_event(
        log,
        {"action": "policy_decision", "decision": "allow"},
    )
    second = append_event(
        log,
        {"action": "policy_decision", "decision": "block"},
    )

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert second["previous_hash"] == first["hash"]

    result = verify_chain(log)
    assert result["valid"] is True
    assert result["records_checked"] == 2


def test_tampering_is_detected(tmp_path):
    log = tmp_path / "audit.jsonl"

    append_event(
        log,
        {"action": "policy_decision", "decision": "allow"},
    )

    record = json.loads(log.read_text(encoding="utf-8"))
    record["event"]["decision"] = "block"
    log.write_text(json.dumps(record) + "\n", encoding="utf-8")

    result = verify_chain(log)

    assert result["valid"] is False
    assert "hash mismatch" in result["error"].lower()


def test_cannot_append_to_tampered_log(tmp_path):
    log = tmp_path / "audit.jsonl"

    append_event(log, {"action": "test", "value": 1})

    record = json.loads(log.read_text(encoding="utf-8"))
    record["event"]["value"] = 999
    log.write_text(json.dumps(record) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid audit log"):
        append_event(log, {"action": "another_event"})


def test_empty_log_can_receive_first_event(tmp_path):
    log = tmp_path / "audit.jsonl"
    log.write_text("", encoding="utf-8")

    append_event(log, {"action": "started"})

    result = verify_chain(log)
    assert result["valid"] is True
    assert result["records_checked"] == 1
