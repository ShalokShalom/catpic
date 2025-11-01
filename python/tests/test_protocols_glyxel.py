"""
Test glyxel protocol implementation.
"""

import pytest
from PIL import Image

from catpic.core import BASIS
from catpic.protocols import get_generator, list_protocols
from catpic.protocols.glyxel import GlyxelGenerator
from catpic.protocols.core import encode_png


class TestGlyxelGenerator:
    """Test glyxel protocol generator."""
    
    def test_protocol_name(self):
        """Test protocol identifier."""
        generator = GlyxelGenerator()
        assert generator.protocol_name == 'glyxel'
    
    def test_can_optimize(self):
        """Test that glyxel cannot optimize."""
        generator = GlyxelGenerator()
        assert generator.can_optimize() is False
    
    def test_generate_from_png(self):
        """Test generating glyxel output from PNG."""
        # Create test image
        img = Image.new('RGB', (10, 10), color='red')
        png_bytes = encode_png(img)
        
        generator = GlyxelGenerator(basis=BASIS.BASIS_2_2)
        output = generator.generate(png_bytes)
        
        # Should return bytes
        assert isinstance(output, bytes)
        
        # Should contain ANSI escape sequences
        output_str = output.decode('utf-8')
        assert '\x1b[' in output_str  # ANSI codes
        
        # Should contain content (ANSI + characters)
        # Exact Unicode blocks depend on image content
        assert len(output_str) > 100  # Should have substantial output
    
    def test_generate_with_config(self):
        """Test generation with explicit dimensions."""
        img = Image.new('RGB', (50, 50), color='blue')
        png_bytes = encode_png(img)
        
        from catpic.protocols import ProtocolConfig
        config = ProtocolConfig(max_width=20, max_height=10)
        
        generator = GlyxelGenerator()
        output = generator.generate(png_bytes, config)
        
        # Should produce output
        assert len(output) > 0
        
        # Count lines (approximately height)
        lines = output.decode('utf-8').split('\n')
        # May have slightly different count due to cell processing
        assert 8 <= len(lines) <= 12  # Roughly 10 ±2
    
    def test_different_basis_levels(self):
        """Test glyxel generation with different BASIS levels."""
        img = Image.new('RGB', (20, 20), color='green')
        png_bytes = encode_png(img)
        
        for basis in [BASIS.BASIS_1_2, BASIS.BASIS_2_2, BASIS.BASIS_2_3, BASIS.BASIS_2_4]:
            generator = GlyxelGenerator(basis=basis)
            output = generator.generate(png_bytes)
            
            assert len(output) > 0, f"Failed for {basis}"
    
    def test_invalid_png(self):
        """Test that invalid PNG raises ValueError."""
        generator = GlyxelGenerator()
        
        with pytest.raises(ValueError, match="Invalid PNG"):
            generator.generate(b"not a png")


class TestGlyxelRegistration:
    """Test glyxel protocol registration."""
    
    def test_glyxel_registered(self):
        """Test that glyxel is auto-registered."""
        protocols = list_protocols()
        assert 'glyxel' in protocols
    
    def test_get_glyxel_generator(self):
        """Test getting glyxel generator from registry."""
        generator = get_generator('glyxel')
        
        assert isinstance(generator, GlyxelGenerator)
        assert generator.protocol_name == 'glyxel'
    
    def test_glyxel_generate_via_registry(self):
        """Test using glyxel through registry."""
        img = Image.new('RGB', (10, 10), color='red')
        png_bytes = encode_png(img)
        
        generator = get_generator('glyxel')
        output = generator.generate(png_bytes)
        
        assert len(output) > 0
        assert b'\x1b[' in output  # ANSI codes
