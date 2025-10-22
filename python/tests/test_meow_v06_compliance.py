"""
MEOW v0.6 compliance tests

These tests verify behavior specified in the MEOW v0.6 specification
"""

import pytest
import tempfile
import json
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
        
        assert str(EXIT_ERROR_INVALID_