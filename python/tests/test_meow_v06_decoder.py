"""
Tests for MEOW v0.6 decoder
"""

import pytest
import tempfile
import json
from pathlib import Path

from catpic.decoder import load_meow, display_meow, show_info
from catpic.core import MEOW_OSC_NUMBER, EXIT_ERROR_FILE_NOT_FOUND


class TestLoadMeow:
    """Test load_meow() function"""
    
    def test_load_file_not_found(self):
        """Non-existent file raises SystemExit with code 5"""
        with pytest.raises(SystemExit) as exc:
            load_meow("/nonexistent/file.meow")
        
        assert exc.value.code == EXIT_ERROR_FILE_NOT_FOUND
    
    def test_load_minimal_file(self):
        """Load minimal MEOW file"""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(b'\x1b[38;2;255;0;0m\xe2\x96\x88')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            assert meow.canvas is None
            assert len(meow.layers) == 1
        finally:
            Path(filepath).unlink()
    
    def test_load_file_with_canvas(self):
        """Load file with canvas block"""
        canvas_json = json.dumps({"meow": "0.6", "size": [80, 24]})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07'.encode())
            f.write(b'ANSI')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            assert meow.canvas is not None
            assert meow.canvas.version == "0.6"
            assert meow.canvas.size == (80, 24)
        finally:
            Path(filepath).unlink()


class TestDisplayStatic:
    """Test display of static (non-animated) MEOW files"""
    
    def test_display_single_layer(self, capsys):
        """Display single layer outputs visible content"""
        layer_json = json.dumps({"id": "test"})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07'.encode())
            f.write(b'TEST_OUTPUT')
            filepath = f.name
        
        try:
            display_meow(filepath)
            captured = capsys.readouterr()
            assert 'TEST_OUTPUT' in captured.out
        finally:
            Path(filepath).unlink()
    
    def test_display_multiple_layers_in_order(self, capsys):
        """Display multiple layers in stream order"""
        layer1_json = json.dumps({"id": "layer1"})
        layer2_json = json.dumps({"id": "layer2"})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer1_json}\x07'.encode())
            f.write(b'OUT1')
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer2_json}\x07'.encode())
            f.write(b'OUT2')
            filepath = f.name
        
        try:
            display_meow(filepath)
            captured = capsys.readouterr()
            
            # Check both outputs present and in order
            assert 'OUT1' in captured.out
            assert 'OUT2' in captured.out
            assert captured.out.index('OUT1') < captured.out.index('OUT2')
        finally:
            Path(filepath).unlink()


class TestShowInfo:
    """Test show_info() metadata display"""
    
    def test_show_info_canvas(self, capsys):
        """show_info displays canvas metadata"""
        canvas_json = json.dumps({
            "meow": "0.6",
            "size": [100, 50],
            "basis": [2, 4],
            "loop": 5,
            "meta": {"author": "test"}
        })
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07'.encode())
            filepath = f.name
        
        try:
            show_info(filepath)
            captured = capsys.readouterr()
            
            assert "Canvas:" in captured.out
            assert "Version: 0.6" in captured.out
            assert "100×50" in captured.out
            assert "2×4" in captured.out
            assert "Loop: 5" in captured.out
            assert "author" in captured.out
        finally:
            Path(filepath).unlink()
    
    def test_show_info_layers(self, capsys):
        """show_info displays layer metadata"""
        layer1_json = json.dumps({
            "id": "bg",
            "box": {"x": 0, "y": 0, "dx": 80, "dy": 24},
            "α": 1.0
        })
        layer2_json = json.dumps({
            "id": "sprite",
            "box": {"x": 10, "y": 5, "dx": 20, "dy": 10},
            "α": 0.8,
            "f": 0,
            "delay": 50
        })
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer1_json}\x07'.encode())
            f.write(b'BG')
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer2_json}\x07'.encode())
            f.write(b'SPRITE')
            filepath = f.name
        
        try:
            show_info(filepath)
            captured = capsys.readouterr()
            
            assert "Layers: 2" in captured.out
            assert "Layer 0:" in captured.out
            assert "ID: bg" in captured.out
            assert "Layer 1:" in captured.out
            assert "ID: sprite" in captured.out
            assert "Alpha: 0.8" in captured.out
            assert "Frame: 0" in captured.out
            assert "Delay: 50ms" in captured.out
        finally:
            Path(filepath).unlink()
    
    def test_show_info_infinite_loop(self, capsys):
        """show_info displays 'infinite' for loop=0"""
        canvas_json = json.dumps({"meow": "0.6", "loop": 0})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07'.encode())
            filepath = f.name
        
        try:
            show_info(filepath)
            captured = capsys.readouterr()
            assert "Loop: infinite" in captured.out
        finally:
            Path(filepath).unlink()


class TestAnimationDetection:
    """Test animation vs static detection"""
    
    def test_static_file_no_animation(self, capsys):
        """File with no frame numbers is static"""
        layer_json = json.dumps({"id": "static"})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07'.encode())
            f.write(b'STATIC_OUTPUT')
            filepath = f.name
        
        try:
            display_meow(filepath)
            captured = capsys.readouterr()
            
            # Should display once, not loop
            assert 'STATIC_OUTPUT' in captured.out
        finally:
            Path(filepath).unlink()
    
    def test_animated_file_has_frames(self):
        """File with frame numbers is detected as animated"""
        layer_json = json.dumps({"id": "sprite", "f": 0})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f:
            f.write(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07'.encode())
            f.write(b'FRAME0')
            filepath = f.name
        
        try:
            meow = load_meow(filepath)
            animated = [l for l in meow.layers if l.frame is not None]
            assert len(animated) > 0
        finally:
            Path(filepath).unlink()


class TestConcatenation:
    """Test that concatenated MEOW files work correctly"""
    
    def test_concatenated_files_stream_order(self):
        """cat file1.meow file2.meow maintains stream order"""
        # Create two separate files
        layer1_json = json.dumps({"id": "from_file1"})
        layer2_json = json.dumps({"id": "from_file2"})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f1:
            f1.write(f'\x1b]{MEOW_OSC_NUMBER};{layer1_json}\x07'.encode())
            f1.write(b'FILE1')
            file1_path = f1.name
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as f2:
            f2.write(f'\x1b]{MEOW_OSC_NUMBER};{layer2_json}\x07'.encode())
            f2.write(b'FILE2')
            file2_path = f2.name
        
        try:
            # Concatenate files
            with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
                combined_data = f1.read() + f2.read()
            
            # Write combined
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.meow', delete=False) as fc:
                fc.write(combined_data)
                combined_path = fc.name
            
            try:
                meow = load_meow(combined_path)
                
                assert len(meow.layers) == 2
                assert meow.layers[0].id == "from_file1"
                assert meow.layers[1].id == "from_file2"
                assert 'FILE1' in meow.layers[0].visible_output
                assert 'FILE2' in meow.layers[1].visible_output
            finally:
                Path(combined_path).unlink()
        
        finally:
            Path(file1_path).unlink()
            Path(file2_path).unlink()
