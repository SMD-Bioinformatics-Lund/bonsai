"""View controller functions."""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

from flask import session
from flask_login import current_user
from pydantic import Field

from ...config import settings
from ...models import RWModel

LOG = logging.getLogger(__name__)

ANNOTATION_SUFFIXES = [
    ".bed",
    ".gtf",
    ".gff",
    ".genePred",
    ".genePredExt",
    ".peaks",
    ".narrowPeak",
    ".broadPeak",
    ".bigBed",
]


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

    type: str = "annotation"
    name_field: str | None = Field(None, alias="nameField")
    filter_types: List[str] = Field(["chromosome", "gene"], alias="filterTypes")


class IgvAlignmentTrack(IgvBaseTrack):
    """Configurations specific to alignment tracks.

    reference: https://github.com/igvteam/igv.js/wiki/Alignment-Track
    """

    type: str = "alignment"
    show_soft_clips: bool = Field(False, alias="showSoftClips")


class IgvVariantTrack(IgvBaseTrack):
    """Configurations specific to variant tracks.

    reference: https://github.com/igvteam/igv.js/wiki/Variant-Track
    """

    type: str = "variant"


class IgvReferenceGenome(RWModel):
    """IGV reference genome container."""

    name: str
    fasta_url: str = Field(..., alias="fastaURL")
    index_url: str = Field(..., alias="indexURL")
    cytoband_url: str | None = Field(None, alias="cytobandURL")


class IgvData(RWModel):
    """Definition of data used by IGV."""

    locus: str
    reference: IgvReferenceGenome
    tracks: List[IgvAnnotationTrack | IgvAlignmentTrack | IgvVariantTrack] = []
    # IGV configuration
    show_ideogram: bool = Field(False, alias="showIdeogram")
    show_svg_button: bool = Field(True, alias="showSVGButton")
    show_ruler: bool = Field(True, alias="showRuler")
    show_center_guide: bool = Field(False, alias="showCenterGuide")
    show_cursor_track_guide: bool = Field(False, alias="showCursorTrackGuide")


def build_api_url(path: str, **kwargs):
    """Build api URL path."""
    base_url = f"{settings.api_external_url}{path}"
    params = [f"{key}={val}" for key, val in kwargs.items()]
    if len(params) > 0:
        url = f"{base_url}?{'&'.join(params)}"
    else:
        url = base_url
    return url


def get_variant(sample_obj: Dict[str, Any], variant_id: str) -> Dict[str, Any] | None:
    """Get variant with Id from sampleObj."""
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
    return None


def make_igv_tracks(
    sample_obj: Dict[str, Any],
    variant_id: str,
    start: int | None = None,
    stop: int | None = None,
) -> IgvData:
    """Make IGV tracks.

    :param sample_obj: Sample object from database
    :type sample_obj: Dict[str, Any]
    :param variant_id: Variant id
    :type variant_id: str
    :param start: start genome position, defaults to None
    :type start: int | None, optional
    :param stop: end position in genome, defaults to None
    :type stop: int | None, optional
    :return: Pydantic container with IGV data.
    :rtype: IgvData
    """
    # get reference genome
    ref_genome = sample_obj["reference_genome"]
    entrypoint_url = os.path.join(
        settings.api_external_url, "resources", "genome", "info"
    )
    reference = IgvReferenceGenome(
        name=ref_genome["accession"],
        fasta_url=f"{entrypoint_url}?file={ref_genome['fasta']}",
        index_url=f"{entrypoint_url}?file={ref_genome['fasta_index']}",
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
        settings.api_external_url, "samples", sample_obj["sample_id"], "alignment"
    )
    tracks = [
        IgvAlignmentTrack(
            name="Read mapping",
            source_type="file",
            url=bam_entrypoint_url,
            index_url=f"{bam_entrypoint_url}?index=true",
            auto_height=True,
            max_height=450,
            display_mode=IgvDisplayMode.SQUISHED,
            order=1,
            show_soft_clips=True,
        ),
    ]
    # add gene track
    gene_url = build_api_url("/resources/genome/info", file=ref_genome["genes"])
    tracks.append(
        IgvAnnotationTrack(
            name="Genes",
            source_type="file",
            format="gff",
            url=gene_url,
            height=120,
            order=2,
            display_mode=IgvDisplayMode.EXPANDED,
            name_field="gene",
            filter_types=["chromosome", "region", "gene", "exon"],
        ),
    )
    # set additional annotation tracks
    for order, annot in enumerate(sample_obj["genome_annotation"], start=3):
        file = Path(annot["file"])
        # check if file is gzipped
        if file.suffix == ".gz" and len(file.suffixes) == 1:
            # warn if file format is unrecognised
            LOG.warning("Unknown file format for file: %s", file)
            continue
        if file.suffix == ".gz" and len(file.suffixes) > 1:
            file_suffix = file.suffixes[-2]
        else:
            file_suffix = file.suffix

        # detect the type of track to add based on the file suffix
        match file_suffix:
            case file_suffix if file_suffix in ANNOTATION_SUFFIXES:
                url = build_api_url("/resources/genome/info", file=file)
                track = IgvAnnotationTrack(
                    name=annot["name"],
                    source_type="file",
                    url=url,
                    order=order,
                )
            case ".vcf":
                url = build_api_url("/resources/genome/info", file=file)
                track = IgvVariantTrack(
                    name=annot["name"],
                    source_type="file",
                    format="vcf",
                    url=url,
                    order=order,
                )
            case _:
                LOG.warning("Unknown file format for file: %s", file)
                track = None
        # add track if defined
        if track is not None:
            tracks.append(track)
    display_obj = IgvData(locus=locus, reference=reference, tracks=tracks)
    return display_obj


def set_session_tracks(display_obj: Dict[str, str]) -> None:
    """Save igv tracks as a session object.

    This way it's easy to verify that a user is requesting
    one of these files from remote_static view endpoint

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
    """Make sure that a user requesting a resource is authenticated
    and resource is in session IGV tracks

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
            "Requested resource to be displayed in IGV not in session's IGV tracks"
        )
        return False
    return True
