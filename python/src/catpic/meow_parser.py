"""
MEOW v0.6 parser - Core data structures and parsing logic
"""

import json
import gzip
import base64
import math
import re
import sys
from dataclasses import dataclass, field
from typing import Optional, Any

from .core import (
    MEOW_VERSION,
    MEOW_OSC_NUMBER,
    DEFAULT_BASIS,
    DEFAULT_ALPHA,
    DEFAULT_FRAME_DELAY,
    EXIT_ERROR_INVALID_METADATA,
)


def strip_frame_markers(text: str) -> str:
    """Remove frame marker lines for clean playback."""
    # Pattern matches: \x1b[2m--- Frame N/Total ---\x1b[0m
    pattern = r'\x1b\[2m--- Frame \d+/\d+ ---\x1b\[0m\n?'
    return re.sub(pattern, '', text)


@dataclass
class CanvasBlock:
    """MEOW v0.6 Canvas metadata block"""
    version: str
    size: Optional[tuple[int, int]] = None
    meld: bool = False
    loop: int = 1
    basis: tuple[int, int] = DEFAULT_BASIS
    meta: dict[str, Any] = field(default_factory=dict)
    
    def is_infinite_loop(self) -> bool:
        """Check if animation loops infinitely (loop=0)"""
        return self.loop == 0


@dataclass
class LayerBlock:
    """MEOW v0.6 Layer metadata block"""
    id: Optional[str] = None
    box: Optional[dict[str, int]] = None
    alpha: float = DEFAULT_ALPHA
    basis: Optional[tuple[int, int]] = None
    ctype: Optional[str] = None
    cells: Optional[str] = None
    frame: Optional[int] = None
    delay: int = DEFAULT_FRAME_DELAY
    visible_output: str = ""
    
    def validate_ctype(self):
        """Validate ctype field according to spec (exit code 4 errors)"""
        # Case 1: cells present without ctype
        if self.cells is not None and self.ctype is None:
            raise ValueError(
                f"Layer contains 'cells' but missing 'ctype' field. "
                f"Encoders MUST specify cells data type. "
                f"Exit code: {EXIT_ERROR_INVALID_METADATA}"
            )
        
        # Case 2: ctype='none' with cells
        if self.ctype == "none" and self.cells is not None:
            raise ValueError(
                f"Layer has ctype='none' but cells present. "
                f"Exit code: {EXIT_ERROR_INVALID_METADATA}"
            )
        
        # Case 3: Unknown ctype with cells
        valid_ctypes = {"ansi-art", "none", None}
        if self.ctype not in valid_ctypes and self.cells is not None:
            raise ValueError(
                f"Unknown ctype '{self.ctype}' with cells present. "
                f"Exit code: {EXIT_ERROR_INVALID_METADATA}"
            )
    
    def get_clamped_alpha(self) -> float:
        """Get alpha value clamped to valid range [0.0, 1.0]"""
        # Handle NaN and Infinity
        if math.isnan(self.alpha) or math.isinf(self.alpha):
            return 1.0
        
        # Clamp to range
        if self.alpha < 0.0:
            return 0.0
        if self.alpha > 1.0:
            return 1.0
        
        return self.alpha
    
    def is_valid_box(self) -> bool:
        """Check if box has valid dimensions (dx>0 and dy>0)"""
        if self.box is None:
            return True
        
        dx = self.box.get('dx', 1)
        dy = self.box.get('dy', 1)
        
        return dx > 0 and dy > 0
    
    def get_clipped_box(self, canvas_size: Optional[tuple[int, int]] = None) -> dict[str, int]:
        """Get box clipped to valid bounds and canvas size"""
        if self.box is None:
            if canvas_size:
                return {'x': 0, 'y': 0, 'dx': canvas_size[0], 'dy': canvas_size[1]}
            return {'x': 0, 'y': 0, 'dx': 80, 'dy': 24}
        
        # Start with current box
        clipped = self.box.copy()
        
        # Clip negative origin to 0
        if clipped.get('x', 0) < 0:
            clipped['x'] = 0
        if clipped.get('y', 0) < 0:
            clipped['y'] = 0
        
        # Clip to canvas if provided
        if canvas_size:
            canvas_w, canvas_h = canvas_size
            x = clipped.get('x', 0)
            y = clipped.get('y', 0)
            dx = clipped.get('dx', canvas_w)
            dy = clipped.get('dy', canvas_h)
            
            # Clip width/height to not exceed canvas
            if x + dx > canvas_w:
                clipped['dx'] = max(0, canvas_w - x)
            if y + dy > canvas_h:
                clipped['dy'] = max(0, canvas_h - y)
        
        return clipped
    
    def get_box(self, canvas_size: tuple[int, int]) -> dict[str, int]:
        """Get layer box with defaults filled in"""
        if self.box is None:
            return {
                'x': 0,
                'y': 0,
                'dx': canvas_size[0],
                'dy': canvas_size[1]
            }
        
        return {
            'x': self.box.get('x', 0),
            'y': self.box.get('y', 0),
            'dx': self.box.get('dx', canvas_size[0]),
            'dy': self.box.get('dy', canvas_size[1])
        }


@dataclass
class MEOWFile:
    """Parsed MEOW v0.6 file"""
    canvas: Optional[CanvasBlock] = None
    layers: list[LayerBlock] = field(default_factory=list)
    
    def infer_canvas_size(self) -> tuple[int, int]:
        """Infer canvas size from layer boxes"""
        if self.canvas and self.canvas.size:
            return self.canvas.size
        
        # Find maximum extents from all layer boxes
        max_x = 0
        max_y = 0
        
        for layer in self.layers:
            if layer.box:
                x = layer.box.get('x', 0)
                y = layer.box.get('y', 0)
                dx = layer.box.get('dx', 0)
                dy = layer.box.get('dy', 0)
                
                max_x = max(max_x, x + dx)
                max_y = max(max_y, y + dy)
        
        # Default to 80x24 if no boxes found
        if max_x == 0 and max_y == 0:
            return (80, 24)
        
        return (max(max_x, 80), max(max_y, 24))
    
    def group_by_frame(self) -> dict[int, list[LayerBlock]]:
        """Group layers by frame number for animation"""
        frames = {}
        
        # Find all unique frame numbers
        frame_numbers = set()
        for layer in self.layers:
            if layer.frame is not None:
                frame_numbers.add(layer.frame)
        
        # If no frames, return all layers as frame 0
        if not frame_numbers:
            return {0: self.layers}
        
        # Group layers for each frame
        for frame_num in sorted(frame_numbers):
            frame_layers = []
            
            # Add static layers (no frame number)
            for layer in self.layers:
                if layer.frame is None:
                    frame_layers.append(layer)
            
            # Add animated layers for this frame
            for layer in self.layers:
                if layer.frame == frame_num:
                    frame_layers.append(layer)
            
            frames[frame_num] = frame_layers
        
        return frames
    
    def should_meld(self) -> bool:
        """Check if melding should be performed (conservative approach)"""
        if self.canvas and self.canvas.meld:
            return True
        return False


class MEOWParser:
    """Parser for MEOW v0.6 format"""
    
    def __init__(self):
        self.canvas: Optional[CanvasBlock] = None
        self.last_canvas: Optional[CanvasBlock] = None
        self.layers: list[LayerBlock] = []
        self.any_meld_hint = False
    
    def parse(self, data: bytes) -> MEOWFile:
        """Parse MEOW v0.6 file data"""
        # Convert to string for processing
        try:
            text = data.decode('utf-8', errors='replace')
        except Exception:
            text = data.decode('latin-1', errors='replace')
        
        # Find all OSC 9876 sequences
        osc_pattern = rf'\x1b\]{MEOW_OSC_NUMBER};([^\x07]+)\x07'
        
        last_pos = 0
        current_layer = None
        
        for match in re.finditer(osc_pattern, text):
            # Get visible output before this OSC
            if current_layer is not None:
                visible = text[last_pos:match.start()]
                current_layer.visible_output = strip_frame_markers(visible)
                self.layers.append(current_layer)
                current_layer = None
            
            # Parse metadata
            metadata_str = match.group(1)
            try:
                metadata = self._parse_metadata(metadata_str.encode('utf-8'))
                
                # Check if canvas or layer block
                if 'meow' in metadata:
                    canvas = self._parse_canvas_block(metadata)
                    self.last_canvas = canvas
                    if canvas.meld:
                        self.any_meld_hint = True
                else:
                    current_layer = self._parse_layer_block(metadata)
                    try:
                        current_layer.validate_ctype()
                    except ValueError as e:
                        print(f"Warning: {e}", file=sys.stderr)
                        current_layer = None
            
            except Exception as e:
                print(f"Warning: Failed to parse metadata: {e}", file=sys.stderr)
            
            last_pos = match.end()
        
        # Handle remaining visible output
        if current_layer is not None:
            visible = text[last_pos:]
            current_layer.visible_output = strip_frame_markers(visible)
            self.layers.append(current_layer)
        elif last_pos == 0:
            # No OSC blocks found - pure ANSI file
            layer = LayerBlock(visible_output=strip_frame_markers(text))
            self.layers.append(layer)
        else:
            # Trailing content after last OSC
            if last_pos < len(text):
                trailing = text[last_pos:]
                if trailing.strip():
                    layer = LayerBlock(visible_output=strip_frame_markers(trailing))
                    self.layers.append(layer)
        
        # Use last canvas block (concatenation semantics)
        return MEOWFile(canvas=self.last_canvas, layers=self.layers)
    
    def _parse_metadata(self, data: bytes) -> dict:
        """Parse metadata (plain JSON or compressed)"""
        # Check if plain JSON (starts with '{')
        if data[0:1] == b'{':
            return json.loads(data)
        
        # Try decompression
        try:
            decompressed = gzip.decompress(base64.b64decode(data))
            return json.loads(decompressed)
        except Exception:
            # Fallback to plain JSON
            return json.loads(data)
    
    def _parse_canvas_block(self, metadata: dict) -> CanvasBlock:
        """Parse canvas metadata block"""
        size = metadata.get('size')
        if size:
            size = tuple(size)
        
        basis = metadata.get('basis', DEFAULT_BASIS)
        if isinstance(basis, list):
            basis = tuple(basis)
        
        return CanvasBlock(
            version=metadata.get('meow', MEOW_VERSION),
            size=size,
            meld=metadata.get('meld', False),
            loop=metadata.get('loop', 1),
            basis=basis,
            meta=metadata.get('meta', {})
        )
    
    def _parse_layer_block(self, metadata: dict) -> LayerBlock:
        """Parse layer metadata block"""
        # Handle alpha field (both α and alpha)
        alpha = metadata.get('α', metadata.get('alpha', DEFAULT_ALPHA))
        
        basis = metadata.get('basis')
        if basis and isinstance(basis, list):
            basis = tuple(basis)
        
        return LayerBlock(
            id=metadata.get('id'),
            box=metadata.get('box'),
            alpha=alpha,
            basis=basis,
            ctype=metadata.get('ctype'),
            cells=metadata.get('cells'),
            frame=metadata.get('f'),
            delay=metadata.get('delay', DEFAULT_FRAME_DELAY)
        )
