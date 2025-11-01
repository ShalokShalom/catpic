"""
Test protocol base infrastructure.
"""

import pytest
from PIL import Image

from catpic.protocols import (
    ProtocolGenerator,
    ProtocolConfig,
    register_protocol,
    get_generator,
    list_protocols,
)
from catpic.protocols.base import ProtocolGenerator
from catpic.protocols.core import decode_png, encode_png, resize_if_needed


class MockProtocol(ProtocolGenerator):
    """Mock protocol for testing."""
    
    @property
    def protocol_name(self) -> str:
        return "mock"
    
    def generate(self, source_data: bytes, config=None) -> bytes:
        return b"MOCK_OUTPUT"
    
    def can_optimize(self) -> bool:
        return False


class TestProtocolConfig:
    """Test ProtocolConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ProtocolConfig()
        
        assert config.max_width is None
        assert config.max_height is None
        assert config.quality == 'auto'
        assert config.preserve_aspect is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = ProtocolConfig(
            max_width=800,
            max_height=600,
            quality='high',
            preserve_aspect=False,
        )
        
        assert config.max_width == 800
        assert config.max_height == 600
        assert config.quality == 'high'
        assert config.preserve_aspect is False
    
    def test_invalid_quality(self):
        """Test that invalid quality raises ValueError."""
        with pytest.raises(ValueError, match="Invalid quality"):
            ProtocolConfig(quality='invalid')


class TestProtocolRegistry:
    """Test protocol registration system."""
    
    def test_register_protocol(self):
        """Test protocol registration."""
        register_protocol('mock', MockProtocol)
        
        assert 'mock' in list_protocols()
    
    def test_get_generator(self):
        """Test getting registered protocol."""
        register_protocol('mock', MockProtocol)
        
        generator = get_generator('mock')
        
        assert isinstance(generator, MockProtocol)
        assert generator.protocol_name == 'mock'
    
    def test_get_unregistered_protocol(self):
        """Test that unregistered protocol raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported protocol"):
            get_generator('nonexistent')
    
    def test_list_protocols(self):
        """Test listing registered protocols."""
        register_protocol('mock', MockProtocol)
        
        protocols = list_protocols()
        
        assert isinstance(protocols, list)
        assert 'mock' in protocols


class TestProtocolCore:
    """Test protocol core utilities."""
    
    def test_encode_decode_png(self):
        """Test PNG encode/decode round-trip."""
        # Create test image
        img = Image.new('RGB', (10, 10), color='red')
        
        # Encode to PNG
        png_bytes = encode_png(img)
        
        assert len(png_bytes) > 0
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'  # PNG signature
        
        # Decode back
        decoded = decode_png(png_bytes)
        
        assert decoded.size == (10, 10)
        assert decoded.mode == 'RGB'
    
    def test_decode_invalid_png(self):
        """Test that invalid PNG raises ValueError."""
        with pytest.raises(ValueError, match="Invalid PNG"):
            decode_png(b"not a png")
    
    def test_resize_if_needed_no_resize(self):
        """Test that image within limits is not resized."""
        img = Image.new('RGB', (100, 100))
        
        resized = resize_if_needed(img, max_width=200, max_height=200)
        
        assert resized.size == (100, 100)
        assert resized is img  # Same object, not copied
    
    def test_resize_if_needed_width_limit(self):
        """Test resizing when width exceeds limit."""
        img = Image.new('RGB', (200, 100))
        
        resized = resize_if_needed(img, max_width=100, preserve_aspect=True)
        
        assert resized.size == (100, 50)  # Aspect preserved
    
    def test_resize_if_needed_height_limit(self):
        """Test resizing when height exceeds limit."""
        img = Image.new('RGB', (100, 200))
        
        resized = resize_if_needed(img, max_height=100, preserve_aspect=True)
        
        assert resized.size == (50, 100)  # Aspect preserved
    
    def test_resize_no_aspect_preservation(self):
        """Test resizing without preserving aspect ratio."""
        img = Image.new('RGB', (200, 100))
        
        resized = resize_if_needed(
            img,
            max_width=100,
            max_height=100,
            preserve_aspect=False
        )
        
        assert resized.size == (100, 100)  # Aspect not preserved
