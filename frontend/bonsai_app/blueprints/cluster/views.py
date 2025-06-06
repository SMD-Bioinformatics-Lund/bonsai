"""Declaration of views for samples"""

import datetime
import json
import logging
from enum import Enum
from typing import Any

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pydantic import BaseModel, ConfigDict
from requests.exceptions import HTTPError

from ...bonsai import TokenObject, cluster_samples, get_samples, get_valid_group_columns
from ...custom_filters import get_json_path

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

    model_config = ConfigDict(use_enum_values=True)


class MetaData(BaseModel):  # pylint: disable=too-few-public-methods
    """Structure of metadata options"""

    metadata: dict[str, dict[str, str | int | float | None]]
    metadata_list: list[str]
    metadata_options: dict[str, DataPointStyle]


cluster_bp = Blueprint(
    "cluster",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/tree/static",
)


def get_value(sample: dict[str | int, Any], value: str | int) -> str | int | float:
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


def fmt_metadata(sample_obj: dict[str, str | int | list[str | dict[str, Any]]], column: dict[str, Any]) -> str:
    data = get_json_path(sample_obj, column["path"])
    match column["type"]:
        case "tags":
            fmt_data = ", ".join([point["label"] for point in data])
        case "comments":
            fmt_data = ", ".join(
                [
                    comment_obj["comment"]
                    for comment_obj in data
                    if comment_obj["displayed"]
                ]
            )
        case "date":
            fmt_data = datetime.datetime.fromisoformat(data).strftime(r"%Y-%m-%d")
        case "list":
            fmt_data = ', '.join(data)
        case _:
            fmt_data = data
    return fmt_data


def gather_metadata(samples: list[dict[str, Any]], column_definition: list[Any]) -> MetaData:
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
    # skip column with sample button
    columns = [col for col in column_definition if not col["hidden"] and col["label"] != ""]
    # create metadata structure
    metadata: dict[str, dict[str, str | int | float | None]] = {}
    for sample in samples:
        # add sample to metadata list
        sample_id = sample["sample_id"]
        # store metadata
        default_cols = {
            col["label"]: fmt_metadata(sample, col) for col in columns if col != ""
        }
        # exclude metadata tables as they cant be rendered
        meta_records: dict[str, str] = {
            meta['fieldname']: meta['value'] for meta in sample['metadata'] if meta['type'] != 'table'}
        metadata[sample_id] = {**default_cols, **meta_records}
    # build list of unique columns
    metadata_list: set[str] = set()
    for sample_meta in metadata.values():
        metadata_list.update(set(sample_meta))
    unique_cols: list[str] = list(metadata_list)
    # build styling for metadata point
    opts: dict[str, DataPointStyle] = {}
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
        metadata_list=unique_cols,
        metadata_options=opts,
    )


@cluster_bp.route("/tree", methods=["GET", "POST"])
@login_required
def tree():
    """grapetree view."""
    if request.method == "POST":
        newick = str(request.form.get("newick"))
        typing_data = request.form.get("typing_data")
        # get samples info as python object
        samples = str(request.form.get("sample-ids", "{}"))
        samples_obj: dict[str, Any] = {} if samples == "" else json.loads(samples)
        # get columns as python object
        column_info = request.form.get("metadata", "{}")
        column_info = None if column_info == "" else json.loads(column_info)
        # query for sample metadata
        if samples_obj == {}:
            metadata = {}
        else:
            token = TokenObject(**current_user.get_id())
            sample_summary = get_samples(
                token, sample_ids=samples_obj["sample_id"], limit=0
            )
            # get column info
            if column_info is None:
                column_info = get_valid_group_columns(token_obj=token)
            metadata = gather_metadata(sample_summary["data"], column_info).model_dump()
        data: dict[str, str] = {"nwk": newick, **metadata}
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
