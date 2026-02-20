from app.core.chunking import chunk_markdown


def test_empty_input_returns_no_chunks() -> None:
    result = chunk_markdown("")
    assert result == []


def test_whitespace_only_returns_no_chunks() -> None:
    result = chunk_markdown("   \n\n  ")
    assert result == []


def test_short_text_is_single_chunk() -> None:
    text = "Hello world, this is a short test document."
    result = chunk_markdown(text)
    assert len(result) == 1
    assert result[0].text == text.strip()
    assert result[0].chunk_index == 0
    assert result[0].chunk_total == 1


def test_heading_preserved_as_section_heading() -> None:
    text = "## Installation\n\nRun pip install mypackage to get started."
    result = chunk_markdown(text)
    assert len(result) == 1
    assert result[0].section_heading == "Installation"
    assert "pip install" in result[0].text


def test_multiple_sections_produce_separate_chunks() -> None:
    text = (
        "## Section A\n\nContent for section A.\n\n"
        "## Section B\n\nContent for section B."
    )
    result = chunk_markdown(text)
    headings = [c.section_heading for c in result]
    assert "Section A" in headings
    assert "Section B" in headings


def test_chunk_index_and_total_are_consistent() -> None:
    # Build a text large enough to produce multiple chunks.
    big_text = "## Big Section\n\n" + ("word " * 2000)
    result = chunk_markdown(big_text, chunk_size_chars=500, overlap_chars=50)
    assert len(result) > 1
    for idx, chunk in enumerate(result):
        assert chunk.chunk_index == idx
        assert chunk.chunk_total == len(result)


def test_h1_and_h3_headings_are_captured() -> None:
    text = "# Top\n\nIntro text.\n\n### Sub\n\nSub text."
    result = chunk_markdown(text)
    headings = {c.section_heading for c in result}
    assert "Top" in headings
    assert "Sub" in headings


def test_no_heading_section_uses_none() -> None:
    text = "Just some content without any markdown headings."
    result = chunk_markdown(text)
    assert len(result) >= 1
    assert result[0].section_heading is None
