# Destination: src/catpic/protocols/kitty.py

"""
Kitty Graphics Protocol generator.

Implements Kitty's native graphics protocol for high-performance image display
in Kitty terminal emulator. Supports direct transmission with PNG encoding.

Protocol documentation: https://sw.kovidgoyal.net/kitty/graphics-protocol/
"""

import base64
from typing import Optional

from ..core import BASIS
from .base import ProtocolGenerator, ProtocolConfig
from .core import decode_png, encode_png, resize_if_needed


class KittyGenerator(ProtocolGenerator):
    """
    Kitty Graphics Protocol generator.
    
    Uses direct transmission mode (f=100) for immediate display.
    Supports RGBA transparency and high-quality PNG encoding.
    """
    
    def __init__(self, basis: Optional[BASIS] = None):
        """
        Initialize Kitty generator.
        
        Args:
            basis: BASIS level (unused for Kitty, kept for interface consistency)
        """
        # Kitty uses native resolution, BASIS not applicable
        self.basis = basis
    
    @property
    def protocol_name(self) -> str:
        """Protocol identifier."""
        return 'kitty'
    
    def generate(
        self,
        source_data: bytes,
        config: Optional[ProtocolConfig] = None,
    ) -> bytes:
        """
        Generate Kitty graphics protocol output from PNG source.
        
        Uses direct transmission mode with base64-encoded PNG chunks.
        
        Args:
            source_data: PNG image bytes
            config: Optional configuration (dimensions, quality)
        
        Returns:
            Kitty graphics escape sequence as UTF-8 bytes
        
        Raises:
            ValueError: If PNG is invalid
        """
        config = config or ProtocolConfig()
        
        # Decode PNG
        img = decode_png(source_data)
        
        # Resize if needed (based on config)
        if config.max_width or config.max_height:
            img = resize_if_needed(
                img,
                config.max_width,
                config.max_height,
                preserve_aspect=config.preserve_aspect
            )
        
        # Re-encode as PNG for Kitty transmission
        # Kitty accepts PNG directly, use quality setting for compression
        compress_level = self._quality_to_compress_level(config.quality)
        png_bytes = encode_png(img, compress_level=compress_level)
        
        # Encode as base64
        b64_data = base64.standard_b64encode(png_bytes).decode('ascii')
        
        # Build Kitty graphics command
        # Format: ESC _G <key>=<val>,...;<base64_data> ESC \
        # Parameters:
        #   f=100  : Direct transmission (temporary image)
        #   a=T    : Transmission mode (direct)
        #   m=1    : More data chunks (0=final, 1=more coming)
        #            For single chunk, m=0
        
        # For simplicity, transmit in single chunk (m=0)
        # Future: Support chunked transmission for large images
        
        kitty_cmd = f'\x1b_Gf=100,a=T,m=0;{b64_data}\x1b\\'
        
        return kitty_cmd.encode('utf-8')
    
    def can_optimize(self) -> bool:
        """
        Kitty can optimize - direct PNG pass-through possible.
        
        Returns:
            True (can pass PNG directly with minimal processing)
        """
        return True
    
    def clear(self) -> bytes:
        """
        Clear previous Kitty image by restoring cursor position.

        For animation, assumes cursor was saved at canvas origin.
        Restores to that position so next frame renders at same location.

        Returns:
            ANSI escape sequence to restore cursor position
        """
        # ESC[u restores cursor to saved position
        # This matches the glyxel animation pattern
        return b'\x1b[u'

    def _quality_to_compress_level(self, quality: str) -> int:
        """
        Map quality setting to PNG compression level.
        
        Args:
            quality: Quality string ('low', 'medium', 'high', 'auto')
        
        Returns:
            PNG compression level (0-9)
        """
        quality_map = {
            'low': 3,      # Faster, larger files
            'medium': 6,   # Balanced (default)
            'high': 9,     # Slower, smaller files
            'auto': 6,     # Default to balanced
        }
        return quality_map.get(quality, 6)
