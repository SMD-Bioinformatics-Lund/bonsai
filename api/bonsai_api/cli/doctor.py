"""Print potential sample data problems from the API container."""

import asyncio
from itertools import groupby

import click

from bonsai_api.doctor import DoctorReport, run_check


@click.command()
@click.pass_context
def doctor(ctx: click.Context):
    """Check all samples for potentially missing alignment and index data."""
    try:
        report = asyncio.run(run_check())
    except Exception as error:
        report = DoctorReport(errors=[f"Sample checks could not complete: {error}"])

    if not report.findings and not report.errors:
        click.echo("No issues found")
    else:
        click.echo(
            f"Checked {report.checked_samples} samples; "
            f"{report.affected_samples} with potential issues."
        )
        for sample_id, findings in groupby(report.findings, key=lambda f: f.sample_id):
            findings = list(findings)
            sample = findings[0]
            label = sample.external_sample_id or sample.lims_id or sample_id
            click.echo(
                f"\n{label} [sample={sample_id}; assay={sample.assay or 'unknown'}]"
            )
            for finding in findings:
                path = f" ({finding.path})" if finding.path else ""
                click.echo(f"  {finding.file_type}: {finding.message}{path}")
        for error in report.errors:
            click.echo(f"\nCheck incomplete: {error}")
    ctx.exit(report.exit_code)
