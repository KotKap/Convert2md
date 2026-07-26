"""
CLI interface for document conversion.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import os
import subprocess
import typer
from rich.console import Console
from rich.progress import Progress

from .converter import DocumentConverter
from .diagram_converter import DiagramConversionError, GeminiDiagramProvider, ImageMermaidConverter
from .diagram_models import BatchPlanner, DEFAULT_MODELS
from .quota import QuotaLedger, RateLimiter
from .model_management import (
    RegisterUsageCommand, UsageQuery, create_model_management_api,
    import_configuration, import_usage,
)

app = typer.Typer(
    name="Convert2MD",
    help="Convert PDF and DOCX documents to Markdown format"
)

console = Console()


def _state_dir() -> Path:
    return Path(os.getenv("CONVERT2MD_STATE_DIR", Path.home() / ".convert2md"))


def _quota_ledger() -> QuotaLedger:
    return QuotaLedger(_state_dir() / "quota.sqlite3")


def _model_management():
    return create_model_management_api(_state_dir())


def _validate_model_name(model_name: str | None) -> None:
    if model_name and model_name not in {model.name for model in DEFAULT_MODELS}:
        names = ", ".join(model.name for model in DEFAULT_MODELS)
        raise typer.BadParameter(f"Unknown model '{model_name}'. Configured models: {names}")


@app.command()
def convert(
    input_file: Path = typer.Argument(
        ...,
        help="Path to the input document (PDF, DOCX, or DOC)",
        exists=True,
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Path to the output Markdown file (default: same directory as input)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output",
    ),
    no_filter: bool = typer.Option(
        False,
        "--no-filter",
        help="Disable noise filtering (page numbers, headers, footers)",
    ),
) -> None:
    """
    Convert a document to Markdown format.
    
    Example:
        convert2md convert report.pdf
        convert2md convert document.docx -o output.md
    """
    
    # Determine output path
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}.md"
    else:
        output_file = Path(output_file)
    
    if verbose:
        console.print(f"[blue]Converting:[/blue] {input_file}")
        console.print(f"[blue]Output:[/blue] {output_file}")
    
    try:
        # Convert document
        with Progress() as progress:
            task = progress.add_task(
                "[cyan]Converting...", total=None
            )
            
            converter = DocumentConverter()
            markdown_content, metadata = converter.convert(input_file, no_filter=no_filter)
            
            progress.update(task, completed=True)
        
        # Save markdown
        converter.save_markdown(markdown_content, output_file)
        
        # Display results
        console.print(f"[green]✓ Conversion successful![/green]")
        console.print(f"[green]Output:[/green] {output_file}")
        
        # Display metadata
        if verbose:
            console.print("\n[cyan]Conversion metadata:[/cyan]")
            console.print(f"  Pages: {metadata.get('pages', 'Unknown')}")
            console.print(f"  Images: {len(metadata.get('images', []))}")
            console.print(f"  Tables: {metadata.get('tables', 0)}")
            console.print(f"  Formulas: {metadata.get('formulas', 0)}")
            
            if metadata.get('images'):
                console.print("\n[cyan]Extracted images:[/cyan]")
                for img in metadata['images']:
                    console.print(f"  - {img.name}")
    
    except FileNotFoundError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)
    
    except ValueError as e:
        console.print(f"[red]✗ Unsupported format:[/red] {e}")
        raise typer.Exit(code=1)
    
    except Exception as e:
        console.print(f"[red]✗ Conversion failed:[/red] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)


@app.command()
def batch(
    input_dir: Path = typer.Argument(
        ...,
        help="Directory containing documents to convert",
        exists=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory (default: same as input directory)",
    ),
    pattern: str = typer.Option(
        "*.*",
        "--pattern", "-p",
        help="File pattern to match (e.g., '*.pdf', '*.docx')",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive", "-r",
        help="Recursively process subdirectories",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output",
    ),
) -> None:
    """
    Convert multiple documents in a directory.
    
    Example:
        convert2md batch ./documents/
        convert2md batch ./documents/ --pattern "*.pdf" --recursive
    """
    
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir
    
    # Find matching files
    if recursive:
        files = list(input_dir.rglob(pattern))
    else:
        files = list(input_dir.glob(pattern))
    
    # Filter only supported document types
    supported_extensions = {'.pdf', '.docx', '.doc'}
    files = [
        f for f in files 
        if f.suffix.lower() in supported_extensions
    ]
    
    if not files:
        console.print(f"[yellow]No documents found matching pattern: {pattern}[/yellow]")
        return
    
    console.print(f"[cyan]Found {len(files)} document(s) to convert[/cyan]\n")
    
    converter = DocumentConverter()
    successful = 0
    failed = 0
    
    with Progress() as progress:
        task = progress.add_task(
            "[cyan]Converting...", total=len(files)
        )
        
        for file_path in files:
            try:
                # Determine output path
                rel_path = file_path.relative_to(input_dir)
                output_path = output_dir / rel_path.with_suffix('.md')
                
                # Create output subdirectory if needed
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert
                markdown_content, _ = converter.convert(file_path)
                converter.save_markdown(markdown_content, output_path)
                
                if verbose:
                    console.print(f"[green]✓[/green] {rel_path}")
                
                successful += 1
            
            except Exception as e:
                console.print(f"[red]✗[/red] {file_path.name}: {e}")
                failed += 1
            
            progress.update(task, advance=1)
    
    # Summary
    console.print(f"\n[cyan]Conversion complete:[/cyan]")
    console.print(f"  [green]Successful:[/green] {successful}")
    if failed > 0:
        console.print(f"  [red]Failed:[/red] {failed}")


@app.command("models")
def list_diagram_models() -> None:
    """Show every model stored in the SQLite model repository."""
    ledger = _quota_ledger()
    models = _model_management().list_models(include_disabled=True)
    console.print(f"[dim]Repository: {_state_dir() / 'model_management.sqlite3'}[/dim]")
    if not models:
        console.print("[yellow]The model repository is empty.[/yellow]")
        return
    for model in models:
        used = ledger.requests_today(model.code)
        quotas = ", ".join(
            value for value in (
                f"{model.rpm} RPM" if model.rpm is not None else "",
                f"{model.tpm} TPM" if model.tpm is not None else "",
                f"{model.rpd} RPD ({used} used today)" if model.rpd is not None else "",
            ) if value
        )
        console.print(
            f"{model.id}: {model.status.value}, context {model.context_window}"
            + (f", {quotas}" if quotas else "")
        )


@app.command("models-import")
def import_models_config(
    config_file: Path = typer.Argument(..., exists=True, dir_okay=False),
) -> None:
    """Import versioned model/provider/price/budget configuration from YAML or JSON."""
    result = import_configuration(_model_management(), config_file)
    console.print(
        f"[green]Imported:[/green] {result.providers} providers, {result.models} models, "
        f"{result.prices} prices, {result.budgets} budgets"
    )


@app.command("usage")
def show_usage() -> None:
    """Show locally recorded model usage and cost."""
    summary = _model_management().get_usage_summary(UsageQuery())
    console.print(
        f"Requests: {summary.request_count}; input: {summary.input_tokens}; "
        f"output: {summary.output_tokens}; cost: {summary.total_cost} {summary.currency}"
    )


@app.command("usage-record")
def record_usage(
    model_id: str = typer.Option(..., "--model", help="Full model ID, e.g. google:gemini-3.1-flash-lite"),
    input_tokens: int = typer.Option(..., "--input-tokens", min=0),
    output_tokens: int = typer.Option(0, "--output-tokens", min=0),
    operation: str = typer.Option("historical", "--operation"),
    cached_input_tokens: int = typer.Option(0, "--cached-input-tokens", min=0),
    reasoning_tokens: int = typer.Option(0, "--reasoning-tokens", min=0),
    image_count: int = typer.Option(0, "--images", min=0),
    occurred_at: Optional[str] = typer.Option(
        None, "--occurred-at", help="ISO 8601 timestamp; defaults to now",
    ),
    scope: str = typer.Option("application", "--scope"),
    document_id: Optional[str] = typer.Option(None, "--document-id"),
    status: str = typer.Option("success", "--status"),
) -> None:
    """Add one existing or externally made model request to usage accounting."""
    timestamp = (
        datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        if occurred_at else datetime.now(timezone.utc)
    )
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    record = _model_management().register_usage(RegisterUsageCommand(
        model_id=model_id, operation=operation, input_tokens=input_tokens,
        output_tokens=output_tokens, cached_input_tokens=cached_input_tokens,
        reasoning_tokens=reasoning_tokens, image_count=image_count, status=status,
        occurred_at=timestamp, scope=scope, document_id=document_id,
    ))
    cost = f"{record.total_cost} {record.currency}" if record.total_cost is not None else "unknown"
    console.print(f"[green]Usage recorded:[/green] {record.request_id}; cost: {cost}")


@app.command("usage-import")
def import_usage_history(
    usage_file: Path = typer.Argument(..., exists=True, dir_okay=False),
) -> None:
    """Import historical usage from CSV, JSON or JSONL."""
    count = import_usage(_model_management(), usage_file)
    console.print(f"[green]Imported usage records:[/green] {count}")


@app.command("web")
def run_web(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port", min=1, max=65535),
    ui_port: int = typer.Option(3000, "--ui-port", min=1, max=65535),
) -> None:
    """Run the local REST API and graphical interface together."""
    try:
        import uvicorn
    except ImportError as error:
        raise typer.BadParameter("Install web dependencies from requirements.txt") from error
    web_dir = Path(__file__).resolve().parent.parent / "web"
    if not (web_dir / "dist" / "server" / "index.js").exists():
        raise typer.BadParameter("Build the interface first: cd web && npm install && npm run build")
    frontend = subprocess.Popen(
        ["npm", "run", "start", "--", "--port", str(ui_port)],
        cwd=web_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    console.print(f"[green]Convert2MD web:[/green] http://127.0.0.1:{ui_port}")
    console.print("[dim]Press Ctrl+C to stop the interface.[/dim]")
    try:
        uvicorn.run("src.web_api:create_web_app", host=host, port=port,
                    reload=False, factory=True)
    finally:
        frontend.terminate()
        try:
            frontend.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend.kill()


@app.command("diagram")
def convert_diagram(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    model_name: Optional[str] = typer.Option(None, "--model", help="Preferred Gemini model"),
) -> None:
    """Convert one PNG/JPG diagram to a same-name Markdown file."""
    _validate_model_name(model_name)
    ledger = _quota_ledger()
    planner = BatchPlanner(ledger)
    excluded_models: set[str] = set()
    try:
        converter = ImageMermaidConverter(
            GeminiDiagramProvider(), ledger, RateLimiter(ledger),
            model_management=_model_management(),
        )
    except DiagramConversionError as error:
        console.print(f"[red]Cannot start ({error.code}):[/red] {error}")
        raise typer.Exit(code=1)

    while True:
        plan = planner.plan(
            [input_file], preferred_model=model_name, excluded_models=excluded_models
        )
        if not plan.assignments:
            console.print("[red]No configured model has remaining daily capacity.[/red]")
            raise typer.Exit(code=1)
        item = plan.assignments[0]
        try:
            output = converter.convert(item.path, item.model)
            console.print(f"[green]✓[/green] {output} ({item.model.name})")
            return
        except DiagramConversionError as error:
            if error.code in {"quota", "model_unavailable"}:
                excluded_models.add(item.model.name)
                console.print(f"[yellow]{item.model.name} unavailable; trying another model.[/yellow]")
                continue
            console.print(f"[red]Diagram conversion failed ({error.code}):[/red] {error}")
            raise typer.Exit(code=1)


@app.command("diagrams")
def convert_diagrams(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False),
    recursive: bool = typer.Option(False, "--recursive", "-r"),
    model_name: Optional[str] = typer.Option(None, "--model", help="Preferred Gemini model"),
    plan_only: bool = typer.Option(False, "--plan-only", help="Show allocation without API calls"),
) -> None:
    """Batch-convert PNG/JPG diagrams and respect shared RPM/TPM/RPD limits."""
    _validate_model_name(model_name)
    iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
    files = sorted(
        path for path in iterator
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )
    if not files:
        console.print("[yellow]No PNG/JPG images found.[/yellow]")
        return

    ledger = _quota_ledger()
    planner = BatchPlanner(ledger)
    plan = planner.plan(files, preferred_model=model_name)
    counts: dict[str, int] = {}
    for item in plan.assignments:
        counts[item.model.name] = counts.get(item.model.name, 0) + 1
    console.print(f"[cyan]Images:[/cyan] {len(files)}")
    for name, count in counts.items():
        console.print(f"  {name}: {count}")
    console.print(f"[cyan]Estimated minimum time:[/cyan] {plan.estimated_seconds:.0f}s")
    if plan.unassigned:
        console.print(f"[yellow]No daily capacity for {len(plan.unassigned)} image(s).[/yellow]")
    if plan_only:
        return

    try:
        converter = ImageMermaidConverter(
            GeminiDiagramProvider(), ledger, RateLimiter(ledger),
            model_management=_model_management(),
        )
    except DiagramConversionError as error:
        console.print(f"[red]Cannot start ({error.code}):[/red] {error}")
        raise typer.Exit(code=1)

    successful = 0
    failed = 0
    deferred = len(plan.unassigned)
    excluded_models: set[str] = set()
    queue = list(plan.assignments)
    while queue:
        item = queue.pop(0)
        try:
            converter.convert(item.path, item.model)
            successful += 1
            console.print(f"[green]✓[/green] {item.path.name} ({item.model.name})")
        except DiagramConversionError as error:
            if error.code in {"quota", "model_unavailable"}:
                excluded_models.add(item.model.name)
                remaining_paths = [item.path, *(entry.path for entry in queue)]
                replacement = planner.plan(
                    remaining_paths,
                    preferred_model=model_name,
                    excluded_models=excluded_models,
                )
                queue = list(replacement.assignments)
                deferred += len(replacement.unassigned)
                console.print(
                    f"[yellow]{item.model.name} unavailable; replanned "
                    f"{len(queue)} remaining image(s).[/yellow]"
                )
                continue
            failed += 1
            console.print(f"[red]✗[/red] {item.path.name} ({error.code}): {error}")
    console.print(
        f"[cyan]Complete:[/cyan] {successful} successful, {failed} failed, "
        f"{deferred} deferred"
    )


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
