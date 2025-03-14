"""Utililty functions for shared by functions in the API."""

import datetime


def get_timestamp() -> datetime.datetime:
    """Get datetime timestamp in utc timezone."""
    return datetime.datetime.now(tz=datetime.UTC)


def format_error_message(exception: Exception) -> str:
    """Format exception message."""
    proc_args = []
    for arg in exception.args:
        if isinstance(arg, (tuple, list)):
            arg_str = ", ".join(arg)
        elif isinstance(arg, dict):
            arg_str = ", ".join([f"{k}={v}" for k, v in arg.items()])
        elif isinstance(arg, str):
            arg_str = arg
        else:
            arg_str = ""

        proc_args.append(arg_str)
    return f"{type(exception).__name__}: {', '.join(proc_args)}"
