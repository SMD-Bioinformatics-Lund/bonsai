"""View controller functions."""

import logging
from pathlib import Path
from typing import Dict, List

from flask import session, url_for
from flask_login import current_user
from pydantic import BaseModel, Field

from app.models import RWModel

LOG = logging.getLogger(__name__)


class IgvBaseTrack(RWModel):
    """Track information for IGV."""

    name: str
    type: str | None = None
    format: str | None = None
    source_type: str = Field(..., alias="sourceType")
    url: str
    index_url: str | None = Field(None, alias="indexURL")
    order: int = 1
    height: int = 50


class IgvReferenceGenome(RWModel):
    name: str
    fasta_url: str = Field(..., alias="fastaURL")
    index_url: str = Field(..., alias="indexURL")
    cytoband_url: str | None = Field(None, alias="cytobandURL")


class IgvData(BaseModel):
    locus: str
    reference: IgvReferenceGenome
    tracks: List[IgvBaseTrack] = []
    # IGV configuration
    show_ideogram: bool = Field(False, alias="showIdeogram")
    show_svg_button: bool = Field(True, alias="showSVGButton")
    show_ruler: bool = Field(True, alias="showRuler")
    show_center_guide: bool = Field(False, alias="showCenterGuide")
    show_cursor_track_guide: bool = Field(False, alias="showCursorTrackGuide")


def get_variant(sample_obj, variant_id: str):
    software, variant_id = variant_id.split("-")
    for pred_res in sample_obj["element_type_result"]:
        if pred_res["software"] == software:
            for variant in pred_res["result"]["variants"]:
                if variant["id"] == int(variant_id):
                    return variant


def make_igv_tracks(
    sample_obj, variant_id: str, start: int | None = None, stop: int | None = None
) -> IgvData:
    variant_obj = get_variant(sample_obj, variant_id)
    if variant_obj:
        start = start or variant_obj["start"]
        stop = stop or variant_obj["start"]
        locus = f"Chromosome:{start}-{stop}"
    else:
        locus = ""

    # set reference genome
    ref_genome = sample_obj["reference_genome"]
    reference = IgvReferenceGenome(
        name=ref_genome["accession"],
        fasta_url=url_for("alignviewers.remote_static", _external=True, file=ref_genome["fasta"]),
        index_url=url_for("alignviewers.remote_static", _external=True, file=ref_genome["fasta_index"]),
    )

    # set annotation tracks
    tracks = []
    for order, annot in enumerate(sample_obj["genome_annotation"], start=1):
        file = Path(annot)
        match file.suffix:
            case ".bam":
                index_url = url_for("alignviewers.remote_static", _external=True, file=f"{annot}.bai")
            case ".bed":
                index_url = None
            case ".vcf":
                index_url = None
        # add track
        tracks.append(
            IgvBaseTrack(
                name=annot.split(".")[0],
                source_type="file",
                url=url_for("alignviewers.remote_static", _external=True, file=annot),
                index_url=index_url,
                order=order,
            )
        )
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
