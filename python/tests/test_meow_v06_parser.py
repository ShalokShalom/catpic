"""
Tests for MEOW v0.6 parser
"""

import pytest
import json
import gzip
import base64
from catpic.meow_parser import (
    MEOWParser,
    CanvasBlock,
    LayerBlock,
    MEOWFile,
)
from catpic.core import (
    MEOW_OSC_NUMBER,
    EXIT_ERROR_INVALID_METADATA,
)


class TestMetadataEncoding:
    """Test metadata compression detection"""
    
    def test_plain_json_detection(self):
        """Plain JSON starts with { and parses correctly"""
        parser = MEOWParser()
        plain_json = b'{"meow":"0.6","size":[80,24]}'
        result = parser._parse_metadata(plain_json)
        
        assert result['meow'] == '0.6'
        assert result['size'] == [80, 24]
    
    def test_compressed_json_detection(self):
        """Compressed JSON decodes correctly"""
        parser = MEOWParser()
        json_str = '{"meow":"0.6","size":[80,24]}'
        compressed = base64.b64encode(gzip.compress(json_str.encode('utf-8')))
        
        result = parser._parse_metadata(compressed)
        assert result['meow'] == '0.6'
        assert result['size'] == [80, 24]
    
    def test_fallback_to_plain_on_decompress_failure(self):
        """If decompression fails, try plain JSON"""
        parser = MEOWParser()
        # Invalid base64 but valid JSON
        data = b'{"meow":"0.6"}'
        result = parser._parse_metadata(data)
        assert result['meow'] == '0.6'


class TestCanvasBlock:
    """Test canvas block parsing"""
    
    def test_minimal_canvas(self):
        """Minimal canvas with just version"""
        parser = MEOWParser()
        metadata = {"meow": "0.6"}
        canvas = parser._parse_canvas_block(metadata)
        
        assert canvas.version == "0.6"
        assert canvas.size is None
        assert canvas.meld is False
        assert canvas.loop == 1
        assert canvas.basis == (2, 2)
        assert canvas.meta == {}
    
    def test_full_canvas(self):
        """Canvas with all fields"""
        parser = MEOWParser()
        metadata = {
            "meow": "0.6",
            "size": [100, 50],
            "meld": True,
            "loop": 0,
            "basis": [2, 4],
            "meta": {"author": "test", "created": "2025-10-19"}
        }
        canvas = parser._parse_canvas_block(metadata)
        
        assert canvas.version == "0.6"
        assert canvas.size == (100, 50)
        assert canvas.meld is True
        assert canvas.loop == 0
        assert canvas.basis == (2, 4)
        assert canvas.meta['author'] == "test"


class TestLayerBlock:
    """Test layer block parsing"""
    
    def test_minimal_layer(self):
        """Minimal layer with no metadata fields"""
        parser = MEOWParser()
        metadata = {}
        layer = parser._parse_layer_block(metadata)
        
        assert layer.id is None
        assert layer.box is None
        assert layer.alpha == 1.0
        assert layer.basis is None
        assert layer.ctype is None
        assert layer.cells is None
        assert layer.frame is None
        assert layer.delay == 100
    
    def test_full_layer(self):
        """Layer with all fields"""
        parser = MEOWParser()
        metadata = {
            "id": "sprite",
            "box": {"x": 10, "y": 5, "dx": 20, "dy": 15},
            "α": 0.8,
            "basis": [2, 3],
            "ctype": "ansi-art",
            "cells": "H4sIAAAAAAAA...",
            "f": 2,
            "delay": 50
        }
        layer = parser._parse_layer_block(metadata)
        
        assert layer.id == "sprite"
        assert layer.box == {"x": 10, "y": 5, "dx": 20, "dy": 15}
        assert layer.alpha == 0.8
        assert layer.basis == (2, 3)
        assert layer.ctype == "ansi-art"
        assert layer.cells == "H4sIAAAAAAAA..."
        assert layer.frame == 2
        assert layer.delay == 50
    
    def test_alpha_fallback(self):
        """Layer accepts both α and alpha fields"""
        parser = MEOWParser()
        
        # Unicode α takes precedence
        metadata1 = {"α": 0.5, "alpha": 0.9}
        layer1 = parser._parse_layer_block(metadata1)
        assert layer1.alpha == 0.5
        
        # Falls back to alpha if α absent
        metadata2 = {"alpha": 0.7}
        layer2 = parser._parse_layer_block(metadata2)
        assert layer2.alpha == 0.7


class TestCtypeValidation:
    """Test ctype field validation (exit code 4 errors)"""
    
    def test_cells_without_ctype_raises(self):
        """cells present without ctype is an error"""
        layer = LayerBlock(cells="data", ctype=None)
        
        with pytest.raises(ValueError) as exc:
            layer.validate_ctype()
        
        assert "missing 'ctype'" in str(exc.value)
        assert str(EXIT_ERROR_INVALID_METADATA) in str(exc.value)
    
    def test_ctype_none_with_cells_raises(self):
        """ctype='none' with cells is an error"""
        layer = LayerBlock(cells="data", ctype="none")
        
        with pytest.raises(ValueError) as exc:
            layer.validate_ctype()
        
        assert "ctype='none' but cells present" in str(exc.value)
    
    def test_unknown_ctype_with_cells_raises(self):
        """Unknown ctype with cells is an error"""
        layer = LayerBlock(cells="data", ctype="unknown")
        
        with pytest.raises(ValueError) as exc:
            layer.validate_ctype()
        
        assert "Unknown ctype" in str(exc.value)
    
    def test_valid_ctype_combinations(self):
        """Valid ctype combinations don't raise"""
        # No cells, no ctype - valid
        LayerBlock().validate_ctype()
        
        # cells with ctype="ansi-art" - valid
        LayerBlock(cells="data", ctype="ansi-art").validate_ctype()
        
        # No cells, ctype="ansi-art" - valid (placeholder)
        LayerBlock(ctype="ansi-art").validate_ctype()
        
        # No cells, ctype="none" - valid (explicit display-only)
        LayerBlock(ctype="none").validate_ctype()


class TestLayerBoxDefaults:
    """Test layer bounding box defaults"""
    
    def test_no_box_uses_canvas_size(self):
        """Layer without box uses full canvas"""
        layer = LayerBlock()
        box = layer.get_box((80, 24))
        
        assert box == {'x': 0, 'y': 0, 'dx': 80, 'dy': 24}
    
    def test_partial_box_uses_defaults(self):
        """Partial box fills in defaults"""
        layer = LayerBlock(box={"x": 10, "y": 5})
        box = layer.get_box((80, 24))
        
        assert box['x'] == 10
        assert box['y'] == 5
        assert box['dx'] == 80
        assert box['dy'] == 24


class TestFileParser:
    """Test complete file parsing"""
    
    def test_parse_minimal_file(self):
        """Parse file with just ANSI output (no metadata)"""
        parser = MEOWParser()
        data = b'\x1b[38;2;255;0;0m\xe2\x96\x88'  # Red block
        
        meow = parser.parse(data)
        
        assert meow.canvas is None
        assert len(meow.layers) == 1
        assert '\x1b[38;2;255;0;0m' in meow.layers[0].visible_output
    
    def test_parse_canvas_and_layer(self):
        """Parse file with canvas and one layer"""
        parser = MEOWParser()
        
        canvas_json = json.dumps({"meow": "0.6", "size": [80, 24]})
        layer_json = json.dumps({"id": "bg", "α": 1.0})
        
        data = (
            f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07'.encode() +
            f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07'.encode() +
            b'ANSI_OUTPUT'
        )
        
        meow = parser.parse(data)
        
        assert meow.canvas is not None
        assert meow.canvas.version == "0.6"
        assert meow.canvas.size == (80, 24)
        
        assert len(meow.layers) == 1
        assert meow.layers[0].id == "bg"
        assert meow.layers[0].visible_output == "ANSI_OUTPUT"
    
    def test_parse_multiple_layers_stream_order(self):
        """Multiple layers maintain stream order"""
        parser = MEOWParser()
        
        layer1_json = json.dumps({"id": "layer1"})
        layer2_json = json.dumps({"id": "layer2"})
        layer3_json = json.dumps({"id": "layer3"})
        
        data = (
            f'\x1b]{MEOW_OSC_NUMBER};{layer1_json}\x07'.encode() + b'OUT1' +
            f'\x1b]{MEOW_OSC_NUMBER};{layer2_json}\x07'.encode() + b'OUT2' +
            f'\x1b]{MEOW_OSC_NUMBER};{layer3_json}\x07'.encode() + b'OUT3'
        )
        
        meow = parser.parse(data)
        
        assert len(meow.layers) == 3
        assert meow.layers[0].id == "layer1"
        assert meow.layers[1].id == "layer2"
        assert meow.layers[2].id == "layer3"
        assert meow.layers[0].visible_output == "OUT1"
        assert meow.layers[1].visible_output == "OUT2"
        assert meow.layers[2].visible_output == "OUT3"
    
    def test_parse_with_compressed_metadata(self):
        """Parse file with gzip-compressed metadata"""
        parser = MEOWParser()
        
        layer_json = json.dumps({
            "id": "compressed_layer",
            "cells": "some_large_data" * 100,
            "ctype": "ansi-art"
        })
        compressed = base64.b64encode(gzip.compress(layer_json.encode('utf-8')))
        
        data = f'\x1b]{MEOW_OSC_NUMBER};'.encode() + compressed + b'\x07ANSI'
        
        meow = parser.parse(data)
        
        assert len(meow.layers) == 1
        assert meow.layers[0].id == "compressed_layer"
        assert meow.layers[0].ctype == "ansi-art"
    
    def test_malformed_json_skipped(self, capsys):
        """Malformed JSON blocks are skipped with warning"""
        parser = MEOWParser()
        
        good_layer = json.dumps({"id": "good"})
        
        data = (
            f'\x1b]{MEOW_OSC_NUMBER};{{invalid json'.encode() + b'\x07BAD' +
            f'\x1b]{MEOW_OSC_NUMBER};{good_layer}\x07'.encode() + b'GOOD'
        )
        
        meow = parser.parse(data)
        
        # Should skip malformed block, parse good one
        assert len(meow.layers) == 1
        assert meow.layers[0].id == "good"
        
        # Should print warning
        captured = capsys.readouterr()
        assert "Warning" in captured.err


class TestAnimationFrames:
    """Test animation frame handling"""
    
    def test_static_layers_no_frame_field(self):
        """Static layers have frame=None"""
        parser = MEOWParser()
        layer_json = json.dumps({"id": "static"})
        
        data = f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07'.encode() + b'OUT'
        meow = parser.parse(data)
        
        assert meow.layers[0].frame is None
    
    def test_animated_layers_with_frame_field(self):
        """Animated layers have frame number"""
        parser = MEOWParser()
        layer1_json = json.dumps({"id": "sprite", "f": 0})
        layer2_json = json.dumps({"id": "sprite", "f": 1})
        
        data = (
            f'\x1b]{MEOW_OSC_NUMBER};{layer1_json}\x07'.encode() + b'FRAME0' +
            f'\x1b]{MEOW_OSC_NUMBER};{layer2_json}\x07'.encode() + b'FRAME1'
        )
        
        meow = parser.parse(data)
        
        assert len(meow.layers) == 2
        assert meow.layers[0].frame == 0
        assert meow.layers[1].frame == 1
    
    def test_mixed_static_and_animated(self):
        """File can have both static and animated layers"""
        parser = MEOWParser()
        
        bg_json = json.dumps({"id": "bg"})  # No frame = static
        sprite0_json = json.dumps({"id": "sprite", "f": 0})
        sprite1_json = json.dumps({"id": "sprite", "f": 1})
        ui_json = json.dumps({"id": "ui"})  # No frame = static
        
        data = (
            f'\x1b]{MEOW_OSC_NUMBER};{bg_json}\x07'.encode() + b'BG' +
            f'\x1b]{MEOW_OSC_NUMBER};{sprite0_json}\x07'.encode() + b'S0' +
            f'\x1b]{MEOW_OSC_NUMBER};{sprite1_json}\x07'.encode() + b'S1' +
            f'\x1b]{MEOW_OSC_NUMBER};{ui_json}\x07'.encode() + b'UI'
        )
        
        meow = parser.parse(data)
        
        static = [l for l in meow.layers if l.frame is None]
        animated = [l for l in meow.layers if l.frame is not None]
        
        assert len(static) == 2
        assert len(animated) == 2
        assert static[0].id == "bg"
        assert static[1].id == "ui"
