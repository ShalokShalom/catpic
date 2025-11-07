# Destination: src/catpic/protocols/__init__.py

"""
MEOW v0.7 Protocol System

Provides abstraction layer for multiple terminal graphics protocols
with automatic capability detection and graceful fallback to glyxel.
"""

from typing import Dict, Type

from .base import ProtocolGenerator, ProtocolConfig
from .glyxel import GlyxelGenerator
from .kitty import KittyGenerator

# Protocol registry (populated as protocols are imported)
_GENERATORS: Dict[str, Type[ProtocolGenerator]] = {}


def register_protocol(name: str, generator_class: Type[ProtocolGenerator]) -> None:
    """
    Register a protocol generator.
    
    Args:
        name: Protocol identifier (e.g., 'kitty', 'sixel')
        generator_class: ProtocolGenerator subclass
    """
    _GENERATORS[name] = generator_class


def get_generator(protocol: str) -> ProtocolGenerator:
    """
    Get protocol generator by name.
    
    Args:
        protocol: Protocol name ('kitty', 'sixel', 'iterm2', 'glyxel')
    
    Returns:
        ProtocolGenerator instance
    
    Raises:
        ValueError: If protocol not supported
    """
    if protocol not in _GENERATORS:
        available = ', '.join(_GENERATORS.keys())
        raise ValueError(
            f"Unsupported protocol: {protocol}. "
            f"Available protocols: {available}"
        )
    
    return _GENERATORS[protocol]()


def list_protocols() -> list[str]:
    """
    List all registered protocol names.
    
    Returns:
        List of protocol identifiers
    """
    return list(_GENERATORS.keys())


# Auto-register protocols
register_protocol('glyxel', GlyxelGenerator)
register_protocol('kitty', KittyGenerator)

__all__ = [
    'ProtocolGenerator',
    'ProtocolConfig',
    'GlyxelGenerator',
    'KittyGenerator',
    'register_protocol',
    'get_generator',
    'list_protocols',
]
