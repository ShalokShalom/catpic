"""
MEOW v0.6 decoder - Display and manipulation
"""

import sys
import time
from pathlib import Path
from typing import Optional

from .core import EXIT_ERROR_FILE_NOT_FOUND, DEFAULT_FRAME_DELAY
from .meow_parser import MEOWParser, MEOWFile


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
    # For phase 1, just output visible content in stream order
    # Melding is not implemented yet (phase 2 feature)
    
    for layer in meow.layers:
        if layer.visible_output:
            print(layer.visible_output, end='')
    
    # Ensure newline at end
    print()


def _display_animated(meow: MEOWFile, meld: bool):
    """Display animated MEOW file"""
    frames = meow.group_by_frame()
    loop_count = meow.canvas.loop if meow.canvas else 1
    is_infinite = meow.canvas.is_infinite_loop() if meow.canvas else False
    
    iteration = 0
    while is_infinite or iteration < loop_count:
        for frame_num in sorted(frames.keys()):
            frame_layers = frames[frame_num]
            
            # Clear screen and position cursor
            print('\x1b[2J\x1b[H', end='')
            
            # Display all layers in this frame
            for layer in frame_layers:
                if layer.visible_output:
                    print(layer.visible_output, end='')
            
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
