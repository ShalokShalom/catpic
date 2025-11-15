# Destination: src/catpic/encoder.py

"""
MEOW v0.7 Encoder - Core functionality with protocol support

Encodes images to MEOW format with dual content:
- Full-resolution PNG in cells field (protocol data)
- Glyxel ANSI in visible output (cat compatibility)
"""

import json
import base64
from pathlib import Path
from shutil import get_terminal_size
from typing import Optional, Union, Tuple

from PIL import Image

from .core import (
    BASIS, CatpicCore, MEOW_VERSION, MEOW_OSC_NUMBER, DEFAULT_BASIS,
    get_char_aspect, build_layer_zero, build_footer
)
from .primitives import image_to_cells, cells_to_ansi_lines
from .protocols.core import encode_png


def calculate_display_dimensions(
    img: Image.Image,
    basis: BASIS,
    max_cols: Optional[int] = None,
    max_rows: Optional[int] = None,
) -> Tuple[int, int]:
    """
    Calculate intelligent display dimensions with basis-aware aspect correction.
    
    Rules:
    - No upscaling (respect native dimensions)
    - Fit within max constraints (prevent overflow)
    - Maintain aspect ratio (visual correctness with basis correction)
    
    Args:
        img: Source image
        basis: BASIS level for pixel-to-char conversion
        max_cols: Maximum terminal columns (None = no limit)
        max_rows: Maximum terminal rows (None = no limit)
    
    Returns:
        (width_chars, height_chars) tuple
    """
    basis_x, basis_y = basis.value
    
    # Get basis-corrected character aspect ratio
    char_aspect = get_char_aspect(basis)
    
    # Start with image aspect ratio
    image_aspect = img.height / img.width
    
    # Calculate width in cells (respecting native size)
    native_width_chars = (img.width + basis_x - 1) // basis_x  # Ceiling division
    
    # Calculate height that preserves visual aspect with basis correction
    # Formula: height_chars = width_chars * image_aspect * (basis_y / basis_x) / char_aspect
    native_height_chars = int(
        native_width_chars * image_aspect * (basis_y / basis_x) / char_aspect
    )
    
    # Ensure at least 1
    native_height_chars = max(1, native_height_chars)
    
    width = native_width_chars
    height = native_height_chars
    
    # Apply constraints (no upscaling, but fit within limits)
    if max_cols and width > max_cols:
        width = max_cols
        # Recalculate height maintaining aspect
        height = int(width * image_aspect * (basis_y / basis_x) / char_aspect)
    
    if max_rows and height > max_rows:
        height = max_rows
        # Recalculate width maintaining aspect
        width = int(height * char_aspect / image_aspect / (basis_y / basis_x))
    
    # Ensure at least 1x1
    width = max(1, width)
    height = max(1, height)
    
    return (width, height)


class CatpicEncoder:
    """
    Encode images to MEOW v0.7 format with protocol support.
    
    Phase 2C: Dual content (PNG + glyxel) with intelligent sizing
    """
    
    def __init__(self, basis: Optional[BASIS] = None):
        """
        Initialize encoder.
        
        Args:
            basis: BASIS level for encoding (default: from config or BASIS_2_2)
        """
        if basis is None:
            # This should never happen now - CLI always provides basis
            # But keep as fallback
            from .core import get_default_basis
            basis = get_default_basis()
        
        self.basis = basis
        self.basis_tuple = basis.value  # (x, y) tuple
    
    def encode_image(
        self,
        image_path: Union[str, Path],
        width: Optional[int] = None,
        height: Optional[int] = None,
        protocol: Optional[str] = None,
    ) -> str:
        """
        Encode a static image to MEOW v0.7 format.
        
        Creates dual-content MEOW file:
        - cells field: full-resolution PNG (for protocol display)
        - visible output: glyxel ANSI (for cat compatibility)
        
        Or glyxel-only mode for minimal file size.
        
        Intelligent sizing (if width/height not specified):
        - Uses min(native_size, terminal_size - margin)
        - No upscaling by default
        - Basis-aware aspect ratio correction
        
        Args:
            image_path: Path to image file
            width: Output width in characters (default: intelligent sizing)
            height: Output height in characters (default: auto from aspect)
            protocol: Protocol mode ('glyxel', 'glyxel_only', None=default to 'glyxel')
        
        Returns:
            MEOW v0.7 formatted string
        """
        # Default to glyxel (dual content)
        if protocol is None:
            protocol = 'glyxel'
        
        # Load image
        with Image.open(image_path) as img:
            img_rgb = img.convert("RGB")
            
            # Store original dimensions
            orig_width, orig_height = img_rgb.size
            
            # Calculate display dimensions with intelligent sizing
            if width is None and height is None:
                # Get terminal size
                term_width, term_height = get_terminal_size()
                
                # Conservative max for cat compatibility: 80 cols
                # But respect native size (no upscaling)
                max_cols = min(80, term_width - 2)  # Leave 2-char margin
                
                width, height = calculate_display_dimensions(
                    img_rgb, self.basis, max_cols=max_cols
                )
            elif width is not None and height is None:
                # Width specified, calculate height maintaining aspect
                char_aspect = get_char_aspect(self.basis)
                basis_x, basis_y = self.basis_tuple
                image_aspect = img_rgb.height / img_rgb.width
                height = int(width * image_aspect * (basis_y / basis_x) / char_aspect)
            elif height is not None and width is None:
                # Height specified, calculate width maintaining aspect
                char_aspect = get_char_aspect(self.basis)
                basis_x, basis_y = self.basis_tuple
                image_aspect = img_rgb.height / img_rgb.width
                width = int(height * char_aspect / image_aspect / (basis_y / basis_x))
            # else: both specified, use as-is
            
            # Generate glyxel visible output
            cells = image_to_cells(img_rgb, width, height, basis=self.basis)
            ansi_lines = cells_to_ansi_lines(cells)
            ansi_output = '\n'.join(ansi_lines)
            
            # Encode full-resolution PNG for protocol data (unless glyxel_only)
            png_data = None
            if protocol != 'glyxel_only':
                png_data = encode_png(img_rgb)
        
        # Build MEOW v0.7 file
        parts = []
        
        # Canvas metadata (layer zero - reserves space, no visible content)
        canvas_metadata = {
            "meow": MEOW_VERSION,
            "size": [width, height],
            "basis": list(self.basis_tuple),
        }
        parts.append(build_layer_zero(canvas_metadata, height))
        
        # Layer 1: Protocol data + visible output
        # Layer metadata OSC MUST come before visible output
        if png_data:
            layer_metadata = {
                "ctype": "png",
                "cells": base64.b64encode(png_data).decode('ascii'),
                "meta": {
                    "orig_size": [orig_width, orig_height],
                },
            }
            layer_json = json.dumps(layer_metadata, separators=(',', ':'))
            parts.append(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07')
        
        # Visible content for this layer (glyxel ANSI)
        parts.append(ansi_output)
        
        # Footer
        parts.append(build_footer(height))
        
        return ''.join(parts)

    def encode_animation(
        self,
        image_path: Union[str, Path],
        width: Optional[int] = None,
        height: Optional[int] = None,
        delay: Optional[int] = None,
        protocol: Optional[str] = None,
    ) -> str:
        """
        Encode animated GIF to MEOW v0.9 format with dual content.
        
        Creates PNG data for each frame to enable protocol-aware animation
        across kitty, sixel, iterm2, and glyxel.
        
        Args:
            image_path: Path to animated GIF
            width: Output width in characters (default: intelligent sizing)
            height: Output height in characters (default: auto from aspect)
            delay: Override frame delay in milliseconds (default: from GIF)
            protocol: Protocol mode ('glyxel', 'glyxel_only', None=dual content)
        
        Returns:
            MEOW v0.9 formatted string with frame metadata and PNG data
        """
        # Default to dual content (PNG + glyxel)
        if protocol is None:
            protocol = 'glyxel'
        
        with Image.open(image_path) as img:
            if not getattr(img, "is_animated", False):
                # Not animated, encode as static
                return self.encode_image(image_path, width, height, protocol)
            
            # Get animation info
            frame_count = getattr(img, 'n_frames', 1)
            default_delay = img.info.get('duration', 100)
            if delay is not None:
                default_delay = delay
            
            # Calculate dimensions from first frame
            img.seek(0)
            img_rgb = img.convert("RGB")
            
            # Intelligent sizing for animations
            if width is None and height is None:
                term_width, term_height = get_terminal_size()
                max_cols = min(80, term_width - 2)
                width, height = calculate_display_dimensions(
                    img_rgb, self.basis, max_cols=max_cols
                )
            elif width is not None and height is None:
                char_aspect = get_char_aspect(self.basis)
                basis_x, basis_y = self.basis_tuple
                image_aspect = img_rgb.height / img_rgb.width
                height = int(width * image_aspect * (basis_y / basis_x) / char_aspect)
            elif height is not None and width is None:
                char_aspect = get_char_aspect(self.basis)
                basis_x, basis_y = self.basis_tuple
                image_aspect = img_rgb.height / img_rgb.width
                width = int(height * char_aspect / image_aspect / (basis_y / basis_x))
            
            # Build MEOW v0.9 file with layer zero structure
            parts = []
            
            canvas_metadata = {
                "meow": MEOW_VERSION,
                "size": [width, height],
                "basis": list(self.basis_tuple),
                "loop": 0,  # Infinite loop
            }
            parts.append(build_layer_zero(canvas_metadata, height))
            
            # Encode each frame as a layer with dual content
            for frame_idx in range(frame_count):
                img.seek(frame_idx)
                frame_rgb = img.convert("RGB")
                
                # Convert to cells for glyxel
                cells = image_to_cells(frame_rgb, width, height, basis=self.basis)
                
                # Generate ANSI output (glyxel fallback)
                ansi_lines = cells_to_ansi_lines(cells)
                ansi_output = '\n'.join(ansi_lines)
                
                # Layer metadata with frame number and timing
                layer_metadata = {
                    "f": frame_idx,
                    "delay": default_delay,
                }
                
                # Add PNG data for protocol-aware rendering (unless glyxel_only)
                if protocol != 'glyxel_only':
                    png_data = encode_png(frame_rgb)
                    layer_metadata["ctype"] = "png"
                    layer_metadata["cells"] = base64.b64encode(png_data).decode('ascii')
                
                # Emit layer metadata
                layer_json = json.dumps(layer_metadata, separators=(',', ':'))
                parts.append(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07')
                
                # Emit visible output (glyxel)
                parts.append(ansi_output)
                
                # Frame separator for cat viewing (visual divider)
                parts.append(f'\n\x1b[2m--- Frame {frame_idx + 1}/{frame_count} ---\x1b[0m\n')
            
            parts.append(build_footer(height))
            
            return ''.join(parts)
