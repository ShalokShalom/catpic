"""
Test suite for MEOW v0.7 layer encoding infrastructure.

Tests LayerSpec, LayerEncoder, and LayerComposer functionality.
"""

import pytest
from pathlib import Path
from PIL import Image

from catpic.core import BASIS
from catpic.encoder_layers import LayerSpec, LayerEncoder, LayerComposer


# Fixtures

@pytest.fixture
def red_image():
    """Create a 10x10 red RGB image."""
    img = Image.new('RGB', (10, 10), color='red')
    return img


@pytest.fixture
def blue_image():
    """Create a 10x10 blue RGB image."""
    img = Image.new('RGB', (10, 10), color='blue')
    return img


@pytest.fixture
def green_image():
    """Create a 10x10 green RGB image."""
    img = Image.new('RGB', (10, 10), color='green')
    return img


@pytest.fixture
def layer_encoder():
    """Create a LayerEncoder with BASIS 2x2."""
    return LayerEncoder(BASIS.BASIS_2_2)


# LayerSpec Tests

class TestLayerSpec:
    """Test LayerSpec validation and metadata generation."""
    
    def test_basic_layer_spec(self, red_image):
        """Test basic LayerSpec creation."""
        spec = LayerSpec(
            image=red_image,
            id="test_layer",
            box=(0, 0, 10, 10),
            alpha=1.0,
        )
        
        assert spec.id == "test_layer"
        assert spec.box == (0, 0, 10, 10)
        assert spec.alpha == 1.0
        assert spec.frame is None
        assert spec.delay is None
    
    def test_alpha_clamping_low(self, red_image):
        """Test alpha clamping to 0.0 minimum."""
        spec = LayerSpec(
            image=red_image,
            id="test",
            box=(0, 0, 10, 10),
            alpha=-0.5,
        )
        
        assert spec.alpha == 0.0
    
    def test_alpha_clamping_high(self, red_image):
        """Test alpha clamping to 1.0 maximum."""
        spec = LayerSpec(
            image=red_image,
            id="test",
            box=(0, 0, 10, 10),
            alpha=1.5,
        )
        
        assert spec.alpha == 1.0
    
    def test_invalid_box_zero_width(self, red_image):
        """Test that zero width box raises ValueError."""
        with pytest.raises(ValueError, match="positive dimensions"):
            LayerSpec(
                image=red_image,
                id="test",
                box=(0, 0, 0, 10),
            )
    
    def test_invalid_box_zero_height(self, red_image):
        """Test that zero height box raises ValueError."""
        with pytest.raises(ValueError, match="positive dimensions"):
            LayerSpec(
                image=red_image,
                id="test",
                box=(0, 0, 10, 0),
            )
    
    def test_invalid_box_negative_x(self, red_image):
        """Test that negative x raises ValueError."""
        with pytest.raises(ValueError, match="non-negative position"):
            LayerSpec(
                image=red_image,
                id="test",
                box=(-1, 0, 10, 10),
            )
    
    def test_invalid_box_negative_y(self, red_image):
        """Test that negative y raises ValueError."""
        with pytest.raises(ValueError, match="non-negative position"):
            LayerSpec(
                image=red_image,
                id="test",
                box=(0, -1, 10, 10),
            )
    
    def test_metadata_generation_basic(self, red_image):
        """Test basic metadata generation."""
        spec = LayerSpec(
            image=red_image,
            id="layer1",
            box=(5, 10, 20, 15),
            alpha=0.8,
        )
        
        metadata = spec.get_metadata()
        
        assert metadata["id"] == "layer1"
        assert metadata["box"] == {"x": 5, "y": 10, "dx": 20, "dy": 15}
        assert metadata["α"] == 0.8
        assert "f" not in metadata
        assert "delay" not in metadata
    
    def test_metadata_generation_with_frame(self, red_image):
        """Test metadata generation with frame number."""
        spec = LayerSpec(
            image=red_image,
            id="frame_0",
            box=(0, 0, 80, 24),
            frame=0,
            delay=100,
        )
        
        metadata = spec.get_metadata()
        
        assert metadata["f"] == 0
        assert metadata["delay"] == 100
    
    def test_metadata_generation_frame_without_delay(self, red_image):
        """Test metadata with frame but no delay."""
        spec = LayerSpec(
            image=red_image,
            id="frame_5",
            box=(0, 0, 80, 24),
            frame=5,
        )
        
        metadata = spec.get_metadata()
        
        assert metadata["f"] == 5
        assert "delay" not in metadata


# LayerEncoder Tests

class TestLayerEncoder:
    """Test LayerEncoder functionality."""
    
    def test_encode_layer_basic(self, layer_encoder, red_image):
        """Test basic layer encoding."""
        spec = LayerSpec(
            image=red_image,
            id="red_layer",
            box=(0, 0, 10, 10),
        )
        
        output = layer_encoder.encode_layer(spec)
        
        # Check for OSC 9876 metadata (don't show full output on failure)
        assert '\x1b]9876;' in output, "Missing OSC 9876 sequence"
        assert '"id":"red_layer"' in output, "Missing layer id"
        assert '"box":{"x":0,"y":0,"dx":10,"dy":10}' in output, "Missing box metadata"
        assert '"α":1.0' in output, "Missing alpha value"
        assert '"ctype":"ansi-art"' in output, "Missing ctype"
        
        # Check for ANSI escape codes (color)
        assert '\x1b[' in output, "Missing ANSI color codes"
    
    def test_encode_layer_with_position(self, layer_encoder, blue_image):
        """Test layer encoding with non-origin position."""
        spec = LayerSpec(
            image=blue_image,
            id="positioned",
            box=(10, 5, 20, 15),
        )
        
        output = layer_encoder.encode_layer(spec)
        
        # Should contain cursor positioning
        assert '\x1b[' in output
        # Check metadata has correct position
        assert '"x":10' in output
        assert '"y":5' in output
    
    def test_encode_layer_with_canvas(self, layer_encoder, green_image):
        """Test layer encoding with canvas metadata."""
        spec = LayerSpec(
            image=green_image,
            id="with_canvas",
            box=(0, 0, 40, 20),
        )
        
        output = layer_encoder.encode_layer_with_canvas(
            spec,
            canvas_size=(40, 20),
        )
        
        # Check for canvas block
        assert '"meow":"0.7"' in output
        assert '"size":[40,20]' in output
        assert '"basis":[2,2]' in output
        
        # Check for layer block
        assert '"id":"with_canvas"' in output
    
    def test_encode_layer_with_canvas_and_loop(self, layer_encoder, red_image):
        """Test canvas encoding with loop parameter."""
        spec = LayerSpec(
            image=red_image,
            id="animated",
            box=(0, 0, 30, 30),
            frame=0,
            delay=100,
        )
        
        output = layer_encoder.encode_layer_with_canvas(
            spec,
            canvas_size=(30, 30),
            loop=0,
        )
        
        assert '"loop":0' in output
    
    def test_encode_layer_with_meld(self, layer_encoder, blue_image):
        """Test canvas encoding with meld flag."""
        spec = LayerSpec(
            image=blue_image,
            id="melded",
            box=(0, 0, 25, 25),
            alpha=0.5,
        )
        
        output = layer_encoder.encode_layer_with_canvas(
            spec,
            canvas_size=(25, 25),
            meld=True,
        )
        
        assert '"meld":true' in output
    
    def test_encode_translucent_layer(self, layer_encoder, red_image):
        """Test encoding layer with translucency."""
        spec = LayerSpec(
            image=red_image,
            id="translucent",
            box=(0, 0, 15, 15),
            alpha=0.7,
        )
        
        output = layer_encoder.encode_layer(spec)
        
        assert '"α":0.7' in output, "Missing alpha value"


# LayerComposer Tests

class TestLayerComposer:
    """Test LayerComposer functionality."""
    
    def test_composer_initialization(self):
        """Test LayerComposer initialization."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(80, 24))
        
        assert composer.basis == BASIS.BASIS_2_2
        assert composer.canvas_size == (80, 24)
        assert len(composer.layers) == 0
    
    def test_add_single_layer(self, red_image):
        """Test adding a single layer."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(50, 30))
        
        spec = LayerSpec(
            image=red_image,
            id="layer1",
            box=(0, 0, 50, 30),
        )
        
        composer.add_layer(spec)
        
        assert len(composer.layers) == 1
        assert composer.layers[0].id == "layer1"
    
    def test_add_multiple_layers(self, red_image, blue_image, green_image):
        """Test adding multiple layers."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(60, 40))
        
        specs = [
            LayerSpec(image=red_image, id="red", box=(0, 0, 60, 40)),
            LayerSpec(image=blue_image, id="blue", box=(10, 10, 40, 20)),
            LayerSpec(image=green_image, id="green", box=(5, 5, 30, 15)),
        ]
        
        for spec in specs:
            composer.add_layer(spec)
        
        assert len(composer.layers) == 3
        assert composer.layers[0].id == "red"
        assert composer.layers[1].id == "blue"
        assert composer.layers[2].id == "green"
    
    def test_layer_exceeds_canvas_width(self, red_image):
        """Test that layer exceeding canvas width raises ValueError."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(80, 24))
        
        spec = LayerSpec(
            image=red_image,
            id="too_wide",
            box=(70, 0, 20, 10),  # 70 + 20 = 90 > 80
        )
        
        with pytest.raises(ValueError, match="extends beyond canvas width"):
            composer.add_layer(spec)
    
    def test_layer_exceeds_canvas_height(self, blue_image):
        """Test that layer exceeding canvas height raises ValueError."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(80, 24))
        
        spec = LayerSpec(
            image=blue_image,
            id="too_tall",
            box=(0, 20, 10, 10),  # 20 + 10 = 30 > 24
        )
        
        with pytest.raises(ValueError, match="extends beyond canvas height"):
            composer.add_layer(spec)
    
    def test_render_single_layer(self, red_image):
        """Test rendering composition with single layer."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(40, 20))
        
        spec = LayerSpec(
            image=red_image,
            id="single",
            box=(0, 0, 40, 20),
        )
        composer.add_layer(spec)
        
        output = composer.render()
        
        # Check canvas block
        assert '"meow":"0.7"' in output
        assert '"size":[40,20]' in output
        
        # Check layer block
        assert '"id":"single"' in output
    
    def test_render_multiple_layers(self, red_image, blue_image):
        """Test rendering composition with multiple layers."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(60, 30))
        
        composer.add_layer(LayerSpec(
            image=red_image,
            id="bottom",
            box=(0, 0, 60, 30),
        ))
        composer.add_layer(LayerSpec(
            image=blue_image,
            id="top",
            box=(10, 10, 40, 15),
            alpha=0.8,
        ))
        
        output = composer.render()
        
        # Check both layers present
        assert '"id":"bottom"' in output
        assert '"id":"top"' in output
        
        # Check stream order (bottom should appear first)
        bottom_pos = output.find('"id":"bottom"')
        top_pos = output.find('"id":"top"')
        assert bottom_pos < top_pos
    
    def test_render_with_loop(self, green_image):
        """Test rendering with loop parameter."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(50, 25))
        
        composer.add_layer(LayerSpec(
            image=green_image,
            id="animated",
            box=(0, 0, 50, 25),
            frame=0,
        ))
        
        output = composer.render(loop=0)
        
        assert '"loop":0' in output
    
    def test_render_with_meld(self, red_image, blue_image):
        """Test rendering with meld flag."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(45, 22))
        
        composer.add_layer(LayerSpec(
            image=red_image,
            id="base",
            box=(0, 0, 45, 22),
        ))
        composer.add_layer(LayerSpec(
            image=blue_image,
            id="overlay",
            box=(10, 5, 25, 12),
            alpha=0.6,
        ))
        
        output = composer.render(meld=True)
        
        assert '"meld":true' in output
    
    def test_render_empty_composition(self):
        """Test that rendering empty composition raises ValueError."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(80, 24))
        
        with pytest.raises(ValueError, match="No layers added"):
            composer.render()
    
    def test_clear_layers(self, red_image, blue_image):
        """Test clearing layers from composition."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(50, 30))
        
        composer.add_layer(LayerSpec(
            image=red_image,
            id="layer1",
            box=(0, 0, 50, 30),
        ))
        composer.add_layer(LayerSpec(
            image=blue_image,
            id="layer2",
            box=(10, 10, 30, 15),
        ))
        
        assert len(composer.layers) == 2
        
        composer.clear()
        
        assert len(composer.layers) == 0


# Integration Tests

class TestLayerIntegration:
    """Test integration between encoder components."""
    
    def test_static_image_as_layer(self, red_image):
        """Test encoding static image using layer infrastructure."""
        encoder = LayerEncoder(BASIS.BASIS_2_2)
        
        spec = LayerSpec(
            image=red_image,
            id="static",
            box=(0, 0, 30, 20),
        )
        
        output = encoder.encode_layer_with_canvas(
            spec,
            canvas_size=(30, 20),
        )
        
        # Should be valid MEOW v0.7
        assert '\x1b]9876;' in output
        assert '"meow":"0.7"' in output
        assert '"id":"static"' in output
    
    def test_animation_frames_as_layers(self, red_image, blue_image, green_image):
        """Test encoding animation frames as layers."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(40, 25))
        
        frames = [
            (red_image, "frame_0"),
            (blue_image, "frame_1"),
            (green_image, "frame_2"),
        ]
        
        for idx, (img, frame_id) in enumerate(frames):
            composer.add_layer(LayerSpec(
                image=img,
                id=frame_id,
                box=(0, 0, 40, 25),
                frame=idx,
                delay=100,
            ))
        
        output = composer.render(loop=0)
        
        # Check all frames present
        assert '"id":"frame_0"' in output
        assert '"id":"frame_1"' in output
        assert '"id":"frame_2"' in output
        
        # Check frame metadata
        assert '"f":0' in output
        assert '"f":1' in output
        assert '"f":2' in output
        assert '"delay":100' in output
    
    def test_overlapping_layers(self, red_image, blue_image):
        """Test composition with overlapping layers."""
        composer = LayerComposer(BASIS.BASIS_2_2, canvas_size=(60, 40))
        
        # Bottom layer (full canvas)
        composer.add_layer(LayerSpec(
            image=red_image,
            id="background",
            box=(0, 0, 60, 40),
            alpha=1.0,
        ))
        
        # Top layer (centered, translucent)
        composer.add_layer(LayerSpec(
            image=blue_image,
            id="foreground",
            box=(20, 15, 20, 10),
            alpha=0.75,
        ))
        
        output = composer.render()
        
        # Verify layer order (don't show full output)
        bg_pos = output.find('"id":"background"')
        fg_pos = output.find('"id":"foreground"')
        assert bg_pos < fg_pos, "Layer stream order incorrect"
        
        # Verify translucency
        assert '"α":1.0' in output, "Missing opaque alpha"
        assert '"α":0.75' in output, "Missing translucent alpha"


# Concatenation Tests

class TestConcatenation:
    """Test layer concatenation workflow."""
    
    def test_concatenate_two_layers(self, red_image, blue_image):
        """Test that two encoded layers can be concatenated."""
        encoder = LayerEncoder(BASIS.BASIS_2_2)
        
        layer1 = encoder.encode_layer_with_canvas(
            LayerSpec(image=red_image, id="layer1", box=(0, 0, 40, 20)),
            canvas_size=(40, 20),
        )
        
        layer2 = encoder.encode_layer(
            LayerSpec(image=blue_image, id="layer2", box=(10, 5, 20, 10))
        )
        
        # Concatenate
        concatenated = layer1 + layer2
        
        # Both layers should be present
        assert '"id":"layer1"' in concatenated
        assert '"id":"layer2"' in concatenated
        
        # Should have canvas from first file
        assert '"meow":"0.7"' in concatenated
        assert '"size":[40,20]' in concatenated
