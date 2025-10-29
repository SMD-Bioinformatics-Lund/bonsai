"""Parse for input config using parsers from this module."""

import json
import logging
from typing import Any, Sequence

from prp.models.config import SampleConfig

from ..models.phenotype import AMRMethodIndex, ElementType
from ..models.sample import SCHEMA_VERSION, MethodIndex, PipelineResult, QcMethodIndex
from . import (
    amrfinder,
    kraken,
    mykrobe,
    resfinder,
    serotypefinder,
    tbprofiler,
    virulencefinder,
)
from .emmtyper import EmmTypingMethodIndex, parse_emm_pred
from .igv import parse_igv_info
from .metadata import parse_run_info
from .qc import parse_gambitcore_results, parse_postalignqc_results, parse_quast_results, parse_nanoplot_results
from .shigapass import ShigaTypingMethodIndex, parse_shiga_pred
from .sccmec import SccmecTypingMethodIndex, parse_sccmec_results
from .spatyper import SpatyperTypingMethodIndex, parse_spatyper_results
from .typing import parse_cgmlst_results, parse_mlst_results
from .virulencefinder import VirulenceMethodIndex

LOG = logging.getLogger(__name__)


def _read_qc(smp_cnf) -> Sequence[QcMethodIndex]:
    """Read all qc related info"""
    qc_results = []
    if smp_cnf.quast:
        qc_results.append(parse_quast_results(smp_cnf.quast))

    if smp_cnf.postalnqc:
        qc_results.append(parse_postalignqc_results(smp_cnf.postalnqc))

    if smp_cnf.gambitcore:
        qc_results.append(parse_gambitcore_results(smp_cnf.gambitcore))

    if smp_cnf.nanoplot:
        qc_results.append(parse_nanoplot_results(smp_cnf.nanoplot))

    return qc_results


def _read_spp_prediction(smp_cnf) -> Sequence[mykrobe.SppMethodIndex]:
    """Read all species prediction results."""
    spp_results = []
    if smp_cnf.kraken:
        spp_results.append(kraken.parse_result(smp_cnf.kraken))

    if smp_cnf.mykrobe:
        spp_results.append(mykrobe.parse_spp_pred(smp_cnf.mykrobe))
    return spp_results


def _read_typing(
    smp_cnf,
) -> Sequence[
    MethodIndex
    | EmmTypingMethodIndex
    | ShigaTypingMethodIndex
    | SccmecTypingMethodIndex
    | SpatyperTypingMethodIndex
]:
    """Read typing all information."""
    typing_result = []
    if smp_cnf.mlst:
        typing_result.append(parse_mlst_results(smp_cnf.mlst))

    if smp_cnf.chewbbaca:
        typing_result.append(parse_cgmlst_results(smp_cnf.chewbbaca))

    if smp_cnf.emmtyper:
        typing_result.extend(parse_emm_pred(smp_cnf.emmtyper))

    if smp_cnf.shigapass:
        typing_result.append(parse_shiga_pred(smp_cnf.shigapass))

    if smp_cnf.spatyper:
        typing_result.append(parse_spatyper_results(smp_cnf.spatyper))

    if smp_cnf.sccmec:
        typing_result.append(parse_sccmec_results(smp_cnf.sccmec))

    # stx typing
    if smp_cnf.virulencefinder:
        tmp_virfinder_res: MethodIndex | None = virulencefinder.parse_stx_typing(
            smp_cnf.virulencefinder
        )
        if tmp_virfinder_res is not None:
            typing_result.append(tmp_virfinder_res)

    if smp_cnf.serotypefinder:
        LOG.info("Parse serotypefinder results")
        # OH typing
        tmp_serotype_res: list[MethodIndex] | None = serotypefinder.parse_oh_typing(
            smp_cnf.serotypefinder
        )
        if tmp_serotype_res is not None:
            typing_result.extend(tmp_serotype_res)

    if smp_cnf.mykrobe:
        lin_res: MethodIndex | None = mykrobe.parse_lineage_pred(smp_cnf.mykrobe)
        if lin_res is not None:
            typing_result.append(lin_res)

    if smp_cnf.tbprofiler:
        typing_result.append(tbprofiler.parse_lineage_pred(smp_cnf.tbprofiler))

    return typing_result


def _read_resistance(smp_cnf) -> Sequence[AMRMethodIndex]:
    """Read resistance predictions."""
    resistance = []
    if smp_cnf.resfinder:
        with smp_cnf.resfinder.open("r", encoding="utf-8") as resfinder_json:
            pred_res = json.load(resfinder_json)
            for method in [ElementType.AMR, ElementType.STRESS]:
                tmp_res = resfinder.parse_amr_pred(pred_res, method)
                if tmp_res.result.genes:
                    resistance.append(tmp_res)

    if smp_cnf.amrfinder:
        for method in [ElementType.AMR, ElementType.STRESS]:
            tmp_res = amrfinder.parse_amr_pred(smp_cnf.amrfinder, method)
            if tmp_res.result.genes:
                resistance.append(tmp_res)

    if smp_cnf.mykrobe:
        tmp_res = mykrobe.parse_amr_pred(smp_cnf.mykrobe, smp_cnf.sample_id)
        if tmp_res is not None:
            resistance.append(tmp_res)

    if smp_cnf.tbprofiler:
        # store pipeline version
        resistance.append(tbprofiler.parse_amr_pred(smp_cnf.tbprofiler))
    return resistance


def _read_virulence(smp_cnf) -> Sequence[VirulenceMethodIndex]:
    """Read virulence results."""
    virulence = []
    if smp_cnf.amrfinder:
        virulence.append(amrfinder.parse_vir_pred(smp_cnf.amrfinder))

    if smp_cnf.virulencefinder:
        # virulence genes
        raw_res: VirulenceMethodIndex | None = virulencefinder.parse_virulence_pred(
            smp_cnf.virulencefinder
        )
        if raw_res is not None:
            virulence.append(raw_res)
    return virulence


def parse_sample(smp_cnf: SampleConfig) -> PipelineResult:
    """Parse sample config object into a combined result object."""
    sample_info, seq_info, pipeline_info = parse_run_info(
        smp_cnf.nextflow_run_info, smp_cnf.software_info
    )
    results: dict[str, Any] = {
        "sequencing": seq_info,
        "pipeline": pipeline_info,
        "qc": _read_qc(smp_cnf),
        "species_prediction": _read_spp_prediction(smp_cnf),
        "typing_result": _read_typing(smp_cnf),
        "element_type_result": [],
        **sample_info,  # add sample_name & lims_id
    }
    if smp_cnf.ref_genome_sequence:
        ref_genome_info, read_mapping, genome_annotation, filtered_variants = parse_igv_info(
            smp_cnf.ref_genome_sequence,
            smp_cnf.ref_genome_annotation,
            smp_cnf.igv_annotations,
        )
        results["reference_genome"] = ref_genome_info
        results["read_mapping"] = read_mapping
        results["genome_annotation"] = genome_annotation
        results["sv_variants"] = filtered_variants["sv_variants"] if filtered_variants else None
        results["indel_variants"] = filtered_variants["indel_variants"] if filtered_variants else None
        results["snv_variants"] = filtered_variants["snv_variants"] if filtered_variants else None
    # read versions of softwares
    if smp_cnf.mykrobe:
        results["pipeline"].softwares.append(mykrobe.get_version(smp_cnf.mykrobe))
    if smp_cnf.tbprofiler:
        results["pipeline"].softwares.append(tbprofiler.get_version(smp_cnf.tbprofiler))

    # add amr and virulence
    results["element_type_result"].extend(
        [*_read_resistance(smp_cnf), *_read_virulence(smp_cnf)]
    )

    # verify data consistancy
    return PipelineResult(
        sample_id=smp_cnf.sample_id, schema_version=SCHEMA_VERSION, **results
    )
