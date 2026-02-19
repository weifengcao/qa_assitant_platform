from app.core.policy import PolicyEngine


def test_deny_patterns_support_phrase_and_regex() -> None:
    engine = PolicyEngine(
        {
            "deny_patterns": ["list all ids", "re:dump\\s+db"],
            "roles": {},
            "redaction": {},
        }
    )

    assert engine.is_denied("Please LIST   all   ids")
    assert engine.is_denied("Can you dump db now?")
    assert not engine.is_denied("Show aggregate usage counts")


def test_match_pattern_supports_exact_and_wildcards() -> None:
    patterns = ["sample.stats.*", "admin.read"]

    assert PolicyEngine.match_pattern("sample.stats.request_volume_24h", patterns)
    assert PolicyEngine.match_pattern("admin.read", patterns)
    assert not PolicyEngine.match_pattern("sample.tools.write", patterns)
