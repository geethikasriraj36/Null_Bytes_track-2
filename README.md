# Aegis starter

Tested skeleton for the Aegis hackathon guide. Every module runs; the LLM is the only external dependency.

    python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env                                     # add your API key and model
    python -m scripts.setup_data
    pytest -q                                                # 13 deterministic tests, no API calls
    python -m scripts.build_qgate_data && python -m scripts.train_qgate
    python -m scripts.eval_qgate                             # E1/E2 quantum results, no API calls
    chainlit run app.py -w                                   # the demo UI
    python -m eval.run --configs 0_baseline 7_full --limit 8 # ablation smoke test (uses the API)
    python -m scripts.verify_audit

Load .env automatically: `from dotenv import load_dotenv; load_dotenv()` is called in aegis/__init__.py.
