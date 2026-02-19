import os
import glob
from typing import Dict, Any, List

def load_docs_from_globs(data_dir: str, org_id: str, pack_id: str, globs: List[str]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    base = os.path.join(data_dir, org_id, pack_id)
    for g in globs:
        for path in glob.glob(os.path.join(base, g), recursive=True):
            if os.path.isdir(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            title = os.path.basename(path)
            docs.append({
                "org_id": org_id,
                "pack_id": pack_id,
                "title": title,
                "url": f"file://{path}",
                "source": f"{pack_id} docs",
                "text": text,
            })
    return docs
