"""Handlers for api services."""

import logging
from functools import partial, wraps
from typing import Callable, List

import requests
from flask import current_app
from pydantic import BaseModel
from requests import HTTPError
from requests.structures import CaseInsensitiveDict

from .config import settings
from .models import SampleBasketObject, SubmittedJob

LOG = logging.getLogger(__name__)


# define default arguments for requests
requests_get = partial(
    requests.get, timeout=settings.request_timeout, verify=settings.verify_ssl
)
requests_post = partial(
    requests.post, timeout=settings.request_timeout, verify=settings.verify_ssl
)
requests_put = partial(
    requests.put, timeout=settings.request_timeout, verify=settings.verify_ssl
)
requests_delete = partial(
    requests.delete, timeout=settings.request_timeout, verify=settings.verify_ssl
)


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
    url = f"{settings.bonsai_api_url}/users/me"
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_users(headers: CaseInsensitiveDict):
    """Get current user from the database."""
    # conduct query
    url = f"{settings.bonsai_api_url}/users"
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def create_user(headers: CaseInsensitiveDict, user_obj: str):
    """Create a new user."""
    # conduct query
    url = f"{settings.bonsai_api_url}/users"
    resp = requests_post(url, headers=headers, json=user_obj)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_user(headers: CaseInsensitiveDict, username: str):
    """Get current user from token"""
    # username = kwargs.get("username")
    # conduct query
    url = f"{settings.bonsai_api_url}/users/{username}"
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_user(headers: CaseInsensitiveDict, username: str, user):
    """Delete the user from the database."""
    # conduct query
    url = f"{settings.bonsai_api_url}/users/{username}"
    resp = requests_put(url, headers=headers, json=user)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def delete_user(headers: CaseInsensitiveDict, username: str):
    """Delete the user from the database."""
    # conduct query
    url = f"{settings.bonsai_api_url}/users/{username}"
    resp = requests_delete(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


def get_auth_token(username: str, password: str) -> TokenObject:
    """Get authentication token from api"""
    # configure header
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    url = f"{settings.bonsai_api_url}/token"
    resp = requests_post(
        url,
        data={"username": username, "password": password},
        headers=headers,
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
    url = f"{settings.bonsai_api_url}/groups"
    LOG.error("query api url: %s", url)
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_group_by_id(headers: CaseInsensitiveDict, group_id: str):
    """Get a group with its group_id from database"""
    # conduct query
    url = f"{settings.bonsai_api_url}/groups/{group_id}"
    current_app.logger.debug("Query API for group %s", group_id)
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def delete_group(headers: CaseInsensitiveDict, group_id: str):
    """Remove group from database."""
    # conduct query
    url = f"{settings.bonsai_api_url}/groups/{group_id}"
    resp = requests_delete(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_group(headers: CaseInsensitiveDict, group_id: str, data):
    """Update information in database for a group with group_id."""
    # conduct query
    url = f"{settings.bonsai_api_url}/groups/{group_id}"
    resp = requests_put(url, json=data, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def create_group(headers: CaseInsensitiveDict, **kwargs):
    """create new group."""
    data = kwargs.get("data")
    # conduct query
    url = f"{settings.bonsai_api_url}/groups"
    resp = requests_post(url, json=data, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def add_samples_to_basket(headers: CaseInsensitiveDict, **kwargs):
    """create new group."""
    samples: List[SampleBasketObject] = kwargs.get("samples")
    samples = [smp.model_dump() for smp in samples]
    # conduct query
    url = f"{settings.bonsai_api_url}/users/basket"
    resp = requests_put(url, json=samples, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def remove_samples_from_basket(headers: CaseInsensitiveDict, **kwargs):
    """create new group."""
    sample_ids: List[str] = kwargs.get("sample_ids")
    # conduct query
    url = f"{settings.bonsai_api_url}/users/basket"
    resp = requests_delete(url, json=sample_ids, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_samples(
    headers: CaseInsensitiveDict,
    limit: int = 20,
    skip: int = 0,
    sample_ids: list[str] | None = None,
):
    """Get multipe samples from database."""
    # conduct query
    url = f"{settings.bonsai_api_url}/samples"
    # get limit, offeset and skip values
    params = {"limit": limit, "skip": skip}
    if sample_ids is not None:
        # sanity check list
        if len(sample_ids) == 0:
            raise ValueError("sample_ids list cant be empty!")
        params["sid"] = sample_ids
    resp = requests_get(url, headers=headers, params=params)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def delete_samples(headers: CaseInsensitiveDict, sample_ids: List[str]):
    """Remove samples from database."""
    # conduct query
    url = f"{settings.bonsai_api_url}/samples/"
    resp = requests_delete(url, headers=headers, json=sample_ids)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_samples_in_group(
    headers: CaseInsensitiveDict,
    group_id: str,
    limit: int = 0,
    skip_lines: int = 0,
    prediction_result: bool = True,
    qc_metrics: bool = False,
):
    """Search the database for the samples that are part of a given group."""
    # conduct query
    url = f"{settings.bonsai_api_url}/groups/{group_id}/samples"
    if group_id is None:
        raise ValueError("No sample id provided.")

    current_app.logger.debug("Query API for samples in group: %s", group_id)
    resp = requests_get(
        url,
        headers=headers,
        params={
            "limit": limit,
            "skip": skip_lines,
            "prediction_result": prediction_result,
            "qc_metrics": qc_metrics,
        },
    )

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_sample_by_id(headers: CaseInsensitiveDict, **kwargs):
    """Get sample from database by id"""
    # conduct query
    sample_id = kwargs.get("sample_id")
    url = f"{settings.bonsai_api_url}/samples/{sample_id}"
    resp = requests_get(url, headers=headers)
    current_app.logger.debug("Query API for sample %s", sample_id)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def cgmlst_cluster_samples(headers: CaseInsensitiveDict):
    """Get groups from database"""
    url = f"{settings.bonsai_api_url}/cluster/cgmlst"
    resp = requests_post(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def post_comment_to_sample(headers: CaseInsensitiveDict, **kwargs):
    """Post comment to sample"""
    sample_id = kwargs.get("sample_id")
    data = {"comment": kwargs.get("comment"), "username": kwargs.get("user_name")}
    # conduct query
    url = f"{settings.bonsai_api_url}/samples/{sample_id}/comment"
    resp = requests_post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def remove_comment_from_sample(headers: CaseInsensitiveDict, **kwargs):
    """Post comment to sample"""
    sample_id = kwargs.get("sample_id")
    comment_id = kwargs.get("comment_id")
    # conduct query
    url = f"{settings.bonsai_api_url}/samples/{sample_id}/comment/{comment_id}"
    resp = requests_delete(url, headers=headers)
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
    url = f"{settings.bonsai_api_url}/samples/{sample_id}/qc_status"
    resp = requests_put(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_variant_info(headers: CaseInsensitiveDict, sample_id, variant_ids, status):
    """Update annotation of resitance variants for a sample"""
    data = {
        "variant_ids": variant_ids,
        **status,
    }
    # conduct query
    url = f"{settings.bonsai_api_url}/samples/{sample_id}/resistance/variants"
    resp = requests_put(url, headers=headers, json=data)
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
    url = f"{settings.bonsai_api_url}/cluster/{typing_method}/"
    resp = requests_post(url, headers=headers, json=data)
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
    url = f"{settings.bonsai_api_url}/samples/{sample_id}/similar"
    current_app.logger.debug(
        "Query API for samples similar to %s, similarity: %s, limit: %s",
        sample_id,
        similarity,
        limit,
    )
    resp = requests_post(
        url,
        headers=headers,
        json={"similarity": similarity, "limit": limit, "cluster": False},
    )
    resp.raise_for_status()
    return SubmittedJob(**resp.json())


@api_authentication
def find_and_cluster_similar_samples(
    headers: CaseInsensitiveDict,
    sample_id: str,
    similarity: float = 0.5,
    limit: int | None = None,
    typing_method: str | None = None,
    cluster_method: str | None = None,
) -> SubmittedJob:
    """Find samples with closest minhash distance to reference."""

    url = f"{settings.bonsai_api_url}/samples/{sample_id}/similar"
    current_app.logger.debug(
        "Query API for samples similar to %s, similarity: %f, limit: %d",
        sample_id,
        similarity,
        limit,
    )
    data = {
        "sample_id": sample_id,
        "similarity": similarity,
        "limit": limit,
        "cluster": True,
        "cluster_method": cluster_method,
        "typing_method": typing_method,
    }
    resp = requests_post(
        url,
        headers=headers,
        json=data,
    )
    resp.raise_for_status()
    return SubmittedJob(**resp.json())


@api_authentication
def get_lims_export_file(headers: CaseInsensitiveDict, sample_id: str) -> str:
    """Query the API for a lims export file."""
    url = f"{settings.bonsai_api_url}/export/{sample_id}/lims"
    resp = requests_get(url, headers=headers)
    resp.raise_for_status()
    return resp.text


def get_valid_group_columns(qc: bool = False):
    """Query API for valid group columns."""
    url = f"{settings.bonsai_api_url}/groups/default/columns"
    resp = requests_get(url, params={"qc": qc})
    resp.raise_for_status()
    return resp.json()


def get_antibiotics():
    """Query the API for antibiotics."""
    url = f"{settings.bonsai_api_url}/resources/antibiotics"
    resp = requests_get(url)
    resp.raise_for_status()
    return resp.json()


def get_variant_rejection_reasons():
    """Query the API for antibiotics."""
    url = f"{settings.bonsai_api_url}/resources/variant/rejection"
    resp = requests_get(url)
    resp.raise_for_status()
    return resp.json()
