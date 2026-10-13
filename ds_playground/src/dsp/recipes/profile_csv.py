"""The built-in profiling recipe (R11, D20), run as a CodeTask inside the sandbox.

The harness runs this file's source as a Python task whose one declared input is the captured CSV,
``data.csv``, and whose one output is ``profile.json`` (app Profile 0.1.0), in canonical JSON. The
parser touches the owner's data, so it runs confined (C18); the harness renders the report from the
validated profile. Nothing here imports the project: the runner executes this text as it is.
"""

import json
from pathlib import Path
from typing import Any

import duckdb

MAX_ROWS, MAX_COLUMNS = 100_000, 200  # D20

INTEGER = "FILTER (WHERE regexp_full_match({c}, '-?[0-9]+'))"
STATS = f"""
SELECT count({{c}}), count(DISTINCT {{c}}), min({{c}}), max({{c}}),
       count(TRY_CAST({{c}} AS BIGINT)) {INTEGER}, count(TRY_CAST({{c}} AS DOUBLE)),
       count(TRY_CAST({{c}} AS TIMESTAMP)),
       count(*) FILTER (WHERE regexp_matches({{c}}, '^-?0[0-9]')),
       min(TRY_CAST({{c}} AS BIGINT)) {INTEGER}, max(TRY_CAST({{c}} AS BIGINT)) {INTEGER},
       min(TRY_CAST({{c}} AS DOUBLE)), max(TRY_CAST({{c}} AS DOUBLE))
FROM t
"""


def profile(path: Path) -> dict[str, Any]:
    """Profile every row of a CSV: counts, nulls, distinct values, ranges and a proposed type.

    Values are read as text so identifiers keep their exact form; a column with leading-zero values
    is proposed as a string even if every value parses as a number. Rows the parser cannot read are
    counted as rejected, never dropped silently. Nothing is sampled or truncated: a table over the
    D20 bounds is refused.
    """
    con = duckdb.connect()
    try:
        con.execute(
            "CREATE TABLE t AS SELECT * FROM read_csv(?, header=true, all_varchar=true,"
            " store_rejects=true)",
            [str(path)],
        )
    except duckdb.Error as error:
        raise ValueError("the file could not be read as CSV") from error
    rows = con.execute("SELECT count(*) FROM t").fetchall()[0][0]
    rejected = con.execute("SELECT count(DISTINCT line) FROM reject_errors").fetchall()[0][0]
    names = [row[0] for row in con.execute("DESCRIBE t").fetchall()]
    if rows > MAX_ROWS or len(names) > MAX_COLUMNS:
        raise ValueError(
            f"{rows} rows and {len(names)} columns exceed the D20 limits"
            f" {MAX_ROWS} and {MAX_COLUMNS}"
        )
    columns = []
    for name in names:
        quoted = '"' + name.replace('"', '""') + '"'
        (non_null, distinct, low, high, ints, doubles, stamps, leading_zero, *ranges) = con.execute(
            STATS.format(c=quoted)
        ).fetchall()[0]
        if non_null == 0 or leading_zero:
            kind = "unknown" if non_null == 0 else "string"
        elif ints == non_null:
            kind, low, high = "integer", ranges[0], ranges[1]
        elif doubles == non_null:
            kind, low, high = "number", ranges[2], ranges[3]
        else:
            kind = "timestamp" if stamps == non_null else "string"
        columns.append(
            {
                "name": name,
                "proposed_type": kind,
                "non_null": non_null,
                "nulls": rows - non_null,
                "distinct": distinct,
                "min": low,
                "max": high,
            }
        )
    return {
        "schema_version": "0.1.0",
        "type": "Profile",
        "rows": rows,
        "rows_rejected": rejected,
        "columns": columns,
    }


if __name__ == "__main__":
    found = profile(Path("../inputs/data.csv"))
    text = json.dumps(
        found, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    Path("profile.json").write_bytes(text.encode())
