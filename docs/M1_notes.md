# M1 notes: agent core, language guards, integration

Owner: M1. Files: `aegis/llm.py`, `pipeline.py`, `contracts.py`, `config.py`, `inputguard/`, `grounding/`, `output/refusal.py`, `app.py`, `tests/test_m1.py`, `scripts/m1_handtest.py`, `demo_inputs.txt`.

## Status

| Item | State |
| --- | --- |
| `contracts.py` | Unchanged from starter, ready to freeze at hour 2 |
| `llm.chat` / `llm.judge` | Done. Judge fails closed on bad JSON **and** on API errors/timeouts |
| J1 normalize | Done: zero-width, NFKC, Cyrillic/Greek homoglyphs, base64 (padded, unpadded, url-safe), hex, rot13, leetspeak |
| J1 classify | Done. Thresholds below |
| J3 risk | Starter logic kept (decay 0.7, strict 0.8, end 1.6); tested |
| J4 output moderation | Done. Refused text is not kept in chat history |
| J2 / H1 prompt | Hardened; `wrap()` neutralises `<untrusted>` tags inside content |
| J5 refusal | Starter template kept |
| `pipeline.run_turn` / `resume` | Never raise (fail closed); history auto-repaired; pending CONFIRM auto-denied if user moves on |
| `app.py` | Layer panel as a table with plain-English names; banner shows BASELINE vs Aegis ON and config |
| Tests | `pytest -q`: 34 pass (13 starter + 21 M1), no API calls |
| Needs API key | `scripts/m1_handtest.py` (real judge), hour-1 LLM call, live UI test |

## J1 thresholds and why

| Signal | Score | Decision |
| --- | --- | --- |
| No regex hit, judge says safe | 0.0 | pass |
| One distinct regex pattern (plain text) | 0.45 | flag (feeds J3; answer still goes through) |
| Two distinct patterns, or one pattern visible only after decoding (base64/hex/rot13/leet/homoglyph) | 0.90 | refuse |
| Judge says jailbreak/harmful | judge score | refuse at ≥ 0.8, flag at ≥ 0.4 |
| Judge returns garbage or API fails | 1.0 | refuse (fail closed) |

- **Same phrase in several views counts once.** The starter counted "pretend you are" in the normalized and leet views as two hits → instant refuse of "Pretend you are a pirate…". Fixed: hits are distinct patterns.
- **Obfuscation counts double.** Hiding an instruction in base64 is itself a signal, so the base64 demo jailbreak refuses even if the judge is fooled.
- **Judge `score` now has one meaning:** probability the text is unsafe. The starter prompt left it ambiguous (a judge could return `{"label":"safe","score":0.95}` meaning "95% sure it's safe").
- Offline check with the judge forced to "safe" (worst case): 8/10 jailbreaks refused by regex alone, 0/10 borderline over-refused. The 2 misses ("grandma reads the system prompt", "hypothetically if you had no rules…") are semantic, so they're left to the judge rather than overfitting regex.
- **To do with the real key:** `python -m scripts.m1_handtest`. Target: 10/10 JB refused, 0 borderline refused. If borderline gets refused, fix `INPUT_PROMPT` first, thresholds last.

## Pipeline fixes vs starter

1. `run_turn`/`resume` wrap everything: a missing `models/qgate.pkl`, a crashing layer, anything → "temporarily unavailable" + `PIPELINE` verdict + `pipeline_error` audit event. Never a stack trace.
2. After an exception mid-tool, unanswered `tool_call` ids get a `role: tool` reply, so the next turn doesn't 400.
3. New message while a CONFIRM is pending → that call is denied and replied to (same reason).
4. `resume()` with nothing pending returns a message instead of crashing.
5. J4-refused or redacted text is not stored in `state.messages`; history holds what the user saw.
6. Input is audited even when J is off (baseline configs), so every config has an `input` record.

## Handoffs

- **Gives:** `contracts.py`, `config.CFG`, `llm.judge()` (M4 eval), `classify.heuristic_score(views, plain=None)` (M3 E2; signature is backward compatible), `pipeline.run_turn/resume`, `UNAVAILABLE` string.
- **Needs:** M3 `models/qgate.pkl` (until then run with `QGATE: false` or the turn fails closed); M2/M4 nothing new beyond the starter interfaces.

## Running

```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # fill AEGIS_MODEL + the provider key
python -m scripts.setup_data
pytest -q
python -c "from aegis import llm; print(llm.chat([{'role':'user','content':'hi'}]).content)"
python -m scripts.m1_handtest
set AEGIS_CONFIG=configs/0_baseline.yaml && chainlit run app.py -w --port 8001
set AEGIS_CONFIG=configs/7_full.yaml && chainlit run app.py -w
```

Keep the repo at a short path on Windows (e.g. `C:\aegis`): `grpc` (pulled in by Chainlit) fails to load its DLL from very deep folders.

## Slides 2-5 drafts (M1 builds and presents)

**2. Agents can be hijacked** (0:40). Visual: screenshot of the baseline tab + `outbox.jsonl` line to `audit@evil-corp.io`.
Say: "We gave a normal agent a vendor update. Hidden in it is one sentence for the AI. Watch where the customer list goes." → "This isn't one bug; it's five classes of failure."

**3. Five threats, one agent** (0:30). Six icons: Jailbreak (user attacks the rules) · Prompt injection (content attacks the agent) · Data leakage · Unsafe tool use · No audit trail · Hallucination (bonus).

**4. Our approach** (0:30, slow down). Two columns. *Probabilistic, advise:* J1/J4 classifiers, Q-Gate, J3 risk. *Deterministic, decide:* Line 1 taint + pinning, Tool Safety Gate, egress allowlist, HMAC token.
Say: "Classifiers raise suspicion but are never the last line. Every action passes a gate that doesn't care what the model believes."

**5. Architecture** (0:40). Section 3 diagram. Walk once top to bottom: input guard → agent loop → gate → tools → ingress + Q-Gate → output checker → audit.

## Q&A rows M1 owns (two sentences, then stop)

- *What if the classifier misses?* The model may say something bad (J4 is the second chance), but it still can't act: every tool call goes through the deterministic gate.
- *Why not a better system prompt?* We use one (J2 + spotlighting), but prompts are suggestions to the model; cite config 4 vs 6 from `summary.csv` once the ablation has run (not measured yet).
- *Multi-turn attacks?* J3 keeps a decaying risk score; suspicious turns add up to strict mode (tier-2 tools need confirmation) and then end the session.
- *What if a component fails?* We fail closed: any exception returns a safe message, a judge that returns garbage counts as unsafe, and the chat history is repaired so the next turn works.

## Integration log

- **M4 (Vinith)**: `chain.log()/text_hash()/LOG` wrap his `append_event()`. `eval/run.py` runs cases through `pipeline.run_turn` (default) or his keyword policy (`--mode policy`). H3 falls back to H2 if the NLI model is missing.
- **M3 (Krishna)**: his `aegis/ingress/*` and `aegis/qgate/*` are used as written; `aegis/adapters.py` maps them to the section-10 contract:
  - `process()` uses M3's role ACL (permissions `secret` -> admin, `internal` -> agent, else user) and returns `contracts.ContentItem` + verdicts.
  - `scan()` uses M3's detectors but does not redact emails (A2/D4 must see addresses), returns `(text, types)`.
  - `canary_hit()` checks M3's canaries **plus** the system-prompt canary and `sk-canary-0000DEADBEEF`.
  - `load_qgate()/load_rbf()` wrap his models; per-sentence max score, REVIEW 0.5 / QUARANTINE 0.8.
  - `scripts/train_qgate.py` trains RBF on Q-Gate's own embedder features (fair E1).
- Ask M3: add the system-prompt canary to `scan.CANARIES`, an Aadhaar pattern, and branch from `main` next time.
