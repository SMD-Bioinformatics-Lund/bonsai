"""Declaration of flask api entrypoints"""

import json
import logging

from flask import Blueprint, Response, flash, jsonify, request
from flask_login import current_user, login_required
from requests import HTTPError

from ...bonsai import (
    TokenObject,
    add_samples_to_basket,
    get_group_by_id,
    get_samples,
    remove_samples_from_basket,
    update_group,
)
from ...models import SampleBasketObject

api_bp = Blueprint("api", __name__, template_folder="templates", static_folder="static")

LOG = logging.getLogger(__name__)


@api_bp.route("/api/basket/add", methods=["POST"])
@login_required
def add_sample_to_basket():
    """Add sample to basket."""
    # if not valid token
    if current_user.get_id() is None:
        return jsonify("Not authenticated"), 401

    # add samples to basket
    sample_ids = json.loads(request.data).get("selectedSamples", [])

    # get auth token
    token = TokenObject(**current_user.get_id())

    # lookup analysis profile for samples
    try:
        response = get_samples(token, sample_ids=sample_ids, limit=0, skip=0)
    except HTTPError as error:
        flash(str(error), "warning")
        message = "Error"
        return_code = 200
        return "Error", 200

    # store sample informaiton in required format
    samples_to_add = []
    for sample in response["data"]:
        samples_to_add.append(
            SampleBasketObject(
                sample_id=sample["sample_id"], analysis_profile=sample["profile"]
            )
        )

    try:
        add_samples_to_basket(token, samples=samples_to_add)
        message = "Added"
        return_code = 200
    except HTTPError as error:
        flash(str(error), "warning")
        message = "Error"
        return_code = 200
    return message, return_code


@api_bp.route("/api/basket/remove", methods=["POST"])
@login_required
def remove_sample_from_basket():
    """Remove sample from basket."""
    # if not valid token
    if current_user.get_id() is None:
        return "Not authenticated", 401

    # verify input
    request_data = json.loads(request.data)
    sample_id = request_data.get("sample_id", None)
    remove_all = request_data.get("remove_all", False)
    if sample_id is None and not remove_all:
        return "Invalid input", 500

    token = TokenObject(**current_user.get_id())
    if remove_all:
        to_remove = [sample["sample_id"] for sample in current_user.basket]
    else:
        to_remove = [sample_id]
    # call bonsai api to remove samples from basket
    try:
        remove_samples_from_basket(token, sample_ids=to_remove)
    except HTTPError as error:
        LOG.error(
            "Error when removing samples from basket for user: %s",
            current_user.username,
        )
        return Response(
            error.response.text,
            status=error.response.status_code,
            mimetype="application/json",
        )

    return f"removed {len(to_remove)} samples", 200


@api_bp.route("/api/groups/<group_id>/samples", methods=["POST", "DEL"])
@login_required
def update_samples_in_group(group_id: str) -> str:
    """Add one or more samples to an existing group."""
    # if not valid token
    if current_user.get_id() is None:
        return jsonify("Not authenticated"), 401

    # get sample ids that should be added from request
    request_data = json.loads(request.data)
    selected_samples = request_data.get("selectedSamples", [])

    # sanity check that the list is not empty
    if not isinstance(selected_samples, list):
        LOG.error("Unexpected format of sample ids, %s", selected_samples)
        return Response("Error when trying to add samples to group", status=500)
    if len(selected_samples) == 0:
        LOG.error("No sample ids in request, %s", selected_samples)
        return Response("No sample ids in request", status=200)

    # get session auth token
    token = TokenObject(**current_user.get_id())

    # get information of the group that should be updated
    try:
        group_obj = get_group_by_id(token, group_id=group_id)
    except HTTPError as error:
        # throw proper error page
        abort(error.response.status_code)

    match request.method:
        case "POST":
            # add samples to group object
            group_obj["included_samples"] = [
                li for li in set(group_obj["included_samples"] + selected_samples)
            ]
        case "DEL":
            # remove sample ids from group object
            group_obj["included_samples"] = [
                li for li in set(group_obj["included_samples"]) - set(selected_samples)
            ]

    # update group object in database
    try:
        update_group(token, group_id=group_id, data=group_obj)
    except HTTPError as error:
        # throw proper error page
        abort(error.response.status_code)

    return selected_samples
