"""
CLI interface for document conversion.
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress

from .converter import DocumentConverter

app = typer.Typer(
    name="Convert2MD",
    help="Convert PDF and DOCX documents to Markdown format"
)

console = Console()


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


def main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main()
