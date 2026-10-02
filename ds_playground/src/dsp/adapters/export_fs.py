import errno
import os
import shutil
from collections.abc import Mapping
from pathlib import Path

from dsp.contracts.canonical import file_digest
from dsp.contracts.errors import DspError, ErrorCode


def stage(root: Path, files: Mapping[str, Path], staging_id: str) -> Path:
    """Copy files into a labelled staging area on the destination filesystem (D23)."""
    if not root.is_dir():
        raise DspError(ErrorCode.NOT_FOUND, "output folder does not exist")
    if shutil.disk_usage(root).free < sum(source.stat().st_size for source in files.values()):
        raise DspError(ErrorCode.QUOTA_EXCEEDED, "not enough free space in the output folder")
    staging = root.resolve() / f".dsp-staging-{staging_id}"
    staging.mkdir()
    for relative, source in files.items():
        target = (staging / relative).resolve()
        if not target.is_relative_to(staging):
            raise DspError(ErrorCode.FORBIDDEN, f"{relative} escapes the output folder")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return staging


def commit_staged(root: Path, staging: Path, digests: Mapping[str, str]) -> str:
    """Verify staged bytes, then rename the staging area to the next free version directory.

    A mismatch leaves the staging area in place, labelled incomplete by its name, and publishes
    nothing. An existing version is never replaced.
    """
    for relative, expected in digests.items():
        if file_digest(staging / relative) != expected:
            raise DspError(ErrorCode.INTERNAL_ERROR, f"staged {relative} does not match its digest")
    number = max((int(p.name[1:]) for p in root.glob("v*") if p.name[1:].isdigit()), default=0)
    while True:
        number += 1
        try:
            os.rename(staging, root / f"v{number}")
        except OSError as error:
            if error.errno not in (errno.ENOTEMPTY, errno.EEXIST, errno.ENOTDIR):
                raise
        else:
            return f"v{number}"
