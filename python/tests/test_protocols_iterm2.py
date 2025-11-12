# Destination: tests/test_protocols_iterm2.py

"""
Tests for iTerm2 inline images protocol.
"""

import pytest
import base64
from io import BytesIO
from PIL import Image

from catpic.protocols.iterm2 import ITerm2Generator
from catpic.protocols import ProtocolConfig
from catpic.protocols.core import encode_png


@pytest.fixture
def iterm2_generator():
    """Create an iTerm2 generator instance."""
    return ITerm2Generator()


@pytest.fixture
def red_4x4_png():
    """Create a 4x4 red image as PNG bytes."""
    img = Image.new('RGB', (4, 4), (255, 0, 0))
    return encode_png(img)


@pytest.fixture
def test_image_png():
    """Create a test image as PNG bytes."""
    img = Image.new('RGB', (16, 16), (0, 128, 255))
    return encode_png(img)


class TestITerm2Generation:
    """Test basic iTerm2 generation."""
    
    def test_generates_iterm2_sequence(self, iterm2_generator, red_4x4_png):
        """iTerm2 output starts with OSC and ends with BEL."""
        output = iterm2_generator.generate(red_4x4_png)
        
        # Should start with OSC (ESC ] 1337)
        assert output.startswith(b'\x1b]1337;'), "Should start with OSC 1337"
        
        # Should contain File=inline=1:
        assert b'File=inline=1:' in output, "Should contain inline parameter"
        
        # Should end with BEL
        assert output.endswith(b'\x07'), "Should end with BEL"
    
    def test_contains_base64_data(self, iterm2_generator, red_4x4_png):
        """iTerm2 output contains base64-encoded data."""
        output = iterm2_generator.generate(red_4x4_png)
        
        # Extract the base64 data
        # Format: ESC]1337;File=inline=1:<base64>BEL
        parts = output.split(b':')
        assert len(parts) == 2, "Should have data after colon"
        
        b64_data = parts[1].rstrip(b'\x07')  # Remove BEL
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(b64_data)
            # Should be valid PNG
            assert decoded.startswith(b'\x89PNG'), "Should contain valid PNG data"
        except Exception as e:
            pytest.fail(f"Invalid base64 or PNG data: {e}")
    
    def test_generates_non_empty_output(self, iterm2_generator, red_4x4_png):
        """iTerm2 output contains data."""
        output = iterm2_generator.generate(red_4x4_png)
        
        # Should have meaningful content
        # ESC]1337;File=inline=1: is 23 bytes, plus base64 data, plus BEL
        assert len(output) > 50, "Should contain escape sequence and base64 data"
    
    def test_respects_max_width(self, iterm2_generator, test_image_png):
        """iTerm2 respects max_width constraint."""
        config = ProtocolConfig(max_width=8)
        output = iterm2_generator.generate(test_image_png, config)
        
        # Should still produce valid output (resized internally)
        assert output.startswith(b'\x1b]1337;')
        assert output.endswith(b'\x07')
        
        # Extract and decode to verify resize
        parts = output.split(b':')
        b64_data = parts[1].rstrip(b'\x07')
        decoded = base64.b64decode(b64_data)
        img = Image.open(BytesIO(decoded))
        
        assert img.width <= 8, "Image width should be constrained"
    
    def test_respects_max_height(self, iterm2_generator, test_image_png):
        """iTerm2 respects max_height constraint."""
        config = ProtocolConfig(max_height=8)
        output = iterm2_generator.generate(test_image_png, config)
        
        # Should still produce valid output (resized internally)
        assert output.startswith(b'\x1b]1337;')
        assert output.endswith(b'\x07')
        
        # Extract and decode to verify resize
        parts = output.split(b':')
        b64_data = parts[1].rstrip(b'\x07')
        decoded = base64.b64decode(b64_data)
        img = Image.open(BytesIO(decoded))
        
        assert img.height <= 8, "Image height should be constrained"


class TestITerm2ImageModes:
    """Test different image modes."""
    
    def test_rgb_mode(self, iterm2_generator):
        """RGB images work correctly."""
        img = Image.new('RGB', (8, 8), (0, 255, 0))
        png_data = encode_png(img)
        output = iterm2_generator.generate(png_data)
        
        assert output.startswith(b'\x1b]1337;')
        assert output.endswith(b'\x07')
    
    def test_rgba_mode(self, iterm2_generator):
        """RGBA images work correctly."""
        img = Image.new('RGBA', (8, 8), (0, 0, 255, 255))
        png_data = encode_png(img)
        output = iterm2_generator.generate(png_data)
        
        assert output.startswith(b'\x1b]1337;')
        assert output.endswith(b'\x07')
    
    def test_grayscale_mode(self, iterm2_generator):
        """Grayscale images work correctly."""
        img = Image.new('L', (8, 8), 128)
        png_data = encode_png(img)
        output = iterm2_generator.generate(png_data)
        
        assert output.startswith(b'\x1b]1337;')
        assert output.endswith(b'\x07')


class TestITerm2Protocol:
    """Test protocol interface."""
    
    def test_protocol_name(self, iterm2_generator):
        """Protocol name is correct."""
        assert iterm2_generator.protocol_name == "iterm2"
    
    def test_cannot_optimize(self, iterm2_generator):
        """iTerm2 doesn't support optimization."""
        assert iterm2_generator.can_optimize is False
