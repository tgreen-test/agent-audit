"""CLI command for generating PDF audit reports."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape

console = Console()


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    default=None,
    help="Output PDF file path. Defaults to <input_name>_report.pdf",
)
@click.option(
    "--title",
    default="AI Agent Security Audit Report",
    help="Report title on the cover page.",
)
@click.option(
    "--organization",
    default="",
    help="Organization name for the cover page.",
)
@click.option(
    "--logo",
    type=click.Path(exists=True),
    default=None,
    help="Path to logo image for cover page (PNG/JPG).",
)
@click.option(
    "--include-suppressed",
    is_flag=True,
    default=False,
    help="Include suppressed (low-confidence) findings in the report.",
)
@click.pass_context
def report(
    ctx: click.Context,
    input_path: str,
    output: str | None,
    title: str,
    organization: str,
    logo: str | None,
    include_suppressed: bool,
):
    """Generate a PDF audit report from scan results.

    INPUT_PATH is a JSON file produced by `agent-audit scan --format json`.

    Example:

        agent-audit scan ./src --format json -o scan.json

        agent-audit report scan.json -o audit_report.pdf
    """
    try:
        from agent_audit.report.generator import ReportGenerator
    except ImportError as exc:
        console.print(
            "[red]Error:[/red] PDF report generation requires additional dependencies.\n"
            "Install with: [bold]pip install agent-audit\\[report][/bold]",
            highlight=False,
        )
        sys.exit(1)

    # Default output path
    if output is None:
        input_stem = Path(input_path).stem
        output = f"{input_stem}_report.pdf"

    verbose = ctx.obj.get("verbose", False) if ctx.obj else False

    if verbose:
        console.print(f"[dim]Input:  {input_path}[/dim]")
        console.print(f"[dim]Output: {output}[/dim]")

    try:
        generator = ReportGenerator(
            title=title,
            organization=organization,
            logo_path=logo,
            include_suppressed=include_suppressed,
        )

        result_path = generator.generate(input_path, output)
        console.print(f"[green]Report generated:[/green] {result_path}")

    except Exception as exc:
        # escape(), not a bare interpolation. The message this path most often carries is
        # generator.py's "Install with: pip install agent-audit[report]", and Rich reads
        # `[report]` in interpolated text as a style tag and prints nothing for it — so the
        # user was told to `pip install agent-audit`, which does not install reportlab. The
        # extra is the whole content of the instruction.
        console.print(f"[red]Error generating report:[/red] {escape(str(exc))}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)
