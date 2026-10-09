
from aegis.ingress.process import process
from aegis.ingress.scan import CANARIES


def test_public_content_accessible_to_user():
    item = process(
        "Public information.",
        source="web",
        label="public",
        user_role="user",
    )

    assert item.accessible
    assert item.text == "Public information."


def test_confidential_content_denied_to_user():
    item = process(
        "Confidential project details.",
        source="internal_db",
        label="confidential",
        user_role="user",
    )

    assert not item.accessible
    assert item.text == "[ACCESS DENIED]"
    assert item.metadata["access_denied"] is True


def test_secret_is_redacted():
    item = process(
        "My key is AKIAIOSFODNN7EXAMPLE",
        source="tool_output",
        label="internal",
        user_role="agent",
    )

    assert "AKIAIOSFODNN7EXAMPLE" not in item.text
    assert item.metadata["redacted"] is True


def test_canary_detected_before_redaction():
    token = next(iter(CANARIES))

    item = process(
        f"Leaked token: {token}",
        source="tool_output",
        label="internal",
        user_role="agent",
    )

    assert token in item.canary_hits
    assert token not in item.text


def test_provenance_and_taint_attached():
    item = process(
        "Fetched page contents.",
        source="browser",
        label="public",
        user_role="agent",
    )

    assert item.source == "browser"
    assert item.tainted
    assert item.metadata["source"] == "browser"
    assert item.metadata["tainted"] is True


def test_custom_acl_overrides_default():
    item = process(
        "Team-only data.",
        source="document",
        label="internal",
        user_role="user",
        allowed_roles=["user", "admin"],
    )

    assert item.accessible