# Null_Bytes_track-2
hackathon repo

## Aegis

A defense-in-depth security layer for a tool-using LLM agent, with a quantum-kernel injection detector (Q-Gate).
*The model can be fooled, but it cannot act on it.*

### Setup (once per laptop; keep the repo at a short path on Windows, e.g. `C:\aegis`)

    python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env                                     # add your own GROQ_API_KEY (console.groq.com)
    python -m scripts.setup_data                             # fake company DB + secret file
    pytest -q                                                # all tests, no API calls

### Q-Gate (no API calls)

    python -m scripts.build_qgate_data                       # deepset/prompt-injections + our docs -> data/qgate_*.jsonl
    python -m scripts.tune_qgate                             # same C grid, same folds, train split only, both models
    python -m scripts.train_qgate                            # -> models/qgate.pkl, models/rbf.pkl
    python -m scripts.eval_qgate                             # E1/E2 -> results/qgate_e1_e2.json
    python -m scripts.qgate_figures                          # slide figures -> results/qgate_circuit.png, qgate_e1.png

### Demo UI (web app: ChatGPT-style sidebar, model picker = ablation switch, stats for nerds)

    python -m web.server                                     # http://localhost:8000
    AEGIS_PORT=8100 python -m web.server                     # another port
    AEGIS_MODEL=mock AEGIS_JUDGE_MODEL=mock python -m web.server   # OFFLINE backup, no API (labelled in the UI)
    python -m scripts.check_e2e                              # guide section 9 checklist, ~10 LLM calls
    python -m scripts.verify_audit logs/audit.jsonl          # tamper check
    # Windows cmd: `set AEGIS_MODEL=mock` etc. on separate lines first. Strings to paste: demo_inputs.txt

Use the model picker to switch between "Aegis · Full protection" and "Baseline · no protection" (each opens a new chat).
The offline model is a scripted stand-in that reproduces the behaviour measured live on gpt-oss-120b; never use it for results.
The old Chainlit UI still works: `chainlit run app.py`.

### Evaluation

    python -m sim.build_cases                                # regenerates sim/cases/aegis_suite.jsonl
    python -m eval.run --configs 0_baseline 1_line1 7_full --workers 2   # real pipeline + LLM
    python -m eval.run --mode policy                         # M4 keyword prototype only, no API
    python -m scripts.plot_results                           # charts from results/summary.csv

Free-tier note: Groq allows ~200k tokens/day per model; one full config over all cases needs ~1M+.
Run the ablation with a paid key (Groq Dev tier costs a few dollars for the whole run) or split it across teammates' keys.

### Where things are

| Path | Owner | What |
| --- | --- | --- |
| `aegis/pipeline.py`, `llm.py`, `inputguard/`, `grounding/`, `app.py` | M1 | agent loop, J1-J5, UI |
| `aegis/tools/`, `line1/`, `toolsafety/`, `policy/` | M2 | simulated tools, taint, gate, A3 |
| `aegis/qgate/`, `ingress/` | M3 | Q-Gate, RBF twin, ingress scanning |
| `aegis/adapters.py` | M1 | M3 modules behind the frozen contract |
| `aegis/audit/`, `output/`, `decide.py`, `eval/`, `sim/` | M4 | audit chain, H2/H3/H5, eval, cases |
| `docs/M1_notes.md` | M1 | thresholds, integration log, slide drafts |

`.env` is loaded automatically (`aegis/__init__.py`). Never commit it.
