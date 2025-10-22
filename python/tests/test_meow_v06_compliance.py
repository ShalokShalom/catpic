"""
MEOW v0.6 compliance tests

These tests verify behavior specified in the MEOW v0.6 specification
"""

import pytest
import tempfile
import json
import gzip
import base64
from pathlib import Path

from catpic.decoder import load_meow
from catpic.meow_parser import LayerBlock
from catpic.core import MEOW_OSC_NUMBER, EXIT_ERROR_INVALID_METADATA


class TestSpecCompliance:
    """Tests from MEOW v0.6 specification"""
    
    def test_osc_9876_hidden(self):
        """OSC 9876 sequences must be hidden from terminal display"""
        # This is a terminal behavior test, but we can verify format
        canvas_json = json.dumps({"meow": "0.6"})
        osc_sequence = f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07'
        
        assert osc_sequence.startswith('\x1b]9876;')
        assert osc_sequence.endswith('\x07')
    
    def test_minimal_valid_file(self):
        """Pure ANSI with no metadata is valid"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(b'\x1b[H\x1b[38;2;255;0;0m\xe2\x96\x88')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            # Should parse without error
            assert meow.canvas is None
            assert len(meow.layers) == 1
        finally:
            Path(filepath).unlink()
    
    def test_stream_order_equals_z_order(self):
        """First layer in file = bottom, last = top"""
        layer1 = json.dumps({"id": "bottom"})
        layer2 = json.dumps({"id": "middle"})
        layer3 = json.dumps({"id": "top"})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer1}\x07'.encode() + b'L1')
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer2}\x07'.encode() + b'L2')
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer3}\x07'.encode() + b'L3')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            assert meow.layers[0].id == "bottom"
            assert meow.layers[1].id == "middle"
            assert meow.layers[2].id == "top"
        finally:
            Path(filepath).unlink()


class TestCtypeCompliance:
    """Test ctype field requirements from spec"""
    
    def test_cells_without_ctype_error_code_4(self):
        """cells without ctype must exit with code 4"""
        layer = LayerBlock(cells="data", ctype=None)
        
        with pytest.raises(ValueError) as exc:
            layer.validate_ctype()
        
        assert str(EXIT_ERROR_INVALID_METADATA) in str(exc.value)
    
    def test_ctype_none_with_cells_error_code_4(self):
        """ctype='none' with cells must exit with code 4"""
        layer = LayerBlock(cells="data", ctype="none")
        
        with pytest.raises(ValueError) as exc:
            layer.validate_ctype()
        
        assert str(EXIT_ERROR_INVALID_METADATA) in str(exc.value)
    
    def test_unknown_ctype_with_cells_error_code_4(self):
        """Unknown ctype with cells must exit with code 4"""
        layer = LayerBlock(cells="data", ctype="future-protocol")
        
        with pytest.raises(ValueError) as exc:
            layer.validate_ctype()
        
        assert str(EXIT_ERROR_INVALID_METADATA) in str(exc.value)
    
    def test_valid_ansi_art_ctype_with_cells(self):
        """ctype='ansi-art' with cells is valid"""
        layer = LayerBlock(cells="dense_ansi_data", ctype="ansi-art")
        # Should not raise
        layer.validate_ctype()
    
    def test_valid_ansi_art_ctype_without_cells(self):
        """ctype='ansi-art' without cells is valid (placeholder)"""
        layer = LayerBlock(ctype="ansi-art")
        # Should not raise
        layer.validate_ctype()
    
    def test_valid_none_ctype_without_cells(self):
        """ctype='none' without cells is valid (explicit display-only)"""
        layer = LayerBlock(ctype="none")
        # Should not raise
        layer.validate_ctype()


class TestAlphaValidation:
    """Test alpha coefficient validation (spec section)"""
    
    def test_alpha_clamped_to_range(self):
        """Alpha values outside 0.0-1.0 are clamped"""
        # Test negative alpha
        layer1 = LayerBlock(alpha=-0.5)
        assert layer1.get_clamped_alpha() == 0.0
        
        # Test alpha > 1.0
        layer2 = LayerBlock(alpha=1.5)
        assert layer2.get_clamped_alpha() == 1.0
        
        # Test valid range
        layer3 = LayerBlock(alpha=0.5)
        assert layer3.get_clamped_alpha() == 0.5
    
    def test_alpha_nan_defaults_to_1(self):
        """Alpha = NaN defaults to 1.0"""
        layer = LayerBlock(alpha=float('nan'))
        assert layer.get_clamped_alpha() == 1.0
    
    def test_alpha_infinity_defaults_to_1(self):
        """Alpha = Infinity defaults to 1.0"""
        layer = LayerBlock(alpha=float('inf'))
        assert layer.get_clamped_alpha() == 1.0


class TestBoxValidation:
    """Test bounding box validation (spec section)"""
    
    def test_negative_dimensions_rejected(self):
        """Box with dx<=0 or dy<=0 should be rejected"""
        layer1 = LayerBlock(box={"x": 0, "y": 0, "dx": 0, "dy": 10})
        assert not layer1.is_valid_box()
        
        layer2 = LayerBlock(box={"x": 0, "y": 0, "dx": 10, "dy": -5})
        assert not layer2.is_valid_box()
    
    def test_negative_origin_clipped(self):
        """Box with x<0 or y<0 should clip to 0"""
        layer = LayerBlock(box={"x": -5, "y": -10, "dx": 20, "dy": 15})
        clipped = layer.get_clipped_box()
        
        assert clipped['x'] == 0
        assert clipped['y'] == 0
    
    def test_box_clipped_to_canvas(self):
        """Box exceeding canvas bounds should clip"""
        layer = LayerBlock(box={"x": 70, "y": 20, "dx": 20, "dy": 10})
        clipped = layer.get_clipped_box(canvas_size=(80, 24))
        
        # x + dx = 90, but canvas is 80 wide
        assert clipped['x'] + clipped['dx'] <= 80
        # y + dy = 30, but canvas is 24 tall
        assert clipped['y'] + clipped['dy'] <= 24


class TestConditionalCompression:
    """Test metadata compression requirements"""
    
    def test_plain_json_without_cells(self):
        """Metadata without cells should use plain JSON"""
        metadata = {"id": "layer", "box": {"x": 0, "y": 0, "dx": 10, "dy": 10}}
        json_str = json.dumps(metadata)
        
        # Should be readable JSON
        assert json_str.startswith('{')
        parsed = json.loads(json_str)
        assert parsed['id'] == "layer"
    
    def test_compressed_with_cells(self):
        """Metadata with cells MUST be compressed"""
        metadata = {
            "id": "layer",
            "ctype": "ansi-art",
            "cells": "\x1b[0m " * 1000  # Large cells data
        }
        json_str = json.dumps(metadata)
        compressed = base64.b64encode(gzip.compress(json_str.encode('utf-8')))
        
        # Compressed should be smaller
        assert len(compressed) < len(json_str)
        
        # Should decode back correctly
        decompressed = gzip.decompress(base64.b64decode(compressed))
        parsed = json.loads(decompressed)
        assert parsed['id'] == "layer"
        assert parsed['ctype'] == "ansi-art"


class TestCanvasSizeDetermination:
    """Test canvas size inference (spec section)"""
    
    def test_explicit_size_field(self):
        """Canvas size from explicit field takes priority"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            canvas_json = json.dumps({"meow": "0.6", "size": [100, 50]})
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07'.encode())
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            assert meow.canvas.size == (100, 50)
        finally:
            Path(filepath).unlink()
    
    def test_infer_from_layer_boxes(self):
        """Canvas size inferred from layer bounding boxes"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            # Layer extends to (50, 30)
            layer_json = json.dumps({"box": {"x": 10, "y": 5, "dx": 40, "dy": 25}})
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07'.encode())
            f.write(b'DATA')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            inferred_size = meow.infer_canvas_size()
            
            # Should be at least 50x30 to contain the layer
            assert inferred_size[0] >= 50
            assert inferred_size[1] >= 30
        finally:
            Path(filepath).unlink()


class TestGracefulDegradation:
    """Test error handling requirements (spec section)"""
    
    def test_malformed_json_continues(self, capsys):
        """Malformed JSON should log warning but continue"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            # Malformed JSON
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{{invalid\x07'.encode())
            # Valid layer after
            good_layer = json.dumps({"id": "good"})
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{good_layer}\x07'.encode())
            f.write(b'GOOD_DATA')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            
            # Should continue and parse valid layer
            assert len(meow.layers) >= 1
            
            # Should log warning
            captured = capsys.readouterr()
            assert "warning" in captured.err.lower() or "error" in captured.err.lower()
        finally:
            Path(filepath).unlink()
    
    def test_decompression_failure_fallback(self):
        """Decompression failure should fallback to plain JSON"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            # Not actually compressed, but looks like base64
            layer_json = '{"id":"test"}'
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07'.encode())
            f.write(b'DATA')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            # Should fallback and parse as plain JSON
            assert len(meow.layers) == 1
            assert meow.layers[0].id == "test"
        finally:
            Path(filepath).unlink()
    
    def test_decoder_must_not_crash(self):
        """Decoder must not crash on any input"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            # Random binary garbage
            f.write(b'\x00\x01\x02\xff\xfe\xfd')
            f.write(f'\x1b]{MEOW_OSC_NUMBER};garbage\x07'.encode())
            f.write(b'\x1b[H\x1b[38;2;255;0;0m\xe2\x96\x88')
            filepath = f.name
        
        try:
            # Should not raise exception
            meow = load_meow(filepath)
            # At minimum, should parse visible ANSI output
            assert meow is not None
        finally:
            Path(filepath).unlink()


class TestAnimationSpec:
    """Test animation specifications"""
    
    def test_frame_grouping(self):
        """Layers group by frame number correctly"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            bg_json = json.dumps({"id": "bg"})  # Static
            sprite0_json = json.dumps({"id": "sprite", "f": 0})
            sprite1_json = json.dumps({"id": "sprite", "f": 1})
            ui_json = json.dumps({"id": "ui"})  # Static
            
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{bg_json}\x07'.encode() + b'BG')
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{sprite0_json}\x07'.encode() + b'S0')
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{sprite1_json}\x07'.encode() + b'S1')
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{ui_json}\x07'.encode() + b'UI')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            frames = meow.group_by_frame()
            
            # Frame 0: bg + sprite_f0 + ui
            assert len(frames[0]) == 3
            assert any(l.id == "bg" for l in frames[0])
            assert any(l.id == "sprite" and l.frame == 0 for l in frames[0])
            assert any(l.id == "ui" for l in frames[0])
            
            # Frame 1: bg + sprite_f1 + ui
            assert len(frames[1]) == 3
            assert any(l.id == "sprite" and l.frame == 1 for l in frames[1])
        finally:
            Path(filepath).unlink()
    
    def test_default_frame_delay(self):
        """Default frame delay is 100ms"""
        layer = LayerBlock(frame=0)
        assert layer.delay == 100
    
    def test_loop_zero_is_infinite(self):
        """loop=0 means infinite looping"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            canvas_json = json.dumps({"meow": "0.6", "loop": 0})
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07'.encode())
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            assert meow.canvas.loop == 0
            assert meow.canvas.is_infinite_loop()
        finally:
            Path(filepath).unlink()


class TestConcatenationSpec:
    """Test concatenation behavior from spec"""
    
    def test_last_canvas_wins(self):
        """When multiple canvas blocks, use LAST one"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            canvas1 = json.dumps({"meow": "0.6", "size": [80, 24]})
            canvas2 = json.dumps({"meow": "0.6", "size": [100, 50]})
            
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas1}\x07'.encode())
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas2}\x07'.encode())
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            # Should use last canvas block
            assert meow.canvas.size == (100, 50)
        finally:
            Path(filepath).unlink()
    
    def test_meld_hint_conservative(self):
        """If ANY canvas has meld=true, perform melding"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            canvas1 = json.dumps({"meow": "0.6", "meld": False})
            canvas2 = json.dumps({"meow": "0.6", "meld": True})
            
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas1}\x07'.encode())
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas2}\x07'.encode())
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            # Should use last canvas which has meld=true
            assert meow.should_meld() is True
        finally:
            Path(filepath).unlink()
