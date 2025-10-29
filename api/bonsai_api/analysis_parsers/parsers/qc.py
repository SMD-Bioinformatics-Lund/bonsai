"""Parse output of QC tools."""

import csv
import json
import logging
import os
import subprocess
from typing import Any, TextIO

import pandas as pd
import numpy as np
import pysam

from ..models.qc import (
    GambitcoreQcResult,
    PostAlignQcResult,
    QcMethodIndex,
    QcSoftware,
    QuastQcResult,
    NanoPlotQcResult,
)

OptionalFile = TextIO | None

LOG = logging.getLogger(__name__)


class QC:
    """Class for retrieving qc results"""

    def __init__(
        self,
        sample_id: str,
        bam: str,
        reference: str,
        cpus: int,
        bed: str | None = None,
        baits: str | None = None,
    ):
        self.results: dict[str, Any] = {}
        self.bam = bam
        self.bed = bed
        self.sample_id = sample_id
        self.cpus = cpus
        self.baits = baits
        self.reference = reference
        self.paired = self.is_paired()
        self.rm_files = True

    def write_json_result(self, json_result: dict, output_filepath: str) -> None:
        """Write out json file"""
        with open(output_filepath, "w", encoding="utf-8") as json_file:
            json.dump(json_result, json_file, indent=4)

    def convert2intervals(self, bed_baits: str, dict_file: str) -> None:
        """Convert files to interval lists"""
        bed2int_cmd = [
            "java",
            "-jar",
            "/usr/bin/picard.jar",
            "BedToIntervalList",
            "-I",
            bed_baits,
            "-O",
            f"{bed_baits}.interval_list",
            "-SD",
            dict_file,
        ]
        self.system_p(bed2int_cmd)

    def parse_hsmetrics(self, hsmetrics: str) -> None:
        """Parse hs metrics"""
        with open(hsmetrics, "r", encoding="utf-8") as fin:
            for line in fin:
                if line.startswith("## METRICS CLASS"):
                    next(fin)
                    vals = next(fin).split("\t")
                    self.results["pct_on_target"] = vals[18]
                    self.results["fold_enrichment"] = vals[26]
                    self.results["median_coverage"] = vals[23]
                    self.results["fold_80"] = vals[33]
                    break

    def parse_ismetrics(self, ismetrics: str) -> None:
        """Parse insert size metrics"""
        with open(ismetrics, "r", encoding="utf-8") as ins:
            for line in ins:
                if line.startswith("## METRICS CLASS"):
                    next(ins)
                    vals = next(ins).split("\t")
                    self.results["ins_size"] = vals[5]
                    self.results["ins_size_dev"] = vals[6]
                    break

    def parse_basecov_bed(self, basecov_fpath: str, thresholds: list[str]) -> None:
        """Parse base coverage bed file using pandas"""
        df = pd.read_csv(basecov_fpath, sep="\t", comment="#", header=0)

        tot_bases = len(df)
        pct_above = {
            min_val: len(df[df["COV"] >= int(min_val)]) for min_val in thresholds
        }
        pct_above = {
            min_val: 100 * (pct_above[min_val] / tot_bases) for min_val in thresholds
        }

        mean_cov = df["COV"].mean()

        # Calculate the inter-quartile range / median (IQR/median)
        quartile1 = df["COV"].quantile(0.25)
        median_cov = df["COV"].median()
        quartile3 = df["COV"].quantile(0.75)
        iqr = quartile3 - quartile1

        coverage_uniformity = (
            iqr / median_cov if quartile1 and quartile3 and median_cov else None
        )

        self.results["pct_above_x"] = pct_above
        self.results["mean_cov"] = mean_cov
        self.results["coverage_uniformity"] = coverage_uniformity
        self.results["quartile1"] = quartile1
        self.results["median_cov"] = median_cov
        self.results["quartile3"] = quartile3

    def is_paired(self) -> bool:
        """Check if reads are paired"""
        bam_file = pysam.AlignmentFile(self.bam)
        for i, read in enumerate(bam_file):
            if read.is_paired:
                return True
            if i >= 1000:
                break
        # If no paired reads are found in the
        # first 1000 reads or read is None
        # return False
        return False

    def system_p(self, cmd: list[str]) -> None:
        """Execute subprocess"""
        LOG.info("RUNNING: %s", " ".join(cmd))
        result = subprocess.run(cmd, check=True, text=True)
        if result.stderr:
            print(f"stderr: {result.stderr}")
        if result.stdout:
            print(f"stdout: {result.stdout}")

    def run(self) -> dict:
        """Run QC info extraction"""
        if self.baits and self.reference:
            LOG.info("Calculating HS-metrics...")
            dict_file = self.reference
            if not dict_file.endswith(".dict"):
                dict_file += ".dict"

            # Convert bed/baits file to interval list
            if not os.path.isfile(f"{self.bed}.interval_list"):
                self.convert2intervals(self.bed, dict_file)
            if not os.path.isfile(f"{self.baits}.interval_list"):
                self.convert2intervals(self.baits, dict_file)

            # Run picard hsmetrics command
            hsmet_cmd: list[str] = [
                "java",
                "-jar",
                "/usr/bin/picard.jar",
                "CollectHsMetrics",
                "-I",
                self.bam,
                "-O",
                f"{self.bam}.hsmetrics",
                "-R",
                self.reference,
                "-BAIT_INTERVALS",
                f"{self.baits}.interval_list",
                "-TARGET_INTERVALS",
                f"{self.bed}.interval_list",
            ]
            self.system_p(hsmet_cmd)

            # Parse hsmetrics output file
            self.parse_hsmetrics(f"{self.bam}.hsmetrics")

        # Collect basic sequencing statistics
        LOG.info("Collecting basic stats...")
        sambamba_flagstat_cmd = (
            f"sambamba flagstat {'-t '+ str(self.cpus) if self.cpus else ''} {self.bam}"
        )
        flagstat = subprocess.check_output(
            sambamba_flagstat_cmd, shell=True, text=True
        ).splitlines()
        n_reads = int(flagstat[0].split()[0])
        n_dup_reads = int(flagstat[3].split()[0])
        n_mapped_reads = int(flagstat[4].split()[0])
        n_read_pairs = int(flagstat[5].split()[0])

        # Get insert size metrics
        if self.paired:
            LOG.info("Collect insert sizes...")
            cmd: list[str] = [
                "java",
                "-jar",
                "/usr/bin/picard.jar",
                "CollectInsertSizeMetrics",
                "-I",
                self.bam,
                "-O",
                f"{self.bam}.inssize",
                "-H",
                f"{self.bam}.ins.pdf",
                "-STOP_AFTER",
                "1000000",
            ]
            self.system_p(cmd)

            # Parse ismetrics output file
            self.parse_ismetrics(f"{self.bam}.inssize")

            if self.rm_files:
                # Remove ismetrics files
                os.remove(f"{self.bam}.inssize")
                os.remove(f"{self.bam}.ins.pdf")

        out_prefix = f"{self.bam}_postalnQC"
        thresholds = ["1", "10", "30", "100", "250", "500", "1000"]

        # Index bam file if .bai does not exist
        if not os.path.exists(f"{self.bam}.bai"):
            LOG.info("Indexing bam file: %s.bai", self.bam)
            sambamba_index_cmd = ["sambamba", "index", self.bam]
            self.system_p(sambamba_index_cmd)

        # Generate sambamba depth command
        LOG.info("Collecting depth stats...")
        sambamba_depth_cmd = ["sambamba", "depth", "base", "-c", "0"]
        if self.cpus:
            sambamba_depth_cmd.extend(["-t", str(self.cpus)])
        if self.bed:
            sambamba_depth_cmd.extend(["-L", self.bed])
        sambamba_depth_cmd.extend([self.bam, "-o", f"{out_prefix}.basecov.bed"])
        self.system_p(sambamba_depth_cmd)

        # Parse base coverage file
        self.parse_basecov_bed(f"{out_prefix}.basecov.bed", thresholds)
        if self.rm_files:
            # Remove base coverage file
            os.remove(f"{out_prefix}.basecov.bed")

        self.results["n_reads"] = n_reads
        self.results["n_mapped_reads"] = n_mapped_reads
        self.results["n_read_pairs"] = n_read_pairs
        self.results["n_dup_reads"] = n_dup_reads
        self.results["dup_pct"] = n_dup_reads / n_mapped_reads
        self.results["sample_id"] = self.sample_id

        return self.results


def parse_quast_results(tsv_fpath: str) -> QcMethodIndex:
    """Parse quast file and extract relevant metrics.

    Args:
        sep (str): seperator

    Returns:
        QuastQcResult: list of key-value pairs
    """
    LOG.info("Parsing tsv file: %s", tsv_fpath)
    with open(tsv_fpath, "r", encoding="utf-8") as tsvfile:
        creader = csv.reader(tsvfile, delimiter="\t")
        header = next(creader)
        raw = [dict(zip(header, row)) for row in creader]
        qc_res = QuastQcResult(
            total_length=int(raw[0]["Total length"]),
            reference_length=raw[0].get("Reference length", None),
            largest_contig=raw[0]["Largest contig"],
            n_contigs=raw[0]["# contigs"],
            n50=raw[0]["N50"],
            ng50=raw[0].get("NG50", None),
            assembly_gc=raw[0]["GC (%)"],
            reference_gc=raw[0].get("Reference GC (%)", None),
            duplication_ratio=raw[0].get("Duplication ratio", None),
        )
    return QcMethodIndex(software=QcSoftware.QUAST, result=qc_res)


def parse_postalignqc_results(postalignqc_fpath: str) -> QcMethodIndex:
    """Parse postalignqc json file and extract relevant metrics.

    Args:
        sep (str): seperator

    Returns:
        PostAlignQc: list of key-value pairs
    """
    LOG.info("Parsing json file: %s", postalignqc_fpath)
    with open(postalignqc_fpath, "r", encoding="utf-8") as jsonfile:
        qc_dict = json.load(jsonfile)
        qc_res = PostAlignQcResult(
            ins_size=(
                None if "ins_size" not in qc_dict else int(float(qc_dict["ins_size"]))
            ),
            ins_size_dev=(
                None
                if "ins_size_dev" not in qc_dict
                else int(float(qc_dict["ins_size_dev"]))
            ),
            mean_cov=int(qc_dict["mean_cov"]),
            pct_above_x=qc_dict["pct_above_x"],
            n_reads=int(qc_dict["n_reads"]),
            n_mapped_reads=int(qc_dict["n_mapped_reads"]),
            n_read_pairs=int(qc_dict["n_read_pairs"]),
            coverage_uniformity=(
                float(qc_dict["coverage_uniformity"])
                if qc_dict.get("coverage_uniformity") is not None
                else None
            ),
            quartile1=float(qc_dict["quartile1"]),
            median_cov=float(qc_dict["median_cov"]),
            quartile3=float(qc_dict["quartile3"]),
        )
    return QcMethodIndex(software=QcSoftware.POSTALIGNQC, result=qc_res)


def parse_alignment_results(
    sample_id: str,
    bam: TextIO,
    reference: TextIO,
    cpus: int,
    output: TextIO,
    bed: OptionalFile = None,
    baits: OptionalFile = None,
) -> None:
    """Parse bam file and extract relevant metrics"""
    LOG.info("Parsing bam file: %s", bam.name)
    qc = QC(
        sample_id,
        bam.name,
        reference.name,
        cpus,
        getattr(bed, "name", None),
        getattr(baits, "name", None),
    )
    qc_dict = qc.run()
    LOG.info("Storing results to: %s", output.name)
    qc.write_json_result(qc_dict, output.name)


def parse_gambitcore_results(gambitcore_fpath: str) -> QcMethodIndex:
    """Parse assembly completion prediction result.

    Args:
        sep (str): seperator

    Returns:
        GambitcoreQcResult: list of key-value pairs
    """
    LOG.info("Parsing tsv file: %s", gambitcore_fpath)
    columns = {
        "Species": "scientific_name",
        "Completeness (%)": "completeness",
        "Assembly Core/species Core": "assembly_core",
        "Closest accession": "closest_accession",
        "Closest distance": "closest_distance",
        "Assembly Kmers": "assembly_kmers",
        "Species Kmers Mean": "species_kmers_mean",
        "Species Kmers Std Dev": "species_kmers_std_dev",
        "Assembly QC": "assembly_qc",
    }

    gambitcore_loa = (
        pd.read_csv(gambitcore_fpath, sep="\t", na_values=["NA"])
        .replace(np.nan, None)
        .rename(columns=columns)
        .to_dict(orient="records")
    )
    gambitcore_hit = gambitcore_loa[0] if gambitcore_loa else {}

    completeness = gambitcore_hit.get("completeness")

    gambitcore_result = GambitcoreQcResult(
        scientific_name=gambitcore_hit.get("scientific_name"),
        completeness=float(completeness.rstrip("%")) if completeness else None,
        assembly_core=gambitcore_hit.get("assembly_core"),
        closest_accession=gambitcore_hit.get("closest_accession"),
        closest_distance=gambitcore_hit.get("closest_distance"),
        assembly_kmers=gambitcore_hit.get("assembly_kmers"),
        species_kmers_mean=gambitcore_hit.get("species_kmers_mean"),
        species_kmers_std_dev=gambitcore_hit.get("species_kmers_std_dev"),
        assembly_qc=gambitcore_hit.get("assembly_qc", "red"),
    )

    return QcMethodIndex(
        software=QcSoftware.GAMBITCORE,
        result=gambitcore_result,
    )


def parse_nanoplot_results(nanoplot_fpath: str) -> QcMethodIndex:
    """Parse NanoPlot QC results.

    Args:
        path: Path to NanoStats.txt file

    Returns:
        QcMethodIndex with NanoPlot results
    """
    LOG.info("Parsing NanoPlot results")

    with open(nanoplot_fpath) as fh:
        # Skip the first line (header)
        next(fh)
        nanoplot_dict = {}
        
        # Parse only first set of metrics
        for _ in range(8):
            line = next(fh).strip()
            key, value = line.split(":", 1)
            value = float(value.strip().replace(",", ""))
            key = key.lower().strip().replace(" ", "_")
            nanoplot_dict[key] = value

    result = NanoPlotQcResult(
        mean_read_length=nanoplot_dict["mean_read_length"],
        mean_read_quality=nanoplot_dict["mean_read_quality"],
        median_read_length=nanoplot_dict["median_read_length"],
        median_read_quality=nanoplot_dict["median_read_quality"],
        number_of_reads=nanoplot_dict["number_of_reads"],
        read_length_n50=nanoplot_dict["read_length_n50"],
        stdev_read_length=nanoplot_dict["stdev_read_length"],
        total_bases=nanoplot_dict["total_bases"]
    )

    return QcMethodIndex(
        software=QcSoftware.NANOPLOT,
        result=result
    )


