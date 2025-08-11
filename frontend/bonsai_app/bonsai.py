"""Handlers for api services."""

import logging
from functools import partial, wraps
from typing import Any, Callable, List

import requests
from flask import current_app
from pydantic import BaseModel
from requests.structures import CaseInsensitiveDict

from .config import settings
from .models import SampleBasketObject, SubmittedJob, ApiGetSamplesDetailsInput

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


def api_authentication(func: Callable[..., Any]) -> Callable[..., Any]:
    """Use authentication token for api.

    :param func: API function to wrap with API auth headers
    :type func: Callable
    :return: Wrapped API function
    :rtype: Callable
    """

    @wraps(func)
    def wrapper(
        token_obj: TokenObject, *args: list[Any], **kwargs: list[Any]
    ) -> Callable[..., Any]:
        """Add authentication headers to API requests.

        :param token_obj: Auth token object
        :type token_obj: TokenObject
        :return: Wrapped API call function
        :rtype: Callable
        """
        headers: CaseInsensitiveDict[str] = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        headers["Authorization"] = f"{token_obj.type.capitalize()} {token_obj.token}"

        return func(headers=headers, *args, **kwargs)

    return wrapper


@api_authentication
def get_current_user(headers: CaseInsensitiveDict[str]):
    """Get current user from token"""
    # conduct query
    url = f"{settings.api_internal_url}/users/me"
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_users(headers: CaseInsensitiveDict[str]):
    """Get current user from the database."""
    # conduct query
    url = f"{settings.api_internal_url}/users/"
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def create_user(headers: CaseInsensitiveDict[str], user_obj: str):
    """Create a new user."""
    # conduct query
    url = f"{settings.api_internal_url}/users/"
    resp = requests_post(url, headers=headers, json=user_obj)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_user(headers: CaseInsensitiveDict[str], username: str):
    """Get current user from token"""
    # username = kwargs.get("username")
    # conduct query
    url = f"{settings.api_internal_url}/users/{username}"
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_user(headers: CaseInsensitiveDict[str], username: str, user: dict[str, str]):
    """Delete the user from the database."""
    # conduct query
    url = f"{settings.api_internal_url}/users/{username}"
    resp = requests_put(url, headers=headers, json=user)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def delete_user(headers: CaseInsensitiveDict[str], username: str):
    """Delete the user from the database."""
    # conduct query
    url = f"{settings.api_internal_url}/users/{username}"
    resp = requests_delete(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


def get_auth_token(username: str, password: str) -> TokenObject:
    """Get authentication token from api"""
    # configure header
    headers: CaseInsensitiveDict[str] = CaseInsensitiveDict()
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    url = f"{settings.api_internal_url}/token"
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
def get_groups(headers: CaseInsensitiveDict[str]):
    """Get groups from database"""
    # conduct query
    url = f"{settings.api_internal_url}/groups/"
    LOG.error("query api url: %s", url)
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_group_by_id(headers: CaseInsensitiveDict[str], group_id: str):
    """Get a group with its group_id from database"""
    # conduct query
    url = f"{settings.api_internal_url}/groups/{group_id}"
    current_app.logger.debug("Query API for group %s", group_id)
    resp = requests_get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def delete_group(headers: CaseInsensitiveDict[str], group_id: str):
    """Remove group from database."""
    # conduct query
    url = f"{settings.api_internal_url}/groups/{group_id}"
    resp = requests_delete(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_group(
    headers: CaseInsensitiveDict[str], group_id: str, data: dict[str, Any]
):
    """Update information in database for a group with group_id."""
    # conduct query
    url = f"{settings.api_internal_url}/groups/{group_id}"
    resp = requests_put(url, json=data, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def create_group(headers: CaseInsensitiveDict[str], data: dict[str, Any]):
    """create new group."""
    # conduct query
    url = f"{settings.api_internal_url}/groups/"
    resp = requests_post(url, json=data, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def add_samples_to_basket(
    headers: CaseInsensitiveDict[str], samples: list[SampleBasketObject]
):
    """create new group."""
    serialised_info = [smp.model_dump() for smp in samples]
    # conduct query
    url = f"{settings.api_internal_url}/users/basket"
    resp = requests_put(url, json=serialised_info, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def remove_samples_from_basket(
    headers: CaseInsensitiveDict[str], sample_ids: list[str]
):
    """create new group."""
    url = f"{settings.api_internal_url}/users/basket"
    resp = requests_delete(url, json=sample_ids, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_samples(
    headers: CaseInsensitiveDict[str],
    limit: int | None= None,
    skip: int | None = None,
    sample_ids: list[str] | None = None,
):
    """Get multipe samples from database.
    
    If sample_ids is provided it will return only those samples.
    """
    # conduct query
    url = f"{settings.api_internal_url}/samples/summary"
    # get limit, offeset and skip values
    if sample_ids is not None:
        # sanity check list
        if len(sample_ids) == 0:
            raise ValueError("sample_ids list cant be empty!")
    data = ApiGetSamplesDetailsInput.model_validate({"limit": limit, "skip": skip, "sid": sample_ids})
    resp = requests_post(url, headers=headers, json=data.model_dump())

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        print(resp.text)
    return resp.json()


@api_authentication
def delete_samples(headers: CaseInsensitiveDict[str], sample_ids: List[str]):
    """Remove samples from database."""
    # conduct query
    url = f"{settings.api_internal_url}/samples/"
    resp = requests_delete(url, headers=headers, json=sample_ids)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def get_samples_in_group(
    headers: CaseInsensitiveDict[str],
    group_id: str | None = None,
    limit: int = 0,
    skip_lines: int = 0,
    prediction_result: bool = True,
    qc_metrics: bool = False,
):
    """Search the database for the samples that are part of a given group."""
    # conduct query
    url = f"{settings.api_internal_url}/groups/{group_id}/samples"
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
def get_sample_by_id(
    headers: CaseInsensitiveDict[str], sample_id: str
) -> dict[str, Any]:
    """Get sample from database by id"""
    # conduct query
    url = f"{settings.api_internal_url}/samples/{sample_id}"
    resp = requests_get(url, headers=headers)
    current_app.logger.debug("Query API for sample %s", sample_id)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def cgmlst_cluster_samples(headers: CaseInsensitiveDict[str]):
    """Get groups from database"""
    url = f"{settings.api_internal_url}/cluster/cgmlst"
    resp = requests_post(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


@api_authentication
def post_comment_to_sample(
    headers: CaseInsensitiveDict[str], sample_id: str, user_name: str, comment: str
):
    """Post comment to sample"""
    data = {"comment": comment, "username": user_name}
    # conduct query
    url = f"{settings.api_internal_url}/samples/{sample_id}/comment"
    resp = requests_post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def remove_comment_from_sample(
    headers: CaseInsensitiveDict[str], sample_id: str, comment_id: str
):
    """Post comment to sample"""
    # conduct query
    url = f"{settings.api_internal_url}/samples/{sample_id}/comment/{comment_id}"
    resp = requests_delete(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_sample_qc_classification(
    headers: CaseInsensitiveDict[str],
    sample_id: str,
    status: str,
    action: str | None,
    comment: str,
):
    """Update the qc classification of a sample"""
    data: dict[str, str | None] = {
        "status": status,
        "action": action,
        "comment": comment,
    }
    # conduct query
    url = f"{settings.api_internal_url}/samples/{sample_id}/qc_status"
    resp = requests_put(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def update_variant_info(
    headers: CaseInsensitiveDict[str],
    sample_id: str,
    variant_ids: str,
    status: dict[str, str | list[str] | None],
):
    """Update annotation of resitance variants for a sample"""
    data: dict[str, str | list[str] | None] = {
        "variant_ids": variant_ids,
        **status,
    }
    # conduct query
    url = f"{settings.api_internal_url}/samples/{sample_id}/resistance/variants"
    resp = requests_put(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()


@api_authentication
def cluster_samples(
    headers: CaseInsensitiveDict[str],
    sample_ids: list[str],
    method: str = "single",
    typing_method: str = "cgmlst",
    distance: str = "jaccard",
) -> SubmittedJob:
    """Cluster samples on selected typing result."""
    url = f"{settings.api_internal_url}/cluster/{typing_method}/"
    resp = requests_post(
        url,
        headers=headers,
        json={
            "sample_ids": sample_ids,
            "method": method,
            "distance": distance,
        },
    )
    resp.raise_for_status()
    return SubmittedJob(**resp.json())


@api_authentication
def find_samples_similar_to_reference(
    headers: CaseInsensitiveDict[str],
    sample_id: str,
    similarity: float = 0.5,
    limit: int | None = None,
) -> SubmittedJob:
    """Find samples with closest minhash distance to reference."""
    # conduct query
    url = f"{settings.api_internal_url}/samples/{sample_id}/similar"
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
    headers: CaseInsensitiveDict[str],
    sample_id: str,
    similarity: float = 0.5,
    limit: int | None = None,
    typing_method: str | None = None,
    cluster_method: str | None = None,
) -> SubmittedJob:
    """Find samples with closest minhash distance to reference."""

    url = f"{settings.api_internal_url}/samples/{sample_id}/similar"
    current_app.logger.debug(
        "Query API for samples similar to %s, similarity: %f, limit: %d",
        sample_id,
        similarity,
        limit,
    )
    data: dict[str, str | int | float | None] = {
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
def get_lims_export_response(headers: CaseInsensitiveDict[str], sample_id: str, fmt: str = "tsv") -> requests.Response:
    """Query the API for a LIMS export file; return the raw response."""
    url = f"{settings.api_internal_url}/export/{sample_id}/lims"
    resp = requests_get(url, headers=headers, params={"fmt": fmt})
    resp.raise_for_status()
    return resp


@api_authentication
def get_valid_group_columns(headers: CaseInsensitiveDict[str], group_id: str | None = None, qc: bool = False):
    """Query API for valid group columns."""
    partial_url: str = (
        "groups/default/columns" if group_id is None 
        else f"groups/{group_id}/columns"
    )
    resp = requests_get(f"{settings.api_internal_url}/{partial_url}", params={"qc": qc}, headers=headers)
    resp.raise_for_status()
    return resp.json()


def get_antibiotics():
    """Query the API for antibiotics."""
    url = f"{settings.api_internal_url}/resources/antibiotics"
    resp = requests_get(url)
    resp.raise_for_status()
    return resp.json()


def get_variant_rejection_reasons():
    """Query the API for antibiotics."""
    url = f"{settings.api_internal_url}/resources/variant/rejection"
    resp = requests_get(url)
    resp.raise_for_status()
    return resp.json()
