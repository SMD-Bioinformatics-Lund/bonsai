"""Functions for computing tags."""
from ..models.tags import Tag, TAG_LIST, VirulenceTag, TagType, TagSeverity
from ..models.sample import SampleInDatabase, PhenotypeResult, PhenotypeType

# Phenotypic tags
def add_pvl(tags: TAG_LIST, sample: SampleInDatabase) -> Tag:
    """Check if sample is PVL toxin positive."""
    virs = [pred for pred in sample.add_phenotype_prediction if pred.type == PhenotypeType.vir.value]
    if len(virs) > 0:
        vir_result: PhenotypeResult = virs[0].result
        has_lukS = any(gene.name == "lukS-PV" for gene in vir_result.genes)
        has_lukF = any(gene.name == "lukF-PV" for gene in vir_result.genes)
        # classify PVL
        if has_lukF and has_lukS:
            tag = Tag(
                type=TagType.virulence,
                label=VirulenceTag.pvl_all_pos,
                description="",
                severity=TagSeverity.danger
            )
        elif any([has_lukF and not has_lukS, has_lukS and not has_lukF]):
            tag = Tag(
                type=TagType.virulence,
                label=VirulenceTag.pvl_lukF_pos if has_lukF else VirulenceTag.pvl_lukS_pos,
                description="",
                severity=TagSeverity.warning
            )
        elif not has_lukF and not has_lukS:
            tag = Tag(
                type=TagType.virulence,
                label=VirulenceTag.pvl_all_neg,
                description="",
                severity=TagSeverity.passed
            )
        tags.append(tag)


ALL_TAG_FUNCS = [add_pvl, ]

def compute_phenotype_tags(sample: SampleInDatabase) -> TAG_LIST:
    """Compute tags based on phenotype prediction."""
    tags = []
    # iterate over tag functions to build up list of tags
    for tag_func in ALL_TAG_FUNCS:
        tag_func(tags, sample)
    return tags