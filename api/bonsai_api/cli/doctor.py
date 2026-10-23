"""Write doctor findings to a table and print summary statistics."""

import asyncio
import csv
from collections import Counter
from typing import TextIO

import click

from bonsai_api.doctor import DoctorReport, run_check


@click.command()
@click.option(
    "-o",
    "--output",
    required=True,
    type=click.File("w", encoding="utf-8", lazy=False),
    help="Write the full report as a tab-separated table to this path.",
)
@click.pass_context
def doctor(ctx: click.Context, output: TextIO):
    """Check all samples and write potential issues to a TSV report."""

    def show_progress(message: str):
        click.echo(message, err=True)

    try:
        report = asyncio.run(run_check(progress=show_progress))
    except Exception as error:
        report = DoctorReport(errors=[f"Sample checks could not complete: {error}"])

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
    try:
        writer = csv.DictWriter(
            output, fieldnames=columns, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for finding in report.findings:
            writer.writerow({"status": "issue", **finding.model_dump()})
        for error in report.errors:
            writer.writerow({"status": "incomplete", "message": error})
        output.flush()
    except OSError as error:
        raise click.ClickException(f"Could not write report: {error}") from error

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
    click.echo(f"Report written to: {output.name}")
    ctx.exit(report.exit_code)
