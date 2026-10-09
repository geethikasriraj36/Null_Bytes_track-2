
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
    monkeypatch.setattr(sim, "FILES", files)

    ctx = {"docs": {}, "outbox": [], "executed": [], "seen_tainted": True}
    ctx_token = sim.CTX.set(ctx)
    try:
        sim.write_note("Review", "Instructions received from a vendor")
    finally:
        sim.CTX.reset(ctx_token)

    saved_note = json.loads(
        (tmp_path / "notes.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    (files / "notes.jsonl").write_text(
        json.dumps(saved_note) + "\n",
        encoding="utf-8",
    )

    result = sim.read_file("notes.jsonl")

    assert len(result) == 1
    read_back = json.loads(result[0]["text"])
    assert read_back["title"] == "Review"
    assert read_back["body"] == "Instructions received from a vendor"
    assert read_back["trust"] == "untrusted"