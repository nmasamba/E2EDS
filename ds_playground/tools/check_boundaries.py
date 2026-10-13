"""Fail when a module under src imports across a forbidden layer boundary (AGENTS.md §4)."""

import ast
import sys
from pathlib import Path

ALLOWED = {
    "contracts": {"contracts"},
    "domain": {"contracts", "domain"},
    "ports": {"contracts", "domain", "ports"},
    "application": {"contracts", "domain", "ports", "application"},
    "adapters": {"contracts", "domain", "ports", "adapters"},
    "dsp_runner": {"contracts"},
}
SUBPROCESS_OK = {"adapters", "harness"}


def violations(src: Path) -> list[str]:
    """Return one line per forbidden import found under ``src/dsp`` and ``src/dsp_runner``."""
    found = []
    for path in sorted([*(src / "dsp").rglob("*.py"), *(src / "dsp_runner").rglob("*.py")]):
        parts = path.relative_to(src).with_suffix("").parts
        layer = parts[0] if parts[0] == "dsp_runner" else parts[1]
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [f"{node.module or ''}.{alias.name}" for alias in node.names]
            else:
                continue
            for name in names:
                target = name.split(".")
                crosses = (
                    target[0] == "dsp"
                    and len(target) > 1
                    and layer in ALLOWED
                    and target[1] not in ALLOWED[layer]
                )
                if crosses or (target[0] == "subprocess" and layer not in SUBPROCESS_OK):
                    named = isinstance(node, ast.ImportFrom) and node.module != "dsp"
                    shown = name.rsplit(".", 1)[0] if named else name
                    found.append(f"{path}:{node.lineno}: {layer} may not import {shown}")
    return found


if __name__ == "__main__":
    problems = violations(Path(__file__).parent.parent / "src")
    print("\n".join(problems) or "boundaries ok")
    sys.exit(1 if problems else 0)
