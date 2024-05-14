"""Declaration of views for samples"""
import json
import logging
from enum import Enum
from typing import Any, Dict, List

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pydantic import BaseModel
from requests.exceptions import HTTPError

from app.bonsai import (
    TokenObject,
    cluster_samples,
    get_samples_by_id,
    get_valid_group_columns,
)
from app.custom_filters import get_json_path

LOG = logging.getLogger(__name__)


class DataType(str, Enum):
    """Valid datatypes"""

    GRADIENT = "gradient"
    CATEGORY = "category"


class DataPointStyle(BaseModel):  # pylint: disable=too-few-public-methods
    """Styling for a grapetree column."""

    label: str
    coltype: str = "character"
    grouptype: str = "alphabetic"
    colorscheme: DataType

    class Config:  # pylint: disable=too-few-public-methods
        """Configure model to resolve Enum values."""

        use_enum_values = True


class MetaData(BaseModel):  # pylint: disable=too-few-public-methods
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


def get_value(sample: Dict[str | int, Any], value: str | int) -> str | int | float:
    """Get value from object.

    :param sample: Sample infomation as dict
    :type sample: Dict[str  |  int, Any]
    :param value: Field name
    :type value: str | int
    :return: The content of the field name.
    :rtype: str | int | float
    """
    val = sample.get(value)
    return "-" if val is None else val


def fmt_metadata(data):
    if isinstance(data, (list, tuple)):
        return ", ".join([point["label"] for point in data])
    else:
        return data


def gather_metadata(samples, column_definition: List[Any]) -> MetaData:
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
    # Get which metadata points to display
    columns = [col for col in column_definition if not col["hidden"]]
    # create metadata structure
    metadata = {}
    for sample in samples:
        # add sample to metadata list
        sample_id = sample["sample_id"]
        # store metadata
        metadata[sample_id] = {
            col["label"]: fmt_metadata(get_json_path(sample, col["path"]))
            for col in columns
        }
    # build metadata list
    metadata_list = set()
    for meta in metadata.values():
        metadata_list.update(set(meta))
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
        # get samples info as python object
        samples = request.form.get("sample-ids", "{}")
        samples = {} if samples == "" else json.loads(samples)
        # get columns as python object
        column_info = request.form.get("metadata", "{}")
        column_info = None if column_info == "" else json.loads(column_info)
        # query for sample metadata
        if samples == {}:
            metadata = {}
        else:
            token = TokenObject(**current_user.get_id())
            sample_summary = get_samples_by_id(token, sample_ids=samples["sample_id"])
            # get column info
            if column_info is None:
                column_info = get_valid_group_columns()
            metadata = gather_metadata(
                sample_summary["records"], column_info
            ).model_dump()
        data = {"nwk": newick, **metadata}
        return render_template(
            "ms_tree.html",
            title=f"{typing_data} cluster",
            typing_data=typing_data,
            data=json.dumps(data),
        )
    return url_for("public.index")


@cluster_bp.route("/cluster_samples", methods=["GET", "POST"])
@login_required
def cluster():
    """Cluster samples and display results in a view."""
    if request.method == "POST":
        body = request.get_json()
        sample_ids = [sample["sample_id"] for sample in body["sample_ids"]]
        typing_method = body.get("typing_method", "cgmlst")
        cluster_method = body.get("cluster_method", "MSTreeV2")
        token = TokenObject(**current_user.get_id())
        # trigger clustering on api
        try:
            job = cluster_samples(
                token,
                sample_ids=sample_ids,
                typing_method=typing_method,
                method=cluster_method,
            )
        except HTTPError as error:
            flash(str(error), "danger")
        else:
            return job.model_dump(mode="json")
    return redirect(url_for("public.index"))
