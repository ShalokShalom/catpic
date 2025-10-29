"""
MEOW v0.6 Layer Encoding - Core Infrastructure

Provides primitives for layer-based composition supporting both:
1. Simple concatenation (cat file1.meow file2.meow)
2. Advanced composition (translucency, optimization)
"""

import json
from dataclasses import dataclass
from typing import Optional

from PIL import Image

from .core import (
    BASIS, MEOW_VERSION, MEOW_OSC_NUMBER,
    get_char_aspect, build_layer_zero, build_footer
)
from .primitives import image_to_cells, cells_to_ansi_lines


@dataclass
class LayerSpec:
    """
    Specification for a single layer.
    
    Attributes:
        image: PIL Image object
        id: Unique identifier for the layer
        box: Position and size (x, y, dx, dy) in character coordinates
        alpha: Translucency coefficient (0.0 = transparent, 1.0 = opaque)
        frame: Frame number for animation (None = static)
        delay: Frame delay in milliseconds (for animation)
        rotation: Rotation in degrees (Phase 3+)
        scale: Scale factor (Phase 3+)
        blend_mode: Blend mode for composition (Phase 3+)
    """
    image: Image.Image
    id: str
    box: tuple[int, int, int, int]  # (x, y, dx, dy)
    alpha: float = 1.0
    frame: Optional[int] = None
    delay: Optional[int] = None
    
    # Future transformation support (Phase 3+)
    rotation: float = 0.0
    scale: float = 1.0
    blend_mode: str = 'normal'
    
    def __post_init__(self):
        """Validate layer specification."""
        # Clamp alpha to valid range
        if self.alpha < 0.0:
            self.alpha = 0.0
        elif self.alpha > 1.0:
            self.alpha = 1.0
        
        # Validate box
        x, y, dx, dy = self.box
        if dx <= 0 or dy <= 0:
            raise ValueError(f"Layer box must have positive dimensions: {self.box}")
        if x < 0 or y < 0:
            raise ValueError(f"Layer box must have non-negative position: {self.box}")
    
    def get_metadata(self) -> dict:
        """
        Generate layer metadata dictionary for MEOW format.
        
        Returns:
            Dictionary with layer metadata fields
        """
        x, y, dx, dy = self.box
        metadata = {
            "id": self.id,
            "box": {"x": x, "y": y, "dx": dx, "dy": dy},
            "α": self.alpha,
        }
        
        # Add optional fields
        if self.frame is not None:
            metadata["f"] = self.frame
        if self.delay is not None:
            metadata["delay"] = self.delay
        
        return metadata


class LayerEncoder:
    """
    Encode individual layers as standalone MEOW blocks.
    
    Designed for concatenation workflow:
        catpic img1.jpg -o layer1.meow
        catpic img2.png -o layer2.meow
        cat layer1.meow layer2.meow > composed.meow
    
    Each encoded layer is a complete, self-contained MEOW block
    that can be concatenated with other layers.
    """
    
    def __init__(self, basis: BASIS):
        """
        Initialize layer encoder.
        
        Args:
            basis: BASIS level for encoding
        """
        self.basis = basis
        self.basis_tuple = basis.value
    
    def encode_layer(
        self,
        spec: LayerSpec,
        ctype: str = "ansi-art",
        is_first_layer: bool = False,
    ) -> str:
        """
        Encode a single layer as a MEOW block.
        
        Args:
            spec: Layer specification
            ctype: Content type (ansi-art, ansi-art+cells, etc.)
            is_first_layer: If False, starts with cursor restore
        
        Returns:
            MEOW formatted string with layer block and ANSI output
        """
        # Extract box dimensions
        x, y, dx, dy = spec.box
        
        # Resize image to fit layer box
        # Account for character aspect ratio
        char_aspect = get_char_aspect()
        target_pixel_width = int(dx * self.basis_tuple[0])
        target_pixel_height = int(dy * self.basis_tuple[1] * char_aspect)
        
        # Convert image to cells
        resized = spec.image.resize(
            (target_pixel_width, target_pixel_height),
            Image.Resampling.LANCZOS
        )
        cells = image_to_cells(resized, dx, dy, basis=self.basis)
        
        # Generate ANSI output
        ansi_lines = cells_to_ansi_lines(cells)
        
        # Build positioned output
        positioned_lines = []
        
        # All layers (except when explicitly first) restore to saved origin
        if not is_first_layer:
            # Restore cursor to saved origin
            positioned_lines.append('\x1b[u')
        
        # Move to layer position using relative positioning
        if y > 0:
            positioned_lines.append(f'\x1b[{y}B')  # Down y rows
        if x > 0:
            positioned_lines.append(f'\x1b[{x}C')  # Right x columns
        
        # Output each line of the layer
        for i, line in enumerate(ansi_lines):
            if i > 0:
                # Move to next row, return to layer x position
                positioned_lines.append('\x1b[B')  # Down 1 row
                positioned_lines.append('\x1b[G')  # Return to column 1
                if x > 0:
                    positioned_lines.append(f'\x1b[{x}C')  # Right x columns
            positioned_lines.append(line)
        
        ansi_output = ''.join(positioned_lines)
        
        # Build MEOW layer block
        layer_metadata = spec.get_metadata()
        layer_metadata["ctype"] = ctype
        layer_json = json.dumps(layer_metadata, separators=(',', ':'), ensure_ascii=False)
        
        parts = [
            f'\x1b]{MEOW_OSC_NUMBER};{layer_json}\x07',
            ansi_output
        ]
        
        return ''.join(parts)
    
    def encode_layer_with_canvas(
        self,
        spec: LayerSpec,
        canvas_size: tuple[int, int],
        loop: Optional[int] = None,
        meld: bool = False,
    ) -> str:
        """
        Encode a layer with canvas metadata block (layer zero).
        
        Layer zero structure:
        - Canvas metadata OSC
        - Height newlines (forces terminal scroll, reserves space)
        - Move up to canvas top
        - Save cursor at top
        
        This ensures canvas always displays fully even near terminal bottom.
        
        Args:
            spec: Layer specification
            canvas_size: Canvas size (width, height) in characters
            loop: Loop count for animation (0 = infinite, None = no loop)
            meld: Whether to enable melding for translucent layers
        
        Returns:
            MEOW formatted string with layer zero and visual layer
        """
        width, height = canvas_size
        
        # Build canvas metadata
        canvas_metadata = {
            "meow": MEOW_VERSION,
            "size": [width, height],
            "basis": list(self.basis_tuple),
        }
        
        if meld:
            canvas_metadata["meld"] = True
        if loop is not None:
            canvas_metadata["loop"] = loop
        
        # Encode visual layer
        layer_block = self.encode_layer(spec, is_first_layer=False)
        
        # Combine layer zero + visual layer + footer
        parts = [
            build_layer_zero(canvas_metadata, height),
            layer_block,
            build_footer(height)
        ]
        
        return ''.join(parts)


class LayerComposer:
    """
    Compose multiple layers with advanced features.
    
    Phase 2A: Basic concatenation wrapper
    Phase 2B: Translucency melding, optimization
    Phase 3+: Transformations (rotation, scaling), blend modes
    """
    
    def __init__(self, basis: BASIS, canvas_size: tuple[int, int]):
        """
        Initialize layer composer.
        
        Args:
            basis: BASIS level for encoding
            canvas_size: Canvas size (width, height) in characters
        """
        self.basis = basis
        self.canvas_size = canvas_size
        self.layers: list[LayerSpec] = []
        self.encoder = LayerEncoder(basis)
    
    def add_layer(self, spec: LayerSpec):
        """
        Add a layer to the composition.
        
        Layers are composed in the order they are added.
        First layer = bottom, last layer = top (stream order = Z-order).
        
        Args:
            spec: Layer specification
        """
        # Validate layer fits in canvas
        x, y, dx, dy = spec.box
        canvas_width, canvas_height = self.canvas_size
        
        if x + dx > canvas_width:
            raise ValueError(
                f"Layer '{spec.id}' extends beyond canvas width: "
                f"{x + dx} > {canvas_width}"
            )
        if y + dy > canvas_height:
            raise ValueError(
                f"Layer '{spec.id}' extends beyond canvas height: "
                f"{y + dy} > {canvas_height}"
            )
        
        self.layers.append(spec)
    
    def render(
        self,
        meld: bool = False,
        loop: Optional[int] = None,
    ) -> str:
        """
        Render composed layers to MEOW format with layer zero.
        
        Layer zero structure:
        - Canvas metadata OSC
        - Height newlines (forces terminal scroll, reserves space)
        - Move up to canvas top
        - Save cursor at top
        
        Visual layers use cursor restore + relative positioning from saved origin.
        Footer restores cursor to bottom and adds final newline.
        
        Phase 2A: Simple concatenation of layer blocks
        Phase 2B: Translucency melding when meld=True
        
        Args:
            meld: If True, pre-meld translucent layers (Phase 2B)
            loop: Loop count for animation (0 = infinite, None = static)
        
        Returns:
            MEOW formatted string with layer zero and all visual layers
        """
        if not self.layers:
            raise ValueError("No layers added to composition")
        
        parts = []
        
        width, height = self.canvas_size
        canvas_metadata = {
            "meow": MEOW_VERSION,
            "size": [width, height],
            "basis": list(self.basis.value),
        }
        
        if meld:
            canvas_metadata["meld"] = True
        if loop is not None:
            canvas_metadata["loop"] = loop
        
        parts.append(build_layer_zero(canvas_metadata, height))
        
        # Encode each visual layer in order (first = bottom)
        for layer_spec in self.layers:
            layer_block = self.encoder.encode_layer(layer_spec, is_first_layer=False)
            parts.append(layer_block)
        
        parts.append(build_footer(height))
        
        return ''.join(parts)
    
    def clear(self):
        """Clear all layers from composition."""
        self.layers.clear()


# Phase 2B TODO: Translucency melding
"""
When meld=True, pre-compose translucent layers:
1. Render bottom layer to pixel buffer
2. For each translucent layer above:
   - Render layer to pixel buffer
   - Alpha blend with buffer below
3. Convert final buffer to cells/ANSI
4. Output as single melded layer

This produces cat-compatible output but loses layer independence.
"""

# Phase 3+ TODO: Transformations
"""
Support rotation, scaling, blend modes:
- encoder_transforms.py module
- Rotate/scale image before layer encoding
- Blend modes: normal, multiply, overlay, screen, etc.
- Visual centroid computation for rotation anchor
"""
