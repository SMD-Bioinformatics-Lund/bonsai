"""Parse variant from VCF files."""

import logging
import re
import os

from cyvcf2 import VCF, Variant

from prp.models.phenotype import VariantBase, VariantType

LOG = logging.getLogger(__name__)
SOURCE_PATTERN = r"##source=(.+)\n"


def _filter_variants(variant_list):
    # Initialize the results dictionary
    filtered_variants = {"sv_variants": [], "indel_variants": [], "snv_variants": []}

    # Iterate through each variant in the list
    for variant in variant_list:
        variant_type = dict(variant).get("variant_type")  # Extract the variant_type
        # Append the variant to the appropriate key in the results dictionary
        if variant_type == "SV":
            filtered_variants["sv_variants"].append(variant)
        elif variant_type == "INDEL":
            filtered_variants["indel_variants"].append(variant)
        elif variant_type == "SNV":
            filtered_variants["snv_variants"].append(variant)
    return filtered_variants


def _get_variant_type(variant) -> VariantType:
    """Parse variant type."""
    match variant.var_type:
        case "snp":
            var_type = VariantType.SNV
        case "mnp":
            var_type = VariantType.MNV
        case "indel":
            var_type = VariantType.INDEL
        case _:
            var_type = VariantType(variant.var_type.upper())
    return var_type


def _get_variant_subtype(ref_base, alt_base):
    # Define purines and pyrimidines
    purines = {"A", "G"}
    pyrimidines = {"C", "T"}

    # Check for transition substitution
    if (ref_base in purines and alt_base in purines) or (
        ref_base in pyrimidines and alt_base in pyrimidines
    ):
        return "TS"

    # If it's not a transition, it must be a transversion
    return "TV"


def parse_variant(variant: Variant, var_id: int, caller: str | None = None):
    """Parse variant info from VCF row."""

    var_objs = []
    # check if variant passed qc filtering
    if len(variant.FILTERS) == 0:
        passed_qc = None
    elif "PASS" in variant.FILTERS:
        passed_qc = True
    else:
        passed_qc = False

    var_type: VariantType = _get_variant_type(variant)

    for alt_idx, alt_var in enumerate(variant.ALT):
        var_subtype = variant.var_subtype.upper()
        if var_subtype == "UNKNOWN":
            var_subtype = _get_variant_subtype(variant.REF, alt_var)
        var_obj = VariantBase(
            id=var_id,
            variant_type=var_type,
            variant_subtype=var_subtype,
            gene_symbol=variant.CHROM,
            start=variant.start,
            end=variant.end,
            ref_nt=variant.REF,
            alt_nt=alt_var,
            frequency=(
                variant.INFO.get("AF")
                if not isinstance(variant.INFO.get("AF"), tuple)
                else variant.INFO.get("AF")[alt_idx]
            ),
            depth=(
                variant.INFO.get("DP")
                if not isinstance(variant.INFO.get("DP"), tuple)
                else variant.INFO.get("DP")[alt_idx]
            ),
            method=variant.INFO.get("SVMETHOD", caller),
            confidence=variant.QUAL,
            passed_qc=passed_qc,
        )
        var_objs.append(var_obj)
    return var_objs


def _get_variant_caller(vcf_obj: VCF) -> str | None:
    """Get source from VCF header to get variant caller sw if possible."""
    match = re.search(SOURCE_PATTERN, vcf_obj.raw_header)
    if match:
        return match.group(1)
    return None


def load_variants(variant_file: str) -> list[VariantBase]:
    """Load variants."""
    if not os.path.exists(variant_file):
        LOG.warning("Variant filepath %s does not exist, check mounts and filepath...", variant_file)
        return None

    vcf_obj = VCF(variant_file)
    try:
        next(vcf_obj)
    except StopIteration:
        LOG.warning("Variant file %s does not include any variants", variant_file)
        return None
    # re-read the variant file
    vcf_obj = VCF(variant_file)

    variant_caller = _get_variant_caller(vcf_obj)

    # parse header from vcf file
    variants = []
    for var_id, variant in enumerate(vcf_obj, start=1):
        variants.extend(parse_variant(variant, var_id=var_id, caller=variant_caller))
    return _filter_variants(variants)


def annotate_delly_variants(writer, vcf, annotation, annot_chrom=False):
    """Annotate a variant called by Delly."""
    locus_tag = 3
    gene_symbol = 4
    # annotate variant
    n_annotated = 0
    for variant in vcf:
        # update chromosome
        if annot_chrom:
            variant.CHROM = annotation.contigs[0]
        # get genes intersecting with SV
        genes = [
            {"gene_symbol": gene[gene_symbol], "locus_tag": gene[locus_tag]}
            for gene in annotation.fetch(variant.CHROM, variant.start, variant.end)
        ]
        # add overlapping genes to INFO
        if len(genes) > 0:
            variant.INFO["gene"] = ",".join([gene["gene_symbol"] for gene in genes])
            variant.INFO["locus_tag"] = ",".join([gene["locus_tag"] for gene in genes])
            n_annotated += 1

        # write variant
        writer.write_record(variant)
