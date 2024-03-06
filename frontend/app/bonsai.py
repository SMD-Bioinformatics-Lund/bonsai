"""Handlers for api services."""
import logging
from functools import wraps
from typing import Callable, List

import requests
from flask import current_app
from pydantic import BaseModel
from requests.structures import CaseInsensitiveDict

from .models import SampleBasketObject, SubmittedJob

LOG = logging.getLogger(__name__)

# Timeout for HTTP request
TIMEOUT = 10


class TokenObject(BaseModel):  # pylint: disable=too-few-public-methods
    """Token object"""

    token: str
    type: str


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
def get_current_user(headers: CaseInsensitiveDict):
    """Get current user from token"""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/users/me'
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_users(headers: CaseInsensitiveDict):
    """Get current user from the database."""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/users'
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def create_user(headers: CaseInsensitiveDict, user_obj: str):
    """Create a new user."""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/users'
    resp = requests.post(url, headers=headers, json=user_obj, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_user(headers: CaseInsensitiveDict, username: str):
    """Get current user from token"""
    #username = kwargs.get("username")
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/users/{username}'
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_user(headers: CaseInsensitiveDict, username: str, user):
    """Delete the user from the database."""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/users/{username}'
    resp = requests.put(url, headers=headers, json=user, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def delete_user(headers: CaseInsensitiveDict, username: str):
    """Delete the user from the database."""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/users/{username}'
    resp = requests.delete(url, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


def get_auth_token(username: str, password: str) -> TokenObject:
    """Get authentication token from api"""
    # configure header
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    url = f'{current_app.config["BONSAI_API_URL"]}/token'
    resp = requests.post(
        url,
        data={"username": username, "password": password},
        headers=headers,
        timeout=TIMEOUT,
    )
    # controll that request
    resp.raise_for_status()
    json_res = resp.json()
    token_obj = TokenObject(token=json_res["access_token"], type=json_res["token_type"])
    return token_obj


@api_authentication
def get_groups(headers: CaseInsensitiveDict):
    """Get groups from database"""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/groups'
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_group_by_id(headers: CaseInsensitiveDict, group_id: str):
    """Get a group with its group_id from database"""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/groups/{group_id}'
    current_app.logger.debug("Query API for group %s", group_id)
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def delete_group(headers: CaseInsensitiveDict, group_id: str):
    """Remove group from database."""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/groups/{group_id}'
    resp = requests.delete(url, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_group(headers: CaseInsensitiveDict, **kwargs):
    """Update information in database for a group with group_id."""
    group_id = kwargs.get("group_id")
    data = kwargs.get("data")
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/groups/{group_id}'
    resp = requests.put(url, json=data, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def create_group(headers: CaseInsensitiveDict, **kwargs):
    """create new group."""
    data = kwargs.get("data")
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/groups'
    resp = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def add_samples_to_basket(headers: CaseInsensitiveDict, **kwargs):
    """create new group."""
    samples: List[SampleBasketObject] = kwargs.get("samples")
    samples = [smp.model_dump() for smp in samples]
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/users/basket'
    resp = requests.put(url, json=samples, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def remove_samples_from_basket(headers: CaseInsensitiveDict, **kwargs):
    """create new group."""
    sample_ids: List[str] = kwargs.get("sample_ids")
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/users/basket'
    resp = requests.delete(url, json=sample_ids, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_samples_in_group(headers: CaseInsensitiveDict, **kwargs):
    """Get groups from database"""
    # conduct query
    group_id = kwargs.get("group_id")
    url = f'{current_app.config["BONSAI_API_URL"]}/groups/{group_id}'
    lookup_samples = kwargs.get("lookup_samples", False)
    resp = requests.get(
        url, headers=headers, params={"lookup_samples": lookup_samples}, timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_samples(headers: CaseInsensitiveDict, **kwargs):
    """Get multipe samples from database."""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples'
    # get limit, offeset and skip values
    parmas = {"limit": kwargs.get("limit", 20), "skip": kwargs.get("skip", 0)}
    resp = requests.get(url, headers=headers, params=parmas, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def delete_samples(headers: CaseInsensitiveDict, sample_ids: List[str]):
    """Remove samples from database."""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/'
    resp = requests.delete(url, headers=headers, json=sample_ids, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_samples_by_id(headers: CaseInsensitiveDict, **kwargs):
    """Search the database for multiple samples"""
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/search'
    sample_id = kwargs.get("sample_ids", None)
    if sample_id is None:
        raise ValueError("No sample id provided.")
    search = {
        "params": {
            "sample_id": sample_id,
        },
        "limit": kwargs.get("limit", 0),
        "skip": kwargs.get("skip", 0),
    }
    current_app.logger.debug("Query API for %s", sample_id)
    resp = requests.post(url, headers=headers, json=search, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_sample_by_id(headers: CaseInsensitiveDict, **kwargs):
    """Get sample from database by id"""
    # conduct query
    sample_id = kwargs.get("sample_id")
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/{sample_id}'
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    current_app.logger.debug("Query API for sample %s", sample_id)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def cgmlst_cluster_samples(headers: CaseInsensitiveDict):
    """Get groups from database"""
    url = f'{current_app.config["BONSAI_API_URL"]}/cluster/cgmlst'
    resp = requests.post(url, headers=headers, timeout=TIMEOUT)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def post_comment_to_sample(headers: CaseInsensitiveDict, **kwargs):
    """Post comment to sample"""
    sample_id = kwargs.get("sample_id")
    data = {"comment": kwargs.get("comment"), "username": kwargs.get("user_name")}
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/{sample_id}/comment'
    resp = requests.post(url, headers=headers, json=data, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def remove_comment_from_sample(headers: CaseInsensitiveDict, **kwargs):
    """Post comment to sample"""
    sample_id = kwargs.get("sample_id")
    comment_id = kwargs.get("comment_id")
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/{sample_id}/comment/{comment_id}'
    resp = requests.delete(url, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_sample_qc_classification(headers: CaseInsensitiveDict, **kwargs):
    """Update the qc classification of a sample"""
    if "sample_id" not in kwargs:
        raise ValueError("Sample id is required for this entrypoint")
    sample_id = kwargs["sample_id"]
    data = {
        "status": kwargs.get("status"),
        "action": kwargs.get("action"),
        "comment": kwargs.get("comment"),
    }
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/{sample_id}/qc_status'
    resp = requests.put(url, headers=headers, json=data, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_variant_info(headers: CaseInsensitiveDict, sample_id, variant_ids = [], status={}):
    """Update annotation of resitance variants for a sample"""
    data = {
        "variant_ids": variant_ids,
        **status,
    }
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/{sample_id}/resistance/variants'
    resp = requests.put(url, headers=headers, json=data, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def cluster_samples(headers: CaseInsensitiveDict, **kwargs) -> SubmittedJob:
    """Cluster samples on selected typing result."""
    typing_method = kwargs.get("typing_method", "cgmslt")
    data = {
        "sample_ids": kwargs.get("sample_ids"),
        "method": kwargs.get("method", "single"),
        "distance": kwargs.get("distance", "jaccard"),
    }
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/cluster/{typing_method}/'
    resp = requests.post(url, headers=headers, json=data, timeout=TIMEOUT)
    resp.raise_for_status()
    return SubmittedJob(**resp.json())


@api_authentication
def find_samples_similar_to_reference(
    headers: CaseInsensitiveDict, **kwargs
) -> SubmittedJob:
    """Find samples with closest minhash distance to reference."""
    sample_id: str = kwargs.get("sample_id")
    similarity: float = kwargs.get("similarity", 0.5)  # similarity score
    limit: int = kwargs.get("limit", None)
    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/{sample_id}/similar'
    current_app.logger.debug(
        "Query API for samples similar to %s, similarity: %s, limit: %s",
        sample_id,
        similarity,
        limit,
    )
    resp = requests.post(
        url,
        headers=headers,
        json={"similarity": similarity, "limit": limit, "cluster": False},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return SubmittedJob(**resp.json())


@api_authentication
def find_and_cluster_similar_samples(
    headers: CaseInsensitiveDict, **kwargs
) -> SubmittedJob:
    """Find samples with closest minhash distance to reference."""
    # params relating to finding similar samples
    sample_id: str = kwargs.get("sample_id")
    similarity: float = kwargs.get("similarity", 0.5)  # similarity score
    limit: int = kwargs.get("limit", None)
    # params relating to clustering
    typing_method: str = kwargs.get("typing_method", None)
    cluster_method: str = kwargs.get("cluster_method", None)

    # conduct query
    url = f'{current_app.config["BONSAI_API_URL"]}/samples/{sample_id}/similar'
    current_app.logger.debug(
        "Query API for samples similar to %s, similarity: %f, limit: %d",
        sample_id,
        similarity,
        limit,
    )
    resp = requests.post(
        url,
        headers=headers,
        json={
            "sample_id": sample_id,
            "similarity": similarity,
            "limit": limit,
            "cluster": True,
            "cluster_method": cluster_method,
            "typing_method": typing_method,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return SubmittedJob(**resp.json())


def get_valid_group_columns():
    """Query API for valid group columns."""
    url = f'{current_app.config["BONSAI_API_URL"]}/groups/default/columns'
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def get_antibiotics():
    """Query the API for antibiotics."""
    url = f'{current_app.config["BONSAI_API_URL"]}/resources/antibiotics'
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def get_variant_rejection_reasons():
    """Query the API for antibiotics."""
    url = f'{current_app.config["BONSAI_API_URL"]}/resources/variant/rejection'
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()
