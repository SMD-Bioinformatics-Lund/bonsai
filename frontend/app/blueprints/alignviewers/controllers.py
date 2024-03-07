"""View controller functions."""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any

from app.config import BONSAI_API_URL
from app.models import RWModel
from flask import session
from flask_login import current_user
from pydantic import BaseModel, Field

LOG = logging.getLogger(__name__)


class IgvDisplayMode(Enum):
    """Valid display modes."""

    COLLAPSED = "COLLAPSED"
    EXPANDED = "EXPANDED"
    SQUISHED = "SQUISHED"


class IgvBaseTrack(RWModel):
    """Track information for IGV.

    For full description of the track options, https://github.com/igvteam/igv.js/wiki/Tracks-2.0
    """

    name: str
    type: str | None = None
    format: str | None = None
    source_type: str = Field(..., alias="sourceType")
    url: str
    index_url: str | None = Field(None, alias="indexURL")
    order: int = 1
    height: int = 50
    auto_height: bool = Field(False, alias="autoHeight")
    min_height: int = Field(50, alias="minHeight")
    max_height: int = Field(500, alias="maxHeight")
    display_mode: IgvDisplayMode = Field(
        IgvDisplayMode.COLLAPSED.value, alias="displayMode"
    )


class IgvAnnotationTrack(IgvBaseTrack):
    """Configurations specific to Annotation tracks.
    
    reference: https://github.com/igvteam/igv.js/wiki/Annotation-Track
    """

    name_field: str | None = Field(None, alias="nameField")
    filter_types: List[str] = Field(["chromosome", "gene"], alias="filterTypes")


class IgvReferenceGenome(RWModel):
    name: str
    fasta_url: str = Field(..., alias="fastaURL")
    index_url: str = Field(..., alias="indexURL")
    cytoband_url: str | None = Field(None, alias="cytobandURL")


class IgvData(RWModel):
    locus: str
    reference: IgvReferenceGenome
    tracks: List[IgvAnnotationTrack | IgvBaseTrack] = []
    # IGV configuration
    show_ideogram: bool = Field(False, alias="showIdeogram")
    show_svg_button: bool = Field(True, alias="showSVGButton")
    show_ruler: bool = Field(True, alias="showRuler")
    show_center_guide: bool = Field(False, alias="showCenterGuide")
    show_cursor_track_guide: bool = Field(False, alias="showCursorTrackGuide")


def build_api_url(path, **kwargs):
    # namedtuple to match the internal signature of urlunparse
    base_url = f"{BONSAI_API_URL}{path}"
    params = [f"{key}={val}" for key, val in kwargs.items()]
    if len(params) > 0:
        url = f"{base_url}?{'&'.join(params)}"
    else:
        url = base_url
    return url


def get_variant(sample_obj: Dict[str, Any], variant_id: str) -> Dict[str, Any]:
    software, variant_id = variant_id.split("-")
    if software in ["sv_variants", "snv_variants"]:
        for variant in sample_obj[software]:
            if variant["id"] == int(variant_id):
                return variant
    else:
        for pred_res in sample_obj["element_type_result"]:
            if pred_res["software"] == software:
                for variant in pred_res["result"]["variants"]:
                    if variant["id"] == int(variant_id):
                        return variant


def make_igv_tracks(
    sample_obj, variant_id: str, start: int | None = None, stop: int | None = None
) -> IgvData:
    # get reference genome
    ref_genome = sample_obj["reference_genome"]
    entrypoint_url = os.path.join(
        BONSAI_API_URL, "resources", "genome", ref_genome["accession"], "info"
    )
    reference = IgvReferenceGenome(
        name=ref_genome["accession"],
        fasta_url=f"{entrypoint_url}?annotation_type=fasta",
        index_url=f"{entrypoint_url}?annotation_type=fasta_index",
    )

    # narrow view to given locus
    variant_obj = get_variant(sample_obj, variant_id)
    if variant_obj:
        start = start or variant_obj["start"]
        stop = variant_obj.get("end") or variant_obj["start"]
        # add padding to structural variants to show surrounding
        if variant_obj["variant_type"] == "SV":
            var_length = (stop - start) + 1
            start = round(start - (var_length * 0.1), 0)
            stop = round(stop + (var_length * 0.1), 0)
        locus = f"{reference.name}:{start}-{stop}"
    else:
        locus = ""

    # generate read mapping track
    bam_entrypoint_url = os.path.join(
        BONSAI_API_URL, "samples", sample_obj["sample_id"], "alignment"
    )
    tracks = [
        IgvBaseTrack(
            name="Read mapping",
            source_type="file",
            type="alignment",
            url=bam_entrypoint_url,
            index_url=f"{bam_entrypoint_url}?index=true",
            auto_height=True,
            max_height=450,
            display_mode=IgvDisplayMode.SQUISHED,
            order=1,
        ),
    ]
    # add gene track
    gene_url = build_api_url(
        f"/resources/genome/{ref_genome['accession']}/info", annotation_type="gff"
    )
    tracks.append(
        IgvAnnotationTrack(
            name="Genes",
            source_type="file",
            format="gff",
            type="annotation",
            url=gene_url,
            height=120,
            order=2,
            display_mode=IgvDisplayMode.EXPANDED,
            name_field="gene",
        ),
    )
    # set additional annotation tracks
    for order, annot in enumerate(sample_obj["genome_annotation"], start=3):
        file = Path(annot["file"])
        match file.suffix:
            case ".bed":
                url = build_api_url(
                    f"/resources/genome/{ref_genome['accession']}/annotation",
                    file=file.name,
                )
                track = IgvBaseTrack(
                    name=annot["name"],
                    source_type="file",
                    type="annotation",
                    url=url,
                    order=order,
                )
            case ".vcf":
                variant_type_suffix, _ = file.suffixes
                url = build_api_url(
                    f"/samples/{sample_obj['sample_id']}/vcf",
                    variant_type=variant_type_suffix[1:].upper(),
                )  # strip leading .
                track = IgvBaseTrack(
                    name=annot["name"],
                    source_type="file",
                    type="variant",
                    url=url,
                    order=order,
                )
        # add track
        tracks.append(track)
    display_obj = IgvData(locus=locus, reference=reference, tracks=tracks)
    return display_obj


def set_session_tracks(display_obj: Dict[str, str]) -> None:
    """Save igv tracks as a session object. This way it's easy to verify that a user is requesting one of these files from remote_static view endpoint

    :param display_object: A display object containing case name, list of genes, locus and tracks
    :type: Dict
    :return: if tracks can be accessed
    :rtype: bool
    """
    session_tracks = list(display_obj.reference.model_dump().values())
    for track in display_obj.tracks:
        session_tracks += list(track.model_dump().values())

    session["igv_tracks"] = session_tracks


def check_session_tracks(resource: str) -> bool:
    """Make sure that a user requesting a resource is authenticated and resource is in session IGV tracks

    :param resource: track content
    :type: str
    :return: if tracks can be accessed
    :rtype: bool
    """
    # Check that user is logged in or that file extension is valid
    if current_user.is_authenticated is False:
        LOG.warning("Unauthenticated user requesting resource via remote_static")
        return False
    if resource not in session.get("igv_tracks", []):
        LOG.warning(
            f"Requested resource to be displayed in IGV not in session's IGV tracks"
        )
        return False
    return True
