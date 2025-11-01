"""
Common utilities for protocol generation.

Provides shared functions for image processing used across
multiple protocol implementations. Protocols can use these
utilities or bypass them for optimization.
"""

import io
from typing import Tuple, Optional

from PIL import Image


def decode_png(png_bytes: bytes) -> Image.Image:
    """
    Decode PNG bytes to PIL Image.
    
    Args:
        png_bytes: PNG image data
    
    Returns:
        PIL Image object
    
    Raises:
        ValueError: If PNG is invalid
    """
    try:
        return Image.open(io.BytesIO(png_bytes))
    except Exception as e:
        raise ValueError(f"Invalid PNG data: {e}")


def encode_png(img: Image.Image, compress_level: int = 6) -> bytes:
    """
    Encode PIL Image to PNG bytes.
    
    Args:
        img: PIL Image object
        compress_level: PNG compression level (0-9, higher = smaller/slower)
    
    Returns:
        PNG image bytes
    """
    buf = io.BytesIO()
    img.save(buf, format='PNG', compress_level=compress_level)
    return buf.getvalue()


def resize_if_needed(
    img: Image.Image,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    preserve_aspect: bool = True,
) -> Image.Image:
    """
    Resize image if it exceeds maximum dimensions.
    
    Args:
        img: Source image
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        preserve_aspect: Maintain aspect ratio
    
    Returns:
        Resized image (or original if within limits)
    """
    if not (max_width or max_height):
        return img
    
    w, h = img.size
    
    # Calculate target dimensions
    target_w, target_h = w, h
    
    if max_width and w > max_width:
        target_w = max_width
        if preserve_aspect:
            target_h = int(h * max_width / w)
    
    if max_height and target_h > max_height:
        target_h = max_height
        if preserve_aspect:
            target_w = int(w * max_height / h)
    
    # Only resize if dimensions changed
    if (target_w, target_h) != (w, h):
        return img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    return img


def convert_to_rgb(img: Image.Image) -> Image.Image:
    """
    Convert image to RGB mode (remove alpha channel).
    
    Used by protocols that don't support transparency (e.g., Sixel).
    
    Args:
        img: Source image
    
    Returns:
        RGB image with white background
    """
    if img.mode == 'RGBA':
        # Create white background
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])  # Alpha channel as mask
        return bg
    elif img.mode != 'RGB':
        return img.convert('RGB')
    return img


def convert_to_rgba(img: Image.Image) -> Image.Image:
    """
    Convert image to RGBA mode (ensure alpha channel).
    
    Used by protocols that require alpha channel.
    
    Args:
        img: Source image
    
    Returns:
        RGBA image
    """
    if img.mode != 'RGBA':
        return img.convert('RGBA')
    return img


def get_pixel_data(img: Image.Image) -> Tuple[bytes, Tuple[int, int], str]:
    """
    Extract raw pixel data from image.
    
    Args:
        img: PIL Image
    
    Returns:
        Tuple of (pixel_bytes, (width, height), mode)
    """
    return img.tobytes(), img.size, img.mode
