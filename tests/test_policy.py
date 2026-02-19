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


def test_filter_allowed_packs_and_tools() -> None:
    engine = PolicyEngine(
        {
            "roles": {
                "Viewer": {
                    "allowed_packs": ["sample.*"],
                    "allowed_tools": ["sample.stats.*"],
                }
            }
        }
    )

    packs = engine.filter_allowed_packs(["sample_service", "admin_console"], roles=["Viewer"])
    tools = engine.filter_allowed_tools(
        ["sample.stats.request_volume_24h", "sample.tools.write"],
        roles=["Viewer"],
    )

    assert packs == ["sample_service"]
    assert tools == ["sample.stats.request_volume_24h"]
