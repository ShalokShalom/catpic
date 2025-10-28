"""
Test translucency melding functionality.

Tests alpha compositing, layer blending, and helper functions.
"""

import pytest
from PIL import Image

from catpic.encoder_melding import (
    meld_layers,
    has_translucent_layers,
    should_meld,
)
from catpic.encoder_layers import LayerSpec
from catpic.core import BASIS


class TestMeldLayers:
    """Test the core meld_layers() function."""
    
    def test_meld_single_opaque_layer(self):
        """Single opaque layer should pass through unchanged."""
        red = Image.new('RGB', (40, 20), (255, 0, 0))
        
        layers = [
            LayerSpec(red, 'layer1', (0, 0, 20, 10), alpha=1.0)
        ]
        
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        # Should be red
        assert result.mode == 'RGB'
        pixel = result.getpixel((0, 0))
        assert pixel == (255, 0, 0)
    
    def test_meld_two_opaque_overlapping_layers(self):
        """Upper opaque layer should completely cover lower layer."""
        red = Image.new('RGB', (40, 20), (255, 0, 0))
        blue = Image.new('RGB', (40, 20), (0, 0, 255))
        
        layers = [
            LayerSpec(red, 'bg', (0, 0, 20, 10), alpha=1.0),
            LayerSpec(blue, 'fg', (0, 0, 20, 10), alpha=1.0),
        ]
        
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        # Top-left should be blue (upper layer wins)
        pixel = result.getpixel((0, 0))
        assert pixel == (0, 0, 255)
    
    def test_meld_translucent_layer_50_percent(self):
        """50% alpha should blend colors evenly."""
        red = Image.new('RGB', (40, 20), (255, 0, 0))
        blue = Image.new('RGB', (40, 20), (0, 0, 255))
        
        layers = [
            LayerSpec(red, 'bg', (0, 0, 20, 10), alpha=1.0),
            LayerSpec(blue, 'fg', (0, 0, 20, 10), alpha=0.5),
        ]
        
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        # Should be approximately 50/50 blend: (127, 0, 127)
        pixel = result.getpixel((0, 0))
        
        # Allow some tolerance for rounding
        assert 120 < pixel[0] < 135, f"Red channel should be ~127, got {pixel[0]}"
        assert pixel[1] < 10, f"Green channel should be ~0, got {pixel[1]}"
        assert 120 < pixel[2] < 135, f"Blue channel should be ~127, got {pixel[2]}"
    
    def test_meld_translucent_layer_25_percent(self):
        """25% alpha should favor background."""
        red = Image.new('RGB', (40, 20), (200, 0, 0))
        blue = Image.new('RGB', (40, 20), (0, 0, 200))
        
        layers = [
            LayerSpec(red, 'bg', (0, 0, 20, 10), alpha=1.0),
            LayerSpec(blue, 'fg', (0, 0, 20, 10), alpha=0.25),
        ]
        
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        pixel = result.getpixel((0, 0))
        
        # 25% blue (50) + 75% red (150) = blend favors red
        assert pixel[0] > pixel[2], "Red should dominate over blue"
        assert pixel[0] > 140, f"Red channel should be >140, got {pixel[0]}"
        assert pixel[2] < 60, f"Blue channel should be <60, got {pixel[2]}"
    
    def test_meld_partial_overlap(self):
        """Layers with partial overlap should blend only in overlap region."""
        red = Image.new('RGB', (40, 20), (255, 0, 0))
        blue = Image.new('RGB', (40, 20), (0, 0, 255))
        
        # Red fills entire canvas, blue only in top-left quadrant
        layers = [
            LayerSpec(red, 'bg', (0, 0, 20, 10), alpha=1.0),
            LayerSpec(blue, 'fg', (0, 0, 10, 5), alpha=0.5),
        ]
        
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        # Top-left should be blended (where blue overlaps)
        overlap_pixel = result.getpixel((5, 5))
        assert 100 < overlap_pixel[0] < 150, "Overlap area should be blended"
        assert 100 < overlap_pixel[2] < 150, "Overlap area should be blended"
        
        # Bottom-right should be pure red (no overlap)
        no_overlap_pixel = result.getpixel((result.width - 5, result.height - 5))
        assert no_overlap_pixel[0] > 240, "Non-overlap should be pure red"
        assert no_overlap_pixel[2] < 20, "Non-overlap should have minimal blue"
    
    def test_meld_non_overlapping_layers(self):
        """Non-overlapping layers should not affect each other."""
        red = Image.new('RGB', (20, 10), (255, 0, 0))
        blue = Image.new('RGB', (20, 10), (0, 0, 255))
        
        # Red on left half, blue on right half
        layers = [
            LayerSpec(red, 'left', (0, 0, 10, 10), alpha=1.0),
            LayerSpec(blue, 'right', (10, 0, 10, 10), alpha=1.0),
        ]
        
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        # Left side should be red
        left_pixel = result.getpixel((5, 5))
        assert left_pixel[0] > 240
        assert left_pixel[2] < 20
        
        # Right side should be blue
        right_pixel = result.getpixel((result.width - 5, 5))
        assert right_pixel[0] < 20
        assert right_pixel[2] > 240
    
    def test_meld_three_layers(self):
        """Multiple translucent layers should composite correctly."""
        red = Image.new('RGB', (40, 20), (255, 0, 0))
        green = Image.new('RGB', (40, 20), (0, 255, 0))
        blue = Image.new('RGB', (40, 20), (0, 0, 255))
        
        layers = [
            LayerSpec(red, 'bg', (0, 0, 20, 10), alpha=1.0),
            LayerSpec(green, 'mid', (0, 0, 20, 10), alpha=0.5),
            LayerSpec(blue, 'fg', (0, 0, 20, 10), alpha=0.5),
        ]
        
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        pixel = result.getpixel((0, 0))
        
        # All three colors should contribute
        assert pixel[0] > 0, "Should have red component"
        assert pixel[1] > 0, "Should have green component"
        assert pixel[2] > 0, "Should have blue component"
    
    def test_meld_zero_alpha(self):
        """Layer with alpha=0 should be invisible."""
        red = Image.new('RGB', (40, 20), (255, 0, 0))
        blue = Image.new('RGB', (40, 20), (0, 0, 255))
        
        layers = [
            LayerSpec(red, 'bg', (0, 0, 20, 10), alpha=1.0),
            LayerSpec(blue, 'fg', (0, 0, 20, 10), alpha=0.0),
        ]
        
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        # Should be pure red (blue is invisible)
        pixel = result.getpixel((0, 0))
        assert pixel == (255, 0, 0)
    
    def test_meld_different_basis_levels(self):
        """Melding should work with different BASIS levels."""
        red = Image.new('RGB', (40, 20), (255, 0, 0))
        blue = Image.new('RGB', (40, 20), (0, 0, 255))
        
        for basis in [BASIS.BASIS_1_2, BASIS.BASIS_2_2, BASIS.BASIS_2_3, BASIS.BASIS_2_4]:
            layers = [
                LayerSpec(red, 'bg', (0, 0, 20, 10), alpha=1.0),
                LayerSpec(blue, 'fg', (0, 0, 20, 10), alpha=0.5),
            ]
            
            result = meld_layers(layers, (20, 10), basis)
            
            # Should produce blended result regardless of basis
            pixel = result.getpixel((0, 0))
            assert 100 < pixel[0] < 150, f"Basis {basis} should blend correctly"
            assert 100 < pixel[2] < 150, f"Basis {basis} should blend correctly"


class TestHelperFunctions:
    """Test helper functions for melding logic."""
    
    def test_has_translucent_layers_none(self):
        """All opaque layers should return False."""
        red = Image.new('RGB', (10, 10), (255, 0, 0))
        blue = Image.new('RGB', (10, 10), (0, 0, 255))
        
        layers = [
            LayerSpec(red, 'l1', (0, 0, 10, 10), alpha=1.0),
            LayerSpec(blue, 'l2', (0, 0, 10, 10), alpha=1.0),
        ]
        
        assert not has_translucent_layers(layers)
    
    def test_has_translucent_layers_one(self):
        """One translucent layer should return True."""
        red = Image.new('RGB', (10, 10), (255, 0, 0))
        blue = Image.new('RGB', (10, 10), (0, 0, 255))
        
        layers = [
            LayerSpec(red, 'l1', (0, 0, 10, 10), alpha=1.0),
            LayerSpec(blue, 'l2', (0, 0, 10, 10), alpha=0.5),
        ]
        
        assert has_translucent_layers(layers)
    
    def test_has_translucent_layers_zero_alpha(self):
        """Zero alpha counts as translucent."""
        red = Image.new('RGB', (10, 10), (255, 0, 0))
        
        layers = [
            LayerSpec(red, 'l1', (0, 0, 10, 10), alpha=0.0),
        ]
        
        assert has_translucent_layers(layers)
    
    def test_should_meld_explicit_true(self):
        """Explicit meld=True should always return True."""
        red = Image.new('RGB', (10, 10), (255, 0, 0))
        
        layers = [
            LayerSpec(red, 'l1', (0, 0, 10, 10), alpha=1.0),
        ]
        
        assert should_meld(layers, meld_hint=True)
    
    def test_should_meld_translucent_layers(self):
        """Translucent layers should trigger melding."""
        red = Image.new('RGB', (10, 10), (255, 0, 0))
        blue = Image.new('RGB', (10, 10), (0, 0, 255))
        
        layers = [
            LayerSpec(red, 'l1', (0, 0, 10, 10), alpha=1.0),
            LayerSpec(blue, 'l2', (0, 0, 10, 10), alpha=0.5),
        ]
        
        assert should_meld(layers, meld_hint=False)
    
    def test_should_meld_opaque_no_hint(self):
        """All opaque layers with no hint should not meld."""
        red = Image.new('RGB', (10, 10), (255, 0, 0))
        
        layers = [
            LayerSpec(red, 'l1', (0, 0, 10, 10), alpha=1.0),
        ]
        
        assert not should_meld(layers, meld_hint=False)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_meld_empty_canvas(self):
        """Canvas with no layers should produce black image."""
        layers = []
        
        # Should not crash, though this is an unusual case
        # In practice, LayerComposer validates this
        result = meld_layers(layers, (20, 10), BASIS.BASIS_2_2)
        
        # Should be black (no layers)
        pixel = result.getpixel((0, 0))
        assert pixel == (0, 0, 0)
    
    def test_meld_very_small_canvas(self):
        """Very small canvas should work."""
        red = Image.new('RGB', (2, 2), (255, 0, 0))
        
        layers = [
            LayerSpec(red, 'l1', (0, 0, 1, 1), alpha=1.0),
        ]
        
        result = meld_layers(layers, (1, 1), BASIS.BASIS_2_2)
        
        assert result.size[0] > 0
        assert result.size[1] > 0
    
    def test_meld_large_canvas(self):
        """Large canvas should work (performance check)."""
        red = Image.new('RGB', (320, 240), (255, 0, 0))
        blue = Image.new('RGB', (320, 240), (0, 0, 255))
        
        layers = [
            LayerSpec(red, 'bg', (0, 0, 160, 120), alpha=1.0),
            LayerSpec(blue, 'fg', (0, 0, 160, 120), alpha=0.5),
        ]
        
        # Should complete without timeout (PIL is fast)
        result = meld_layers(layers, (160, 120), BASIS.BASIS_2_2)
        
        assert result.size == (320, 240)
