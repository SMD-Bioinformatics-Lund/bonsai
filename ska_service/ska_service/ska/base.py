"""Ska2 base command."""

import logging
import subprocess
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import Sequence

LOG = logging.getLogger(__name__)


def _format_cli_options(options: dict[str, str | int | Path]) -> Sequence[str]:
    """
    Format command line options.

    Expected outcome
    o=foo => [-o, foo]
    out=foo => [--out, foo]
    """
    fmt_opts = []
    for key, val in options.items():
        fmt_opts.extend([f"-{key}" if len(key) == 1 else f"--{key}", str(val)])
    return fmt_opts


def ska_base(
    command: str,
    options: dict[str, str | int | Path] | None = None,
    arguments: Sequence[str | Path] | None = None,
    verbose: bool = False,
    encoding: str = "utf-8",
) -> CompletedProcess:
    """Base wrapper for the SKA2 executable."""
    cli_command = ["ska", command]

    # build cli command and casting all types to strings
    if verbose:
        cli_command.append("--verbose")

    if options is not None:
        cli_command.extend(_format_cli_options(options))

    if arguments is not None:
        cli_command.extend([str(arg) for arg in arguments])

    LOG.debug("Running subprocess command: %s", cli_command)
    proc = subprocess.run(
        cli_command,
        capture_output=True,
        check=False,
        encoding=encoding,
    )

    # check returncode and raise subprocess error
    if not proc.returncode == 0:
        LOG.debug("SKA error - CMD: %s; msg: %s", proc.args, proc.stderr)
        raise CalledProcessError(cmd=proc.args, returncode=proc.returncode)

    return proc


def ska_version() -> str:
    """Return the version of SKA."""
    proc = ska_base("--version")
    return proc.stdout.strip().replace("ska ", "")
