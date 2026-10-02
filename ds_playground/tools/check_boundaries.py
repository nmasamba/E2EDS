"""Fail when a module under src/dsp imports across a forbidden layer boundary (AGENTS.md §4)."""

import ast
import sys
from pathlib import Path

ALLOWED = {
    "contracts": {"contracts"},
    "domain": {"contracts", "domain"},
    "ports": {"contracts", "domain", "ports"},
    "application": {"contracts", "domain", "ports", "application"},
    "adapters": {"contracts", "domain", "ports", "adapters"},
}
SUBPROCESS_OK = {"adapters", "harness"}


def violations(src: Path) -> list[str]:
    """Return one line per forbidden import found under ``src/dsp``."""
    found = []
    for path in sorted((src / "dsp").rglob("*.py")):
        layer = path.relative_to(src / "dsp").with_suffix("").parts[0]
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
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
                    found.append(f"{path}:{node.lineno}: {layer} may not import {name}")
    return found


if __name__ == "__main__":
    problems = violations(Path(__file__).parent.parent / "src")
    print("\n".join(problems) or "boundaries ok")
    sys.exit(1 if problems else 0)
