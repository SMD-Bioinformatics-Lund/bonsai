"""Declaration of flask api entrypoints"""
from flask import Blueprint, request, session, jsonify
from flask_login import login_required, current_user
import json

api_bp = Blueprint("api", __name__, template_folder="templates", static_folder="static")


@api_bp.route("/api/basket/add", methods=["POST"])
@login_required
def add_sample_to_basket():
    """Add sample to basket."""
    # if not valid token
    if current_user.get_id() is None:
        return jsonify("Not authenticated"), 401

    if request.method == "POST":
        # add samples to basket
        samples_in_basket = session.get("basket", [])
        samples_to_add = json.loads(request.data).get("selectedSamples")
        # add only unique id
        session["basket"] = list(
            {
                entry["sampleId"]: entry for entry in samples_in_basket + samples_to_add
            }.values()
        )
        msg = ', '.join([entry["sampleId"] for entry in samples_in_basket])
        return f"Added {msg}", 200


@api_bp.route("/api/basket/remove", methods=["POST"])
@login_required
def remove_sample_from_basket():
    """Remove sample from basket."""
    # if not valid token
    if current_user.get_id() is None:
        return "Not authenticated", 401

    if request.method == "POST":
        # add samples to basket
        samples_in_basket = session.get("basket")
        to_remove = json.loads(request.data).get("sampleId", "")
        samples = [sid for sid in samples_in_basket if not sid["sampleId"] == to_remove]
        session["basket"] = samples
        return f"removed {to_remove}", 200
    return "", 200