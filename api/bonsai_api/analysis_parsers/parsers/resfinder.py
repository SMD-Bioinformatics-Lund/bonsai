"""Parse resfinder results."""

import logging
from itertools import chain
from typing import Any

from ..models.base import ParserOutput
from ..models.phenotype import (
    AMRMethodIndex,
    AnnotationType,
    ElementAmrSubtype,
    ElementStressSubtype,
    ElementType,
    ElementTypeResult,
    PhenotypeInfo,
)
from ..models.phenotype import PredictionSoftware as Software
from ..models.phenotype import (
    ResfinderGene,
    ResfinderVariant,
    StressMethodIndex,
    VariantSubType,
    VariantType,
)
from .utils import get_nt_change

from ..registry import register_parser

LOG = logging.getLogger(__name__)

STRESS_FACTORS = {
    ElementStressSubtype.BIOCIDE: [
        "formaldehyde",
        "benzylkonium chloride",
        "ethidium bromide",
        "chlorhexidine",
        "cetylpyridinium chloride",
        "hydrogen peroxide",
    ],
    ElementStressSubtype.HEAT: ["temperature"],
}


def lookup_antibiotic_class(antibiotic: str) -> str:
    """Lookup antibiotic class for antibiotic name.

    Antibiotic classes are sourced from resfinder db v2.2.1
    """
    lookup_table = {
        "unknown aminocyclitol": "aminocyclitol",
        "spectinomycin": "aminocyclitol",
        "unknown aminoglycoside": "aminoglycoside",
        "gentamicin": "aminoglycoside",
        "gentamicin c": "aminoglycoside",
        "tobramycin": "aminoglycoside",
        "streptomycin": "aminoglycoside",
        "amikacin": "aminoglycoside",
        "kanamycin": "aminoglycoside",
        "kanamycin a": "aminoglycoside",
        "neomycin": "aminoglycoside",
        "paromomycin": "aminoglycoside",
        "kasugamycin": "aminoglycoside",
        "g418": "aminoglycoside",
        "capreomycin": "aminoglycoside",
        "isepamicin": "aminoglycoside",
        "dibekacin": "aminoglycoside",
        "lividomycin": "aminoglycoside",
        "ribostamycin": "aminoglycoside",
        "butiromycin": "aminoglycoside",
        "butirosin": "aminoglycoside",
        "hygromycin": "aminoglycoside",
        "netilmicin": "aminoglycoside",
        "apramycin": "aminoglycoside",
        "sisomicin": "aminoglycoside",
        "arbekacin": "aminoglycoside",
        "astromicin": "aminoglycoside",
        "fortimicin": "aminoglycoside",
        "unknown analog of d-alanine": "analog of d-alanine",
        "d-cycloserine": "analog of d-alanine",
        "unknown beta-lactam": "beta-lactam",
        "amoxicillin": "beta-lactam",
        "amoxicillin+clavulanic acid": "beta-lactam",
        "ampicillin": "beta-lactam",
        "ampicillin+clavulanic acid": "beta-lactam",
        "aztreonam": "beta-lactam",
        "cefazolin": "beta-lactam",
        "cefepime": "beta-lactam",
        "cefixime": "beta-lactam",
        "cefotaxime": "beta-lactam",
        "cefotaxime+clavulanic acid": "beta-lactam",
        "cefoxitin": "beta-lactam",
        "ceftaroline": "beta-lactam",
        "ceftazidime": "beta-lactam",
        "ceftazidime+avibactam": "beta-lactam",
        "ceftriaxone": "beta-lactam",
        "cefuroxime": "beta-lactam",
        "cephalothin": "beta-lactam",
        "ertapenem": "beta-lactam",
        "imipenem": "beta-lactam",
        "meropenem": "beta-lactam",
        "penicillin": "beta-lactam",
        "piperacillin": "beta-lactam",
        "piperacillin+tazobactam": "beta-lactam",
        "temocillin": "beta-lactam",
        "ticarcillin": "beta-lactam",
        "ticarcillin+clavulanic acid": "beta-lactam",
        "cephalotin": "beta-lactam",
        "piperacillin+clavulanic acid": "beta-lactam",
        "unknown diarylquinoline": "diarylquinoline",
        "bedaquiline": "diarylquinoline",
        "unknown quinolone": "quinolone",
        "ciprofloxacin": "quinolone",
        "nalidixic acid": "quinolone",
        "fluoroquinolone": "quinolone",
        "unknown folate pathway antagonist": "folate pathway antagonist",
        "sulfamethoxazole": "folate pathway antagonist",
        "trimethoprim": "folate pathway antagonist",
        "unknown fosfomycin": "fosfomycin",
        "fosfomycin": "fosfomycin",
        "unknown glycopeptide": "glycopeptide",
        "vancomycin": "glycopeptide",
        "teicoplanin": "glycopeptide",
        "bleomycin": "glycopeptide",
        "unknown ionophores": "ionophores",
        "narasin": "ionophores",
        "salinomycin": "ionophores",
        "maduramicin": "ionophores",
        "unknown iminophenazine": "iminophenazine",
        "clofazimine": "iminophenazine",
        "unknown isonicotinic acid hydrazide": "isonicotinic acid hydrazide",
        "isoniazid": "isonicotinic acid hydrazide",
        "unknown lincosamide": "lincosamide",
        "lincomycin": "lincosamide",
        "clindamycin": "lincosamide",
        "unknown macrolide": "macrolide",
        "carbomycin": "macrolide",
        "azithromycin": "macrolide",
        "oleandomycin": "macrolide",
        "spiramycin": "macrolide",
        "tylosin": "macrolide",
        "telithromycin": "macrolide",
        "erythromycin": "macrolide",
        "unknown nitroimidazole": "nitroimidazole",
        "metronidazole": "nitroimidazole",
        "unknown oxazolidinone": "oxazolidinone",
        "linezolid": "oxazolidinone",
        "unknown amphenicol": "amphenicol",
        "chloramphenicol": "amphenicol",
        "florfenicol": "amphenicol",
        "unknown pleuromutilin": "pleuromutilin",
        "tiamulin": "pleuromutilin",
        "unknown polymyxin": "polymyxin",
        "colistin": "polymyxin",
        "unknown pseudomonic acid": "pseudomonic acid",
        "mupirocin": "pseudomonic acid",
        "unknown rifamycin": "rifamycin",
        "rifampicin": "rifamycin",
        "unknown salicylic acid - anti-folate": "salicylic acid - anti-folate",
        "para-aminosalicyclic acid": "salicylic acid - anti-folate",
        "unknown steroid antibacterial": "steroid antibacterial",
        "fusidic acid": "steroid antibacterial",
        "unknown streptogramin a": "streptogramin a",
        "dalfopristin": "streptogramin a",
        "pristinamycin iia": "streptogramin a",
        "virginiamycin m": "streptogramin a",
        "quinupristin+dalfopristin": "streptogramin a",
        "unknown streptogramin b": "streptogramin b",
        "quinupristin": "streptogramin b",
        "pristinamycin ia": "streptogramin b",
        "virginiamycin s": "streptogramin b",
        "unknown synthetic"
        "derivative of nicotinamide": "synthetic derivative"
        " of nicotinamide",
        "pyrazinamide": "synthetic derivative of nicotinamide",
        "unknown tetracycline": "tetracycline",
        "tetracycline": "tetracycline",
        "doxycycline": "tetracycline",
        "minocycline": "tetracycline",
        "tigecycline": "tetracycline",
        "unknown thioamide": "thioamide",
        "ethionamide": "thioamide",
        "unknown unspecified": "unspecified",
        "ethambutol": "unspecified",
        "cephalosporins": "under_development",
        "carbapenem": "under_development",
        "norfloxacin": "under_development",
        "ceftiofur": "under_development",
    }
    return lookup_table.get(antibiotic, "unknown")


def _assign_res_subtype(
    prediction: dict[str, Any], element_type: ElementType
) -> ElementStressSubtype | None:
    """Assign element subtype from resfindere prediction."""
    assigned_subtype = None
    if element_type == ElementType.STRESS:
        for sub_type, phenotypes in STRESS_FACTORS.items():
            # get intersection of subtype phenotypes and predicted phenos
            intersect = set(phenotypes) & set(prediction["phenotypes"])
            if len(intersect) > 0:
                assigned_subtype = sub_type
    elif element_type == ElementType.AMR:
        assigned_subtype = ElementAmrSubtype.AMR
    else:
        LOG.warning("Dont know how to assign subtype for %s", element_type)
    return assigned_subtype


def _get_resfinder_amr_sr_profie(resfinder_result, limit_to_phenotypes=None):
    """Get resfinder susceptibility/resistance profile."""
    susceptible = set()
    resistant = set()
    for phenotype in resfinder_result["phenotypes"].values():
        # skip phenotype if its not part of the desired category
        if (
            limit_to_phenotypes is not None
            and phenotype["key"] not in limit_to_phenotypes
        ):
            continue

        if "amr_resistant" in phenotype.keys():
            if phenotype["amr_resistant"]:
                resistant.add(phenotype["amr_resistance"])
            else:
                susceptible.add(phenotype["amr_resistance"])
    return {"susceptible": list(susceptible), "resistant": list(resistant)}


def _parse_resfinder_amr_genes(
    resfinder_result, limit_to_phenotypes=None
) -> list[ResfinderGene]:
    """Get resistance genes from resfinder result."""
    results = []
    for info in resfinder_result["seq_regions"].values():
        # Get only acquired resistance genes
        if not info["ref_database"][0].startswith("Res"):
            continue

        # Get only genes of desired phenotype
        if limit_to_phenotypes is not None:
            intersect = set(info["phenotypes"]) & set(limit_to_phenotypes)
            if len(intersect) == 0:
                continue

        # get element type by peeking at first phenotype
        first_pheno = info["phenotypes"][0]
        res_category = ElementType(
            resfinder_result["phenotypes"][first_pheno]["category"].upper()
        )
        element_subtype = _assign_res_subtype(info, res_category)

        # format phenotypes
        phenotype = [
            PhenotypeInfo(
                type=res_category,
                name=phe,
                group=lookup_antibiotic_class(phe),
                annotation_type=AnnotationType.TOOL,
                annotation_author=Software.RESFINDER.value,
                reference=info["pmids"],
            )
            for phe in info["phenotypes"]
        ]

        # store results
        gene = ResfinderGene(
            # info
            gene_symbol=info["name"],
            accession=info["ref_acc"],
            element_type=res_category,
            element_subtype=element_subtype,
            phenotypes=phenotype,
            # position
            ref_start_pos=info["ref_start_pos"],
            ref_end_pos=info["ref_end_pos"],
            ref_gene_length=info["ref_seq_length"],
            alignment_length=info["alignment_length"],
            # prediction
            depth=info["depth"],
            identity=info["identity"],
            coverage=info["coverage"],
        )
        results.append(gene)
    # sort genes
    genes = sorted(results, key=lambda entry: (entry.gene_symbol, entry.coverage))
    return genes


def _parse_resfinder_amr_variants(
    resfinder_result, limit_to_phenotypes=None
) -> tuple[ResfinderVariant, ...]:
    """Get resistance genes from resfinder result."""
    # get prediction method
    prediction_method = None
    for exec_info in resfinder_result["software_executions"].values():
        prediction_method = exec_info["parameters"]["method"]

    # parse prediction result
    results = []
    for var_id, info in enumerate(resfinder_result["seq_variations"].values(), start=1):
        # Get only variants from desired phenotypes
        if limit_to_phenotypes is not None:
            if len(set(info["phenotypes"]) & set(limit_to_phenotypes)) == 0:
                continue
        # get gene depth
        if "seq_regions" in resfinder_result:
            info["depth"] = resfinder_result["seq_regions"][info["seq_regions"][0]][
                "depth"
            ]
        else:
            info["depth"] = 0
        # translate variation type bools into classifier
        if info["substitution"]:
            var_sub_type = VariantSubType.SUBSTITUTION
        elif info["insertion"]:
            var_sub_type = VariantSubType.INSERTION
        elif info["deletion"]:
            var_sub_type = VariantSubType.DELETION
        else:
            raise ValueError("Output has no known mutation type")

        # get gene symbol and accession nr
        gene_symbol, _, gene_accnr = info["seq_regions"][0].split(";;")

        ref_nt, alt_nt = get_nt_change(info["ref_codon"], info["var_codon"])
        phenotype = [
            PhenotypeInfo(
                type=ElementType.AMR,
                group=lookup_antibiotic_class(phe),
                name=phe,
                annotation_type=AnnotationType.TOOL,
            )
            for phe in info["phenotypes"]
        ]
        variant = ResfinderVariant(
            id=var_id,
            variant_type=VariantType.SNV,
            variant_subtype=var_sub_type,
            phenotypes=phenotype,
            # position
            reference_sequence=gene_symbol,
            accession=gene_accnr,
            start=info["ref_start_pos"],
            end=info["ref_end_pos"],
            ref_nt=ref_nt,
            alt_nt=alt_nt,
            ref_aa=info["ref_aa"],
            alt_aa=info["var_aa"],
            # consequense
            depth=info["depth"],
            method=prediction_method,
            passed_qc=True,  # resfinder only presents variants passing qc
        )
        results.append(variant)
    # sort variants
    variants = sorted(
        results, key=lambda entry: (entry.reference_sequence, entry.start)
    )
    return variants


def parse_amr_pred(
    prediction: dict[str, Any], resistance_category: ElementType
) -> AMRMethodIndex:
    """Parse resfinder resistance prediction results."""
    # resfinder missclassifies resistance the param amr_category by setting all to amr
    LOG.info("Parsing resistance prediction")
    # parse resistance based on the category
    stress_factors = list(chain(*STRESS_FACTORS.values()))
    categories = {
        ElementType.STRESS: stress_factors,
        ElementType.AMR: list(set(prediction["phenotypes"]) - set(stress_factors)),
    }
    # parse resistance
    sr_profile = _get_resfinder_amr_sr_profie(
        prediction, categories[resistance_category]
    )
    res_genes = _parse_resfinder_amr_genes(prediction, categories[resistance_category])
    res_mut = _parse_resfinder_amr_variants(prediction, categories[resistance_category])
    resistance = ElementTypeResult(
        phenotypes=sr_profile, genes=res_genes, variants=res_mut
    )
    if resistance_category == ElementType.AMR:
        return AMRMethodIndex(
            type=resistance_category, software=Software.RESFINDER, result=resistance
        )

    return StressMethodIndex(
        type=resistance_category, software=Software.RESFINDER, result=resistance
    )


@register_parser("resfinder", "0.0.0")
def parse_amr_pred_v1(
    prediction: dict[str, Any], resistance_category: ElementType
) -> ParserOutput:
    """Parse resfinder resistance prediction results."""
    # resfinder missclassifies resistance the param amr_category by setting all to amr
    LOG.info("Parsing resistance prediction")
    # parse resistance based on the category
    stress_factors = list(chain(*STRESS_FACTORS.values()))
    categories = {
        ElementType.STRESS: stress_factors,
        ElementType.AMR: list(set(prediction["phenotypes"]) - set(stress_factors)),
    }
    # parse resistance
    sr_profile = _get_resfinder_amr_sr_profie(
        prediction, categories[resistance_category]
    )
    res_genes = _parse_resfinder_amr_genes(prediction, categories[resistance_category])
    res_mut = _parse_resfinder_amr_variants(prediction, categories[resistance_category])
    resistance = ElementTypeResult(
        phenotypes=sr_profile, genes=res_genes, variants=res_mut
    )
    if resistance_category == ElementType.AMR:
        out_data = AMRMethodIndex(
            type=resistance_category, software=Software.RESFINDER, result=resistance
        )
    else:
        out_data = StressMethodIndex(
            type=resistance_category, software=Software.RESFINDER, result=resistance
        )
    return ParserOutput(target_field="element_type_result", data=out_data)
