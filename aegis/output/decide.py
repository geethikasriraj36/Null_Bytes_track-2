
"""H5: ANSWER / ANSWER-PRUNED / ABSTAIN from H2 and optional H3."""
from aegis.contracts import Verdict
from aegis.output.refusal import ABSTAIN


def decide(
    checked: list[dict],
    require_h3: bool = False,
) -> tuple[str, Verdict]:
    """Return only supported sentences.

    When require_h3=True, a sentence must pass both H2 and H3.
    H3 failures and unchecked H3 results are not accepted.
    """
    good = []

    for item in checked:
        if not item.get("supported", False):
            continue

        if require_h3 and (
            item.get("nli_label") != "entailment"
            or item.get("nli_entailment", 0.0) < 0.65
        ):
            continue

        good.append(item["sentence"])

    if not good:
        return ABSTAIN, Verdict(
            layer="H5",
            decision="abstain",
            score=1.0,
            details={"require_h3": require_h3},
        )

    if len(good) < len(checked):
        dropped = len(checked) - len(good)
        return " ".join(good), Verdict(
            layer="H5",
            decision="prune",
            score=dropped / len(checked),
            details={"dropped": dropped, "require_h3": require_h3},
        )

    return " ".join(good), Verdict(
        layer="H5",
        decision="pass",
        details={"require_h3": require_h3},
    )
