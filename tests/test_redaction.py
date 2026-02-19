from app.core.redaction import apply_redaction


def test_redaction_masks_email_and_long_id() -> None:
    text = "Contact john.doe@example.com with token 1234567890abcdef1234567890abcdef"
    out = apply_redaction(
        text,
        {"mask_emails": True, "mask_long_ids": True},
    )

    assert "jo***@example.com" in out
    assert "1234...cdef" in out


def test_redaction_suppresses_small_counts() -> None:
    text = "errors=2 warnings=11 total=1"
    out = apply_redaction(
        text,
        {"mask_emails": False, "mask_long_ids": False, "suppress_small_counts": 10},
    )

    assert "errors=<10" in out
    assert "warnings=11" in out
    assert "total=<10" in out
