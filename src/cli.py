"""
CLI interface for document conversion.
"""

from pathlib import Path
from typing import Optional
import os
import typer
from rich.console import Console
from rich.progress import Progress

from .converter import DocumentConverter
from .diagram_converter import DiagramConversionError, GeminiDiagramProvider, ImageMermaidConverter
from .diagram_models import BatchPlanner, DEFAULT_MODELS
from .quota import QuotaLedger, RateLimiter

app = typer.Typer(
    name="Convert2MD",
    help="Convert PDF and DOCX documents to Markdown format"
)

console = Console()


def _quota_ledger() -> QuotaLedger:
    state_dir = Path(os.getenv("CONVERT2MD_STATE_DIR", Path.home() / ".convert2md"))
    return QuotaLedger(state_dir / "quota.sqlite3")


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
    """Show configured image-to-Mermaid models and locally known daily usage."""
    ledger = _quota_ledger()
    for model in DEFAULT_MODELS:
        used = ledger.requests_today(model.name)
        console.print(
            f"{model.name}: {used}/{model.rpd} RPD, {model.rpm} RPM, {model.tpm} TPM"
        )


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
            GeminiDiagramProvider(), ledger, RateLimiter(ledger)
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
            GeminiDiagramProvider(), ledger, RateLimiter(ledger)
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
