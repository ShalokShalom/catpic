"""
MEOW v0.6 Encoder - Core functionality

Phase 1: Essential single-layer encoding
Phase 2 TODO: Multi-layer, animation, translucency, cells compression
"""

import json
from pathlib import Path
from typing import Optional, Union, Tuple

from PIL import Image

from .core import BASIS, CatpicCore, MEOW_VERSION, MEOW_OSC_NUMBER, DEFAULT_BASIS
from .primitives import image_to_cells, cells_to_ansi_lines


class CatpicEncoder:
    """
    Encode images to MEOW v0.6 format.
    
    Phase 1: Single-layer static images with v0.6 metadata
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
            width: Output width in characters (default: 80)
            height: Output height in characters (default: auto from aspect ratio)
        
        Returns:
            MEOW v0.6 formatted string with OSC 9876 metadata
        
        Phase 1: Single layer, no cells field, pre-rendered visible output
        """
        # Load image
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            
            # Calculate dimensions
            if width is None:
                width = 80
            
            if height is None:
                # Maintain aspect ratio
                aspect = img.height / img.width
                basis_x, basis_y = self.basis_tuple
                cell_aspect = basis_y / basis_x
                height = int(width * aspect / cell_aspect)
            
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
        # Phase 1: No layer metadata, just pure ANSI output
        # (Valid per spec: "Minimal Valid File" section)
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
        
        Phase 1: Basic implementation - encodes first frame only
        Phase 2 TODO: Multi-frame with proper frame metadata
        
        Args:
            image_path: Path to animated GIF
            width: Output width in characters
            height: Output height in characters
            delay: Frame delay in milliseconds (default: from GIF)
        
        Returns:
            MEOW v0.6 formatted string
        """
        with Image.open(image_path) as img:
            if not getattr(img, "is_animated", False):
                # Not animated, encode as static
                return self.encode_image(image_path, width, height)
            
            # Phase 1: Just encode first frame
            # TODO Phase 2: Implement full animation with frame metadata
            img.seek(0)
            
            # Get delay from GIF if not specified
            if delay is None:
                delay = img.info.get('duration', 100)
            
            # Save first frame to temp and encode
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                img.convert('RGB').save(tmp.name)
                result = self.encode_image(tmp.name, width, height)
            
            Path(tmp.name).unlink()
            
            # Add animation hint in canvas metadata
            # Phase 1: Just add loop field
            # TODO Phase 2: Add proper frame layers
            result = result.replace(
                '"basis"',
                f'"loop":0,"basis"',  # loop=0 means infinite
                1  # Replace only first occurrence
            )
            
            return result


# Phase 2 TODO: Advanced encoder features
"""
## Phase 2 Encoder Features (Deferred)

### Multi-Layer Encoding
- Layer detection from transparent PNGs
- Separate foreground/background layers
- Layer bounding boxes
- Layer IDs

### Animation Encoding
- Proper frame-based layer blocks
- Frame metadata with 'f' field
- Per-frame delay timing
- Static + animated layer composition
- Frame optimization (only changed regions)

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

### Implementation Files Needed
- src/catpic/encoder_layers.py - Multi-layer logic
- src/catpic/encoder_animation.py - Frame handling
- src/catpic/encoder_cells.py - Cells field generation
- src/catpic/encoder_compression.py - Metadata compression

### Tests Needed
- tests/test_encoder_v06_layers.py
- tests/test_encoder_v06_animation.py
- tests/test_encoder_v06_cells.py
- tests/test_encoder_v06_compression.py
"""
