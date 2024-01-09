"""Declaration of flask api entrypoints"""
import json

import requests
from flask import Blueprint, flash, jsonify, request
from flask_login import current_user, login_required

from app.bonsai import TokenObject, add_samples_to_basket, remove_samples_from_basket
from app.models import SampleBasketObject

api_bp = Blueprint("api", __name__, template_folder="templates", static_folder="static")


@api_bp.route("/api/basket/add", methods=["POST"])
@login_required
def add_sample_to_basket():
    """Add sample to basket."""
    # if not valid token
    if current_user.get_id() is None:
        return jsonify("Not authenticated"), 401

    # add samples to basket
    raw_samples = json.loads(request.data).get("selectedSamples")
    # cast to correct type
    samples_to_add = [SampleBasketObject(**smp) for smp in raw_samples]
    try:
        token = TokenObject(**current_user.get_id())
        add_samples_to_basket(token, samples=samples_to_add)
        message = "Added"
        return_code = 200
    except requests.exceptions.HTTPError as error:
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
    remove_samples_from_basket(token, sample_ids=to_remove)

    return f"removed {len(to_remove)}", 200
