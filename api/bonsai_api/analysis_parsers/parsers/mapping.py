"""Parse mapping and alignment files."""

import pysam


def get_reference_seq_accnr(bam_path: str) -> str:
    """Get reference sequence accession number.

    :param sam_path: sam file path
    :type sam_path: str
    :return: accession number
    :rtype: str
    """
    samfile = pysam.AlignmentFile(bam_path)
    # get first read
    read = next(samfile.fetch())
    return read.reference_name
