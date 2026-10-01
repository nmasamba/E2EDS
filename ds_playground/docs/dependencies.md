# Dependencies

One line per production dependency: why it is here, its licence as stated upstream, and the alternative.
Exact versions are pinned in `pyproject.toml` and `uv.lock`. Licences below are upstream statements, not a
pin-level legal review (open decision O23).

| Package | Why | Licence (upstream) | Alternative |
|---|---|---|---|
| duckdb 1.5.5 | Embedded SQL over CSV/Parquet for profiling and preparation (suite pin, ADR24) | MIT | pandas or polars; more code for the same checks |
| jsonschema 4.26.0 (`format-nongpl`) | Validates objects against the draft 2020-12 contracts with format assertion | MIT | fastjsonschema; weaker format support |
| typer 0.27.2 | CLI | MIT | argparse; more code |

Development only: ruff, mypy, pytest, pytest-cov, pytest-socket, types-jsonschema.
