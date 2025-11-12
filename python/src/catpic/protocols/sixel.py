# Destination: src/catpic/protocols/sixel.py

"""
Sixel Graphics Protocol implementation.

Sixel is a bitmap graphics format supported by:
- xterm (with -ti vt340 or configure --enable-sixel-graphics)
- mlterm
- foot
- mintty (Windows)
- wezterm
- And many others

Sixel uses palette-based color with up to 256 colors.
"""

from PIL import Image
from io import BytesIO
from typing import Optional

from .base import ProtocolGenerator, ProtocolConfig


class SixelGenerator(ProtocolGenerator):
    """
    Generate Sixel graphics sequences.
    
    Sixel is a bitmap format that encodes 6 vertical pixels at a time
    using printable ASCII characters. It's widely supported across
    terminal emulators.
    """
    
    @property
    def protocol_name(self) -> str:
        """Return protocol name."""
        return "sixel"
    
    @property
    def can_optimize(self) -> bool:
        """Sixel doesn't support incremental updates."""
        return False
    
    def generate(self, png_data: bytes, config: Optional[ProtocolConfig] = None) -> bytes:
        """
        Generate Sixel graphics sequence from PNG data.
        
        Uses PIL's built-in Sixel support via libsixel if available,
        otherwise uses a basic implementation.
        
        Args:
            png_data: PNG image data
            config: Optional configuration (max_width, max_height, quality)
            
        Returns:
            Sixel escape sequence as bytes
        """
        if config is None:
            config = ProtocolConfig()
        
        # Load image
        img = Image.open(BytesIO(png_data))
        
        # Resize if needed
        if config.max_width or config.max_height:
            img = self._resize_image(img, config.max_width, config.max_height)
        
        # Convert to RGB (Sixel doesn't support transparency directly)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Quantize to 256 colors for Sixel palette
        # Most Sixel implementations support 256 colors max
        img_quantized = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
        
        # Try to use PIL's Sixel support (requires libsixel)
        try:
            sixel_buffer = BytesIO()
            img_quantized.save(sixel_buffer, format='SIXEL')
            sixel_data = sixel_buffer.getvalue()
            
            # Ensure it's wrapped in DCS (Device Control String)
            if not sixel_data.startswith(b'\x1bP'):
                sixel_data = b'\x1bPq' + sixel_data
            if not sixel_data.endswith(b'\x1b\\'):
                sixel_data = sixel_data + b'\x1b\\'
            
            return sixel_data
            
        except (OSError, KeyError, ValueError):
            # libsixel not available or save failed
            # Fall back to basic implementation
            return self._generate_basic_sixel(img_quantized)
    
    def _generate_basic_sixel(self, img: Image.Image) -> bytes:
        """
        Basic Sixel encoder without libsixel dependency.
        
        This is a simplified implementation that produces valid
        Sixel output for terminals without libsixel.
        
        Sixel format:
        - DCS: ESC P <params> q
        - Raster attributes: " <Pan> ; <Pad> ; <Ph> ; <Pv>
        - Color definitions: # <color> ; 2 ; <R> ; <G> ; <B>
        - Sixel data: # <color> <sixel-chars>
        - Line terminator: -
        - Carriage return: $
        - String terminator: ESC \
        
        Args:
            img: Quantized image (palette mode)
            
        Returns:
            Sixel escape sequence
        """
        if img.mode != 'P':
            img = img.quantize(colors=256)
        
        palette = img.getpalette()
        if palette is None:
            # No palette, convert to RGB and quantize
            img = img.convert('RGB').quantize(colors=256)
            palette = img.getpalette()
        
        width, height = img.size
        pixels = img.load()
        
        # Start Sixel sequence: DCS with parameters
        # P1=aspect ratio (typically omitted), P2=background mode (0=current color)
        parts = [b'\x1bPq']
        
        # Raster attributes: "<Pan>;<Pad>;<Ph>;<Pv>
        # Pan/Pad = pixel aspect ratio (1:1), Ph/Pv = width/height
        raster_attr = f'"1;1;{width};{height}'.encode('ascii')
        parts.append(raster_attr)
        
        # Define color palette
        # RGB values must be 0-100 (percentage, not 0-255!)
        palette_size = len(palette) // 3
        for i in range(palette_size):
            r = palette[i * 3] * 100 // 255
            g = palette[i * 3 + 1] * 100 // 255
            b = palette[i * 3 + 2] * 100 // 255
            color_def = f'#{i};2;{r};{g};{b}'.encode('ascii')
            parts.append(color_def)
        
        # Encode image data (6 vertical pixels at a time)
        for y in range(0, height, 6):
            first_color = True
            
            for color_idx in range(palette_size):
                # Build sixel data for this color in this band
                sixel_data = []
                
                for x in range(width):
                    sixel_char = 0
                    for bit in range(6):
                        py = y + bit
                        if py < height:
                            try:
                                if pixels[x, py] == color_idx:
                                    sixel_char |= (1 << bit)
                            except (IndexError, KeyError):
                                pass
                    
                    sixel_data.append(sixel_char)
                
                # Only output if this color is used in this band
                if any(c > 0 for c in sixel_data):
                    if not first_color:
                        # Return to start of line for next color
                        parts.append(b'$')
                    
                    # Select color
                    parts.append(f'#{color_idx}'.encode('ascii'))
                    
                    # Encode sixel data with run-length encoding
                    i = 0
                    while i < len(sixel_data):
                        char = sixel_data[i]
                        # Count repeats
                        count = 1
                        while i + count < len(sixel_data) and sixel_data[i + count] == char:
                            count += 1
                        
                        # Output with repeat count if > 3 (saves space)
                        if count > 3:
                            parts.append(f'!{count}'.encode('ascii'))
                            parts.append(bytes([63 + char]))
                        else:
                            # Just output the characters
                            for _ in range(count):
                                parts.append(bytes([63 + char]))
                        
                        i += count
                    
                    first_color = False
            
            # Move to next band (new line)
            if y + 6 < height:
                parts.append(b'-')
        
        # End Sixel sequence
        parts.append(b'\x1b\\')
        
        return b''.join(parts)
    
    def _resize_image(self, img: Image.Image, max_width: Optional[int], max_height: Optional[int]) -> Image.Image:
        """Resize image maintaining aspect ratio."""
        width, height = img.size
        
        if max_width and width > max_width:
            ratio = max_width / width
            width = max_width
            height = int(height * ratio)
        
        if max_height and height > max_height:
            ratio = max_height / height
            height = max_height
            width = int(width * ratio)
        
        if (width, height) != img.size:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        
        return img
