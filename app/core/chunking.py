import re
from dataclasses import dataclass
from typing import Dict, List, Optional


_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


@dataclass(frozen=True)
class TextChunk:
    text: str
    section_heading: Optional[str]
    chunk_index: int
    chunk_total: int


def _split_markdown_sections(markdown_text: str) -> List[Dict[str, Optional[str]]]:
    sections: List[Dict[str, Optional[str]]] = []
    current_heading: Optional[str] = None
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_lines
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({"heading": current_heading, "content": content})
        current_lines = []

    for line in markdown_text.splitlines():
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            flush()
            current_heading = heading_match.group(2).strip()
            continue
        current_lines.append(line)
    flush()

    if not sections and markdown_text.strip():
        sections.append({"heading": None, "content": markdown_text.strip()})
    return sections


def _chunk_text(content: str, chunk_size_chars: int, overlap_chars: int) -> List[str]:
    if not content.strip():
        return []

    step = max(chunk_size_chars - overlap_chars, 1)
    out: List[str] = []
    start = 0
    while start < len(content):
        end = start + chunk_size_chars
        piece = content[start:end].strip()
        if piece:
            out.append(piece)
        if end >= len(content):
            break
        start += step
    return out


def chunk_markdown(
    markdown_text: str,
    chunk_size_chars: int = 4200,
    overlap_chars: int = 700,
) -> List[TextChunk]:
    sections = _split_markdown_sections(markdown_text)
    chunks: List[TextChunk] = []
    for section in sections:
        section_heading = section.get("heading")
        content = section.get("content") or ""
        for piece in _chunk_text(
            content=content,
            chunk_size_chars=chunk_size_chars,
            overlap_chars=overlap_chars,
        ):
            chunks.append(
                TextChunk(
                    text=piece,
                    section_heading=section_heading,
                    chunk_index=0,
                    chunk_total=0,
                )
            )

    total = len(chunks)
    return [
        TextChunk(
            text=chunk.text,
            section_heading=chunk.section_heading,
            chunk_index=idx,
            chunk_total=total,
        )
        for idx, chunk in enumerate(chunks)
    ]
