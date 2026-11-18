"""Report sample integrity findings for interactive and scheduled checks."""

import asyncio
import csv
from collections import Counter

import click

from bonsai_api.doctor import DoctorReport, run_check


def write_tsv(report: DoctorReport, path: str) -> str:
    columns = [
        "status",
        "sample_id",
        "external_sample_id",
        "lims_id",
        "assay",
        "file_type",
        "message",
        "path",
    ]
    with click.open_file(path, "w", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output, fieldnames=columns, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for finding in report.findings:
            writer.writerow({"status": "issue", **finding.model_dump()})
        for error in report.errors:
            writer.writerow({"status": "incomplete", "message": error})
        output.flush()
        return output.name


def show_summary(report: DoctorReport, output_name: str) -> None:
    click.echo(f"Samples checked: {report.checked_samples}")
    click.echo(f"Samples with potential issues: {report.affected_samples}")
    click.echo(f"Findings: {len(report.findings)}")
    click.echo(f"Incomplete checks: {len(report.errors)}")
    if report.findings:
        click.echo("Findings by file type:")
        for file_type, count in sorted(
            Counter(f.file_type for f in report.findings).items()
        ):
            click.echo(f"  {file_type}: {count}")
    if report.errors:
        click.echo("Check incomplete. See the report for details.")
    elif not report.findings:
        click.echo("No issues found")
    click.echo(f"Report written to: {output_name}")


def show_alert(report: DoctorReport, max_samples: int) -> None:
    """Print affected sample IDs and incomplete checks to stderr."""
    labels = {"alignment": "Alignment", "minhash": "MinHash", "ska": "SKA"}
    findings_by_check: dict[str, dict[str, set[str]]] = {}
    for finding in report.findings:
        check = finding.file_type.split("-", 1)[0]
        samples = findings_by_check.setdefault(check, {})
        samples.setdefault(finding.sample_id, set()).add(finding.message)

    for check, samples in sorted(findings_by_check.items()):
        count = len(samples)
        summary = f"{labels.get(check, check)} findings for {count} sample(s)"
        if 0 < max_samples < count:
            summary += f" (showing first {max_samples})"
        click.echo(summary, err=True)
        for sample_id, messages in sorted(samples.items())[:max_samples]:
            click.echo(f"  {sample_id}  {', '.join(sorted(messages))}", err=True)

    if report.errors:
        click.echo("Doctor check incomplete", err=True)
        for error in report.errors:
            click.echo(f"  {error}", err=True)


@click.command()
@click.option(
    "-o",
    "--output",
    metavar="PATH",
    help="Write the full TSV report to this path. Required for TSV format.",
)
@click.option(
    "--format",
    "report_format",
    type=click.Choice(["tsv", "alert"]),
    default="tsv",
    show_default=True,
    help="Write a TSV report or print alerts to stderr for scheduled checks.",
)
@click.option(
    "--include-alignments",
    is_flag=True,
    help="Also check alignment files and their indexes.",
)
@click.option(
    "--max-samples",
    type=click.IntRange(min=0),
    default=50,
    show_default=True,
    help="Maximum sample IDs per check in alert output. Use 0 for counts only.",
)
@click.pass_context
def doctor(
    ctx: click.Context,
    output: str | None,
    report_format: str,
    include_alignments: bool,
    max_samples: int,
):
    """Check SKA and MinHash data for all samples."""
    if report_format == "tsv" and output is None:
        raise click.UsageError("--output is required with --format tsv.")

    def show_progress(message: str):
        click.echo(message, err=True)

    try:
        report = asyncio.run(
            run_check(
                progress=show_progress if report_format == "tsv" else None,
                include_alignments=include_alignments,
            )
        )
    except Exception as error:
        report = DoctorReport(errors=[f"Sample checks could not complete: {error}"])

    if report_format == "alert":
        show_alert(report, max_samples)
    if output is not None:
        try:
            output_name = write_tsv(report, output)
        except OSError as error:
            click.echo(f"Error: Could not write report: {error}", err=True)
            ctx.exit(2)
        if report_format == "tsv":
            show_summary(report, output_name)
    ctx.exit(report.exit_code)
