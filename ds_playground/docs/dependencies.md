# Dependencies

One line per production dependency: why it is here, its licence as stated upstream, and the alternative.
Exact versions are pinned in `pyproject.toml` and `uv.lock`. Licences below are upstream statements, not a
pin-level legal review (open decision O23).

| Package | Why | Licence (upstream) | Alternative |
|---|---|---|---|
| duckdb 1.5.5 | Embedded SQL over CSV/Parquet for profiling and preparation (suite pin, ADR24) | MIT | pandas or polars; more code for the same checks |
| fastapi 0.141.1 | The local harness API (suite pin) | MIT | Starlette alone; more code for the same routes |
| httpx 0.28.1 | The CLI's authenticated client to the harness | BSD-3-Clause | urllib; more code |
| jsonschema 4.26.0 (`format-nongpl`) | Validates objects against the draft 2020-12 contracts with format assertion | MIT | fastjsonschema; weaker format support |
| typer 0.27.2 | CLI | MIT | argparse; more code |
| uvicorn 0.54.0 | Serves the harness on the loopback socket it is handed | BSD-3-Clause | hypercorn |

Development only: ruff, mypy, pytest, pytest-cov, pytest-socket, types-jsonschema.
