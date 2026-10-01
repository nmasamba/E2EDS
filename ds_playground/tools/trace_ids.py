"""List which suite IDs in a sprint's scope appear in a test or an evidence record."""

import re
import sys
from pathlib import Path

PREFIX = r"(?:ADR|[ACDR])"


def scope(prompts: str, sprint: int) -> set[str]:
    """Return the acceptance, requirement, default, decision and control IDs in a sprint heading."""
    heading = re.search(rf"^## Sprint {sprint} — .*$", prompts, re.MULTILINE)
    if not heading:
        raise SystemExit(f"no Sprint {sprint} heading in prompts.md")
    line = heading.group()
    ids = set(re.findall(rf"\b{PREFIX}\d{{2}}\b", line))
    for prefix, low, high in re.findall(rf"\b({PREFIX})(\d{{2}})–{PREFIX}?(\d{{2}})\b", line):
        ids |= {f"{prefix}{n:02d}" for n in range(int(low), int(high) + 1)}
    return ids


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    wanted = scope((root / "prompts.md").read_text(), int(sys.argv[1]))
    files = [p for d in ("tests", "docs/evidence") for p in (root / d).rglob("*") if p.is_file()]
    text = "".join(p.read_text() for p in files if p.suffix in {".py", ".json"})
    for ident in sorted(wanted):
        print(ident, "covered" if re.search(rf"\b{ident}\b", text) else "MISSING")
