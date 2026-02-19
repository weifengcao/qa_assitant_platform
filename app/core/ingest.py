import os
import glob
from typing import Dict, Any, List

def _chunk_text(text: str, chunk_words: int = 180, overlap_words: int = 30) -> List[str]:
    words = text.split()
    if not words:
        return []
    step = max(chunk_words - overlap_words, 1)
    chunks: List[str] = []
    for start in range(0, len(words), step):
        end = start + chunk_words
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(words):
            break
    return chunks


def load_docs_from_globs(data_dir: str, org_id: str, pack_id: str, globs: List[str]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    base = os.path.join(data_dir, org_id, pack_id)
    for pattern in globs:
        paths = sorted(glob.glob(os.path.join(base, pattern), recursive=True))
        for path in paths:
            if os.path.isdir(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            title = os.path.basename(path)
            rel_path = os.path.relpath(path, base)
            url = f"data/{org_id}/{pack_id}/{rel_path}"
            chunks = _chunk_text(text)
            if not chunks:
                continue

            for idx, chunk in enumerate(chunks):
                chunk_title = title if len(chunks) == 1 else f"{title} (part {idx + 1})"
                docs.append(
                    {
                        "org_id": org_id,
                        "pack_id": pack_id,
                        "title": chunk_title,
                        "url": url,
                        "source": f"{pack_id} docs",
                        "text": chunk,
                        "chunk_index": idx,
                        "chunk_total": len(chunks),
                    }
                )
    return docs
