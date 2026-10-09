"""H3: Natural Language Inference support checker."""
from __future__ import annotations

import math

MODEL_NAME = "cross-encoder/nli-deberta-v3-small"
DEFAULT_THRESHOLD = 0.65


def load_model():
    """Load the local NLI model; first use may download model weights."""
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "Install H3 dependencies with: "
            "python -m pip install sentence-transformers"
        ) from exc

    try:
        return CrossEncoder(MODEL_NAME)
    except Exception as exc:
        raise RuntimeError(f"Could not load NLI model {MODEL_NAME}") from exc


def _probabilities(scores):
    """Convert logits ordered as contradiction, entailment, neutral."""
    values = [float(x) for x in scores]
    if len(values) != 3:
        raise ValueError(f"Expected 3 NLI scores; received {len(values)}")
    peak = max(values)
    exps = [math.exp(x - peak) for x in values]
    total = sum(exps)
    return [x / total for x in exps]


def check(checked, passages, model=None, threshold=DEFAULT_THRESHOLD):
    """Combine H2 citation validation with semantic entailment checking."""
    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must be between 0 and 1")

    if model is None:
        model = load_model()

    results = []
    for item in checked:
        result = dict(item)
        h2_ok = bool(item.get("supported", False))
        result["h2_supported"] = h2_ok
        result["nli_label"] = "not_checked"
        result["nli_entailment"] = 0.0
        result["nli_contradiction"] = 0.0
        result["nli_neutral"] = 0.0
        result["supported"] = False

        ids = item.get("ids", [])
        valid_ids = list(dict.fromkeys(pid for pid in ids if pid in passages))
        if not h2_ok or not ids or len(valid_ids) != len(ids):
            results.append(result)
            continue

        pairs = [(passages[pid].text, item["sentence"]) for pid in valid_ids]
        predictions = model.predict(pairs)

        best = None
        for prediction in predictions:
            probs = _probabilities(prediction)
            if best is None or probs[1] > best[1]:
                best = probs

        contradiction, entailment, neutral = best
        if contradiction > entailment:
            label = "contradiction"
        elif entailment > neutral:
            label = "entailment"
        else:
            label = "neutral"

        result.update({
            "nli_label": label,
            "nli_entailment": entailment,
            "nli_contradiction": contradiction,
            "nli_neutral": neutral,
            "supported": label == "entailment" and entailment >= threshold,
        })
        results.append(result)

    return results
