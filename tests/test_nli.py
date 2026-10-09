from aegis.contracts import ContentItem
from aegis.output.nli import check


class FakeModel:
    """Returns logits in contradiction, entailment, neutral order."""
    def __init__(self, prediction):
        self.prediction = prediction

    def predict(self, pairs):
        return [self.prediction for _ in pairs]


def test_entailed_sentence_passes():
    passage = ContentItem(
        id="p_12345678",
        text="The device weighs 10 kg.",
        source="doc",
    )
    checked = [{
        "sentence": "The device weighs 10 kg. [p_12345678]",
        "ids": ["p_12345678"],
        "supported": True,
        "missing": [],
    }]
    result = check(
        checked, {passage.id: passage},
        model=FakeModel([-2.0, 4.0, -1.0]),
    )
    assert result[0]["supported"] is True
    assert result[0]["nli_label"] == "entailment"


def test_contradiction_is_rejected():
    passage = ContentItem(
        id="p_12345678",
        text="The device weighs 10 kg.",
        source="doc",
    )
    checked = [{
        "sentence": "The device weighs 20 kg. [p_12345678]",
        "ids": ["p_12345678"],
        "supported": True,
        "missing": [],
    }]
    result = check(
        checked, {passage.id: passage},
        model=FakeModel([4.0, -2.0, -1.0]),
    )
    assert result[0]["supported"] is False
    assert result[0]["nli_label"] == "contradiction"


def test_h2_failure_cannot_be_overridden():
    passage = ContentItem(
        id="p_12345678",
        text="The device weighs 10 kg.",
        source="doc",
    )
    checked = [{
        "sentence": "The device weighs 20 kg.",
        "ids": [],
        "supported": False,
        "missing": ["20"],
    }]
    result = check(
        checked, {passage.id: passage},
        model=FakeModel([-2.0, 4.0, -1.0]),
    )
    assert result[0]["supported"] is False
    assert result[0]["nli_label"] == "not_checked"


def test_missing_citation_is_rejected():
    checked = [{
        "sentence": "An unsupported claim.",
        "ids": ["p_87654321"],
        "supported": True,
        "missing": [],
    }]
    result = check(
        checked, {},
        model=FakeModel([-2.0, 4.0, -1.0]),
    )
    assert result[0]["supported"] is False


def test_invalid_threshold_is_rejected():
    try:
        check([], {}, model=FakeModel([-2.0, 4.0, -1.0]), threshold=1.0)
    except ValueError:
        return
    raise AssertionError("Expected invalid threshold to raise ValueError")
