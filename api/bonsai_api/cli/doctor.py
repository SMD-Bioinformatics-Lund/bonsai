"""CLI presentation of read-only integrity reports."""

import asyncio
import json
from collections import defaultdict

import click

from bonsai_api.doctor import FILE_TYPES, DoctorReport, run_check


@click.group()
def doctor():
    """Inspect sample data and report integrity problems without repairing them."""


@doctor.command("check")
@click.option(
    "--assay",
    "assays",
    multiple=True,
    help="Select a current assay; repeat to select several.",
)
@click.option(
    "--sample",
    "sample_ids",
    multiple=True,
    help="Select an internal sample ID, Lab ID, or LIMS ID; repeatable.",
)
@click.option(
    "--file-type",
    "file_types",
    multiple=True,
    type=click.Choice(FILE_TYPES),
    help="Limit checks to a resource category; repeatable. Alignment includes its index.",
)
@click.option(
    "--group-by",
    type=click.Choice(["sample", "file-type"]),
    default="sample",
    show_default=True,
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.option(
    "--timeout",
    type=click.IntRange(min=1),
    default=60,
    show_default=True,
    help="Maximum wait in seconds per worker batch.",
)
@click.option(
    "-o",
    "--output",
    type=click.File("w"),
    default="-",
    help="Write report to a file instead of stdout.",
)
@click.pass_context
def check(
    ctx, assays, sample_ids, file_types, group_by, output_format, timeout, output
):
    """Check required resources. Exit 0: clean, 1: problems, 2: incomplete.

    Different filters narrow the selection together. This checks availability
    and index membership; full file-content validation is not performed.
    """
    try:
        report = asyncio.run(
            run_check(
                assays=assays,
                sample_ids=sample_ids,
                file_types=file_types,
                timeout=timeout,
            )
        )
    except Exception as error:
        report = DoctorReport(errors=[f"Sample checks could not complete: {error}"])
    groups = defaultdict(list)
    for finding in report.findings:
        key = finding.sample_id if group_by == "sample" else finding.file_type
        groups[key].append(finding.model_dump(mode="json"))
    groups = dict(sorted(groups.items()))
    status = (
        "incomplete" if report.errors else ("problems" if report.findings else "clean")
    )
    if output_format == "json":
        payload = report.model_dump(mode="json", exclude={"findings"})
        payload.update(
            status=status,
            affected_samples=report.affected_samples,
            group_by=group_by,
            groups=groups,
            selection={
                "assays": assays,
                "samples": sample_ids,
                "file_types": file_types,
            },
        )
        click.echo(json.dumps(payload, indent=2), file=output)
    else:
        click.echo(
            f"Doctor: {status}. Checked {report.checked_samples} samples; "
            f"{report.affected_samples} affected; {len(report.findings)} findings.",
            file=output,
        )
        for group, findings in groups.items():
            click.echo(f"\n{group}", file=output)
            for finding in findings:
                label = (
                    finding["external_sample_id"]
                    or finding["lims_id"]
                    or finding["sample_id"]
                )
                path = f" ({finding['path']})" if finding["path"] else ""
                click.echo(
                    f"  {label} [sample={finding['sample_id']}; assay={finding['assay'] or 'unknown'}; "
                    f"{finding['file_type']}]: {finding['message']}{path}",
                    file=output,
                )
        for error in report.errors:
            click.echo(f"\nINCOMPLETE: {error}", file=output)
        if report.checked_samples == 0 and not report.errors:
            click.echo("No samples were found.", file=output)
    ctx.exit(report.exit_code)
