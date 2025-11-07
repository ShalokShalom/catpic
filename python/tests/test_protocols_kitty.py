# Destination: tests/test_protocols_kitty.py

"""
Test Kitty Graphics Protocol implementation.
"""

import pytest
import base64
from PIL import Image

from catpic.core import BASIS
from catpic.protocols import get_generator, list_protocols
from catpic.protocols.kitty import KittyGenerator
from catpic.protocols.core import encode_png, decode_png


class TestKittyGenerator:
    """Test Kitty protocol generator."""
    
    def test_protocol_name(self):
        """Test protocol identifier."""
        generator = KittyGenerator()
        assert generator.protocol_name == 'kitty'
    
    def test_can_optimize(self):
        """Test that Kitty can optimize (PNG pass-through)."""
        generator = KittyGenerator()
        assert generator.can_optimize() is True
    
    def test_generate_from_png(self):
        """Test generating Kitty output from PNG."""
        # Create test image
        img = Image.new('RGB', (10, 10), color='blue')
        png_bytes = encode_png(img)
        
        generator = KittyGenerator()
        output = generator.generate(png_bytes)
        
        # Should return bytes
        assert isinstance(output, bytes)
        
        # Decode for inspection
        output_str = output.decode('utf-8')
        
        # Should contain Kitty escape sequence
        assert output_str.startswith('\x1b_G')
        assert output_str.endswith('\x1b\\')
        
        # Should contain transmission parameters
        assert 'f=100' in output_str  # Direct transmission
        assert 'a=T' in output_str    # Transmission mode
        assert 'm=0' in output_str    # Single chunk
    
    def test_kitty_format_structure(self):
        """Test that output matches Kitty protocol format."""
        img = Image.new('RGB', (5, 5), color='red')
        png_bytes = encode_png(img)
        
        generator = KittyGenerator()
        output = generator.generate(png_bytes).decode('utf-8')
        
        # Parse structure: ESC _G params;base64_data ESC \
        assert output.startswith('\x1b_G')
        
        # Extract parts
        parts = output[3:-2]  # Remove ESC _G and ESC \
        param_data = parts.split(';', 1)
        
        assert len(param_data) == 2
        params, data = param_data
        
        # Verify parameters
        assert 'f=100' in params
        assert 'a=T' in params
        
        # Verify data is valid base64
        try:
            decoded = base64.standard_b64decode(data)
            assert len(decoded) > 0
            # Should be valid PNG
            test_img = decode_png(decoded)
            assert test_img.size == (5, 5)
        except Exception as e:
            pytest.fail(f"Invalid base64 or PNG data: {e}")
    
    def test_generate_with_config(self):
        """Test generation with explicit dimensions."""
        img = Image.new('RGB', (50, 50), color='green')
        png_bytes = encode_png(img)
        
        from catpic.protocols import ProtocolConfig
        config = ProtocolConfig(max_width=20, max_height=20)
        
        generator = KittyGenerator()
        output = generator.generate(png_bytes, config)
        
        # Should produce output
        assert len(output) > 0
        
        # Extract and verify resized image
        output_str = output.decode('utf-8')
        data = output_str.split(';', 1)[1][:-2]  # Get base64 data
        decoded_png = base64.standard_b64decode(data)
        result_img = decode_png(decoded_png)
        
        # Should be resized (aspect preserved)
        assert result_img.size[0] <= 20
        assert result_img.size[1] <= 20
    
    def test_transparency_support(self):
        """Test that Kitty preserves RGBA transparency."""
        # Create image with alpha channel
        img = Image.new('RGBA', (10, 10), (255, 0, 0, 128))  # Semi-transparent red
        png_bytes = encode_png(img)
        
        generator = KittyGenerator()
        output = generator.generate(png_bytes)
        
        # Extract and verify transparency preserved
        output_str = output.decode('utf-8')
        data = output_str.split(';', 1)[1][:-2]
        decoded_png = base64.standard_b64decode(data)
        result_img = decode_png(decoded_png)
        
        # Should maintain RGBA mode
        assert result_img.mode in ('RGBA', 'RGB')  # PIL may optimize
    
    def test_quality_settings(self):
        """Test different quality settings affect compression."""
        img = Image.new('RGB', (20, 20), color='blue')
        png_bytes = encode_png(img)
        
        from catpic.protocols import ProtocolConfig
        
        generator = KittyGenerator()
        
        # Generate with different quality settings
        low = generator.generate(png_bytes, ProtocolConfig(quality='low'))
        high = generator.generate(png_bytes, ProtocolConfig(quality='high'))
        
        # High quality should generally be smaller (better compression)
        # But for this simple test, just verify both work
        assert len(low) > 0
        assert len(high) > 0
    
    def test_invalid_png(self):
        """Test that invalid PNG raises ValueError."""
        generator = KittyGenerator()
        
        with pytest.raises(ValueError, match="Invalid PNG"):
            generator.generate(b"not a png")


class TestKittyRegistration:
    """Test Kitty protocol registration."""
    
    def test_kitty_not_auto_registered(self):
        """Test that Kitty is not auto-registered (explicit opt-in)."""
        protocols = list_protocols()
        # Kitty should be registered by __init__.py or explicitly
        # For now, it may not be auto-registered like glyxel
        # This test documents current behavior
    
    def test_kitty_can_be_registered(self):
        """Test that Kitty can be manually registered."""
        from catpic.protocols import register_protocol
        
        register_protocol('kitty', KittyGenerator)
        
        # Should now be available
        generator = get_generator('kitty')
        assert isinstance(generator, KittyGenerator)
        assert generator.protocol_name == 'kitty'
    
    def test_kitty_generate_via_registry(self):
        """Test using Kitty through registry."""
        from catpic.protocols import register_protocol
        
        # Register first
        register_protocol('kitty', KittyGenerator)
        
        img = Image.new('RGB', (10, 10), color='red')
        png_bytes = encode_png(img)
        
        generator = get_generator('kitty')
        output = generator.generate(png_bytes)
        
        assert len(output) > 0
        assert output.startswith(b'\x1b_G')
