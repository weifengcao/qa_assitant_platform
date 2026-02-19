from app.core.doc_index import HybridDocIndex, InMemoryDocIndex


def test_hybrid_search_exposes_lexical_signal() -> None:
    index = HybridDocIndex(alpha=0.7)
    index.ingest(
        [
            {
                "org_id": "demo",
                "pack_id": "sample_service",
                "title": "rate_limits.md",
                "url": "data/demo/sample_service/howto/rate_limits.md",
                "source": "sample docs",
                "text": "Rate limits depend on API tier and can be increased.",
            },
            {
                "org_id": "demo",
                "pack_id": "sample_service",
                "title": "billing.md",
                "url": "data/demo/sample_service/howto/billing.md",
                "source": "sample docs",
                "text": "Billing cycles are monthly with annual discounts.",
            },
        ]
    )

    hits = index.search("rate limits", filters={"org_id": "demo", "pack_id": "sample_service"})

    assert hits
    assert any(hit["lexical_score"] > 0 for hit in hits)


def test_clear_with_filters_only_removes_target_slice() -> None:
    index = InMemoryDocIndex()
    index.ingest(
        [
            {
                "org_id": "demo",
                "pack_id": "sample_service",
                "title": "a",
                "url": "a",
                "source": "s",
                "text": "one",
            },
            {
                "org_id": "demo",
                "pack_id": "other_pack",
                "title": "b",
                "url": "b",
                "source": "s",
                "text": "two",
            },
        ]
    )

    removed = index.clear(filters={"org_id": "demo", "pack_id": "sample_service"})

    assert removed == 1
    assert index.count(filters={"org_id": "demo", "pack_id": "sample_service"}) == 0
    assert index.count(filters={"org_id": "demo", "pack_id": "other_pack"}) == 1


def test_vector_only_index_returns_scores() -> None:
    index = InMemoryDocIndex()
    index.ingest(
        [
            {
                "org_id": "demo",
                "pack_id": "sample_service",
                "title": "a",
                "url": "a",
                "source": "s",
                "text": "rotate api key safely",
            }
        ]
    )

    hits = index.search("rotate api key", filters={"org_id": "demo"}, top_k=1)

    assert hits
    assert "vector_score" in hits[0]
