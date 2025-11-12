# Destination: src/catpic/protocols/__init__.py

"""
Protocol system for catpic.

Auto-registers all protocol generators.
"""

from .base import ProtocolGenerator, ProtocolConfig
from .glyxel import GlyxelGenerator
from .kitty import KittyGenerator
from .sixel import SixelGenerator
from .iterm2 import ITerm2Generator  # ADD THIS LINE


# Global registry
_PROTOCOLS = {}


def register_protocol(name: str, generator_class: type[ProtocolGenerator]):
    """Register a protocol generator."""
    _PROTOCOLS[name] = generator_class


def get_generator(protocol: str) -> ProtocolGenerator:
    """Get a protocol generator instance."""
    if protocol not in _PROTOCOLS:
        raise ValueError(
            f"Unsupported protocol: {protocol}. "
            f"Available protocols: {', '.join(_PROTOCOLS.keys())}"
        )
    return _PROTOCOLS[protocol]()


def list_protocols() -> list[str]:
    """List all registered protocols."""
    return list(_PROTOCOLS.keys())


# Auto-register protocols
register_protocol('glyxel', GlyxelGenerator)
register_protocol('kitty', KittyGenerator)
register_protocol('sixel', SixelGenerator)
register_protocol('iterm2', ITerm2Generator)  # ADD THIS LINE


__all__ = [
    'ProtocolGenerator',
    'ProtocolConfig',
    'register_protocol',
    'get_generator',
    'list_protocols',
]

