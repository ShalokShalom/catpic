# Destination: src/catpic/protocols/iterm2.py

"""
iTerm2 Inline Images Protocol implementation.

iTerm2's inline images protocol is also supported by:
- iTerm2 (native)
- VS Code integrated terminal
- WezTerm (with compatibility mode)
- Tabby

The protocol uses base64-encoded image data wrapped in an OSC (Operating System Command)
escape sequence.

Reference: https://iterm2.com/documentation-images.html
"""

import base64
from io import BytesIO
from typing import Optional

from PIL import Image

from .base import ProtocolGenerator, ProtocolConfig


class ITerm2Generator(ProtocolGenerator):
    """
    Generate iTerm2 inline image sequences.
    
    Format: ESC ] 1337 ; File = [arguments] : base64-data BEL
    
    This is one of the simplest graphics protocols - just base64-encode
    the PNG data and wrap it in an escape sequence.
    """
    
    @property
    def protocol_name(self) -> str:
        """Return protocol name."""
        return "iterm2"
    
    @property
    def can_optimize(self) -> bool:
        """iTerm2 doesn't support incremental updates."""
        return False
    
    def generate(self, png_data: bytes, config: Optional[ProtocolConfig] = None) -> bytes:
        """
        Generate iTerm2 inline image escape sequence from PNG data.
        
        Args:
            png_data: PNG image data
            config: Optional configuration (max_width, max_height, quality)
            
        Returns:
            iTerm2 escape sequence as bytes
        """
        if config is None:
            config = ProtocolConfig()
        
        # Load image to check if resizing is needed
        img = Image.open(BytesIO(png_data))
        
        # Resize if needed
        if config.max_width or config.max_height:
            img = self._resize_image(img, config.max_width, config.max_height)
            
            # Re-encode as PNG after resize
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            png_data = buffer.getvalue()
        
        # Base64 encode the PNG data
        b64_data = base64.b64encode(png_data).decode('ascii')
        
        # Build iTerm2 escape sequence
        # ESC ] 1337 ; File = inline=1 : <base64-data> BEL
        # inline=1 means display inline (required for terminal output)
        escape_seq = f'\x1b]1337;File=inline=1:{b64_data}\x07'
        
        return escape_seq.encode('ascii')
    
    def _resize_image(self, img: Image.Image, max_width: Optional[int], max_height: Optional[int]) -> Image.Image:
        """Resize image maintaining aspect ratio."""
        width, height = img.size
        
        if max_width and width > max_width:
            ratio = max_width / width
            width = max_width
            height = int(height * ratio)
        
        if max_height and height > max_height:
            ratio = max_height / height
            height = max_height
            width = int(width * ratio)
        
        if (width, height) != img.size:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        return img
