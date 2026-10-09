# Null_Bytes_track-2
hackathon repo

## Aegis

Tested skeleton for the Aegis hackathon guide. Every module runs; the LLM is the only external dependency.

    python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env                                     # add your API key and model
    python -m scripts.setup_data
    pytest -q                                                # deterministic tests, no API calls
    python -m scripts.build_qgate_data && python -m scripts.train_qgate
    python -m scripts.eval_qgate                             # E1/E2 quantum results, no API calls
    chainlit run app.py -w                                   # the demo UI
    python -m eval.run --configs 0_baseline 7_full --limit 8 # M4 eval (prototype policy for now, no API)
    python -m scripts.verify_audit logs/audit.jsonl              # app audit log (eval writes results/audit.jsonl)

Load .env automatically: `from dotenv import load_dotenv; load_dotenv()` is called in aegis/__init__.py.
