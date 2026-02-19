from pathlib import Path

from app.core.ingest import load_docs_from_globs


def test_ingest_populates_required_chunk_metadata(tmp_path: Path) -> None:
    doc_dir = tmp_path / "data" / "demo" / "sample_service" / "howto"
    doc_dir.mkdir(parents=True, exist_ok=True)
    doc_path = doc_dir / "guide.md"
    doc_path.write_text("# Rotate Key\nStep 1\nStep 2\n", encoding="utf-8")

    docs = load_docs_from_globs(
        data_dir=str(tmp_path / "data"),
        org_id="demo",
        pack_id="sample_service",
        globs=["howto/**/*.md"],
    )

    assert docs
    item = docs[0]
    assert item["org_id"] == "demo"
    assert item["pack_id"] == "sample_service"
    assert item["title"] == "guide.md"
    assert item["url"].endswith("data/demo/sample_service/howto/guide.md")
    assert item["source"] == "sample_service docs"
    assert item["section_heading"] == "Rotate Key"
    assert item["updated_at"]
