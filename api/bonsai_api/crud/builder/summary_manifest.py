"""Specifies manifest"""

from typing import Annotated

from pydantic import Field

from .types import BuilderArgs, ColumnFull, LookupSpec, Manifest

BuilderSpec = Annotated[BuilderArgs | LookupSpec, Field(discriminator="kind")]

BUILDER_REGISTRY: dict[str, BuilderSpec] = {
    "bracken": BuilderArgs(
        selector={"software": "bracken"}, source_path="species_prediction"
    ),
    "quast": BuilderArgs(selector={"software": "quast"}, source_path="qc_result"),
    "postalignqc": BuilderArgs(selector={"software": "postalignqc"}, source_path="qc_result"),
    "gambit": BuilderArgs(selector={"software": "gambit"}, source_path="qc_result"),
    "mlst": BuilderArgs(
        selector={"software": "mlst"},
        source_path="typing_result",
        exclude_fields=["alleles"],
    ),
    "chewbbaca": BuilderArgs(
        selector={"software": "chewbbaca"},
        source_path="typing_result",
        exclude_fields=["alleles"],
    ),
    "emm": BuilderArgs(
        selector={"software": "emmtyper"},
        source_path="typing_result",
        exclude_fields=["emm_like_alleles"],
    ),
    "stx": BuilderArgs(
        selector={"software": "virulencefinder"}, source_path="typing_result"
    ),
    "o_type": BuilderArgs(
        selector={"software": "serotypefinder", "type": "o_type"},
        source_path="typing_result",
    ),
    "h_type": BuilderArgs(
        selector={"software": "serotypefinder", "type": "h_type"},
        source_path="typing_result",
    ),
    "groups": LookupSpec(
        from_collection="sample_group_collection",
        as_field="groups_info",
        let={"group_ids": {"$ifNull": ["$groups", []]}},
        pipeline=[
            {"$match": {"$expr": {"$in": ["$core.group_id", "$$group_ids"]}}},
            {"$project": {"_id": 0, "id": "$core.group_id", "display_name": "$core.display_name"}},
        ],
    ),
}

MANIFEST = Manifest(
    columns=[
        ColumnFull(id="sample_id", label="Id", path="$sample_id", default_visible=True),
        ColumnFull(
            id="sample_name", label="Name", path="$sample_name", default_visible=True
        ),
        ColumnFull(
            id="lims_id", label="LIMS id", path="$lims_id", default_visible=True
        ),
        ColumnFull(
            id="assay", label="Assay", path="$latest_pipeline_run.assay", default_visible=True
        ),
        ColumnFull(
            id="created_at",
            label="Uploaded",
            path="$created_at",
            default_visible=True,
            type="date",
        ),
        ColumnFull(
            id="qc_status",
            label="QC",
            path="$qc_status",
            default_visible=True,
            type="object",
        ),
        ColumnFull(
            id="groups",
            label="Groups",
            path="$groups_info",
            requires=["groups"],
            default_visible=True,
            type="object",
        ),
        ColumnFull(
            id="comments",
            label="Comments",
            path="$comments",
            default_visible=True,
            type="object",
        ),
        ColumnFull(
            id="release_life_cycle",
            label="Release life cycle",
            path="$latest_pipeline_run.pipeline_info.definition.release_life_cycle",
        ),
        ColumnFull(
            id="sequencing_run",
            label="Sequencing run",
            path="$sequencing.sequencing_run_id",
            default_visible=True,
        ),
        ColumnFull(
            id="sequencing_platform",
            label="Sequencing platform",
            path="$sequencing.platform",
        ),
        ColumnFull(
            id="sequencing_date",
            label="Sequencing date",
            path="$sequencing.sequenced_at",
        ),
        ColumnFull(
            id="pipeline_version", label="Pipeline version", path="$latest_pipeline_run.pipeline_info.definition.version"
        ),
        ColumnFull(
            id="analysis_date",
            label="Analysis date",
            path="$latest_pipeline_run.executed_at",
            type="date",
            default_visible=True,
        ),
        ColumnFull(
            id="tags", label="Tags", path="$tags", type="object", default_visible=True
        ),
        ColumnFull(
            id="bracken_scientific_name",
            requires=["bracken"],
            label="Bracken spp",
            path="$bracken.scientific_name",
            default_visible=True,
        ),
        ColumnFull(id="quast_n50", requires=["quast"], label="N50", path="$quast.n50"),
        ColumnFull(
            id="quast_total_length",
            requires=["quast"],
            label="Total assembly len",
            path="$quast.total_length",
        ),
        ColumnFull(
            id="mlst_sequence_type",
            requires=["mlst"],
            label="MLST ST",
            path="$mlst.sequence_type",
        ),
        ColumnFull(
            id="mlst_scheme",
            requires=["mlst"],
            label="MLST Schema",
            path="$mlst.scheme",
        ),
        ColumnFull(
            id="chewbacca_n_missing",
            requires=["chewbbaca"],
            label="Nr missing cgMLST alleles",
            path="$chewbbaca.n_missing",
        ),
        ColumnFull(
            id="chewbacca_n_novel",
            requires=["chewbbaca"],
            label="Nr novel cgMLST alleles",
            path="$chewbbaca.n_novel",
        ),
        ColumnFull(
            id="emm_type", requires=["emm"], label="EMM Type", path="$emm.emmtype"
        ),
        ColumnFull(
            id="emm_cluster",
            requires=["emm"],
            label="EMM Cluster",
            path="$emm.emm_cluster",
        ),
        ColumnFull(id="stx", requires=["stx"], label="STX", path="$stx"),
        ColumnFull(
            id="postalignqc_pct_above_x",
            requires=["postalignqc"],
            label="Coverage breadth above x",
            path="$postalignqc.pct_above_x",
            type="object",
        ),
        ColumnFull(
            id="postalignqc_mean_cov",
            requires=["postalignqc"],
            label="Mean coverage",
            path="$postalignqc.mean_cov",
            type="number",
        ),
        ColumnFull(
            id="postalignqc_median_cov",
            requires=["postalignqc"],
            label="Median coverage",
            path="$postalignqc.median_cov",
            type="number",
        ),
        ColumnFull(
            id="postalignqc_n_reads",
            requires=["postalignqc"],
            label="Nr Reads",
            path="$postalignqc.n_reads",
            type="number",
        ),
        ColumnFull(
            id="postalignqc_n_mapped_reads",
            requires=["postalignqc"],
            label="Nr Mapped reads",
            path="$postalignqc.n_mapped_reads",
            type="number",
        ),
    ],
)
