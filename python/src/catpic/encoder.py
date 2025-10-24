"""
MEOW v0.6 Encoder - Core functionality

Encodes images to MEOW format with proper aspect ratio compensation
"""

import json
from pathlib import Path
from shutil import get_terminal_size
from typing import Optional, Union

from PIL import Image

from .core import BASIS, CatpicCore, MEOW_VERSION, MEOW_OSC_NUMBER, DEFAULT_BASIS, get_char_aspect
from .primitives import image_to_cells, cells_to_ansi_lines


class CatpicEncoder:
    """
    Encode images to MEOW v0.6 format.
    
    Phase 1: Single-layer static images with v0.6 metadata
    Phase 2: Full animation support
    """
    
    def __init__(self, basis: Optional[BASIS] = None):
        """
        Initialize encoder.
        
        Args:
            basis: BASIS level for encoding (default: BASIS_2_2)
        """
        if basis is None:
            from .core import get_default_basis
            basis = get_default_basis()
        
        self.basis = basis
        self.basis_tuple = basis.value  # (x, y) tuple
    
    def encode_image(
        self,
        image_path: Union[str, Path],
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> str:
        """
        Encode a static image to MEOW v0.6 format.
        
        Args:
            image_path: Path to image file
            width: Output width in characters (default: terminal width or 80)
            height: Output height in characters (default: auto from aspect ratio)
        
        Returns:
            MEOW v0.6 formatted string with OSC 9876 metadata
        """
        # Load image
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            
            # Calculate dimensions
            if width is None:
                width = 80  # Default to 80 columns
            
            # Cap width to terminal size to prevent wrapping corruption
            term_width, _ = get_terminal_size()
            if width > term_width:
                width = term_width
            
            # Cap width to terminal size to prevent wrapping corruption
            term_width, _ = get_terminal_size()
            if width > term_width:
                width = term_width
            
            if height is None:
                # Maintain aspect ratio with terminal character aspect compensation
                # Terminal characters are ~2x taller than wide, so multiply by 0.5
                image_aspect = img.height / img.width
                char_aspect = get_char_aspect()
                height = int(width * image_aspect / char_aspect)
            
            # Convert to cells (primitives handles resizing internally)
            cells = image_to_cells(img, width, height, basis=self.basis)
            
            # Generate ANSI output
            ansi_lines = cells_to_ansi_lines(cells)
            ansi_output = '\n'.join(ansi_lines)
        
        # Build MEOW v0.6 file
        parts = []
        
        # Canvas block (optional but recommended)
        canvas_metadata = {
            "meow": MEOW_VERSION,
            "size": [width, height],
            "basis": list(self.basis_tuple),
        }
        canvas_json = json.dumps(canvas_metadata, separators=(',', ':'))
        parts.append(f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07')
        
        # Layer block with visible output
        parts.append(ansi_output)
        
        return ''.join(parts)
    
    def encode_animation(
        self,
        image_path: Union[str, Path],
        width: Optional[int] = None,
        height: Optional[int] = None,
        delay: Optional[int] = None,
    ) -> str:
        """
        Encode animated GIF to MEOW v0.6 format.
        
        Args:
            image_path: Path to animated GIF
            width: Output width in characters (default: terminal width)
            height: Output height in characters (default: auto from aspect)
            delay: Override frame delay in milliseconds (default: from GIF)
        
        Returns:
            MEOW v0.6 formatted string with frame metadata
        """
        with Image.open(image_path) as img:
            if not getattr(img, "is_animated", False):
                # Not animated, encode as static
                return self.encode_image(image_path, width, height)
            
            # Get animation info
            frame_count = getattr(img, 'n_frames', 1)
            default_delay = img.info.get('duration', 100)
            if delay is not None:
                default_delay = delay
            
            # Calculate dimensions from first frame
            img.seek(0)
            img_rgb = img.convert("RGB")
            
            if width is None:
                width = 80  # Default to 80 columns
            
            if height is None:
                image_aspect = img_rgb.height / img_rgb.width
                char_aspect = get_char_aspect()
                height = int(width * image_aspect / char_aspect)
            
            # Build MEOW v0.6 file
            parts = []
            
            # Canvas block with loop and size
            canvas_metadata = {
                "meow": MEOW_VERSION,
                "size": [width, height],
                "basis": list(self.basis_tuple),
                "loop": 0,  # Infinite loop
            }
            canvas_json = json.dumps(canvas_metadata, separators=(',', ':'))
            parts.append(f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07')
            
            # Encode each frame as a layer with frame number
            for frame_idx in range(frame_count):
                img.seek(frame_idx)
                frame_rgb = img.convert("RGB")
                
                # Convert to cells
                cells = image_to_cells(frame_rgb, width, height, basis=self.basis)
                
                # Generate ANSI output
                ansi_lines = cells_to_ansi_lines(cells)
                ansi_output = '\n'.join(ansi_lines)
                
                # Layer block with frame metadata
                layer_metadata = {
                    "f": frame_idx,
                    "delay": default_delay,
                }
                layer_json = json.dumps(layer_metadata, separators=(',', ':'))
                parts.append(f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07')
                parts.append(ansi_output)
                
                # Frame separator for cat viewing (visual divider)
                parts.append(f'\n\x1b[2m--- Frame {frame_idx + 1}/{frame_count} ---\x1b[0m\n')
            
            return ''.join(parts)


# Phase 2 TODO: Advanced encoder features
"""
## Phase 2+ Encoder Features (Deferred)

### Multi-Layer Encoding
- Layer detection from transparent PNGs
- Separate foreground/background layers
- Layer bounding boxes
- Layer IDs

### Translucency Support
- Alpha channel encoding
- Pre-melding for cat compatibility
- Alpha coefficient in layer metadata
- Visual centroid computation

### Cells Field Generation
- Dense ANSI string format
- Skip cell encoding (\\x1b[0m )
- Row-major cell order
- Conditional compression (gzip+base64)
- ctype field validation

### Metadata Compression
- Detect cells presence
- Automatic gzip compression
- Base64 encoding
- Size threshold logic

### Advanced Features
- Sparse visible output optimization
- Cursor positioning for efficiency
- Multiple canvas concatenation
- Layer reordering support
"""
