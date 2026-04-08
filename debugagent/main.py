from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from debugagent import __version__
from debugagent.agent.loop import AgentLoop
from debugagent.config import AgentConfig
from debugagent.memory.improvement_log import ImprovementLog
from debugagent.schemas.models import BugTask
from debugagent.utils.code_utils import diff_code
from debugagent.utils.hash_utils import bug_signature

app = typer.Typer(help="DebugAgent - Self-improving code debugging agent")
console = Console()


@app.command()
def run(
    file: Path = typer.Option(..., "--file", help="Path to the buggy Python file"),
    tests: Path = typer.Option(..., "--tests", help="Path to the pytest test file"),
    retries: int = typer.Option(5, "--max-retries", help="Maximum repair attempts"),
    desc: str = typer.Option("", "--desc", help="Optional description of the bug"),
    no_trace: bool = typer.Option(False, "--no-trace", help="Disable Langfuse tracing"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed runtime logs"),
    apply_fix: bool = typer.Option(True, "--apply-fix/--no-apply-fix", help="Write accepted fix back to --file"),
):
    if not file.exists() or not tests.exists():
        raise typer.BadParameter("Both --file and --tests must exist")

    buggy_code = file.read_text(encoding="utf-8")
    test_suite = tests.read_text(encoding="utf-8")

    task = BugTask(
        task_id=bug_signature(buggy_code),
        buggy_code=buggy_code,
        test_suite=test_suite,
        description=desc,
        max_retries=retries,
    )

    config = AgentConfig.from_env(no_trace=no_trace, verbose=verbose)
    config.max_retries = retries

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task("Running DebugAgent...", total=None)
        result = AgentLoop(config).run(task)

    if result.status.value == "SUCCESS":
        console.print(f"[bold green]Fixed in {result.total_attempts} attempt(s)[/bold green]")
        console.print(f"Tokens used: {result.total_tokens}")
        console.print(f"Duration: {result.session_duration_s:.1f}s")

        if result.accepted_fix:
            if apply_fix:
                file.write_text(result.accepted_fix, encoding="utf-8")
                console.print("[cyan]Applied fix to source file.[/cyan]")
            console.print("[bold]Diff:[/bold]")
            console.print(diff_code(buggy_code, result.accepted_fix) or "No diff generated")
    else:
        console.print(f"[bold red]Failed with status: {result.status.value}[/bold red]")
        console.print(f"Attempts: {result.total_attempts}")
        console.print(f"Final error class: {result.final_error_class.value}")
        raise typer.Exit(code=1)


@app.command()
def stats(
    chart: bool = typer.Option(False, "--chart", help="Export improvement chart data as JSON"),
    output: Path = typer.Option(Path("improvement_curve.json"), "--output", help="Output file path for chart data"),
):
    log = ImprovementLog()
    data = log.get_improvement_curve()

    table = Table(title="Improvement Curve by Error Class")
    table.add_column("Error Class", style="cyan")
    table.add_column("Total Sessions", style="magenta")
    table.add_column("Avg Retries", style="yellow")
    table.add_column("Best: 1-shot %", style="green")

    for row in data:
        table.add_row(
            row["error_class"],
            str(row["total_sessions"]),
            f"{row['avg_retries']:.2f}",
            f"{row['one_shot_pct']:.0f}%",
        )

    console.print(table)

    if chart:
        log.export_chart_data(str(output))
        console.print(f"[cyan]Chart data exported to {output}[/cyan]")


@app.command()
def version() -> None:
    console.print(f"debugagent {__version__}")


@app.command()
def reset(
    chroma_dir: Path = typer.Option(Path("./chroma_db"), "--chroma-dir"),
    sqlite_path: Path = typer.Option(Path("./debugagent.db"), "--sqlite-path"),
    session_dir: Path = typer.Option(Path("./sessions"), "--session-dir"),
) -> None:
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir, ignore_errors=True)
    if sqlite_path.exists():
        sqlite_path.unlink(missing_ok=True)
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
    console.print("[green]State reset complete.[/green]")


if __name__ == "__main__":
    app()
