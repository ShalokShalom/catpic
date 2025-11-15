# Destination: src/catpic/decoder.py

"""
MEOW v0.9 decoder - Protocol-aware display with animation support
"""

import sys
import os
import base64
from pathlib import Path
from typing import Union, Optional, List, Dict, Any

from .core import EXIT_ERROR_FILE_NOT_FOUND, EXIT_ERROR_GENERAL, DEFAULT_FRAME_DELAY
from .meow_parser import MEOWParser, MEOWContent
from .protocols import get_generator, list_protocols
from .protocols.core import decode_png
from .framebuffer import FrameBuffer
from .renderer import LayerRenderer
from .detection import detect_best_protocol
from .geometry import GeometryAPI


def get_terminal_size() -> tuple[int, int]:
    """Get terminal size (width, height) or return defaults."""
    try:
        size = os.get_terminal_size()
        return (size.columns, size.lines)
    except (AttributeError, OSError):
        return (80, 24)


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
# Display Operations - Protocol-Aware
# ============================================================================

def display_meow(
    content: Union[str, bytes],
    meld: bool = False,
    protocol: Optional[str] = None,
) -> None:
    """
    Display MEOW content with protocol-aware rendering.
    
    Uses FrameBuffer and LayerRenderer abstractions to enable
    animation across all graphics protocols (kitty, sixel, iterm2, glyxel).

    Args:
        content: MEOW format content (string or bytes)
        meld: Force runtime melding (translucency recomputation)
        protocol: Protocol to use ('kitty', 'sixel', 'iterm2', 'glyxel', 'auto')
                 None or 'auto' = auto-detect best protocol
    
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
    
    # Infer canvas size if not explicitly provided
    width, height = GeometryAPI.infer_canvas_size(meow)
    
    # Determine protocol
    if protocol is None or protocol == 'auto':
        protocol_name = detect_best_protocol()
    else:
        protocol_name = protocol
    
    # Check if we can use protocol-aware rendering
    has_png_data = any(layer.cells and layer.ctype == 'png' for layer in meow.layers)
    
    if has_png_data and protocol_name != 'glyxel':
        # Protocol-aware rendering (kitty, sixel, iterm2)
        _display_protocol_aware(meow, protocol_name, width, height, meld)
    else:
        # Fallback to glyxel visible output
        _display_glyxel_fallback(content_bytes, meow, width, height)


def _display_protocol_aware(
    meow: MEOWContent,
    protocol: str,
    width: int,
    height: int,
    meld: bool,
) -> None:
    """
    Display MEOW using protocol-aware rendering with FrameBuffer + LayerRenderer.
    
    Supports both static images and animations using native protocols.
    """
    # Create display abstractions
    framebuffer = FrameBuffer(protocol, width, height)
    renderer = LayerRenderer(framebuffer)
    
    # Prepare layers for rendering
    layers_data = []
    cumulative_time = 0
    is_animation = False
    
    for layer in meow.layers:
        if not layer.cells or layer.ctype != 'png':
            continue
        
        try:
            # Decode PNG data
            png_data = base64.b64decode(layer.cells)
            
            # Calculate timing
            if layer.frame is not None and layer.delay:
                # Animated: use cumulative timing
                render_at_ms = cumulative_time
                cumulative_time += layer.delay
                is_animation = True
            else:
                # Static: immediate
                render_at_ms = 0
            
            layers_data.append({
                'data': png_data,
                'render_at_ms': render_at_ms,
            })
            
        except Exception as e:
            print(f"Warning: Failed to decode layer: {e}", file=sys.stderr)
            continue
    
    if not layers_data:
        print("Error: No valid PNG layers found", file=sys.stderr)
        sys.exit(EXIT_ERROR_GENERAL)
    
    # Setup animation canvas if this is animated content
    if is_animation:
        # Calculate actual terminal lines needed for protocol
        basis = meow.canvas.basis if meow.canvas and meow.canvas.basis else (2, 2)
        terminal_lines = GeometryAPI.get_terminal_lines_for_protocol(height, basis, protocol)
        renderer.setup_animation_canvas(terminal_lines)
    
    # Get loop count
    loop_count = meow.canvas.loop if meow.canvas else 1
    
    # Render with protocol-aware animation
    try:
        renderer.render_with_loop(layers_data, loop_count)
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        print(file=sys.stderr)
    finally:
        # Teardown animation canvas if it was set up
        if is_animation:
            basis = meow.canvas.basis if meow.canvas and meow.canvas.basis else (2, 2)
            terminal_lines = GeometryAPI.get_terminal_lines_for_protocol(height, basis, protocol)
            renderer.teardown_animation_canvas(terminal_lines)


def _display_glyxel_fallback(content_bytes: bytes, meow: MEOWContent, width: int, height: int) -> None:
    """
    Fallback to glyxel visible output rendering.
    
    Used when:
    - No PNG data available
    - Protocol is glyxel
    - Protocol-aware rendering fails
    """
    # Check if animated
    has_frames = any(layer.frame is not None for layer in meow.layers)
    
    if has_frames:
        # Use legacy animation rendering (glyxel visible output)
        _display_animated_legacy(meow, height)
    else:
        # Simple static display
        print(content_bytes.decode('utf-8'), end='')
        sys.stdout.flush()


def _display_animated_legacy(meow: MEOWContent, canvas_height: int):
    """
    Legacy glyxel animation display (preserves existing behavior).
    
    Uses visible_output field with ANSI cursor positioning.
    This is kept for backward compatibility and as glyxel fallback.
    """
    frames = meow.group_by_frame()
    loop_count = meow.canvas.loop if meow.canvas else 1
    is_infinite = meow.canvas.is_infinite_loop() if meow.canvas else False
    
    # Get terminal size for truncation
    term_width, term_height = get_terminal_size()
    
    # Emit layer zero to scroll terminal and establish origin
    if canvas_height:
        # Reserve vertical space (scroll terminal)
        print('\n' * canvas_height, end='')
        # Move up to canvas top
        print(f'\x1b[{canvas_height}A', end='')
        # Save cursor at canvas origin
        print('\x1b[s', end='')
        sys.stdout.flush()
    
    # Auto-truncate to fit terminal (leave room for prompt)
    display_height = min(canvas_height, term_height - 2)
    
    # Hide cursor for animation
    print('\x1b[?25l', end='', flush=True)
    
    try:
        import time
        
        iteration = 0
        while is_infinite or iteration < loop_count:
            for frame_num in sorted(frames.keys()):
                frame_layers = frames[frame_num]
                
                # Build frame output
                frame_buffer = []
                frame_buffer.append('\x1b[u')  # Restore cursor
                
                # Collect layer output
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
                    truncated_line = _truncate_ansi_line(line, term_width)
                    frame_buffer.append(truncated_line)
                    frame_buffer.append('\x1b[K')  # Clear to end of line
                    
                    if idx < display_height - 1:
                        frame_buffer.append('\x1b[B\x1b[G')  # Next line
                
                # Write frame
                sys.stdout.write(''.join(frame_buffer))
                sys.stdout.flush()
                
                # Get delay
                delay_ms = DEFAULT_FRAME_DELAY
                for layer in frame_layers:
                    if layer.frame is not None:
                        delay_ms = layer.delay
                        break
                
                time.sleep(delay_ms / 1000.0)
            
            iteration += 1
            
    except KeyboardInterrupt:
        pass
    finally:
        # Restore cursor position and show cursor
        print('\x1b[u\x1b[?25h', end='', flush=True)
        # Move cursor below animation
        print(f'\x1b[{canvas_height}B')


def _truncate_ansi_line(line: str, max_width: int) -> str:
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
