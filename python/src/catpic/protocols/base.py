"""
Base protocol interface for MEOW v0.7 protocol system.

Defines abstract interface that all protocol generators must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProtocolConfig:
    """
    Configuration for protocol generation.
    
    Attributes:
        max_width: Maximum width in pixels (None = no limit)
        max_height: Maximum height in pixels (None = no limit)
        quality: Quality setting ('low', 'medium', 'high', 'auto')
        preserve_aspect: Whether to maintain aspect ratio
    """
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    quality: str = 'auto'
    preserve_aspect: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        valid_qualities = ['low', 'medium', 'high', 'auto']
        if self.quality not in valid_qualities:
            raise ValueError(
                f"Invalid quality '{self.quality}'. "
                f"Must be one of: {', '.join(valid_qualities)}"
            )


class ProtocolGenerator(ABC):
    """
    Abstract base class for protocol generators.
    
    All protocol implementations (Kitty, Sixel, iTerm2, glyxel)
    must implement this interface.
    """
    
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """
        Protocol identifier.
        
        Returns:
            Protocol name (e.g., 'kitty', 'sixel', 'glyxel')
        """
        pass
    
    @abstractmethod
    def generate(
        self,
        source_data: bytes,
        config: Optional[ProtocolConfig] = None,
    ) -> bytes:
        """
        Generate protocol output from source data.
        
        Args:
            source_data: Source image bytes (format determined by implementation)
            config: Optional generation configuration
        
        Returns:
            Protocol-specific output bytes ready for terminal display
        
        Raises:
            ValueError: If source_data is invalid
            RuntimeError: If generation fails
        """
        pass
    
    @abstractmethod
    def can_optimize(self) -> bool:
        """
        Check if this protocol can bypass common processing.
        
        Returns:
            True if protocol can use fast paths (e.g., PNG pass-through)
            False if protocol requires full processing pipeline
        """
        pass

    def clear(self) -> bytes:
        """
        Generate escape sequence to clear previous output.
        
        Used for animation to clear the previous frame before displaying
        the next one. Default implementation returns empty bytes (no clearing).
        
        Protocols should override this if they need specific clearing logic:
        - Glyxel: ANSI cursor positioning and clear sequences
        - Kitty/Sixel/iTerm2: May not need explicit clearing (image replacement)
        
        Returns:
            Escape sequence to clear display, or empty bytes
        """
        return b''
    
    def supports_animation(self) -> bool:
        """
        Check if protocol supports efficient frame sequences.
        
        Returns True for protocols that can handle animation efficiently
        (kitty, sixel, iterm2 can replace images in place).
        Returns False for protocols where animation is expensive.
        
        Default: True (most protocols support animation reasonably well)
        
        Returns:
            True if protocol supports efficient animation
        """
        return True
    
    def validate_source(self, source_data: bytes) -> bool:
        """
        Validate source data before generation.
        
        Default implementation checks for non-empty data.
        Override for protocol-specific validation.
        
        Args:
            source_data: Source data to validate
        
        Returns:
            True if valid, False otherwise
        """
        return len(source_data) > 0
