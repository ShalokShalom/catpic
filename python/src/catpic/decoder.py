# Destination: src/catpic/decoder.py

"""
MEOW v0.7 decoder - Protocol-aware display with graceful fallback
"""

import sys
import time
import os
import base64
from pathlib import Path
from typing import Union, Optional

from .core import EXIT_ERROR_FILE_NOT_FOUND, EXIT_ERROR_GENERAL, DEFAULT_FRAME_DELAY
from .meow_parser import MEOWParser, MEOWContent
from .protocols import get_generator, list_protocols
from .protocols.core import decode_png


def get_terminal_size() -> tuple[int, int]:
    """Get terminal size (width, height) or return defaults."""
    try:
        size = os.get_terminal_size()
        return (size.columns, size.lines)
    except (AttributeError, OSError):
        return (80, 24)


def truncate_ansi_line(line: str, max_width: int) -> str:
    """
    Truncate a line with ANSI codes to max_width visible characters.
    
    ANSI escape sequences don't count toward visible width.
    """
    if max_width <= 0:
        return ""
    
    visible_count = 0
    result = []
    i = 0
    
    while i < len(line) and visible_count < max_width:
        if line[i:i+2] == '\x1b[':
            # ANSI escape sequence - find the end
            end = line.find('m', i)
            if end != -1:
                result.append(line[i:end+1])
                i = end + 1
                continue
        
        # Regular character
        result.append(line[i])
        visible_count += 1
        i += 1
    
    return ''.join(result)


def truncate_ansi_output(output: str, max_width: int, max_height: int) -> str:
    """Truncate ANSI output to fit terminal dimensions."""
    lines = output.split('\n')
    
    # Truncate to max height
    lines = lines[:max_height]
    
    # Truncate each line to max width
    truncated_lines = [truncate_ansi_line(line, max_width) for line in lines]
    
    return '\n'.join(truncated_lines)


# ============================================================================
# File I/O Operations
# ============================================================================

def load_meow_file(filepath: Union[str, Path]) -> bytes:
    """
    Load MEOW file from disk as bytes.
    
    Args:
        filepath: Path to .meow file
        
    Returns:
        MEOW content as bytes
        
    Raises:
        SystemExit: With code 5 if file not found or cannot be read
    """
    path = Path(filepath)
    
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(EXIT_ERROR_FILE_NOT_FOUND)
    
    try:
        return path.read_bytes()
    except Exception as e:
        print(f"Error: Cannot read file {filepath}: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR_FILE_NOT_FOUND)


def save_meow_file(filepath: Union[str, Path], content: Union[str, bytes]) -> None:
    """
    Save MEOW content to disk.
    
    Args:
        filepath: Destination path
        content: MEOW content (string or bytes)
        
    Raises:
        SystemExit: If file cannot be written
    """
    path = Path(filepath)
    
    try:
        if isinstance(content, str):
            path.write_text(content, encoding='utf-8')
        else:
            path.write_bytes(content)
    except Exception as e:
        print(f"Error: Cannot write file {filepath}: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR_GENERAL)


# ============================================================================
# Display Operations
# ============================================================================

def display_meow(
    content: Union[str, bytes],
    meld: bool = False,
    protocol: Optional[str] = None,
) -> None:
    """
    Display MEOW content to terminal with protocol support.

    Args:
        content: MEOW format content (string or bytes)
        meld: Force runtime melding (translucency recomputation)
        protocol: Protocol to use ('glyxel', 'sixel', 'kitty', etc.)
                 None = use visible output (glyxel fallback)
    
    Raises:
        SystemExit: If content cannot be parsed
    """
    # Parse content
    try:
        parser = MEOWParser()
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        
        meow = parser.parse(content_bytes)
    except Exception as e:
        print(f"Error: Invalid MEOW content: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR_GENERAL)
    
    # Check if animated
    has_frames = any(layer.frame is not None for layer in meow.layers)

    if has_frames:
        # Animations always use visible output (for now)
        _display_animated(meow, meld)
    else:
        # Static images can use protocol display
        _display_static(meow, meld, protocol, content_bytes)


def _display_static(
    meow: MEOWContent,
    meld: bool,
    protocol: Optional[str],
    raw_content: bytes,
) -> None:
    """
    Display static MEOW content with protocol support.
    
    If protocol specified and cells field present, use protocol display.
    Otherwise fall back to visible output (glyxel).
    """
    # Try protocol display if requested
    if protocol and protocol != 'glyxel':
        # Look for layer with cells field
        for layer in meow.layers:
            if layer.cells and layer.ctype == 'png':
                try:
                    # Decode PNG from cells field
                    png_data = base64.b64decode(layer.cells)
                    img = decode_png(png_data)
                    
                    # Get terminal dimensions
                    term_width, term_height = get_terminal_size()
                    
                    # Calculate display size using intelligent sizing
                    # Same logic as encoder: min(native, terminal - margin)
                    from .encoder import calculate_display_dimensions
                    from .core import get_default_basis
                    
                    basis = get_default_basis()
                    max_cols = term_width - 2  # Leave margin
                    max_rows = term_height - 2  # Leave room for prompt
                    
                    display_width, display_height = calculate_display_dimensions(
                        img, basis, max_cols=max_cols, max_rows=max_rows
                    )
                    
                    # Convert to pixels for protocol (protocols work in pixels)
                    basis_x, basis_y = basis.value
                    pixel_width = display_width * basis_x
                    pixel_height = display_height * basis_y
                    
                    from .protocols import ProtocolConfig
                    config = ProtocolConfig(
                        max_width=pixel_width,
                        max_height=pixel_height,
                    )
                    
                    # Generate protocol output
                    generator = get_generator(protocol)
                    
                    # Re-encode PNG for protocol (with resizing)
                    from .protocols.core import encode_png, resize_if_needed
                    resized_img = resize_if_needed(img, pixel_width, pixel_height, preserve_aspect=True)
                    resized_png = encode_png(resized_img)
                    
                    output = generator.generate(resized_png, config)
                    
                    # Display protocol output
                    print(output.decode('utf-8'), end='')
                    print()  # Trailing newline
                    sys.stdout.flush()
                    return
                    
                except Exception as e:
                    # Protocol display failed, fall back to glyxel
                    print(f"Warning: Protocol display failed: {e}", file=sys.stderr)
                    print("Falling back to glyxel...", file=sys.stderr)
    
    # Fallback: use raw content (includes glyxel visible output + footer)
    if isinstance(raw_content, bytes):
        print(raw_content.decode('utf-8'), end='')
    else:
        print(raw_content, end='')
    sys.stdout.flush()


def _display_animated(meow: MEOWContent, meld: bool):
    """
    Display animated MEOW content with full frame buffering.
    
    Each frame is completely rendered to a buffer before any terminal I/O,
    preventing visual tearing and interleaved output artifacts.
    """
    frames = meow.group_by_frame()
    loop_count = meow.canvas.loop if meow.canvas else 1
    is_infinite = meow.canvas.is_infinite_loop() if meow.canvas else False
    
    # Get terminal size for truncation
    term_width, term_height = get_terminal_size()
    
    # Get canvas height
    canvas_height = meow.canvas.size[1] if meow.canvas and meow.canvas.size else 24
    
    # Emit layer zero to scroll terminal and establish origin
    if meow.canvas and meow.canvas.size:
        height = meow.canvas.size[1]
        # Reserve vertical space (scroll terminal)
        print('\n' * height, end='')
        # Move up to canvas top
        print(f'\x1b[{height}A', end='')
        # Save cursor at canvas origin
        print('\x1b[s', end='')
        sys.stdout.flush()
    
    # Auto-truncate to fit terminal (leave room for prompt)
    display_height = min(canvas_height, term_height - 2)
    
    # Hide cursor for animation
    print('\x1b[?25l', end='', flush=True)
    
    try:
        iteration = 0
        while is_infinite or iteration < loop_count:
            for frame_num in sorted(frames.keys()):
                frame_layers = frames[frame_num]
                
                # === FULL FRAME BUFFERING ===
                # Build entire frame output in memory before any I/O
                frame_buffer = []
                
                # Start with cursor restore
                frame_buffer.append('\x1b[u')
                
                # Collect all layer output for this frame
                frame_output = []
                for layer in frame_layers:
                    if layer.visible_output:
                        frame_output.append(layer.visible_output)
                
                combined = ''.join(frame_output)
                lines = combined.split('\n')
                
                # Build output for each line
                for idx, line in enumerate(lines):
                    if idx >= display_height:
                        break
                    
                    # Truncate line to terminal width
                    truncated_line = truncate_ansi_line(line, term_width)
                    frame_buffer.append(truncated_line)
                    
                    # Clear to end of line
                    frame_buffer.append('\x1b[K')
                    
                    # Move to next line (down 1, column 0) - but not after last line
                    if idx < display_height - 1:
                        frame_buffer.append('\x1b[B\x1b[G')
                
                # === ATOMIC FRAME OUTPUT ===
                # Write entire frame in one I/O operation
                sys.stdout.write(''.join(frame_buffer))
                sys.stdout.flush()
                
                # Get delay from first animated layer in frame
                delay_ms = DEFAULT_FRAME_DELAY
                for layer in frame_layers:
                    if layer.frame is not None:
                        delay_ms = layer.delay
                        break
                
                # Sleep for frame delay
                time.sleep(delay_ms / 1000.0)
            
            iteration += 1
            
    except KeyboardInterrupt:
        pass
    finally:
        # Restore cursor position and show cursor
        print('\x1b[u\x1b[?25h', end='', flush=True)
        
        # Move cursor below animation
        print(f'\x1b[{canvas_height}B')


# ============================================================================
# Metadata Operations
# ============================================================================

def parse_meow(content: Union[str, bytes]) -> MEOWContent:
    """
    Parse MEOW content to MEOWContent object.
    
    Args:
        content: MEOW format content (string or bytes)
        
    Returns:
        Parsed MEOWContent object
        
    Raises:
        ValueError: If content cannot be parsed
    """
    try:
        parser = MEOWParser()
        if isinstance(content, str):
            return parser.parse(content.encode('utf-8'))
        else:
            return parser.parse(content)
    except Exception as e:
        raise ValueError(f"Invalid MEOW content: {e}")


def show_info(filepath: Union[str, Path]) -> None:
    """
    Display metadata information about a MEOW file.
    
    Args:
        filepath: Path to .meow file
    """
    content = load_meow_file(filepath)
    meow = parse_meow(content)
    
    # Canvas information
    if meow.canvas:
        print("Canvas:")
        print(f"  Version: {meow.canvas.version}")
        
        if meow.canvas.size:
            w, h = meow.canvas.size
            print(f"  Size: {w}×{h}")
        
        if meow.canvas.basis != (2, 2):
            bx, by = meow.canvas.basis
            print(f"  Basis: {bx}×{by}")
        
        if meow.canvas.loop == 0:
            print("  Loop: infinite")
        elif meow.canvas.loop != 1:
            print(f"  Loop: {meow.canvas.loop}")
        
        if meow.canvas.meta:
            print("  Metadata:")
            for key, value in meow.canvas.meta.items():
                print(f"    {key}: {value}")
        
        print()
    
    # Layer information
    print(f"Layers: {len(meow.layers)}")
    
    for idx, layer in enumerate(meow.layers):
        print(f"\nLayer {idx}:")
        
        if layer.id:
            print(f"  ID: {layer.id}")
        
        if layer.box:
            x = layer.box.get('x', 0)
            y = layer.box.get('y', 0)
            dx = layer.box.get('dx', 0)
            dy = layer.box.get('dy', 0)
            print(f"  Box: ({x}, {y}) {dx}×{dy}")
        
        if layer.alpha != 1.0:
            print(f"  Alpha: {layer.alpha}")
        
        if layer.basis:
            bx, by = layer.basis
            print(f"  Basis: {bx}×{by}")
        
        if layer.ctype:
            print(f"  Content Type: {layer.ctype}")
            
        if layer.cells:
            print(f"  Cells: {len(layer.cells)} bytes (base64)")
            # Try to show original size if PNG
            if layer.ctype == 'png':
                try:
                    png_data = base64.b64decode(layer.cells)
                    img = decode_png(png_data)
                    print(f"  Original Size: {img.width}×{img.height} pixels")
                except:
                    pass
        
        if layer.frame is not None:
            print(f"  Frame: {layer.frame}")
            print(f"  Delay: {layer.delay}ms")
        
        if layer.visible_output:
            print(f"  Visible Output: {len(layer.visible_output)} bytes")


# ============================================================================
# Deprecated - Backward Compatibility
# ============================================================================

def load_meow(filepath: str) -> MEOWContent:
    """
    DEPRECATED: Use load_meow_file() + parse_meow() instead.
    
    Load and parse a MEOW file.
    
    Args:
        filepath: Path to .meow file
        
    Returns:
        Parsed MEOWContent object
    """
    content = load_meow_file(filepath)
    return parse_meow(content)
