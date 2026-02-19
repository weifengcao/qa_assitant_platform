from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal

DocSourceType = Literal["filesystem", "url_list"]


@dataclass(frozen=True)
class DocSource:
    org_id: str
    pack_id: str
    type: DocSourceType
    config: Dict[str, Any] = field(default_factory=dict)


def filesystem_source(org_id: str, pack_id: str, base_path: str, globs: List[str]) -> DocSource:
    return DocSource(
        org_id=org_id,
        pack_id=pack_id,
        type="filesystem",
        config={"base_path": base_path, "globs": globs},
    )


def url_list_source(org_id: str, pack_id: str, urls: List[str]) -> DocSource:
    return DocSource(
        org_id=org_id,
        pack_id=pack_id,
        type="url_list",
        config={"urls": urls},
    )
