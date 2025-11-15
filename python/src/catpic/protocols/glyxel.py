"""
Glyxel protocol - Unicode block character rendering.

Wraps existing catpic glyxel rendering into protocol interface.
This is the universal fallback protocol that works in any UTF-8 terminal.
"""

from typing import Optional

from ..core import BASIS, get_char_aspect
from ..primitives import image_to_cells, cells_to_ansi_lines
from .base import ProtocolGenerator, ProtocolConfig
from .core import decode_png


class GlyxelGenerator(ProtocolGenerator):
    """
    Glyxel protocol generator.
    
    Uses existing catpic rendering pipeline (image_to_cells, cells_to_ansi_lines)
    to generate Unicode block character output with ANSI truecolor.
    """
    
    def __init__(self, basis: Optional[BASIS] = None):
        """
        Initialize glyxel generator.
        
        Args:
            basis: BASIS level for rendering (default: from environment)
        """
        if basis is None:
            from ..core import get_default_basis
            basis = get_default_basis()
        
        self.basis = basis
    
    @property
    def protocol_name(self) -> str:
        """Protocol identifier."""
        return 'glyxel'
    
    def generate(
        self,
        source_data: bytes,
        config: Optional[ProtocolConfig] = None,
    ) -> bytes:
        """
        Generate glyxel output from PNG source.
        
        Args:
            source_data: PNG image bytes
            config: Optional configuration (uses dimensions if provided)
        
        Returns:
            ANSI glyxel output as UTF-8 bytes
        """
        config = config or ProtocolConfig()
        
        # Decode PNG
        img = decode_png(source_data)
        
        # Calculate dimensions
        if config.max_width or config.max_height:
            width = config.max_width or 80
            height = config.max_height or 24
        else:
            # Auto-calculate from image aspect ratio
            width = 80
            char_aspect = get_char_aspect()
            image_aspect = img.height / img.width
            height = int(width * image_aspect / char_aspect)
        
        # Convert to cells using existing pipeline
        cells = image_to_cells(img, width, height, basis=self.basis)
        
        # Convert cells to ANSI output
        ansi_lines = cells_to_ansi_lines(cells)
        ansi_output = '\n'.join(ansi_lines)
        
        return ansi_output.encode('utf-8')
    
    def can_optimize(self) -> bool:
        """
        Glyxel cannot optimize - requires full processing.
        
        Returns:
            False (always needs full cell conversion)
        """
        return False

    def clear(self) -> bytes:
        """
        Clear glyxel output using ANSI escape sequences.
        
        Returns cursor to home position and clears the screen.
        This is used for animation to clear the previous frame.
        
        Returns:
            ANSI escape sequence to clear and reset cursor
        """
        # ESC[H moves cursor to home (1,1)
        # ESC[2J clears entire screen
        return b'\x1b[H\x1b[2J'
