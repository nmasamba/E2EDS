from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer

from dsp.adapters import export_fs
from dsp.adapters.duckdb_profile import profile_csv
from dsp.adapters.ledger_sqlite import SqliteLedger
from dsp.adapters.store_fs import ContentStore
from dsp.application.packs import profile_and_export, verify_pack
from dsp.contracts.errors import DspError, TrustedContext
from dsp.harness.instance import connect, home

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _fail(error: DspError) -> typer.Exit:
    typer.echo(str(error), err=True)
    return typer.Exit(2)


@app.command()
def profile(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option(exists=True, file_okay=False, help="Output folder.")],
) -> None:
    """Profile a CSV file and export a hash-verified pack to a new version folder."""
    state = home()
    try:
        receipt = profile_and_export(
            TrustedContext.local(),
            file,
            out,
            ledger=SqliteLedger(state / "ledger.sqlite", _now),
            store=ContentStore(state / "store"),
            exporter=export_fs,
            profiler=profile_csv,
            clock=_now,
            new_id=lambda: uuid4().hex,
        )
    except DspError as error:
        raise _fail(error) from error
    typer.echo(f"exported {out / receipt['version']} ({len(receipt['files'])} files)")


@app.command()
def verify(directory: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """Check every file in an exported pack against the digests in its manifest."""
    try:
        bad = verify_pack(directory)
    except DspError as error:
        raise _fail(error) from error
    if bad:
        typer.echo(f"MISMATCH: {', '.join(bad)}", err=True)
        raise typer.Exit(2)
    typer.echo("verified")


@app.command()
def status() -> None:
    """Start or reconnect to the local harness and report it."""
    try:
        info = connect(home()).get("/v1/status").json()
    except DspError as error:
        raise _fail(error) from error
    typer.echo(f"harness running (pid {info['pid']}, version {info['version']})")
