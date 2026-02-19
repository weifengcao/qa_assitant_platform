from typing import Dict, Any, List, Optional
from app.core.policy import PolicyEngine

class ProductPack:
    pack_id: str
    display_name: str

    def keywords(self) -> List[str]:
        return []

    def doc_globs(self) -> List[str]:
        """Relative globs under data/<org>/<pack>/ for ingestion."""
        return []

    def tools(self) -> List[Dict[str, Any]]:
        return []

class PackRegistry:
    def __init__(self):
        self._packs: Dict[str, ProductPack] = {}

    def register(self, pack: ProductPack) -> None:
        self._packs[pack.pack_id] = pack

    def get(self, pack_id: str) -> Optional[ProductPack]:
        return self._packs.get(pack_id)

    def list(self) -> List[ProductPack]:
        return list(self._packs.values())

    def route(self, message: str, pack_hint: Optional[str] = None) -> List[ProductPack]:
        if pack_hint and pack_hint in self._packs:
            return [self._packs[pack_hint]]
        m = message.lower()
        matches = [p for p in self._packs.values() if any(k in m for k in p.keywords())]
        return matches or list(self._packs.values())

    def catalog(self) -> List[Dict[str, Any]]:
        out = []
        for p in self._packs.values():
            out.append({
                "pack_id": p.pack_id,
                "display_name": p.display_name,
                "keywords": p.keywords(),
                "tools": [t.get("name") for t in p.tools()],
            })
        return out

def filter_packs_for_user(packs: List[ProductPack], policy: PolicyEngine, roles: List[str]) -> List[ProductPack]:
    allowed = policy.allowed_packs(roles)
    return [p for p in packs if PolicyEngine.match_pattern(p.pack_id, allowed)]
