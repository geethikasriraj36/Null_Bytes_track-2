"""H5: ANSWER / ANSWER-PRUNED / ABSTAIN from the H2 (and optional H3) results."""
from aegis.contracts import Verdict
from aegis.output.refusal import ABSTAIN

def decide(checked: list[dict]) -> tuple[str, Verdict]:
    good = [c["sentence"] for c in checked if c["supported"]]
    if not good:
        return ABSTAIN, Verdict(layer="H5", decision="abstain", score=1.0)
    if len(good) < len(checked):
        return " ".join(good), Verdict(layer="H5", decision="prune", score=1 - len(good) / len(checked),
                                       details={"dropped": len(checked) - len(good)})
    return " ".join(good), Verdict(layer="H5", decision="pass")
