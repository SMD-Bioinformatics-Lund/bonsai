"""Declaration of views for samples"""
import json
from enum import Enum
from typing import Dict

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from requests.exceptions import HTTPError

from app.bonsai import TokenObject, cluster_samples, get_samples_by_id
from pydantic import BaseModel
import logging

LOG = logging.getLogger(__name__)


class DataType(str, Enum):
    """Valid datatypes"""

    GRADIENT = "gradient"
    CATEGORY = "category"


class DataPointStyle(BaseModel):
    """Styling for a grapetree column."""

    label: str
    coltype: str = "character"
    grouptype: str = "alphabetic"
    colorscheme: DataType

    class Config:
        use_enum_values = True


class MetaData(BaseModel):
    """Structure of metadata options"""

    metadata: Dict[str, Dict[str, str | int | float]]
    metadata_list: list[str]
    metadata_options: Dict[str, DataPointStyle]


cluster_bp = Blueprint(
    "cluster",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/tree/static",
)


def get_value(sample, value):
    val = sample.get(value)
    return "-" if val is None else val


def gather_metadata(samples) -> MetaData:
    """Create metadata structure.

    GrapeTree metadata structure
    ============================
    metadata = dict[metadata_name,value]
    metadata_list = list[sample_id]
    metadata_options = dict[metadata_name, formatting_options]

    formatting_options = dict[options, values]

    valid options
    - label
    - coltype
    - grouptype
    - colorscheme
    """
    # create metadata structure
    metadata = {}
    for sample in samples:
        # add sample to metadata list
        # store metadata
        sample_id = sample["sample_id"]
        metadata[sample_id] = {
            # "location": get_value(sample, "location"),
            "time": sample["created_at"],
            "st": get_value(sample["mlst"], "sequence_type"),
        }
    # build metadata list
    metadata_list = set()
    for meta in metadata.values():
        metadata_list.update({name for name in meta})
    metadata_list = list(metadata_list)
    # build styling for metadata point
    opts = {}
    for meta_name in metadata_list:
        dtype = DataType.CATEGORY
        opt = DataPointStyle(
            label=meta_name,
            coltype="character",
            grouptype="alphabetic",
            colorscheme=dtype,
        )
        # store options
        opts[meta_name] = opt
    # return Meta object
    return MetaData(
        metadata=metadata,
        metadata_list=metadata_list,
        metadata_options=opts,
    )


@cluster_bp.route("/tree", methods=["GET", "POST"])
@login_required
def tree():
    """grapetree view."""
    if request.method == "POST":
        newick = request.form.get("newick")
        typing_data = request.form.get("typing_data")
        samples = json.loads(request.form.get("metadata"))
        # query for sample metadata
        token = TokenObject(**current_user.get_id())
        sample_summary = get_samples_by_id(token, sample_ids=samples["sample_id"])
        metadata = gather_metadata(sample_summary["records"])
        data = dict(nwk=newick, **metadata.dict())
        return render_template(
            "ms_tree.html", title=f"{typing_data} cluster", typing_data=typing_data, data=json.dumps(data)
        )
    return url_for("public.index")


@cluster_bp.route("/cluster_samples", methods=["GET", "POST"])
@login_required
def cluster():
    """Cluster samples and display results in a view."""
    if request.method == "POST":

        body = request.get_json()
        sample_ids = [
            sample["sample_id"]
            for sample in body["sample_ids"]
        ]
        typing_method = body.get("typing_method", "cgmlst")
        cluster_method = body.get("cluster_method", "MSTreeV2")
        LOG.error(f"Got cluster request, samples: {sample_ids}; method: {typing_method}, cluster: {cluster_method}")
        token = TokenObject(**current_user.get_id())
        # trigger clustering on api
        try:
            job = cluster_samples(
                token, sample_ids=sample_ids, typing_method=typing_method, method=cluster_method
            )
        except HTTPError as error:
            flash(str(error), "danger")
        else:
            return job.model_dump(mode='json')
    return redirect(url_for("public.index"))
