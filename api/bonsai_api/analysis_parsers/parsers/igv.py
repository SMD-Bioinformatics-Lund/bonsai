"""Parse metadata passed to pipeline."""

import logging
from pathlib import Path

from .variant import load_variants

from prp.models.config import IgvAnnotation
from prp.models.phenotype import VariantBase

from ..models.sample import IgvAnnotationTrack, ReferenceGenome

LOG = logging.getLogger(__name__)


def _extract_accn_from_header(fasta_fpath: str):
    with open(fasta_fpath, "r") as fin:
        header = fin.readline().strip()
    return str(header[1:].split()[0])

def parse_igv_info(
    ref_genome_sequence: Path,
    ref_genome_annotation: Path,
    igv_annotations: list[IgvAnnotation],
) -> tuple[ReferenceGenome, str | None, list[IgvAnnotationTrack], list[VariantBase]]:
    """Parse IGV information.

    :param reference_genome: Nextflow analysis metadata in json format.
    :type reference_genome: str
    :return: Reference genome information.
    :rtype: ReferenceGenome
    """
    LOG.info("Parse IGV info.")

    read_mapping_info: list[IgvAnnotationTrack] = []

    igv_alignment_track: str | None = None
    for annotation in igv_annotations:
        uri = str(annotation.uri)
        if annotation.type == "alignment":
            igv_alignment_track = uri
        elif annotation.type == "variant":
            filtered_variants = load_variants(uri)
            igv_annotation_track = IgvAnnotationTrack(
                name=annotation.name,
                file=uri,
            )
            read_mapping_info.append(igv_annotation_track)
        else:
            igv_annotation_track = IgvAnnotationTrack(
                name=annotation.name,
                file=uri,
            )
            read_mapping_info.append(igv_annotation_track)

    ref_genome_sequence_fpath = str(ref_genome_sequence)
    ref_genome_sequence_fai = ref_genome_sequence.parent / (
        ref_genome_sequence.name + ".fai"
    )
    species_name = ref_genome_sequence.parent.name.replace("_", " ")
    accession = _extract_accn_from_header(ref_genome_sequence_fpath)

    reference_genome_info = ReferenceGenome(
        name=species_name.capitalize(),
        accession=accession,
        fasta=ref_genome_sequence_fpath,
        fasta_index=str(ref_genome_sequence_fai),
        genes=str(ref_genome_annotation),
    )

    return reference_genome_info, igv_alignment_track, read_mapping_info, filtered_variants
