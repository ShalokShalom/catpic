"""
Test encoder output structure and consistency.

Validates that encoded MEOW files have correct layer zero structure,
footers, and consistent output across versions.
"""

import pytest
from pathlib import Path

from catpic.encoder import CatpicEncoder
from catpic.core import BASIS, MEOW_OSC_NUMBER


class TestLayerZeroStructure:
    """Test that encoder produces correct layer zero structure."""
    
    def test_encode_image_has_layer_zero_components(self):
        """Verify layer zero contains all required components."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        # Layer zero components (in order)
        assert f'\x1b]{MEOW_OSC_NUMBER};' in result  # Canvas metadata OSC
        assert '\n' * 10 in result  # Height newlines (10 for height=10)
        assert '\x1b[10A' in result  # Move up 10 rows
        assert '\x1b[s' in result  # Save cursor
        
        # Footer
        assert '\x1b[u\x1b[10B\n' in result  # Restore, move down, newline
    
    def test_encode_image_layer_zero_order(self):
        """Verify layer zero components appear in correct order."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        # Find positions of key components
        osc_pos = result.find(f'\x1b]{MEOW_OSC_NUMBER};')
        newlines_pos = result.find('\n' * 10)
        move_up_pos = result.find('\x1b[10A')
        save_pos = result.find('\x1b[s')
        footer_pos = result.find('\x1b[u\x1b[10B\n')
        
        # Verify order
        assert osc_pos < newlines_pos, "Canvas OSC should come before newlines"
        assert newlines_pos < move_up_pos, "Newlines should come before move up"
        assert move_up_pos < save_pos, "Move up should come before save"
        assert save_pos < footer_pos, "Save should come before footer"
    
    def test_encode_image_correct_newline_count(self):
        """Verify newline count matches canvas height."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        
        for height in [5, 10, 20, 24]:
            result = encoder.encode_image(
                'tests/fixtures/red_4x4.png',
                width=20,
                height=height
            )
            
            # Extract layer zero (before first visual content)
            layer_zero_end = result.find('\x1b[s') + len('\x1b[s')
            layer_zero = result[:layer_zero_end]
            
            # Count newlines in layer zero
            newline_count = layer_zero.count('\n')
            assert newline_count == height, f"Expected {height} newlines, got {newline_count}"
    
    def test_encode_image_footer_matches_height(self):
        """Verify footer move-down matches canvas height."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        
        for height in [5, 10, 20]:
            result = encoder.encode_image(
                'tests/fixtures/red_4x4.png',
                width=20,
                height=height
            )
            
            expected_footer = f'\x1b[u\x1b[{height}B\n'
            assert expected_footer in result, f"Footer should move down {height} rows"


class TestAnimationStructure:
    """Test animation encoding structure (currently no layer zero)."""
    
    def test_encode_animation_has_canvas_metadata(self):
        """Verify animation has canvas block with loop."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_animation('tests/fixtures/bounce_small.gif', width=20, height=10)
        
        # Should have canvas metadata with loop
        assert f'\x1b]{MEOW_OSC_NUMBER};' in result
        assert '"loop":0' in result  # Infinite loop
    
    def test_encode_animation_frame_count(self):
        """Verify all frames are encoded."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_animation('tests/fixtures/bounce_small.gif')
        
        # Count frame metadata blocks
        frame_count = result.count('"f":')
        
        # Verify it matches GIF frame count
        from PIL import Image
        with Image.open('tests/fixtures/bounce_small.gif') as img:
            expected_frames = img.n_frames
        
        assert frame_count == expected_frames


class TestOutputConsistency:
    """Test output consistency and determinism."""
    
    def test_encode_image_deterministic_small(self):
        """Verify encoding is deterministic for small images."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        
        result1 = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        result2 = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        assert result1 == result2, "Encoding should be deterministic"
    
    def test_encode_image_deterministic_large(self):
        """Verify encoding is deterministic for larger images."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        
        result1 = encoder.encode_image('tests/fixtures/red_64x64.jpg', width=40, height=20)
        result2 = encoder.encode_image('tests/fixtures/red_64x64.jpg', width=40, height=20)
        
        assert result1 == result2, "Encoding should be deterministic"
    
    def test_encode_image_different_sizes_differ(self):
        """Verify different dimensions produce different output."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        
        result_20x10 = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        result_40x20 = encoder.encode_image('tests/fixtures/red_4x4.png', width=40, height=20)
        
        assert result_20x10 != result_40x20, "Different dimensions should produce different output"
    
    def test_encode_animation_deterministic(self):
        """Verify animation encoding is deterministic."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        
        result1 = encoder.encode_animation('tests/fixtures/bounce_small.gif', width=20, height=10)
        result2 = encoder.encode_animation('tests/fixtures/bounce_small.gif', width=20, height=10)
        
        assert result1 == result2, "Animation encoding should be deterministic"


class TestOutputIntegrity:
    """Test that output maintains ANSI/MEOW format integrity."""
    
    def test_encode_image_single_layer_zero(self):
        """Verify only one layer zero per file."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        # Count cursor saves (should be exactly 1)
        save_count = result.count('\x1b[s')
        assert save_count == 1, f"Should have exactly 1 cursor save, found {save_count}"
    
    def test_encode_image_single_footer(self):
        """Verify only one footer per file."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        # Count cursor restores in footer position (at end)
        # Footer format: \x1b[u\x1b[{height}B\n
        restore_count = result.count('\x1b[u')
        assert restore_count == 1, f"Should have exactly 1 cursor restore, found {restore_count}"
    
    def test_encode_image_no_embedded_nulls(self):
        """Verify output contains no null bytes."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        assert '\x00' not in result, "MEOW output should not contain null bytes"
    
    def test_encode_image_utf8_encodable(self):
        """Verify output can be encoded as UTF-8."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        # Should not raise
        result.encode('utf-8')
    
    def test_encode_image_ends_with_newline(self):
        """Verify output ends with newline (footer)."""
        encoder = CatpicEncoder(BASIS.BASIS_2_2)
        result = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        assert result.endswith('\n'), "Output should end with newline from footer"


class TestDifferentBasisLevels:
    """Test layer zero structure across different BASIS levels."""
    
    @pytest.mark.parametrize("basis", [
        BASIS.BASIS_1_2,
        BASIS.BASIS_2_2,
        BASIS.BASIS_2_3,
        BASIS.BASIS_2_4,
    ])
    def test_layer_zero_all_basis_levels(self, basis):
        """Verify layer zero works with all BASIS levels."""
        encoder = CatpicEncoder(basis)
        result = encoder.encode_image('tests/fixtures/red_4x4.png', width=20, height=10)
        
        # Should have layer zero components regardless of basis
        assert '\x1b[s' in result
        assert '\x1b[u\x1b[10B\n' in result
