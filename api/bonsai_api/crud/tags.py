"""Functions for computing tags."""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Protocol, runtime_checkable

from bonsai_api.config import (BrackenThresholds, MykrobeThresholds,
                               normalize_species_key, thresholds_cfg)
from bonsai_api.models.sample import SampleInDatabase
from bonsai_api.models.tags import (ResistanceTag, Tag, TagList, TagSeverity,
                                    TagType, VirulenceTag)
from prp.models.phenotype import ElementType, ElementTypeResult
from prp.models.species import (BrackenSpeciesPrediction,
                                MykrobeSpeciesPrediction)
from prp.models.typing import TypingMethod

LOG = logging.getLogger(__name__)


# Phenotypic tags
def add_pvl(tags: TagList, sample: SampleInDatabase) -> None:
    """Check if sample is PVL toxin positive."""
    virs = [
        pred
        for pred in sample.element_type_result
        if pred.type == ElementType.VIR.value
    ]
    if len(virs) > 0:
        vir_result: ElementTypeResult = virs[0].result
        has_luks = any(gene.gene_symbol.startswith("lukS") for gene in vir_result.genes)
        has_lukf = any(gene.gene_symbol.startswith("lukF") for gene in vir_result.genes)
        # classify PVL
        if has_lukf and has_luks:
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_ALL_POS,
                description="Both lukF and lukS were identified",
                severity=TagSeverity.DANGER,
            )
        elif any([has_lukf and not has_luks, has_luks and not has_lukf]):
            tag = Tag(
                type=TagType.VIRULENCE,
                label=(
                    VirulenceTag.PVL_LUKF_POS if has_lukf else VirulenceTag.PVL_LUKS_POS
                ),
                description="One of the luk sub-units identified",
                severity=TagSeverity.WARNING,
            )
        elif not has_lukf and not has_luks:
            tag = Tag(
                type=TagType.VIRULENCE,
                label=VirulenceTag.PVL_ALL_NEG,
                description="Neither lukF or lukS was identified",
                severity=TagSeverity.PASSED,
            )
        tags.append(tag)


def add_mrsa(tags: TagList, sample: SampleInDatabase) -> None:
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


def add_stx_type(tags: TagList, sample: SampleInDatabase) -> None:
    """Check if sample STX type."""
    for type_res in sample.typing_result:
        if type_res.type == TypingMethod.STX.value:
            tag = Tag(
                type=TagType.TYPING,
                label=type_res.result.gene_symbol.upper(),
                description="",
                severity=TagSeverity.INFO,
            )
            tags.append(tag)


def add_oh_type(tags: TagList, sample: SampleInDatabase) -> None:
    """Check if sample OH type."""
    for type_res in sample.typing_result:
        if type_res.type in [TypingMethod.OTYPE.value, TypingMethod.HTYPE.value]:
            tag = Tag(
                type=TagType.TYPING,
                label=type_res.result.sequence_name.upper(),
                description="",
                severity=TagSeverity.INFO,
            )
            tags.append(tag)


def add_shigella_typing(tags: TagList, sample: SampleInDatabase) -> None:
    """Get if an E. coli sample is typed as a Shigella."""
    for type_res in sample.typing_result:
        if type_res.type == TypingMethod.SHIGATYPE:
            if type_res.result.ipah.lower() == "ipah+":
                if type_res.result.predicted_serotype is not None:
                    result = "Shigella"
                else:
                    result = "EIEC"
                # type_res.result.sequence_name.upper()
                tag = Tag(
                    type=TagType.TYPING,
                    label=result,
                    description=type_res.result.predicted_serotype,
                    severity=TagSeverity.INFO,
                )
                tags.append(tag)


def _pick_main_bracken(
    preds: Iterable[BrackenSpeciesPrediction],
) -> BrackenSpeciesPrediction:
    # Robust even if caller doesn't pre-sort
    try:
        return max(preds, key=lambda p: p.fraction_total_reads)
    except ValueError:
        raise ValueError("Empty Bracken predictions list.")


def _pick_main_mykrobe(
    preds: Iterable[MykrobeSpeciesPrediction],
) -> MykrobeSpeciesPrediction:
    # Species coverage tends to be the meaningful ranking for mykrobe
    try:
        return max(preds, key=lambda p: p.species_coverage)
    except ValueError:
        raise ValueError("Empty Mykrobe predictions list.")


# Protocols define only what we need, decoupling from concrete classes.
@runtime_checkable
class BrackenSpecies(Protocol):
    scientific_name: str
    fraction_total_reads: float
    kraken_assigned_reads: int
    added_reads: int


@runtime_checkable
class MykrobeSpecies(Protocol):
    scientific_name: str
    species_coverage: float
    phylogenetic_group_coverage: float


@dataclass(frozen=True)
class EvalResult:
    passed: bool
    reason: str  # empty when passed
    software: str
    species: str


def evaluate_bracken(preds: list[BrackenSpeciesPrediction]) -> EvalResult:
    main = _pick_main_bracken(preds)
    cfg = thresholds_cfg.species
    thr: BrackenThresholds = cfg.get_bracken(
        main.scientific_name
    )  # guaranteed non-None by validator
    # Decide on > or >= per your QC policy — here we use >= (inclusive)
    frac_ok = main.fraction_total_reads >= thr.min_fraction
    reads = (main.kraken_assigned_reads or 0) + (main.added_reads or 0)
    reads_ok = reads >= thr.min_reads

    if frac_ok and reads_ok:
        return EvalResult(
            True, "", "bracken", normalize_species_key(main.scientific_name)
        )

    reasons: list[str] = []
    if not frac_ok:
        reasons.append(
            f"fraction_total_reads {main.fraction_total_reads:.3f} < min {thr.min_fraction:.3f}"
        )
    if not reads_ok:
        reasons.append(f"reads {reads} < min {thr.min_reads}")
    return EvalResult(
        False,
        "; ".join(reasons),
        "bracken",
        normalize_species_key(main.scientific_name),
    )


def evaluate_mykrobe(preds: list[MykrobeSpecies]) -> EvalResult:
    """Evaluate Mykrobe species prediction results."""
    main = _pick_main_mykrobe(preds)
    cfg = thresholds_cfg.species
    thr: MykrobeThresholds = cfg.get_mykrobe(main.scientific_name)

    sp_ok = main.species_coverage >= (
        thr.min_species_coverage * 100
    )  # transpose 0-1 to 100
    pg_ok = main.phylogenetic_group_coverage >= (
        thr.min_phylogenetic_group_coverage * 100
    )

    if sp_ok and pg_ok:
        return EvalResult(
            True, "", "mykrobe", normalize_species_key(main.scientific_name)
        )

    reasons: list[str] = []
    if not sp_ok:
        reasons.append(
            f"species_coverage {main.species_coverage:.3f} < min {thr.min_species_coverage:.3f}"
        )
    if not pg_ok:
        reasons.append(
            f"phylogenetic_group_coverage {main.phylogenetic_group_coverage:.3f} < min {thr.min_phylogenetic_group_coverage:.3f}"
        )
    return EvalResult(
        False,
        "; ".join(reasons),
        "mykrobe",
        normalize_species_key(main.scientific_name),
    )


# Registry for routing (easy to extend)
SPP_EVALUATORS: dict[str, Callable[[list[Any]], EvalResult]] = {
    "bracken": evaluate_bracken,
    "mykrobe": evaluate_mykrobe,
}


def flag_uncertain_spp_prediction(tags: TagList, sample: SampleInDatabase) -> None:
    """Flag samples with uncertain species id predictions."""
    for spp_pred in sample.species_prediction:
        software = getattr(spp_pred, "software", None)
        evaluator = SPP_EVALUATORS.get(software)
        if evaluator is None:
            raise NotImplementedError(f"No function for evaluating {software}")

        # spp_pred.result MUST be a list; evaluator will validate non-empty
        result = evaluator(spp_pred.result)
        if not result.passed:
            # Consider adding details into the tag (label/description/metadata)
            tag = Tag(
                type=TagType.QC,
                label="Contamination or Uncertain Species Prediction",
                description=(
                    f"{result.software}/{result.species}: {result.reason} "
                    f"(see thresholds.toml)"
                ),
                severity=TagSeverity.WARNING,
            )
            tags.append(tag)


# Tagging functions with the species they are applicable for
ALL_TAG_FUNCS = [
    {"species": ["Staphylococcus aureus"], "func": add_pvl},
    {"species": ["Staphylococcus aureus"], "func": add_mrsa},
    {"species": ["Escherichia coli"], "func": add_stx_type},
    {"species": ["Escherichia coli"], "func": add_oh_type},
    {
        "species": [
            "Escherichia coli",
            "Klebsiella pneumoniae",
            "Shigella sonnei",
            "Shigella dysenteriae",
        ],
        "func": add_shigella_typing,
    },
    {
        "species": "all",
        "func": flag_uncertain_spp_prediction,
    },
]


def compute_phenotype_tags(sample: SampleInDatabase) -> TagList:
    """Compute tags based on bracken phenotype prediction."""
    tags = []
    # iterate over tag functions to build up list of tags
    for tag_func in ALL_TAG_FUNCS:
        # bracken should always be included regardless of specie.
        try:
            spp_res = next(
                (
                    pred
                    for pred in sample.species_prediction
                    if pred.software == "bracken"
                )
            )
        except StopIteration as error:
            raise ValueError(
                f"No Bracken spp result for sample {sample.sample_id}"
            ) from error
        major_spp = spp_res.result[0].scientific_name
        LOG.debug("Major spp %s in %s", major_spp, str(tag_func["species"]))
        if major_spp in tag_func["species"] or tag_func["species"] == "all":
            tag_func["func"](tags, sample)
    return tags
