# Destination: src/catpic/geometry.py

"""
Geometry calculations and inference for catpic content.

Provides bidirectional conversion between:
- Glyxel cells ↔ Pixels
- Canvas dimensions ↔ Terminal lines
- Inference of canvas size from content
- Protocol-aware display calculations
"""

import re
from typing import Tuple, Optional

from .core import BASIS_ASPECT_CORRECTIONS


class GeometryAPI:
    """
    Geometry calculations for catpic content.
    
    This API enables:
    - Idempotent conversion (glyxel ↔ PNG ↔ glyxel)
    - Canvas size inference from visible output
    - Protocol-aware terminal line calculation
    - Basis-aware aspect ratio handling
    """
    
    @staticmethod
    def infer_canvas_size(meow) -> Tuple[int, int]:
        """
        Infer canvas size from MEOW content.
        
        Priority:
        1. Explicit canvas.size metadata
        2. Infer from visible_output (glyxel content)
        3. Infer from PNG dimensions + basis
        4. Default to terminal size
        
        Args:
            meow: MEOWContent object
            
        Returns:
            (width, height) in character cells
        """
        # Priority 1: Explicit metadata
        if meow.canvas and meow.canvas.size:
            return meow.canvas.size
        
        # Priority 2: Infer from glyxel visible output
        for layer in meow.layers:
            if layer.visible_output:
                size = GeometryAPI._infer_from_visible_output(layer.visible_output)
                if size:
                    return size
        
        # Priority 3: Infer from PNG + basis
        for layer in meow.layers:
            if layer.cells and layer.ctype == 'png':
                try:
                    import base64
                    from .protocols.core import decode_png
                    
                    png_data = base64.b64decode(layer.cells)
                    img = decode_png(png_data)
                    
                    # Get basis (layer basis or canvas basis)
                    basis = layer.basis if layer.basis else (
                        meow.canvas.basis if meow.canvas and meow.canvas.basis else (2, 2)
                    )
                    
                    return GeometryAPI.pixels_to_glyxel(img.width, img.height, basis)
                except Exception:
                    continue
        
        # Priority 4: Default to terminal size
        import os
        try:
            size = os.get_terminal_size()
            return (size.columns, size.lines)
        except (AttributeError, OSError):
            return (80, 24)
    
    @staticmethod
    def _infer_from_visible_output(visible_output: str) -> Optional[Tuple[int, int]]:
        """
        Infer canvas dimensions from glyxel visible output.
        
        Args:
            visible_output: ANSI-rendered glyxel content
            
        Returns:
            (width, height) in cells, or None if cannot infer
        """
        if not visible_output:
            return None
        
        lines = visible_output.split('\n')
        height = len(lines)
        
        if height == 0:
            return None
        
        # Calculate max visible width (strip ANSI codes)
        max_width = 0
        for line in lines:
            visible_width = GeometryAPI._count_visible_chars(line)
            max_width = max(max_width, visible_width)
        
        return (max_width, height)
    
    @staticmethod
    def _count_visible_chars(text: str) -> int:
        """
        Count visible characters in text, excluding ANSI escape sequences.
        
        Args:
            text: Text potentially containing ANSI codes
            
        Returns:
            Count of visible characters
        """
        # Remove ANSI escape sequences
        # Pattern: ESC [ ... m  (SGR - colors/styles)
        #          ESC ] ... BEL/ST  (OSC - operating system commands)
        ansi_pattern = r'\x1b\[[0-9;]*m|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)'
        stripped = re.sub(ansi_pattern, '', text)
        return len(stripped)
    
    @staticmethod
    def glyxel_to_pixels(width: int, height: int, basis: Tuple[int, int]) -> Tuple[int, int]:
        """
        Convert glyxel cell dimensions to pixel dimensions.
        
        Args:
            width: Width in glyxel cells
            height: Height in glyxel cells
            basis: Glyxel basis [bx, by]
            
        Returns:
            (pixel_width, pixel_height)
        """
        bx, by = basis
        return (width * bx, height * by)
    
    @staticmethod
    def pixels_to_glyxel(pixel_width: int, pixel_height: int, basis: Tuple[int, int]) -> Tuple[int, int]:
        """
        Convert pixel dimensions to glyxel cell dimensions.
        
        Args:
            pixel_width: Width in pixels
            pixel_height: Height in pixels
            basis: Glyxel basis [bx, by]
            
        Returns:
            (cell_width, cell_height)
        """
        bx, by = basis
        cell_width = (pixel_width + bx - 1) // bx  # Ceiling division
        cell_height = (pixel_height + by - 1) // by
        return (cell_width, cell_height)
    
    @staticmethod
    def get_terminal_lines_for_protocol(
        canvas_height: int,
        basis: Tuple[int, int],
        protocol: str
    ) -> int:
        """
        Calculate actual terminal lines needed for rendering.
        
        This addresses protocol-specific rendering behavior:
        - Glyxel: 1 cell = 1 terminal line
        - Image protocols: Depends on pixel height and terminal cell size
        
        Args:
            canvas_height: Canvas height in cells
            basis: Glyxel basis [bx, by]
            protocol: Protocol name ('kitty', 'sixel', 'iterm2', 'glyxel')
            
        Returns:
            Number of terminal lines required
        """
        if protocol == 'glyxel':
            # Glyxel renders 1:1 with terminal cells
            return canvas_height
        
        # For image protocols, calculate based on pixel height
        # Image protocols render at pixel resolution, terminal wraps to lines
        _, pixel_height = GeometryAPI.glyxel_to_pixels(1, canvas_height, basis)
        
        # Estimate terminal cell height in pixels
        # Common values: 16-25px per cell (depends on font/terminal)
        # Use conservative estimate: 20px per cell
        TERMINAL_CELL_HEIGHT_PX = 20
        
        # Calculate lines needed (ceiling division)
        terminal_lines = (pixel_height + TERMINAL_CELL_HEIGHT_PX - 1) // TERMINAL_CELL_HEIGHT_PX
        
        # Add safety margin for terminal chrome
        return terminal_lines + 1
    
    @staticmethod
    def get_aspect_correction(basis: Tuple[int, int]) -> float:
        """
        Get aspect ratio correction factor for basis.
        
        Args:
            basis: Glyxel basis [bx, by]
            
        Returns:
            Aspect correction factor
        """
        basis_key = f"{basis[0]}x{basis[1]}"
        return BASIS_ASPECT_CORRECTIONS.get(basis_key, 1.0)
