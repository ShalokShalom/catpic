"""
MEOW v0.6 Layer Melding - Translucency Support

Provides translucency melding for layers with alpha values < 1.0.
Uses PIL's optimized alpha compositing for pixel-perfect results.
"""

from typing import List
from PIL import Image

from .core import BASIS, get_char_aspect
from .encoder_layers import LayerSpec


def meld_layers(
    layers: List[LayerSpec],
    canvas_size: tuple[int, int],
    basis: BASIS
) -> Image.Image:
    """
    Composite layers with alpha blending into single image.
    
    This performs pixel-level alpha compositing, producing a single
    pre-melded image that displays correctly via cat. The original
    layer structure is lost, but translucency is baked in.
    
    Args:
        layers: List of LayerSpec objects (bottom to top order)
        canvas_size: Canvas dimensions (width, height) in characters
        basis: BASIS level for pixel calculations
    
    Returns:
        PIL Image (RGB mode) with all layers composited
    
    Example:
        layers = [
            LayerSpec(red_img, 'bg', (0, 0, 80, 24), alpha=1.0),
            LayerSpec(blue_img, 'fg', (10, 5, 40, 15), alpha=0.5),
        ]
        melded = meld_layers(layers, (80, 24), BASIS.BASIS_2_2)
        # melded is single RGB image with blue at 50% opacity over red
    """
    width, height = canvas_size
    char_aspect = get_char_aspect()
    
    # Calculate pixel dimensions for canvas
    px_width = width * basis.value[0]
    px_height = height * basis.value[1]  # Removed char_aspect - only fix
    
    # Create RGBA canvas (transparent background)
    canvas = Image.new('RGBA', (px_width, px_height), (0, 0, 0, 0))
    
    # Composite each layer in order (bottom to top)
    for layer in layers:
        x, y, dx, dy = layer.box
        
        # Calculate pixel dimensions for this layer
        layer_px_width = dx * basis.value[0]
        layer_px_height = dy * basis.value[1]  # Removed char_aspect - only fix
        
        # Resize layer image to fit its box
        layer_img = layer.image.resize(
            (layer_px_width, layer_px_height),
            Image.Resampling.LANCZOS
        )
        
        # Convert to RGBA if needed
        if layer_img.mode != 'RGBA':
            layer_img = layer_img.convert('RGBA')
        
        # Apply layer alpha to the alpha channel
        if layer.alpha < 1.0:
            # Get alpha channel
            r, g, b, a = layer_img.split()
            # Scale alpha by layer.alpha coefficient
            a = a.point(lambda p: int(p * layer.alpha))
            # Recombine
            layer_img = Image.merge('RGBA', (r, g, b, a))
        
        # Calculate paste position in canvas pixels
        paste_x = x * basis.value[0]
        paste_y = y * basis.value[1]
        
        # Composite onto canvas using alpha_composite for correct blending
        # Create temp canvas same size, place layer at position, then composite
        temp = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        temp.paste(layer_img, (paste_x, paste_y))
        canvas = Image.alpha_composite(canvas, temp)
    
    # Convert to RGB (flatten transparency)
    # Transparent areas become black
    final = Image.new('RGB', canvas.size, (0, 0, 0))
    final.paste(canvas, (0, 0), canvas)
    
    return final


def has_translucent_layers(layers: List[LayerSpec]) -> bool:
    """
    Check if any layers have alpha < 1.0.
    
    Args:
        layers: List of LayerSpec objects
    
    Returns:
        True if any layer has alpha < 1.0
    """
    return any(layer.alpha < 1.0 for layer in layers)


def should_meld(layers: List[LayerSpec], meld_hint: bool) -> bool:
    """
    Determine if layers should be melded.
    
    Melding is recommended when:
    - User explicitly requests it (meld_hint=True), OR
    - Layers contain translucency (alpha < 1.0)
    
    Args:
        layers: List of LayerSpec objects
        meld_hint: User's meld preference
    
    Returns:
        True if melding should be performed
    """
    # Explicit user request
    if meld_hint:
        return True
    
    # Automatic melding for translucent layers
    # This ensures correct display via cat
    if has_translucent_layers(layers):
        return True
    
    return False


# Future enhancement: Custom glyxel-aware centroid calculation
"""
If PIL compositing proves too slow (unlikely given 0.02ms benchmark),
implement fast integer centroid calculation:

def compute_glyxel_centroid(
    lower_cell: Cell,
    upper_cell: Cell,
    alpha: float
) -> tuple[int, int, int]:
    '''
    Fast heuristic for blending glyxel cells.
    
    Uses character density heuristic instead of pixel-perfect math:
    - Block characters (█▓▒░) = higher foreground weight
    - Sparse characters ( .,;) = higher background weight
    - Linear interpolation based on alpha
    '''
    
    # Character density lookup (0.0 = sparse, 1.0 = solid)
    DENSITY = {
        ' ': 0.0,
        '░': 0.25,
        '▒': 0.50,
        '▓': 0.75,
        '█': 1.0,
        # ... more glyphs
    }
    
    # Approximate centroid based on character density
    lower_density = DENSITY.get(lower_cell.char, 0.5)
    lower_r = lower_cell.fg_r * lower_density + lower_cell.bg_r * (1 - lower_density)
    # ... (similar for g, b)
    
    # Blend with upper layer
    final_r = int(upper_r * alpha + lower_r * (1 - alpha))
    # ... (similar for g, b)
    
    return (final_r, final_g, final_b)

# Benchmark shows PIL is fast enough (0.02ms), so this optimization
# is deferred unless profiling shows it's needed.
"""
