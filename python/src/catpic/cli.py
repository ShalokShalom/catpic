# Destination: src/catpic/cli.py

"""Command-line interface for catpic MEOW v0.7."""

from pathlib import Path
from typing import Optional

import click

from .core import BASIS, get_default_basis
from .decoder import load_meow_file, display_meow, show_info as show_meow_info
from .encoder import CatpicEncoder
from .protocols import list_protocols


def parse_basis(basis_str: str) -> BASIS:
    """Parse BASIS string to BASIS enum."""
    basis_map = {
        "1,2": BASIS.BASIS_1_2,
        "2,2": BASIS.BASIS_2_2,
        "2,3": BASIS.BASIS_2_3,
        "2,4": BASIS.BASIS_2_4,
    }

    if basis_str not in basis_map:
        raise click.BadParameter(
            f"Invalid BASIS '{basis_str}'. Must be one of: {', '.join(basis_map.keys())}"
        )

    return basis_map[basis_str]


@click.command()
@click.argument(
    "image_file", type=click.Path(exists=True, path_type=Path), required=True
)
@click.option("--basis", "-b", default=None, help="BASIS level (1,2 | 2,2 | 2,3 | 2,4)")
@click.option("--width", "-w", type=int, help="Output width in characters")
@click.option("--height", "-h", type=int, help="Output height in characters")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Save to .meow file")
@click.option("--info", "-i", is_flag=True, help="Show file information")
@click.option("--meld", is_flag=True, help="Force runtime melding (Phase 2 feature)")
@click.option(
    "--protocol", "-p",
    type=click.Choice(['glyxel', 'glyxel_only'], case_sensitive=False),
    default=None,
    help="Display/encoding protocol (glyxel=dual content, glyxel_only=minimal)"
)
@click.version_option(version="0.7.0")
def main(
    image_file: Path,
    basis: Optional[str],
    width: Optional[int],
    height: Optional[int],
    output: Optional[Path],
    info: bool,
    meld: bool,
    protocol: Optional[str],
) -> None:
    """
    catpic - Terminal image viewer using MEOW v0.7 format.

    Examples:
      catpic photo.jpg                     # Encode and display (dual content)
      catpic photo.jpg -o photo.meow       # Save with PNG + glyxel
      catpic photo.meow                    # Display (uses protocol if available)
      catpic photo.meow --info             # Show metadata
      catpic photo.jpg --protocol glyxel_only  # Minimal ANSI only
      
    Protocol Modes:
      glyxel (default)    Dual content: PNG + glyxel (best quality)
      glyxel_only         Minimal: glyxel ANSI only (smallest size)
      
    Environment:
      CATPIC_BASIS - Default BASIS (e.g., "2,4")
      
    Phase 1: Single-layer static images
    Phase 2: Multi-layer, animation, translucency
    Phase 2C: Protocol support (glyxel integrated, Sixel/Kitty/iTerm2 coming)
    """
    # Normalize protocol name
    if protocol:
        protocol = protocol.lower()
    
    # Parse BASIS
    if basis is None:
        basis_enum = get_default_basis()
    else:
        try:
            basis_enum = parse_basis(basis)
        except click.BadParameter as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)

    # Handle MEOW files
    if image_file.suffix.lower() == ".meow":
        if output:
            click.echo("Error: Cannot re-encode .meow files", err=True)
            raise SystemExit(1)
        
        if info:
            show_meow_info(str(image_file))
        else:
            # Load file and display
            content = load_meow_file(str(image_file))
            # Use protocol for display if specified
            display_meow(content, meld=meld, protocol=protocol)
        return

    # Handle regular images
    if info:
        show_image_info(image_file)
        return

    # Encode image
    try:
        encoder = CatpicEncoder(basis=basis_enum)
        
        # Check if animated
        from PIL import Image
        with Image.open(image_file) as img:
            is_animated = getattr(img, "is_animated", False)
        
        if is_animated:
            meow_content = encoder.encode_animation(
                image_file, width, height, protocol=protocol
            )
        else:
            meow_content = encoder.encode_image(
                image_file, width, height, protocol=protocol
            )
        
        # Output (encoder returns string)
        if output:
            output.write_text(meow_content, encoding='utf-8')
            
            # Show helpful info about what was encoded
            if protocol == 'glyxel_only':
                click.echo(f"Saved to {output} (glyxel-only, minimal size)")
            else:
                click.echo(f"Saved to {output} (dual content: PNG + glyxel)")
        else:
            # Display encoded content
            display_meow(meow_content, meld=meld, protocol=protocol)
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def show_image_info(file_path: Path) -> None:
    """Display image file information."""
    try:
        from PIL import Image

        with Image.open(file_path) as img:
            click.echo(f"File: {file_path}")
            click.echo(f"Format: {img.format}")
            click.echo(f"Size: {img.width}×{img.height} pixels")
            click.echo(f"Mode: {img.mode}")
            if getattr(img, "is_animated", False):
                frames = getattr(img, 'n_frames', '?')
                click.echo(f"Animated: Yes ({frames} frames)")
                if 'duration' in img.info:
                    click.echo(f"Frame delay: {img.info['duration']}ms")
            
            # File size
            size = file_path.stat().st_size
            if size < 1024:
                size_str = f"{size} bytes"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            click.echo(f"File size: {size_str}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
