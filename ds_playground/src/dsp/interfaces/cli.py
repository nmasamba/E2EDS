from pathlib import Path
from typing import Annotated, Any

import typer

from dsp.application.packs import verify_pack
from dsp.contracts.errors import DspError, ErrorCode
from dsp.harness.instance import connect, home

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _fail(error: DspError) -> typer.Exit:
    typer.echo(str(error), err=True)
    return typer.Exit(2)


def _call(method: str, route: str, **body: str) -> Any:
    """Send one request to the harness, starting it if needed, and return its JSON answer."""
    response = connect(home()).request(method, route, json=body or None)
    answer = response.json()
    if response.is_error:
        raise DspError(ErrorCode(answer["code"]), answer["message"])
    return answer


def _line(grant: dict[str, str]) -> str:
    return f"{grant['handle']} {grant['purpose']} {grant['label']}"


@app.command()
def profile(
    file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option(exists=True, file_okay=False, help="Output folder.")],
) -> None:
    """Profile a CSV file and export a hash-verified pack to a new version folder.

    Naming the file and the folder here grants the harness that file and that folder.
    """
    try:
        source = _call("POST", "/v1/grants", purpose="source_root", path=str(file.resolve()))
        output = _call("POST", "/v1/grants", purpose="output_root", path=str(out.resolve()))
        result = _call(
            "POST",
            "/v1/profiles",
            source_handle=source["handle"],
            relative_path=".",
            output_handle=output["handle"],
        )
    except DspError as error:
        raise _fail(error) from error
    typer.echo(f"exported {out / result['version']} ({result['files']} files)")


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
        info = _call("GET", "/v1/status")
    except DspError as error:
        raise _fail(error) from error
    typer.echo(f"harness running (pid {info['pid']}, version {info['version']})")


@app.command()
def grant(
    folder: Annotated[Path, typer.Argument(exists=True)],
    purpose: Annotated[str, typer.Option(help="source_root or output_root.")],
) -> None:
    """Grant the harness a folder to read data from, or a folder to export into."""
    try:
        typer.echo(_line(_call("POST", "/v1/grants", purpose=purpose, path=str(folder.resolve()))))
    except DspError as error:
        raise _fail(error) from error


@app.command()
def grants() -> None:
    """List the active grants: handle, purpose and folder name."""
    try:
        for active in _call("GET", "/v1/grants")["grants"]:
            typer.echo(_line(active))
    except DspError as error:
        raise _fail(error) from error


@app.command()
def revoke(handle: str) -> None:
    """Revoke a grant by its handle."""
    try:
        _call("POST", f"/v1/grants/{handle}/revoke")
    except DspError as error:
        raise _fail(error) from error
    typer.echo(f"revoked {handle}")


@app.command()
def hardware() -> None:
    """Observe this machine's processors, memory, storage and accelerators, and report them."""
    try:
        snapshot = _call("POST", "/v1/hardware")
    except DspError as error:
        raise _fail(error) from error

    def known(value: object) -> object:
        return "unknown" if value is None else value

    system, memory, gpus = snapshot["system"], snapshot["memory"], snapshot["accelerators"]
    free = [volume["available_gib"] for volume in snapshot["storage"]] or [None]
    typer.echo(
        f"{known(system['os'])} {known(system['architecture'])}: "
        f"{known(snapshot['cpu']['visible_logical_processors'])} processors, "
        f"{known(memory['total_gib'])} GiB memory ({known(memory['available_gib'])} available), "
        f"{known(free[0])} GiB free"
    )
    models = ", ".join(device["model"] for device in gpus["devices"])
    typer.echo(f"accelerators {gpus['inventory_status']} {models}".rstrip())
    for probe in snapshot["probes"]:
        if probe["status"] != "observed":
            typer.echo(f"{probe['name']}: {probe['status']}: {probe['safe_summary']}")
