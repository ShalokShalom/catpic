# Destination: src/catpic/framebuffer.py

"""
Protocol-agnostic display abstraction.

Provides a unified interface for rendering images to the terminal
regardless of the underlying graphics protocol (kitty, sixel, iterm2, glyxel).
"""

import sys
from typing import Optional

from .protocols import get_generator, ProtocolConfig


class FrameBuffer:
    """
    Protocol-agnostic framebuffer for terminal display.
    
    Wraps protocol generators and provides a clean interface for
    rendering images, clearing the display, and managing frame sequences.
    
    This abstraction enables:
    - Protocol-aware animation (frame sequences in kitty/sixel/iterm2)
    - External frame sources (games, video players, emulators)
    - Future optimizations (double-buffering, damage tracking)
    """
    
    def __init__(self, protocol: str, width: int, height: int):
        """
        Initialize framebuffer with protocol and dimensions.
        
        Args:
            protocol: Protocol name ('kitty', 'sixel', 'iterm2', 'glyxel')
            width: Display width in characters
            height: Display height in characters
        """
        self.protocol_name = protocol
        self.protocol = get_generator(protocol)
        self.width = width
        self.height = height
        self.config = ProtocolConfig(max_width=width, max_height=height)
    
    def render(self, png_data: bytes) -> None:
        """
        Render PNG image data to terminal.
        
        Args:
            png_data: PNG-encoded image data
        """
        output = self.protocol.generate(png_data, self.config)
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
    
    def clear(self) -> None:
        """
        Clear the display area.
        
        Uses protocol-specific clearing if available (e.g., cursor positioning
        for glyxel, image deletion for protocols that support it).
        """
        clear_seq = self.protocol.clear()
        if clear_seq:
            sys.stdout.buffer.write(clear_seq)
            sys.stdout.buffer.flush()
    
    def present(self) -> None:
        """
        Present the framebuffer (swap buffers if double-buffered).
        
        Current implementation: Immediate mode (no buffering).
        Future: Double-buffering support for smoother animation.
        """
        # Placeholder for future double-buffering
        # For now, render() is immediate
        pass
    
    def supports_animation(self) -> bool:
        """
        Check if protocol supports efficient frame sequences.
        
        Returns:
            True if protocol can handle animation efficiently
        """
        return self.protocol.supports_animation()
    
    @property
    def is_immediate_mode(self) -> bool:
        """
        Check if framebuffer is in immediate mode (no buffering).
        
        Returns:
            True for current implementation (always immediate)
        """
        return True
