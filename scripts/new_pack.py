#!/usr/bin/env python3
import argparse
from pathlib import Path

PACK_TEMPLATE = """from typing import List

from app.core.packs import ProductPack
from app.core.tools import ToolDef
from packs.{pack_id}.tools import sample_metric


class {class_name}(ProductPack):
    pack_id = "{pack_id}"
    display_name = "{display_name}"

    def keywords(self) -> List[str]:
        return ["{pack_id}"]

    def doc_globs(self) -> List[str]:
        return ["howto/**/*.md", "howto/**/*.txt"]

    def tools(self) -> List[ToolDef]:
        return [
            ToolDef(
                name="{pack_id}.stats.sample_metric",
                description="Sample metric tool for {display_name}.",
                schema={{
                    "type": "object",
                    "properties": {{
                        "timeframe": {{"type": "string"}},
                    }},
                    "additionalProperties": False,
                }},
                default_args={{"timeframe": "24h"}},
                keywords=["metric", "stats"],
                connector={{"type": "mock", "handler": sample_metric}},
            )
        ]
"""


TOOLS_TEMPLATE = """from datetime import datetime, timezone
from typing import Any, Dict


def sample_metric(args: Dict[str, Any]) -> Dict[str, Any]:
    timeframe = args.get("timeframe", "24h")
    now = datetime.now(timezone.utc).isoformat()
    value = 42
    return {{
        "data": {{"value": value, "timeframe": timeframe, "as_of": now}},
        "rendered": f"- Tool `{pack_id}.stats.sample_metric` returned **{{value}}** (timeframe: {{timeframe}}, as of {{now}})",
        "source": "{pack_id}_mock",
    }}
"""


DOC_TEMPLATE = """# {display_name} How-to

Use this folder for markdown runbooks and product docs.

Recommended structure:
- `howto/` for step-by-step operational guides
- `reference/` for static config and API details
"""


README_MARKER = "## Add a Pack"


def _camel_case(pack_id: str) -> str:
    return "".join(part.capitalize() for part in pack_id.replace("-", "_").split("_"))


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def _update_readme(readme_path: Path, pack_id: str, display_name: str) -> None:
    section = (
        f"\n{README_MARKER}\n"
        f"1. Generate scaffold:\n"
        f"   `python scripts/new_pack.py --pack_id {pack_id} --display_name \"{display_name}\"`\n"
        f"2. Register `packs/{pack_id}/pack.py` in `app/api.py`.\n"
        f"3. Add docs under `data/demo/{pack_id}/howto/`.\n"
        f"4. Add tool handlers in `packs/{pack_id}/tools.py`.\n"
    )
    if not readme_path.exists():
        return
    text = readme_path.read_text(encoding="utf-8")
    if README_MARKER not in text:
        readme_path.write_text(text.rstrip() + "\n" + section, encoding="utf-8")
        return

    generated_header = "### Generated Pack Entries"
    entry = (
        f"- `{pack_id}` ({display_name}): register `packs/{pack_id}/pack.py` in `app/api.py` "
        f"and add docs under `data/demo/{pack_id}/howto/`."
    )
    if entry in text:
        return

    if generated_header in text:
        readme_path.write_text(text.rstrip() + "\n" + entry + "\n", encoding="utf-8")
        return

    readme_path.write_text(text.rstrip() + f"\n\n{generated_header}\n{entry}\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new assistant pack.")
    parser.add_argument("--pack_id", required=True, help="Unique pack id, e.g. mypack")
    parser.add_argument("--display_name", required=True, help="Human-friendly pack name")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    pack_id = args.pack_id.strip()
    display_name = args.display_name.strip()
    class_name = f"{_camel_case(pack_id)}Pack"

    _write_file(
        repo_root / "packs" / pack_id / "__init__.py",
        "",
    )
    _write_file(
        repo_root / "packs" / pack_id / "pack.py",
        PACK_TEMPLATE.format(pack_id=pack_id, display_name=display_name, class_name=class_name),
    )
    _write_file(
        repo_root / "packs" / pack_id / "tools.py",
        TOOLS_TEMPLATE.format(pack_id=pack_id),
    )
    _write_file(
        repo_root / "data" / "demo" / pack_id / "howto" / "README.md",
        DOC_TEMPLATE.format(display_name=display_name),
    )
    _update_readme(repo_root / "README.md", pack_id=pack_id, display_name=display_name)

    print(f"Scaffolded pack '{pack_id}' at packs/{pack_id}")


if __name__ == "__main__":
    main()
