"""
MEOW v0.6 decoder - Display and manipulation
"""

import sys
import time
import os
import re
from pathlib import Path
from typing import Optional

from .core import EXIT_ERROR_FILE_NOT_FOUND, DEFAULT_FRAME_DELAY
from .meow_parser import MEOWParser, MEOWFile


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


def load_meow(filepath: str) -> MEOWFile:
    """
    Load and parse a MEOW file
    
    Args:
        filepath: Path to .meow file
        
    Returns:
        Parsed MEOWFile object
        
    Raises:
        SystemExit: With code 5 if file not found
    """
    path = Path(filepath)
    
    if not path.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(EXIT_ERROR_FILE_NOT_FOUND)
    
    try:
        data = path.read_bytes()
    except Exception as e:
        print(f"Error: Cannot read file {filepath}: {e}", file=sys.stderr)
        sys.exit(EXIT_ERROR_FILE_NOT_FOUND)
    
    parser = MEOWParser()
    return parser.parse(data)


def display_meow(filepath: str, meld: bool = False):
    """
    Display a MEOW file to terminal
    
    Args:
        filepath: Path to .meow file
        meld: Force runtime melding (translucency recomputation)
    """
    meow = load_meow(filepath)
    
    # Check if animated
    has_frames = any(layer.frame is not None for layer in meow.layers)
    
    if has_frames:
        _display_animated(meow, meld)
    else:
        _display_static(meow, meld)


def _display_static(meow: MEOWFile, meld: bool):
    """Display static (non-animated) MEOW file"""
    # Get terminal size for truncation
    term_width, term_height = get_terminal_size()
    
    # Leave 1 line for prompt to avoid scrolling
    display_height = term_height - 1
    
    for layer in meow.layers:
        if layer.visible_output:
            truncated = truncate_ansi_output(layer.visible_output, term_width, display_height)
            print(truncated, end='')
    
    sys.stdout.flush()


def _display_animated(meow: MEOWFile, meld: bool):
    """Display animated MEOW file"""
    frames = meow.group_by_frame()
    loop_count = meow.canvas.loop if meow.canvas else 1
    is_infinite = meow.canvas.is_infinite_loop() if meow.canvas else False
    
    # Get terminal size for truncation
    term_width, term_height = get_terminal_size()
    
    # Get canvas height
    canvas_height = meow.canvas.size[1] if meow.canvas and meow.canvas.size else 24
    
    # Auto-truncate to fit terminal (leave room for prompt)
    display_height = min(canvas_height, term_height - 2)
    
    # Save cursor position and hide cursor at start
    print('\x1b[s\x1b[?25l', end='', flush=True)
    
    try:
        iteration = 0
        while is_infinite or iteration < loop_count:
            for frame_num in sorted(frames.keys()):
                frame_layers = frames[frame_num]
                
                # Restore to saved cursor position
                output_buffer = ['\x1b[u']
                
                # Collect all layer output for this frame
                frame_output = []
                for layer in frame_layers:
                    if layer.visible_output:
                        frame_output.append(layer.visible_output)
                
                combined = ''.join(frame_output)
                lines = combined.split('\n')
                
                # Output each line with cursor positioning
                for idx, line in enumerate(lines):
                    if idx >= display_height:
                        break
                    
                    # Truncate line to terminal width
                    truncated_line = truncate_ansi_line(line, term_width)
                    output_buffer.append(truncated_line)
                    
                    # Clear to end of line
                    output_buffer.append('\x1b[K')
                    
                    # Move to next line (down 1, column 0) - but not after last line
                    if idx < display_height - 1:
                        output_buffer.append('\x1b[B\x1b[G')
                
                # Output entire frame at once
                print(''.join(output_buffer), end='', flush=True)
                
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
        for _ in range(display_height):
            print('\x1b[B', end='')
        print()  # Final newline for prompt


def show_info(filepath: str):
    """
    Display metadata information about a MEOW file
    
    Args:
        filepath: Path to .meow file
    """
    meow = load_meow(filepath)
    
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
            print(f"  Cells: {len(layer.cells)} bytes")
        
        if layer.frame is not None:
            print(f"  Frame: {layer.frame}")
            print(f"  Delay: {layer.delay}ms")
        
        if layer.visible_output:
            print(f"  Visible Output: {len(layer.visible_output)} bytes")
