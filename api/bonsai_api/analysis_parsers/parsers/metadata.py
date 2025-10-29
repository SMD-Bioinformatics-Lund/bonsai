"""Parse metadata passed to pipeline."""

import json
import logging
from datetime import datetime
from typing import Any

from Bio import SeqIO

from ..models.metadata import (
    MetaEntry,
    PipelineInfo,
    SequencingInfo,
    SoupVersion,
    TableMetadataEntry,
)

LOG = logging.getLogger(__name__)


def get_database_info(software_info: list[str]) -> list[SoupVersion]:
    """Get database or software information.

    :param software_info: list of file objects for db records.
    :type software_info: list[str]
    :return: Description of software or database version.
    :rtype: list[SoupVersion]
    """
    db_info = []
    for soup_filepath in software_info:
        with open(soup_filepath, "r", encoding="utf-8") as soup:
            dbs = json.load(soup)
            if isinstance(dbs, (list, tuple)):
                for db in dbs:
                    db_info.append(SoupVersion(**db))
            else:
                db_info.append(SoupVersion(**dbs))
    return db_info


def parse_date_from_run_id(run_id: str) -> datetime | None:
    """
    Get the date of sequencing from run id as datetime object.

    XXX_20240112 -> 2024-01-12
    """
    err_msg = "Unrecognized format of run_id, sequence time cant be determined"
    if "_" not in run_id:
        LOG.warning(err_msg)
        return None
    # parse date string
    try:
        seq_date = datetime.strptime(run_id.split("_")[0], r"%y%m%d")
    except ValueError:
        LOG.warning(err_msg)
        seq_date = None
    return seq_date


def parse_run_info(
    run_metadata: str, software_info: list[str]
) -> tuple[dict[str, Any], SequencingInfo, PipelineInfo]:
    """Parse nextflow analysis information.

    :param run_metadata: Nextflow analysis metadata in json format.
    :type run_metadata: str
    :return: Analysis metadata record.
    :rtype: RunMetadata
    """
    LOG.info("Parse run metadata.")
    with open(run_metadata, encoding="utf-8") as jsonfile:
        run_info = json.load(jsonfile)
    # get sample info
    sample_info = {
        "sample_name": run_info["sample_name"],
        "lims_id": run_info["lims_id"],
    }
    # get sequencing info
    seq_info = SequencingInfo(
        run_id=run_info["sequencing_run"],
        platform=run_info["sequencing_platform"],
        instrument=None,
        method={"method": run_info["sequencing_type"]},
        date=parse_date_from_run_id(run_info["sequencing_run"]),
    )
    # get pipeline info
    soup_versions = get_database_info(software_info)
    pipeline_info = PipelineInfo(
        pipeline=run_info["pipeline"],
        version=run_info["version"],
        commit=run_info["commit"],
        analysis_profile=run_info["analysis_profile"],
        assay=run_info["assay"],
        release_life_cycle=run_info["release_life_cycle"],
        configuration_files=run_info["configuration_files"],
        workflow_name=run_info["workflow_name"],
        command=run_info["command"],
        softwares=soup_versions,
        date=datetime.fromisoformat(run_info["date"]),
    )
    return sample_info, seq_info, pipeline_info


def get_gb_genome_version(fasta_path: str) -> str:
    """Retrieve genbank genome version"""
    record = next(SeqIO.parse(fasta_path, "fasta"))
    return record.id, record.description.rstrip(", complete genome")


def process_custom_metadata(metadata: list[MetaEntry]) -> list[MetaEntry]:
    """Processing of custom metadata entries."""
    proc_meta: list[MetaEntry] = []
    for record in metadata:
        # read csv file content to string.
        if isinstance(record, TableMetadataEntry):
            with open(record.value) as inpt:
                upd_model = record.model_copy(update={"value": inpt.read()})
            proc_meta.append(upd_model)
        else:
            proc_meta.append(record)
    return proc_meta
