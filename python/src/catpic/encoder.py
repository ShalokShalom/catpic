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
from typing import Optional, Union

from PIL import Image

from .core import (
    BASIS, CatpicCore, MEOW_VERSION, MEOW_OSC_NUMBER, DEFAULT_BASIS,
    get_char_aspect, build_layer_zero, build_footer
)
from .primitives import image_to_cells, cells_to_ansi_lines
from .protocols.core import encode_png


class CatpicEncoder:
    """
    Encode images to MEOW v0.7 format with protocol support.
    
    Phase 2C: Dual content (PNG + glyxel) or glyxel-only mode
    """
    
    def __init__(self, basis: Optional[BASIS] = None):
        """
        Initialize encoder.
        
        Args:
            basis: BASIS level for encoding (default: BASIS_2_2)
        """
        if basis is None:
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
        
        Args:
            image_path: Path to image file
            width: Output width in characters (default: 80)
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
            
            # Calculate display dimensions for glyxel
            if width is None:
                width = 80  # Default to 80 columns
            
            # Cap width to terminal size to prevent wrapping corruption
            term_width, _ = get_terminal_size()
            if width > term_width:
                width = term_width
            
            if height is None:
                # Maintain aspect ratio with terminal character aspect compensation
                image_aspect = img_rgb.height / img_rgb.width
                char_aspect = get_char_aspect()
                height = int(width * image_aspect / char_aspect)
            
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
        
        # Canvas metadata
        canvas_metadata = {
            "meow": MEOW_VERSION,
            "size": [width, height],
            "basis": list(self.basis_tuple),
        }
        parts.append(build_layer_zero(canvas_metadata, height))
        
        # Layer metadata with protocol data (if not glyxel_only)
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
        
        # Visual layer content (glyxel)
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
        Encode animated GIF to MEOW v0.7 format with layer zero.
        
        Note: Animation currently uses glyxel-only encoding.
        Protocol support for animations is future work.
        
        Args:
            image_path: Path to animated GIF
            width: Output width in characters (default: 80)
            height: Output height in characters (default: auto from aspect)
            delay: Override frame delay in milliseconds (default: from GIF)
            protocol: Protocol mode (currently ignored for animations)
        
        Returns:
            MEOW v0.7 formatted string with frame metadata
        """
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
            
            if width is None:
                width = 80  # Default to 80 columns
            
            if height is None:
                image_aspect = img_rgb.height / img_rgb.width
                char_aspect = get_char_aspect()
                height = int(width * image_aspect / char_aspect)
            
            # Build MEOW v0.7 file with layer zero structure
            parts = []
            
            canvas_metadata = {
                "meow": MEOW_VERSION,
                "size": [width, height],
                "basis": list(self.basis_tuple),
                "loop": 0,  # Infinite loop
            }
            parts.append(build_layer_zero(canvas_metadata, height))
            
            # Encode each frame as a layer with frame number
            for frame_idx in range(frame_count):
                img.seek(frame_idx)
                frame_rgb = img.convert("RGB")
                
                # Convert to cells
                cells = image_to_cells(frame_rgb, width, height, basis=self.basis)
                
                # Generate ANSI output
                ansi_lines = cells_to_ansi_lines(cells)
                ansi_output = '\n'.join(ansi_lines)
                
                # Layer block with frame metadata
                layer_metadata = {
                    "f": frame_idx,
                    "delay": default_delay,
                }
                layer_json = json.dumps(layer_metadata, separators=(',', ':'))
                parts.append(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07')
                parts.append(ansi_output)
                
                # Frame separator for cat viewing (visual divider)
                parts.append(f'\n\x1b[2m--- Frame {frame_idx + 1}/{frame_count} ---\x1b[0m\n')
            
            parts.append(build_footer(height))
            
            return ''.join(parts)
