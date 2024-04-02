#! /usr/bin/env python
"""Upload sample to Bonsai."""
import click
from functools import wraps
import json
import requests
from requests.structures import CaseInsensitiveDict
from pydantic import BaseModel, Field, FilePath
from typing import Callable
import yaml

USER_ENV = "BONSAI_USER"
PASSWD_ENV = "BONSAI_PASSWD"
TIMEOUT = 10

class SampleConfig(BaseModel):
    """Definition of a sample configuration."""

    group_id: str | None = Field(None, description="Add sample to group with id")
    prp_result: FilePath = Field(..., description="Path to PRP output")
    minhash_signature: FilePath = Field(..., description="Path to minhash signature")


    def assinged_to_group(self) -> bool:
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


def get_auth_token(ctx: ExecutionContext) -> TokenObject:
    """Get authentication token from api"""
    # configure header
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    url = f'{ctx.api_url}/token'
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
def upload_sample(headers: CaseInsensitiveDict, ctx: ExecutionContext, cnf: SampleConfig) -> str:
    """Create a new sample."""
    sample_obj = json.load(cnf.prp_result.open())
    resp = requests.post(f'{ctx.api_url}/samples', headers=headers, json=sample_obj, timeout=TIMEOUT)

    resp.raise_for_status()
    resp_data = resp.json()
    return resp_data["sample_id"]


@api_authentication
def upload_signature(headers: CaseInsensitiveDict, ctx: ExecutionContext, cnf: SampleConfig, sample_id: str) -> str:
    """Upload a genome signature to sample."""
    resp = requests.post(f'{ctx.api_url}/samples/{sample_id}/signature', headers=headers, files={"signature": cnf.minhash_signature.open()}, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def add_sample_to_group(headers: CaseInsensitiveDict, ctx: ExecutionContext, cnf: SampleConfig, sample_id: str) -> str:
    """Add sample to a group."""
    resp = requests.put(f'{ctx.api_url}/groups/{cnf.group_id}/sample', headers=headers, params={"sample_id": sample_id}, timeout=TIMEOUT)

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


@click.command()
@click.option("-a", "--api", type=str, help="Upload configuration")
@click.option("-u", "--user", envvar=USER_ENV, type=str, help="Username")
@click.option("-p", "--password", envvar=PASSWD_ENV, type=str, help="Password")
@click.option("-i", "--input", required=True, type=click.File(), help="Upload configuration")
def cli(api, user, password, input):
    """Upload a sample to Bonsai"""
    if user is None:
        raise click.BadOptionUsage(user, f"No username set. Use either the --user option or env variable {USER_ENV}")
    if password is None:
        raise click.BadOptionUsage(password, f"No username set. Use either the --password option or env variable {PASSWD_ENV}")
    
    # read upload config and verify content
    cnf = SampleConfig(**yaml.safe_load(input))

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
    try:
        sample_id = upload_sample(token_obj=ctx.token, ctx=ctx, cnf=cnf)
    except requests.exceptions.HTTPError as error:
        if error.response.status_code == 409:
            click.secho(f"Sample {sample_id} has already been uploaded", fg="yellow")
        else:
            msg, _ = _process_generic_status_codes(error, sample_id)
            raise click.UsageError(msg) from error
    # upload minhash signature to sample
    try:
        upload_signature(token_obj=ctx.token, ctx=ctx, sample_id=sample_id, cnf=cnf)
    except requests.exceptions.HTTPError as error:
        if error.response.status_code == 409:
            click.secho(f"Sample {sample_id} has alread a signature file, skipping", fg="yellow")
        else:
            msg, _ = _process_generic_status_codes(error, sample_id)
            raise click.UsageError(msg) from error
    # add sample to group if it was assigned one.
    if cnf.assinged_to_group():
        try:
            add_sample_to_group(token_obj=ctx.token, ctx=ctx, cnf=cnf, sample_id=sample_id)
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
    cli()