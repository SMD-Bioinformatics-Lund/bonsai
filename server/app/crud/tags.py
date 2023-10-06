"""Functions for computing tags."""
from multiprocessing.sharedctypes import Value
from ..models.phenotype import ElementTypeResult, ElementType
from ..models.sample import SampleInDatabase
from ..models.tags import (
    TAG_LIST,
    Tag,
    TagSeverity,
    TagType,
    VirulenceTag,
    ResistanceTag,
)


# Phenotypic tags
def add_pvl(tags: TAG_LIST, sample: SampleInDatabase) -> Tag:
    """Check if sample is PVL toxin positive."""
    virs = [
        pred
        for pred in sample.element_type_result
        if pred.type == ElementType.VIR.value
    ]
    if len(virs) > 0:
        vir_result: ElementTypeResult = virs[0].result
        has_lukS = any(gene.gene_symbol.startswith("lukS") for gene in vir_result.genes)
        has_lukF = any(gene.gene_symbol.startswith("lukF") for gene in vir_result.genes)
        # classify PVL
        if has_lukF and has_lukS:
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_ALL_POS,
                description="Both lukF and lukS were identified",
                severity=TagSeverity.DANGER,
            )
        elif any([has_lukF and not has_lukS, has_lukS and not has_lukF]):
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_LUKF_POS
                if has_lukF
                else VirulenceTag.PVL_LUKS_POS,
                description="One of the luk sub-units identified",
                severity=TagSeverity.WARNING,
            )
        elif not has_lukF and not has_lukS:
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_ALL_NEG,
                description="Neither lukF or lukS was identified",
                severity=TagSeverity.PASSED,
            )
        tags.append(tag)


def add_mrsa(tags: TAG_LIST, sample: SampleInDatabase) -> Tag:
    """Check if sample is MRSA.

    An SA is classified as MRSA if it carries either mecA, mecB or mecC.
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3780952/
    """
    mrsa_genes = []
    valid_genes = ["mecA", "mecB", "mecC"]
    for prediction in sample.element_type_result:
        if not prediction.type == ElementType.AMR.value:
            continue

        for gene in prediction.result.genes:
            # lookup if has valid genes
            gene_lookup = [
                gene.gene_symbol.startswith(symbol)
                for symbol in valid_genes
                if gene.gene_symbol is not None
            ]
            if any(gene_lookup):
                mrsa_genes.append(gene.gene_symbol)

    # add MRSA tag if needed
    if len(mrsa_genes) > 0:
        tag = Tag(
            type=TagType.RESISTANCE,
            label=ResistanceTag.MRSA,
            description=f"Carried genes: {' '.join(mrsa_genes)}",
            severity=TagSeverity.DANGER,
        )
    else:
        tag = Tag(
            type=TagType.RESISTANCE,
            label=ResistanceTag.MSSA,
            description="",
            severity=TagSeverity.INFO,
        )
    tags.append(tag)


ALL_TAG_FUNCS = [add_pvl, add_mrsa]


def compute_phenotype_tags(sample: SampleInDatabase) -> TAG_LIST:
    """Compute tags based on phenotype prediction."""
    tags = []
    # iterate over tag functions to build up list of tags
    for tag_func in ALL_TAG_FUNCS:
        tag_func(tags, sample)
    return tags
