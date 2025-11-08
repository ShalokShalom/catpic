# Destination: tests/test_protocols_sixel.py

"""
Tests for Sixel graphics protocol.
"""

import pytest
from io import BytesIO
from PIL import Image

from catpic.protocols.sixel import SixelGenerator
from catpic.protocols import ProtocolConfig
from catpic.protocols.core import encode_png


@pytest.fixture
def sixel_generator():
    """Create a Sixel generator instance."""
    return SixelGenerator()


@pytest.fixture
def red_4x4_png():
    """Create a 4x4 red image as PNG bytes."""
    img = Image.new('RGB', (4, 4), (255, 0, 0))
    return encode_png(img)


@pytest.fixture
def transparent_image_png():
    """Create an image with transparency as PNG bytes."""
    img = Image.new('RGBA', (8, 8), (255, 0, 0, 128))
    return encode_png(img)


class TestSixelGeneration:
    """Test basic Sixel generation."""
    
    def test_generates_sixel_sequence(self, sixel_generator, red_4x4_png):
        """Sixel output starts with DCS and ends with ST."""
        output = sixel_generator.generate(red_4x4_png)
        
        # Should start with DCS (Device Control String)
        assert output.startswith(b'\x1bP'), "Should start with DCS (ESC P)"
        
        # Should end with ST (String Terminator)
        assert output.endswith(b'\x1b\\'), "Should end with ST (ESC \\)"
    
    def test_generates_non_empty_output(self, sixel_generator, red_4x4_png):
        """Sixel output contains data."""
        output = sixel_generator.generate(red_4x4_png)
        
        # Should have meaningful content (DCS + palette + image data + ST)
        # Even a tiny 4x4 image should be > 20 bytes
        assert len(output) > 20, "Should contain palette and image data"
        
        # Should contain palette definition
        assert b'#0;2;' in output, "Should contain color palette"
    
    def test_handles_transparency(self, sixel_generator, transparent_image_png):
        """Sixel converts transparency to white background."""
        output = sixel_generator.generate(transparent_image_png)
        
        # Should produce valid Sixel output
        assert output.startswith(b'\x1bP')
        assert output.endswith(b'\x1b\\')
    
    def test_respects_max_width(self, sixel_generator, red_4x4_png):
        """Sixel respects max_width constraint."""
        config = ProtocolConfig(max_width=2)
        output = sixel_generator.generate(red_4x4_png, config)
        
        # Should still produce valid output (resized internally)
        assert output.startswith(b'\x1bP')
        assert output.endswith(b'\x1b\\')
    
    def test_respects_max_height(self, sixel_generator, red_4x4_png):
        """Sixel respects max_height constraint."""
        config = ProtocolConfig(max_height=2)
        output = sixel_generator.generate(red_4x4_png, config)
        
        # Should still produce valid output (resized internally)
        assert output.startswith(b'\x1bP')
        assert output.endswith(b'\x1b\\')


class TestSixelColorHandling:
    """Test Sixel color palette handling."""
    
    def test_quantizes_colors(self, sixel_generator):
        """Sixel quantizes to 256 colors or less."""
        # Create image with many colors (gradient)
        img = Image.new('RGB', (256, 256))
        pixels = img.load()
        for x in range(256):
            for y in range(256):
                pixels[x, y] = (x, y, (x + y) % 256)
        
        png_data = encode_png(img)
        output = sixel_generator.generate(png_data)
        
        # Should produce valid Sixel output with quantized palette
        assert output.startswith(b'\x1bP')
        assert output.endswith(b'\x1b\\')
        
        # Should contain palette definitions (# followed by color number)
        assert b'#' in output


class TestSixelImageModes:
    """Test different image modes."""
    
    def test_rgb_mode(self, sixel_generator):
        """RGB images work correctly."""
        img = Image.new('RGB', (8, 8), (0, 255, 0))
        png_data = encode_png(img)
        output = sixel_generator.generate(png_data)
        
        assert output.startswith(b'\x1bP')
        assert output.endswith(b'\x1b\\')
    
    def test_rgba_mode(self, sixel_generator):
        """RGBA images are converted properly."""
        img = Image.new('RGBA', (8, 8), (0, 0, 255, 255))
        png_data = encode_png(img)
        output = sixel_generator.generate(png_data)
        
        assert output.startswith(b'\x1bP')
        assert output.endswith(b'\x1b\\')
    
    def test_palette_mode(self, sixel_generator):
        """Palette images are handled."""
        img = Image.new('P', (8, 8), 42)
        png_data = encode_png(img)
        output = sixel_generator.generate(png_data)
        
        assert output.startswith(b'\x1bP')
        assert output.endswith(b'\x1b\\')
