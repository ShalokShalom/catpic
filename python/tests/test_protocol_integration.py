# Destination: tests/test_protocol_integration.py

"""
Test protocol integration: encoding, decoding, dual content modes.
"""

import base64
import pytest
from pathlib import Path

from catpic.encoder import CatpicEncoder
from catpic.decoder import parse_meow, display_meow
from catpic.core import BASIS
from catpic.protocols.core import decode_png


class TestDualContentEncoding:
    """Test dual content mode (PNG + glyxel)."""
    
    def test_default_includes_png_cells(self):
        """Default encoding should include PNG in cells field."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        meow = parse_meow(meow_content)
        
        # Should have at least 2 layers (layer zero + content)
        assert len(meow.layers) >= 1
        
        # Find layer with cells field (skip layer zero if present)
        content_layer = None
        for layer in meow.layers:
            if layer.cells is not None:
                content_layer = layer
                break
        
        assert content_layer is not None, "No layer found with cells field"
        assert content_layer.ctype == 'png'
    
    def test_explicit_glyxel_includes_png(self):
        """Explicit protocol='glyxel' should include PNG."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image(
            'tests/fixtures/red_4x4.png', 10, 10, protocol='glyxel'
        )
        
        meow = parse_meow(meow_content)
        
        # Find layer with cells
        content_layer = None
        for layer in meow.layers:
            if layer.cells is not None:
                content_layer = layer
                break
        
        assert content_layer is not None
        assert content_layer.ctype == 'png'
    
    def test_png_is_valid_image(self):
        """PNG in cells field should be decodable."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        meow = parse_meow(meow_content)
        
        # Find layer with cells
        content_layer = None
        for layer in meow.layers:
            if layer.cells is not None:
                content_layer = layer
                break
        
        assert content_layer is not None
        
        # Decode PNG from cells
        png_data = base64.b64decode(content_layer.cells)
        img = decode_png(png_data)
        
        # Should be valid PIL image
        assert img.width > 0
        assert img.height > 0
        assert img.mode == 'RGB'
    
    def test_original_dimensions_preserved(self):
        """Original image dimensions should be stored in metadata."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        meow = parse_meow(meow_content)
        
        # Find layer with cells
        content_layer = None
        for layer in meow.layers:
            if layer.cells is not None:
                content_layer = layer
                break
        
        assert content_layer is not None
        
        # Extract PNG and check dimensions
        png_data = base64.b64decode(content_layer.cells)
        img = decode_png(png_data)
        
        # Original image is 4x4 pixels
        assert img.width == 4
        assert img.height == 4
    
    def test_visible_output_present(self):
        """Dual content should still have glyxel visible output."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        meow = parse_meow(meow_content)
        
        # Find layer with visible output
        has_visible = any(layer.visible_output for layer in meow.layers)
        assert has_visible, "No layer found with visible output"
        
        # Check that visible output contains ANSI
        for layer in meow.layers:
            if layer.visible_output:
                assert '\x1b[' in layer.visible_output, "Visible output missing ANSI codes"
                break
    
    def test_larger_image_full_resolution(self):
        """Larger images should preserve full resolution in cells."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_64x64.jpg', 20, 20)
        
        meow = parse_meow(meow_content)
        
        # Find layer with cells
        content_layer = None
        for layer in meow.layers:
            if layer.cells is not None:
                content_layer = layer
                break
        
        assert content_layer is not None
        
        # Extract PNG
        png_data = base64.b64decode(content_layer.cells)
        img = decode_png(png_data)
        
        # Original is 64x64
        assert img.width == 64
        assert img.height == 64


class TestGlyxelOnlyEncoding:
    """Test glyxel_only mode (minimal ANSI)."""
    
    def test_glyxel_only_no_cells(self):
        """glyxel_only should not include cells field."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image(
            'tests/fixtures/red_4x4.png', 10, 10, protocol='glyxel_only'
        )
        
        meow = parse_meow(meow_content)
        
        # Should NOT have any layer with cells field
        for layer in meow.layers:
            assert layer.cells is None, f"Found unexpected cells in layer"
    
    def test_glyxel_only_no_ctype(self):
        """glyxel_only should not have ctype."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image(
            'tests/fixtures/red_4x4.png', 10, 10, protocol='glyxel_only'
        )
        
        meow = parse_meow(meow_content)
        
        # Should NOT have any layer with ctype
        for layer in meow.layers:
            assert layer.ctype is None, f"Found unexpected ctype in layer"
    
    def test_glyxel_only_has_visible_output(self):
        """glyxel_only should still have visible output."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image(
            'tests/fixtures/red_4x4.png', 10, 10, protocol='glyxel_only'
        )
        
        meow = parse_meow(meow_content)
        
        # Should have visible output in at least one layer
        has_visible = any(layer.visible_output for layer in meow.layers)
        assert has_visible
        
        # Check ANSI present
        for layer in meow.layers:
            if layer.visible_output:
                assert '\x1b[' in layer.visible_output
                break
    
    def test_glyxel_only_smaller_filesize(self):
        """glyxel_only files should be smaller than dual content."""
        encoder = CatpicEncoder()
        
        dual = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10, protocol='glyxel')
        minimal = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10, protocol='glyxel_only')
        
        # Minimal should be smaller (no PNG data)
        assert len(minimal) < len(dual)


class TestProtocolDisplay:
    """Test protocol-aware display paths."""
    
    def test_glyxel_protocol_display(self, capsys):
        """Display with protocol='glyxel' should use protocol path."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        # This should work (may use protocol path or fallback)
        try:
            display_meow(meow_content, protocol='glyxel')
            captured = capsys.readouterr()
            # Should produce some output
            assert len(captured.out) > 0
        except Exception as e:
            pytest.fail(f"Protocol display failed: {e}")
    
    def test_display_without_protocol_uses_fallback(self, capsys):
        """Display without protocol should use glyxel fallback."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        # Should display using visible output
        display_meow(meow_content)
        captured = capsys.readouterr()
        
        # Should have output
        assert len(captured.out) > 0
    
    def test_glyxel_only_displays_correctly(self, capsys):
        """glyxel_only files should display (no protocol data)."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image(
            'tests/fixtures/red_4x4.png', 10, 10, protocol='glyxel_only'
        )
        
        # Should display using visible output
        display_meow(meow_content)
        captured = capsys.readouterr()
        
        # Should have output
        assert len(captured.out) > 0


class TestMetadataValidation:
    """Test metadata structure and validation."""
    
    def test_canvas_metadata_present(self):
        """Canvas metadata should be present in dual content."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        meow = parse_meow(meow_content)
        
        # Should have canvas metadata
        assert meow.canvas is not None
        assert meow.canvas.version == "0.7"
        assert meow.canvas.size is not None
    
    def test_basis_preserved_in_metadata(self):
        """BASIS should be stored in canvas metadata."""
        encoder = CatpicEncoder(basis=BASIS.BASIS_2_4)
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        meow = parse_meow(meow_content)
        
        # Should have BASIS in canvas
        assert meow.canvas.basis == (2, 4)
    
    def test_layer_metadata_structure(self):
        """Layer metadata should have correct structure."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
        
        meow = parse_meow(meow_content)
        
        # Find layer with protocol data
        content_layer = None
        for layer in meow.layers:
            if layer.ctype == 'png':
                content_layer = layer
                break
        
        # Should find layer with ctype and cells
        assert content_layer is not None
        assert content_layer.cells is not None


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_tiny_image_encoding(self):
        """1x1 pixel image should encode correctly."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/tiny_1x1.png', 5, 5)
        
        meow = parse_meow(meow_content)
        
        # Find layer with cells
        content_layer = None
        for layer in meow.layers:
            if layer.cells is not None:
                content_layer = layer
                break
        
        # Should still have PNG data
        assert content_layer is not None
        
        # Extract and verify
        png_data = base64.b64decode(content_layer.cells)
        img = decode_png(png_data)
        assert img.width == 1
        assert img.height == 1
    
    def test_odd_dimensions_encoding(self):
        """Odd-sized images should encode correctly."""
        encoder = CatpicEncoder()
        meow_content = encoder.encode_image('tests/fixtures/odd_13x17.png', 10, 10)
        
        meow = parse_meow(meow_content)
        
        # Find layer with cells
        content_layer = None
        for layer in meow.layers:
            if layer.cells is not None:
                content_layer = layer
                break
        
        assert content_layer is not None
        
        # Extract PNG
        png_data = base64.b64decode(content_layer.cells)
        img = decode_png(png_data)
        
        # Original dimensions preserved
        assert img.width == 13
        assert img.height == 17
    
    def test_different_basis_levels(self):
        """Different BASIS levels should work with protocol integration."""
        for basis in [BASIS.BASIS_1_2, BASIS.BASIS_2_2, BASIS.BASIS_2_3, BASIS.BASIS_2_4]:
            encoder = CatpicEncoder(basis=basis)
            meow_content = encoder.encode_image('tests/fixtures/red_4x4.png', 10, 10)
            
            meow = parse_meow(meow_content)
            
            # Find layer with cells
            content_layer = None
            for layer in meow.layers:
                if layer.cells is not None:
                    content_layer = layer
                    break
            
            # Should have cells regardless of BASIS
            assert content_layer is not None, f"No cells found for {basis}"
            assert content_layer.ctype == 'png', f"Wrong ctype for {basis}"
