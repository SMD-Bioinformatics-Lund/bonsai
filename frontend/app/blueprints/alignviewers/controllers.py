"""View controller functions."""

from flask import url_for, session
from flask_login import current_user
import logging
from typing import Dict, Any

LOG = logging.getLogger(__name__)


def get_variant(sample_obj, variant_id: str):
    software, variant_id = variant_id.split("-")
    for pred_res in sample_obj["element_type_result"]:
        if pred_res["software"] == software:
            for variant in pred_res["result"]["variants"]:
                if variant["id"] == int(variant_id):
                    return variant


def make_igv_tracks(sample_obj, variant_id: str, start: int | None=None, stop: int | None=None):
    display_obj = {}

    variant_obj = get_variant(sample_obj, variant_id)
    if variant_obj:
        start = start or variant_obj["start"]
        stop = stop or variant_obj["start"]
        display_obj["locus"] = f"Chromosome:{start}-{stop}"

    # set reference genome
    ref_genome = sample_obj["reference_genome"]
    display_obj["reference_track"] = {
        "id": ref_genome["accession"],
        "name": ref_genome["name"],
        "fastaUrl": url_for("alignviewers.remote_static", file=ref_genome["fasta"]),
        "indexUrl": url_for("alignviewers.remote_static", file=ref_genome["fasta_index"]),
    }
    # set annotation tracks
    tracks = []
    for annot in sample_obj["genome_annotation"]:
        tracks.append({
            "name": annot.split('.')[0],
            "sourceType": "file",
            "url": url_for("alignviewers.remote_static", file=annot)
        })
    return display_obj
    """
    HUMAN_GENES_38 = {
        "name": "Genes",
        "track_name": "genes_track",
        "type": "annotation",
        "sourceType": "file",
        "displayMode": "EXPANDED",
        "visibilityWindow": 300000000,
        "format": HG38GENES_FORMAT,
        "url": HG38GENES_URL,
        "indexURL": HG38GENES_INDEX_URL,
    }
    CLINVAR_SV_38 = {
        "name": "ClinVar SVs",
        "track_name": "clinvar_svs",
        "type": "annotation",
        "sourceType": "file",
        "displayMode": "SQUISHED",
        "visibilityWindow": 3000000000,
        "format": "bigBed",
        "height": 100,
        "url": HG38CLINVAR_SVS_URL,
    }
    """
    return display_obj


def set_session_tracks(display_obj: Dict[str, str]) -> None:
    """Save igv tracks as a session object. This way it's easy to verify that a user is requesting one of these files from remote_static view endpoint

    :param display_object: A display object containing case name, list of genes, locus and tracks
    :type: Dict
    :return: if tracks can be accessed
    :rtype: bool
    """
    session_tracks = list(display_obj.get("reference_track", {}).values())
    for key, track_items in display_obj.items():
        if key not in ["tracks", "custom_tracks", "sample_tracks", "cloud_public_tracks"]:
            continue
        for track_item in track_items:
            session_tracks += list(track_item.values())

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
        LOG.warning(f"Requested resource to be displayed in IGV not in session's IGV tracks")
        return False
    return True