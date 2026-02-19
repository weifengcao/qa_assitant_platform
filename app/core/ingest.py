import glob
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.chunking import chunk_markdown
from app.core.docsources import DocSource, filesystem_source


def _to_iso_timestamp(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _load_from_filesystem_source(
    source: DocSource,
    chunk_size_chars: int,
    overlap_chars: int,
) -> List[Dict[str, Any]]:
    base_path = source.config.get("base_path", "")
    patterns = source.config.get("globs", []) or []

    docs: List[Dict[str, Any]] = []
    for pattern in patterns:
        matches = sorted(glob.glob(os.path.join(base_path, pattern), recursive=True))
        for path in matches:
            if os.path.isdir(path):
                continue

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            chunks = chunk_markdown(
                markdown_text=text,
                chunk_size_chars=chunk_size_chars,
                overlap_chars=overlap_chars,
            )
            if not chunks:
                continue

            rel_path = os.path.relpath(path, base_path)
            doc_title = os.path.basename(path)
            updated_at = _to_iso_timestamp(os.path.getmtime(path))
            url = f"data/{source.org_id}/{source.pack_id}/{rel_path}"
            doc_source = f"{source.pack_id} docs"

            for chunk in chunks:
                docs.append(
                    {
                        "org_id": source.org_id,
                        "pack_id": source.pack_id,
                        "title": doc_title,
                        "url": url,
                        "source": doc_source,
                        "section_heading": chunk.section_heading,
                        "updated_at": updated_at,
                        "chunk_index": chunk.chunk_index,
                        "chunk_total": chunk.chunk_total,
                        "text": chunk.text,
                    }
                )
    return docs


def load_docs_from_sources(
    sources: List[DocSource],
    chunk_size_chars: int = 4200,
    overlap_chars: int = 700,
) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for source in sources:
        if source.type == "filesystem":
            docs.extend(
                _load_from_filesystem_source(
                    source=source,
                    chunk_size_chars=chunk_size_chars,
                    overlap_chars=overlap_chars,
                )
            )
        elif source.type == "url_list":
            # M1 stub: URL loader is intentionally deferred.
            continue
    return docs


def load_docs_from_globs(
    data_dir: str,
    org_id: str,
    pack_id: str,
    globs: List[str],
    chunk_size_chars: int = 4200,
    overlap_chars: int = 700,
) -> List[Dict[str, Any]]:
    source = filesystem_source(
        org_id=org_id,
        pack_id=pack_id,
        base_path=os.path.join(data_dir, org_id, pack_id),
        globs=globs,
    )
    return load_docs_from_sources(
        sources=[source],
        chunk_size_chars=chunk_size_chars,
        overlap_chars=overlap_chars,
    )
