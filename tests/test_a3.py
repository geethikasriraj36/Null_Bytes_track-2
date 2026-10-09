
import json

from aegis.tools import sim


def test_note_trust_metadata_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(sim, "DATA", tmp_path)

    sim.write_note("Clean note", "Ordinary meeting notes")

    saved = json.loads((tmp_path / "notes.jsonl").read_text().splitlines()[0])

    assert saved["title"] == "Clean note"
    assert saved["body"] == "Ordinary meeting notes"
    assert saved["trust"] == "trusted"


def test_note_written_in_tainted_context_is_untrusted(tmp_path, monkeypatch):
    monkeypatch.setattr(sim, "DATA", tmp_path)

    ctx = {"docs": {}, "outbox": [], "executed": [], "seen_tainted": True}
    token = sim.CTX.set(ctx)
    try:
        sim.write_note("Review", "Content derived from untrusted material")
    finally:
        sim.CTX.reset(token)

    saved = json.loads((tmp_path / "notes.jsonl").read_text().splitlines()[0])

    assert saved["trust"] == "untrusted"



def test_untrusted_note_read_preserves_its_label(tmp_path, monkeypatch):
    monkeypatch.setattr(sim, "DATA", tmp_path)

    files = tmp_path / "files"
    files.mkdir()

    note = {
        "title": "Review",
        "body": "Instructions received from a vendor",
        "trust": "untrusted",
    }

    (files / "notes.jsonl").write_text(
        json.dumps(note) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sim, "FILES", files)

    result = sim.read_file("notes.jsonl")

    assert len(result) == 1
    saved = json.loads(result[0]["text"])
    assert saved["title"] == "Review"
    assert saved["trust"] == "untrusted"
