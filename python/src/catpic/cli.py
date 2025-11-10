# Destination: src/catpic/cli.py

"""Command-line interface for catpic MEOW v0.7."""

import os
import sys
from pathlib import Path
from typing import Optional

import click

from .core import BASIS, get_default_basis
from .decoder import load_meow_file, display_meow, show_info as show_meow_info
from .encoder import CatpicEncoder
from .protocols import list_protocols
from .detection import detect_best_protocol, supports_protocol, get_detector


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
    "image_file", type=click.Path(exists=True, path_type=Path), required=False
)
@click.option("--basis", "-b", default=None, help="BASIS level (1,2 | 2,2 | 2,3 | 2,4)")
@click.option("--width", "-w", type=int, help="Output width in characters")
@click.option("--height", "-h", type=int, help="Output height in characters")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Save to .meow file")
@click.option("--info", "-i", is_flag=True, help="Show file information")
@click.option("--meld", is_flag=True, help="Force runtime melding")
@click.option(
    "--protocol", "-p",
    default=None,
    help="Display/encoding protocol (auto/glyxel/glyxel_only/kitty/sixel)"
)
@click.option("--detect", is_flag=True, help="Detect terminal and output optimal config")
@click.option("--config", "show_config", is_flag=True, help="Show current configuration")
@click.option("--yes", "-y", is_flag=True, help="Non-interactive mode (accept all prompts)")
@click.option("--debug", is_flag=True, help="Show debug messages")
@click.version_option(version="0.7.0")
def main(
    image_file: Optional[Path],
    basis: Optional[str],
    width: Optional[int],
    height: Optional[int],
    output: Optional[Path],
    info: bool,
    meld: bool,
    protocol: Optional[str],
    detect: bool,
    show_config: bool,
    yes: bool,
    debug: bool,
) -> None:
    """catpic - Terminal image viewer using MEOW v0.7 format.

    \b
    Examples:
      catpic photo.jpg                         # Auto-detect and display
      catpic photo.jpg -o photo.meow           # Save dual-content MEOW file
      catpic photo.meow                        # Display MEOW file
      catpic photo.meow --info                 # Show metadata
      
      catpic --detect                          # Detect terminal, output config
      eval $(catpic --detect)                  # Apply detected config
      
      catpic --config                          # Show current config
      eval $(catpic --detect)                  # Apply detected config
      catpic photo.jpg --protocol sixel        # One-off protocol override
      catpic photo.jpg --basis 2,4             # One-off basis override
      
      catpic photo.jpg --debug                 # Show detection messages

    \b
    Configuration:
      catpic uses CATPIC_CONFIG environment variable (JSON format).
      
      --config shows current configuration
      --detect generates optimal configuration for this terminal
      --protocol and --basis provide session overrides (don't modify ENV)
      
      Aspect ratios are set via CATPIC_CONFIG only (see --detect output)

    \b
    Environment Variables:
      CATPIC_CONFIG             Configuration (JSON format)
    """
    try:
        _main_impl(
            image_file, basis, width, height, output, info, meld,
            protocol, detect, show_config, yes, debug
        )
    except Exception as e:
        # Never dump tracebacks when used with eval
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _main_impl(
    image_file: Optional[Path],
    basis: Optional[str],
    width: Optional[int],
    height: Optional[int],
    output: Optional[Path],
    info: bool,
    meld: bool,
    protocol: Optional[str],
    detect: bool,
    show_config: bool,
    yes: bool,
    debug: bool,
) -> None:
    """Internal main implementation (wrapped by error handler)."""
    
    # Handle --config flag
    if show_config:
        from .config import load_config, export_config
        config = load_config()
        click.echo(export_config(config))
        return
    
    # Handle --detect flag
    if detect:
        from .config import export_config
        
        # Detect all capabilities
        detector = get_detector()
        capabilities = detector.detect_capabilities(use_cache=False)
        best_protocol = capabilities[0].value
        
        # Build helpful comments
        click.echo("# Terminal capabilities detected:")
        for cap in capabilities:
            if cap.value == best_protocol:
                click.echo(f"#   {cap.value:8} - recommended (best quality)")
            elif cap.value == 'glyxel':
                click.echo(f"#   {cap.value:8} - available (universal fallback)")
            else:
                click.echo(f"#   {cap.value:8} - available")
        
        click.echo("#")
        click.echo("# To persist these settings:")
        click.echo("#   eval $(catpic --detect)")
        click.echo("#   echo 'eval $(catpic --detect)' >> ~/.bashrc")
        click.echo("#")
        click.echo("# To customize aspect ratios, edit CATPIC_CONFIG directly:")
        click.echo('#   export CATPIC_CONFIG=\'{"protocol":"kitty",...,"aspect 2x4":1.8}\'')
        
        # Build config with detected values
        config = {
            "protocol": best_protocol,
            "basis": "2,2",
            "aspect base": 2.0,
            "aspect 1x2": 2.0,
            "aspect 2x2": 0.9,
            "aspect 2x3": 1.5,
            "aspect 2x4": 2.0,
        }
        
        click.echo(export_config(config))
        return
    
    # If no image file, show help
    if image_file is None:
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        return
    
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
            sys.exit(1)

    # Handle MEOW files
    if image_file.suffix.lower() == ".meow":
        if output:
            click.echo("Error: Cannot re-encode .meow files", err=True)
            sys.exit(1)
        
        if info:
            show_meow_info(str(image_file))
        else:
            # Auto-detect protocol if not specified
            display_protocol = protocol
            if display_protocol is None or display_protocol == 'auto':
                display_protocol = detect_best_protocol()
                if debug and display_protocol != 'glyxel':
                    click.echo(f"Auto-detected: {display_protocol}", err=True)
            else:
                # Validate protocol is supported
                if not supports_protocol(display_protocol):
                    if debug:
                        click.echo(
                            f"Warning: Protocol '{display_protocol}' may not be supported by this terminal",
                            err=True
                        )
            
            # Load file and display
            content = load_meow_file(str(image_file))
            display_meow(content, meld=meld, protocol=display_protocol)
        return

    # Handle regular images
    if info:
        show_image_info(image_file)
        return

    # Encode image
    encoder = CatpicEncoder(basis=basis_enum)
    
    # Check if animated
    from PIL import Image
    with Image.open(image_file) as img:
        is_animated = getattr(img, "is_animated", False)
    
    # Determine encoding protocol (glyxel vs glyxel_only)
    encode_protocol = protocol
    if encode_protocol is None or encode_protocol == 'auto':
        # Default to dual-content encoding
        encode_protocol = 'glyxel'
    elif encode_protocol not in ['glyxel', 'glyxel_only']:
        # For display protocols, encode as dual-content
        encode_protocol = 'glyxel'
    
    if is_animated:
        meow_content = encoder.encode_animation(
            image_file, width, height, protocol=encode_protocol
        )
    else:
        meow_content = encoder.encode_image(
            image_file, width, height, protocol=encode_protocol
        )
    
    # Output
    if output:
        output.write_text(meow_content, encoding='utf-8')
        
        # Show helpful info about what was encoded
        if encode_protocol == 'glyxel_only':
            click.echo(f"Saved to {output} (glyxel-only, minimal size)")
        else:
            click.echo(f"Saved to {output} (dual content: PNG + glyxel)")
    else:
        # Display encoded content with protocol detection
        display_protocol = protocol
        if display_protocol is None or display_protocol == 'auto':
            display_protocol = detect_best_protocol()
            if debug and display_protocol != 'glyxel':
                click.echo(f"Auto-detected: {display_protocol}", err=True)
        else:
            # Validate protocol is supported
            if not supports_protocol(display_protocol):
                if debug:
                    click.echo(
                        f"Warning: Protocol '{display_protocol}' may not be supported by this terminal",
                        err=True
                    )
        
        display_meow(meow_content, meld=meld, protocol=display_protocol)


def show_image_info(file_path: Path) -> None:
    """Display image file information."""
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


if __name__ == "__main__":
    # Add custom help topic for config
    if len(sys.argv) == 3 and sys.argv[1] == "--help" and sys.argv[2] == "config":
        from catpic.config import show_config_help
        show_config_help()
        sys.exit(0)
    
    main()
