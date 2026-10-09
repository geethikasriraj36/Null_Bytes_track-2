
from aegis.ingress.scan import CANARIES, canary_hit, redact, scan


def test_detects_email():
    result = scan("Contact user@example.com for details.")
    assert any(item["type"] == "email" for item in result["matches"])


def test_redacts_aws_key():
    text = "Key: AKIAIOSFODNN7EXAMPLE"
    cleaned = redact(text)

    assert "AKIAIOSFODNN7EXAMPLE" not in cleaned
    assert "[REDACTED]" in cleaned


def test_detects_canary():
    token = next(iter(CANARIES))

    assert token in canary_hit(f"Leaked token: {token}")


def test_redacts_valid_luhn_card():
    # Synthetic test number; do not use real payment data.
    text = "Card number: 4111 1111 1111 1111"
    cleaned = redact(text)

    assert "4111 1111 1111 1111" not in cleaned


def test_preserves_invalid_luhn_number():
    text = "Reference number: 4111 1111 1111 1112"

    assert redact(text) == text


def test_benign_text_unchanged():
    text = "Please summarize the quarterly sales report."

    assert redact(text) == text