"""Declaration of views for samples"""
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from app.bonsai import cluster_samples, get_samples_by_id, TokenObject
from flask_login import login_required, current_user
from typing import Dict
from pydantic import BaseModel
from enum import Enum
import json


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
        mlst_res = next(
            res["result"] for res in sample["typing_result"] if res["type"] == "mlst"
        )
        metadata[sample_id] = {
            "location": get_value(sample, "location"),
            "time": sample["created_at"],
            "st": get_value(mlst_res, "sequence_type"),
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
        samples = json.loads(request.form.get("metadata"))
        # query for sample metadata
        token = TokenObject(**current_user.get_id())
        samples = get_samples_by_id(token, sample_ids=samples["sample_id"])
        metadata = gather_metadata(samples["records"])
        data = dict(nwk=newick, **metadata.dict())
        return render_template(
            "ms_tree.html", title="cgMLST Cluster", data=json.dumps(data)
        )
    return url_for("public.index")


@cluster_bp.route("/cluster_samples", methods=["GET", "POST"])
@login_required
def cluster_and_display_tree():
    """Cluster samples and display results in a view."""
    if request.method == "POST":
        sample_ids = [
            sample["sample_id"]
            for sample in json.loads(request.form.get("sampleIds", ""))
        ]
        token = TokenObject(**current_user.get_id())
        # trigger clustering on api
        newick = cluster_samples(token, sample_ids=sample_ids, typing_method="cgmlst")

        # get metadata
        samples = get_samples_by_id(token, sample_ids=sample_ids)
        metadata = gather_metadata(samples["records"])
        # query for sample metadata
        data = dict(nwk=newick, **metadata.dict())
        return render_template(
            "ms_tree.html", title="cgMLST Cluster", data=json.dumps(data)
        )
    return url_for("public.index")
