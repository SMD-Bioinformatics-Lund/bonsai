"""Functions for computing tags."""
from multiprocessing.sharedctypes import Value
from ..models.phenotype import PhenotypeResult, PhenotypeType
from ..models.sample import SampleInDatabase
from ..models.tags import TAG_LIST, Tag, TagSeverity, TagType, VirulenceTag


# Phenotypic tags
def add_pvl(tags: TAG_LIST, sample: SampleInDatabase) -> Tag:
    """Check if sample is PVL toxin positive."""
    virs = [
        pred for pred in sample.phenotype_result if pred.type == PhenotypeType.VIR.value
    ]
    if len(virs) > 0:
        vir_result: PhenotypeResult = virs[0].result
        has_lukS = any(gene.name == "lukS-PV" for gene in vir_result.genes)
        has_lukF = any(gene.name == "lukF-PV" for gene in vir_result.genes)
        # classify PVL
        if has_lukF and has_lukS:
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_ALL_POS,
                description="",
                severity=TagSeverity.DANGER,
            )
        elif any([has_lukF and not has_lukS, has_lukS and not has_lukF]):
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_LUKF_POS
                if has_lukF
                else VirulenceTag.PVL_LUKS_POS,
                description="",
                severity=TagSeverity.WARNING,
            )
        elif not has_lukF and not has_lukS:
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_ALL_NEG,
                description="",
                severity=TagSeverity.PASSED,
            )
        tags.append(tag)


ALL_TAG_FUNCS = [
    add_pvl,
]


def compute_phenotype_tags(sample: SampleInDatabase) -> TAG_LIST:
    """Compute tags based on phenotype prediction."""
    tags = []
    # iterate over tag functions to build up list of tags
    for tag_func in ALL_TAG_FUNCS:
        tag_func(tags, sample)
    return tags
