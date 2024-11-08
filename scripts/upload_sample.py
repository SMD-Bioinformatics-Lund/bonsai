#! /usr/bin/env python
"""Upload sample to Bonsai."""
import json
from functools import wraps
from io import TextIOWrapper
from pathlib import Path
from typing import Callable

import click
import requests
import yaml
from pydantic import BaseModel, Field, FilePath, ValidationError
from requests.structures import CaseInsensitiveDict

USER_ENV = "BONSAI_USER"
PASSWD_ENV = "BONSAI_PASSWD"
TIMEOUT = 10


class SampleConfig(BaseModel):
    """Definition of a sample configuration."""

    group_id: str | None = Field(None, description="Add sample to group with id")
    prp_result: FilePath = Field(..., description="Path to PRP output")
    minhash_signature: FilePath = Field(..., description="Path to minhash signature")
    ska_index: FilePath | None = Field(
        ..., description="Path to ska index for SNV clustring"
    )

    def assinged_to_group(self) -> bool:
        """Return True if sample is assigned to a group."""
        return self.group_id is not None


class TokenObject(BaseModel):  # pylint: disable=too-few-public-methods
    """Token object"""

    token: str
    type: str


class ExecutionContext(BaseModel):
    """Container for execution context."""

    username: str
    password: str
    api_url: str
    token: TokenObject | None = None


def _rel_to_abs_path(path: Path | str, base_path: Path) -> str:
    """Resolve relative paths to absolute.

    if a path is relative, convert to absolute from the configs parent directory
    i.e.  prp_path = ./results/sample_name.json --> /data/samples/results/sample_name.json
          given, cnf_path = /data/samples/cnf.yml
    relative paths are used when bootstraping a test database
    """
    rel_path = Path(path) if Path(path).is_absolute() else base_path / path
    return str(rel_path.absolute())


def process_input_config(config_file: TextIOWrapper) -> SampleConfig:
    """Take PRP config and convert it to a config object."""
    raw_config = yaml.safe_load(config_file)
    base_path = Path(config_file.name).parent

    prp_result = _rel_to_abs_path(raw_config.get("prp_result"), base_path)
    minhash_signature = _rel_to_abs_path(raw_config.get("minhash_signature"), base_path)
    ska_index = (
        _rel_to_abs_path(raw_config.get("ska_index"), base_path)
        if raw_config.get("ska_index")
        else None
    )

    # cast as SampleConfig object and validate input
    return SampleConfig(
        group_id=raw_config.get("group_id"),
        prp_result=prp_result,
        minhash_signature=minhash_signature,
        ska_index=ska_index,
    )


def get_auth_token(ctx: ExecutionContext) -> TokenObject:
    """Get authentication token from api"""
    # configure header
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    url = f"{ctx.api_url}/token"
    resp = requests.post(
        url,
        data={"username": ctx.username, "password": ctx.password},
        headers=headers,
        timeout=TIMEOUT,
    )
    # controll that request
    resp.raise_for_status()
    json_res = resp.json()
    token_obj = TokenObject(token=json_res["access_token"], type=json_res["token_type"])
    return token_obj


def api_authentication(func: Callable) -> Callable:
    """Use authentication token for api.

    :param func: API function to wrap with API auth headers
    :type func: Callable
    :return: Wrapped API function
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(token_obj: TokenObject, *args, **kwargs) -> Callable:
        """Add authentication headers to API requests.

        :param token_obj: Auth token object
        :type token_obj: TokenObject
        :return: Wrapped API call function
        :rtype: Callable
        """
        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        headers["Authorization"] = f"{token_obj.type.capitalize()} {token_obj.token}"

        return func(headers=headers, *args, **kwargs)

    return wrapper


@api_authentication
def upload_sample_result(
    headers: CaseInsensitiveDict, ctx: ExecutionContext, cnf: SampleConfig
) -> str:
    """Create a new sample."""
    sample_obj = json.load(cnf.prp_result.open())
    resp = requests.post(
        f"{ctx.api_url}/samples/", headers=headers, json=sample_obj, timeout=TIMEOUT
    )

    resp.raise_for_status()
    resp_data = resp.json()
    return resp_data["sample_id"]


@api_authentication
def upload_signature(
    headers: CaseInsensitiveDict,
    ctx: ExecutionContext,
    cnf: SampleConfig,
    sample_id: str,
) -> str:
    """Upload a genome signature to sample."""
    resp = requests.post(
        f"{ctx.api_url}/samples/{sample_id}/signature",
        headers=headers,
        files={"signature": cnf.minhash_signature.open()},
        timeout=TIMEOUT,
    )

    resp.raise_for_status()
    return resp.json()


@api_authentication
def add_ska_index(
    headers: CaseInsensitiveDict,
    ctx: ExecutionContext,
    cnf: SampleConfig,
    sample_id: str,
) -> str:
    """Upload a genome signature to sample."""
    resp = requests.post(
        f"{ctx.api_url}/samples/{sample_id}/ska_index",
        headers=headers,
        params={"index": cnf.ska_index},
        timeout=TIMEOUT,
    )

    resp.raise_for_status()
    return resp.json()


@api_authentication
def add_sample_to_group(
    headers: CaseInsensitiveDict,
    ctx: ExecutionContext,
    cnf: SampleConfig,
    sample_id: str,
) -> str:
    """Add sample to a group."""
    resp = requests.put(
        f"{ctx.api_url}/groups/{cnf.group_id}/sample",
        headers=headers,
        params={"sample_id": sample_id},
        timeout=TIMEOUT,
    )

    resp.raise_for_status()
    return resp.json()


def _process_generic_status_codes(error, sample_id):
    """Process generic http status codes."""
    is_major_error = True
    match error.response.status_code:
        case 404:
            msg = f"Sample with {sample_id} is not in Bonsai"
            is_major_error = False
        case 500:
            msg = "An unexpected error occured in Bonsai, check bonsai api logs"
        case _:
            msg = f"An unknown error occurred; {str(error)}"
    return msg, is_major_error


def upload_sample(ctx: ExecutionContext, cnf: SampleConfig) -> str:
    """Upload a sample with files for clustring."""
    try:
        sample_id = upload_sample_result(  # pylint: disable=no-value-for-parameter
            token_obj=ctx.token, ctx=ctx, cnf=cnf
        )
    except requests.exceptions.HTTPError as error:
        if error.response.status_code == 409:
            click.secho("Sample have already been uploaded", fg="yellow")
        else:
            msg, _ = _process_generic_status_codes(error, "")
            raise click.UsageError(msg) from error
    # upload minhash signature to sample
    try:
        upload_signature(  # pylint: disable=no-value-for-parameter
            token_obj=ctx.token, ctx=ctx, sample_id=sample_id, cnf=cnf
        )
    except requests.exceptions.HTTPError as error:
        if error.response.status_code == 409:
            click.secho(
                f"Sample {sample_id} has already a signature file, skipping",
                fg="yellow",
            )
        else:
            msg, _ = _process_generic_status_codes(error, sample_id)
            raise click.UsageError(msg) from error
    # add ska index path to sample
    if cnf.ska_index is not None:
        try:
            add_ska_index(  # pylint: disable=no-value-for-parameter
                token_obj=ctx.token, ctx=ctx, sample_id=sample_id, cnf=cnf
            )
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 409:
                click.secho(
                    f"Sample {sample_id} is already associated with a ska index file, skipping",
                    fg="yellow",
                )
            else:
                msg, _ = _process_generic_status_codes(error, sample_id)
                raise click.UsageError(msg) from error
    return sample_id


@click.command()
@click.option("-a", "--api", required=True, type=str, help="Upload configuration")
@click.option("-u", "--user", envvar=USER_ENV, type=str, help="Username")
@click.option("-p", "--password", envvar=PASSWD_ENV, type=str, help="Password")
@click.option(
    "-i",
    "--input",
    "sample_conf",
    required=True,
    type=click.File(),
    help="Upload configuration",
)
def cli(api, user, password, sample_conf):
    """Upload a sample to Bonsai"""
    if user is None:
        raise click.BadOptionUsage(
            user,
            f"No username set. Use either the --user option or env variable {USER_ENV}",
        )
    if password is None:
        raise click.BadOptionUsage(
            password,
            f"No username set. Use either the --password option or env variable {PASSWD_ENV}",
        )

    # read upload config and verify content
    try:
        cnf: SampleConfig = process_input_config(sample_conf)
    except ValidationError as err:
        err_json = json.loads(err.json())[0]
        err_msg = (
            f"Input config file is invalid.\n{err_json['msg']}: {err_json['input']}"
        )
        raise click.BadArgumentUsage(err_msg)

    # login
    ctx = ExecutionContext(username=user, password=password, api_url=api)
    # add token if
    try:
        token = get_auth_token(ctx)
    except ValueError as error:
        raise click.UsageError(str(error)) from error

    # add token to ctx
    ctx = ctx.model_copy(update={"token": token})
    # upload sample
    sample_id = upload_sample(ctx=ctx, cnf=cnf)
    # add sample to group if it was assigned one.
    if cnf.assinged_to_group():
        try:
            add_sample_to_group(  # pylint: disable=no-value-for-parameter
                token_obj=ctx.token, ctx=ctx, cnf=cnf, sample_id=sample_id
            )
        except requests.exceptions.HTTPError as error:
            match error.response.status_code:
                case 404:
                    msg = f"Group with id {cnf.group_id} is not in Bonsai"
                case 500:
                    msg = "An unexpected error occured in Bonsai, check bonsai api logs"
                case _:
                    msg = f"An unknown error occurred; {str(error)}"
            # raise error and abort execution
            raise click.UsageError(msg) from error

    # exit script
    click.secho("Sample uploaded", fg="green")


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
