"""Core catpic functionality and constants."""

import os
from enum import Enum
from typing import Dict, List, Optional, Tuple

# MEOW v0.7 format constants
MEOW_VERSION = "0.7"
MEOW_OSC_NUMBER = 9876
MEOW_OSC_PREFIX = f"\x1b]{MEOW_OSC_NUMBER};"
MEOW_OSC_SUFFIX = "\x07"

# Default values for MEOW format
DEFAULT_BASIS = (2, 2)
DEFAULT_CANVAS_SIZE = (80, 24)
DEFAULT_ALPHA = 1.0
DEFAULT_FRAME_DELAY = 100  # milliseconds
DEFAULT_CHAR_ASPECT = 2.0  # Terminal characters are roughly 2:1 (height:width)
SUPPORTED_SOURCE_FORMATS = ["png"] # Protocol-related constants (v0.7)
DEFAULT_SOURCE_FORMAT = "png"

# Exit codes (MEOW v0.6 spec)
EXIT_SUCCESS = 0
EXIT_ERROR_GENERAL = 1
EXIT_ERROR_PARSE = 2
EXIT_ERROR_NO_CANVAS_SIZE = 3
EXIT_ERROR_INVALID_METADATA = 4
EXIT_ERROR_FILE_NOT_FOUND = 5
EXIT_ERROR_WRITE_ERROR = 6


class BASIS(Enum):
    """BASIS system for catpic quality levels."""
    
    BASIS_1_2 = (1, 2)  # 4 patterns - Universal compatibility
    BASIS_2_2 = (2, 2)  # 16 patterns - Balanced
    BASIS_2_3 = (2, 3)  # 64 patterns - High quality  
    BASIS_2_4 = (2, 4)  # 256 patterns - Ultra quality


def get_default_basis() -> BASIS:
    """
    Get default BASIS from environment variable or fallback.
    
    Reads CATPIC_BASIS environment variable (format: "2,2" or "2x2" or "2_2")
    Falls back to BASIS_2_2 if not set or invalid.
    
    Examples:
        export CATPIC_BASIS=2,4  # Use ultra quality
        export CATPIC_BASIS=1,2  # Use universal compatibility
    """
    env_basis = os.environ.get('CATPIC_BASIS', '').strip()
    
    if not env_basis:
        return BASIS.BASIS_2_2  # Default
    
    # Parse various formats: "2,2" or "2x2" or "2_2"
    for sep in [',', 'x', '_', ' ']:
        if sep in env_basis:
            parts = env_basis.split(sep)
            if len(parts) == 2:
                try:
                    x, y = int(parts[0]), int(parts[1])
                    # Map to BASIS enum
                    basis_map = {
                        (1, 2): BASIS.BASIS_1_2,
                        (2, 2): BASIS.BASIS_2_2,
                        (2, 3): BASIS.BASIS_2_3,
                        (2, 4): BASIS.BASIS_2_4,
                    }
                    if (x, y) in basis_map:
                        return basis_map[(x, y)]
                except ValueError:
                    pass
    
    # Invalid format, fall back to default
    return BASIS.BASIS_2_2

"""
Basis-aware aspect ratio correction system.

Each basis has different pixel arrangements that interact with terminal
font metrics differently. This matrix provides relative corrections.

The base aspect ratio (2.0) assumes a typical terminal where characters
are roughly 2x taller than wide. The corrections adjust for how different
basis configurations compress/stretch visuals.
"""

# Internal basis correction matrix
# Format: {(basis_x, basis_y): correction_multiplier}
# These are relative adjustments to the base aspect ratio (2.0)
# Values determined through visual tuning in typical terminal
BASIS_ASPECT_CORRECTIONS = {
    (1, 2): 2.0,    # 1x2: 2 vertical pixels - needs 2x correction (4.0 effective)
    (2, 2): 0.9,    # 2x2: 4 pixels in 2x2 grid - slight correction (1.8 effective)
    (2, 3): 1.5,    # 2x3: 6 pixels - moderate correction (3.0 effective)
    (2, 4): 2.0,    # 2x4: 8 pixels - strong correction (4.0 effective)
}

# Base aspect ratio for typical terminals (chars are ~2x taller than wide)
BASE_CHAR_ASPECT = 2.0


def get_char_aspect(basis: Optional[BASIS] = None) -> float:
    """
    Get character aspect ratio with basis-specific correction.
    
    Uses CATPIC_CONFIG for aspect ratios.
    
    Args:
        basis: BASIS enum value (if None, returns base aspect only)
    
    Returns:
        Corrected character aspect ratio for this basis
    """
    # Try to load from config
    try:
        from .config import load_config
        config = load_config()
        
        if basis is None:
            return config.get('aspect base', BASE_CHAR_ASPECT)
        
        # Get basis-specific aspect
        basis_x, basis_y = basis.value
        basis_key = f"aspect {basis_x}x{basis_y}"
        
        if basis_key in config:
            return config[basis_key]
        
        # Fall back to base aspect with internal correction
        base_aspect = config.get('aspect base', BASE_CHAR_ASPECT)
        correction = BASIS_ASPECT_CORRECTIONS.get((basis_x, basis_y), 1.0)
        return base_aspect * correction
        
    except Exception:
        # Config system not available, use legacy approach
        base_aspect = float(os.getenv('CATPIC_CHAR_ASPECT', BASE_CHAR_ASPECT))
        
        if basis is None:
            return base_aspect
        
        basis_x, basis_y = basis.value
        correction = BASIS_ASPECT_CORRECTIONS.get((basis_x, basis_y), 1.0)
        return base_aspect * correction

class CatpicCore:
    """Core catpic constants and Unicode character sets for mosaic encoding."""
    
    # Unicode block characters for different BASIS levels
    BLOCKS: Dict[BASIS, List[str]] = {
        BASIS.BASIS_1_2: [
            " ",  # Empty
            "▀",  # Upper half
            "▄",  # Lower half  
            "█",  # Full block
        ],
        
        BASIS.BASIS_2_2: [
            " ", "▘", "▝", "▀",  # 0000, 0001, 0010, 0011
            "▖", "▌", "▞", "▛",  # 0100, 0101, 0110, 0111
            "▗", "▚", "▐", "▜",  # 1000, 1001, 1010, 1011
            "▄", "▙", "▟", "█",  # 1100, 1101, 1110, 1111
        ],
        
        BASIS.BASIS_2_3: [
            " ", "🬀", "🬁", "🬂", "🬃", "🬄", "🬅", "🬆",
            "🬇", "🬈", "🬉", "🬊", "🬋", "🬌", "🬍", "🬎",
            "🬏", "🬐", "🬑", "🬒", "🬓", "🬔", "🬕", "🬖",
            "🬗", "🬘", "🬙", "🬚", "🬛", "🬜", "🬝", "🬞",
            "🬟", "🬠", "🬡", "🬢", "🬣", "🬤", "🬥", "🬦",
            "🬧", "🬨", "🬩", "🬪", "🬫", "🬬", "🬭", "🬮",
            "🬯", "🬰", "🬱", "🬲", "🬳", "🬴", "🬵", "🬶",
            "🬷", "🬸", "🬹", "🬺", "🬻", "▀", "▄", "█",
        ],
        
        # Sextant blocks (64 glyphs)
        BASIS.BASIS_2_3: list(
            " 🬀🬁🬂🬃🬄🬅🬆🬇🬈🬉🬊🬋🬌🬍🬎🬏🬐🬑🬒🬓▌🬔🬕🬖🬗🬘🬙🬚🬛🬜🬝🬞🬟🬠🬡🬢🬣🬤🬥🬦🬧▐🬨🬩🬪🬫🬬🬭🬮🬯🬰🬱🬲🬳🬴🬵🬶🬷🬸🬹🬺🬻█"
        ),

        # Octant blocks (256 glyphs)
        BASIS.BASIS_2_4: list(
            " 𜺨𜺫🮂𜴀▘𜴁𜴂𜴃𜴄▝𜴅𜴆𜴇𜴈▀𜴉𜴊𜴋𜴌🯦𜴍𜴎𜴏𜴐𜴑𜴒𜴓𜴔𜴕𜴖𜴗𜴘𜴙𜴚𜴛𜴜𜴝𜴞𜴟🯧𜴠𜴡𜴢𜴣𜴤𜴥𜴦𜴧𜴨𜴩𜴪𜴫𜴬𜴭𜴮𜴯𜴰𜴱𜴲𜴳𜴴𜴵🮅"
            "𜺣𜴶𜴷𜴸𜴹𜴺𜴻𜴼𜴽𜴾𜴿𜵀𜵁𜵂𜵃𜵄▖𜵅𜵆𜵇𜵈▌𜵉𜵊𜵋𜵌▞𜵍𜵎𜵏𜵐▛𜵑𜵒𜵓𜵔𜵕𜵖𜵗𜵘𜵙𜵚𜵛𜵜𜵝𜵞𜵟𜵠𜵡𜵢𜵣𜵤𜵥𜵦𜵧𜵨𜵩𜵪𜵫𜵬𜵭𜵮𜵯𜵰"
            "𜺠𜵱𜵲𜵳𜵴𜵵𜵶𜵷𜵸𜵹𜵺𜵻𜵼𜵽𜵾𜵿𜶀𜶁𜶂𜶃𜶄𜶅𜶆𜶇𜶈𜶉𜶊𜶋𜶌𜶍𜶎▗𜶏𜶐𜶑𜶒▚𜶓𜶔𜶕𜶖▐𜶗𜶘𜶙𜶚▜𜶛𜶜𜶝𜶞𜶟𜶠𜶡𜶢𜶣𜶤𜶥𜶦𜶧𜶨𜶩𜶪𜶫"
            "▂𜶬𜶭𜶮𜶯𜶰𜶱𜶲𜶳𜶴𜶵𜶶𜶷𜶸𜶹𜶺𜶻𜶼𜶽𜶾𜶿𜷀𜷁𜷂𜷃𜷄𜷅𜷆𜷇𜷈𜷉𜷊𜷋𜷌𜷍𜷎𜷏𜷐𜷑𜷒𜷓𜷔𜷕𜷖𜷗𜷘𜷙𜷚▄𜷛𜷜𜷝𜷞▙𜷟𜷠𜷡𜷢▟𜷣▆𜷤𜷥█"
        ),
    }
    
    # ANSI color format strings
    RESET = "\x1b[0m"
    FG_COLOR = "\x1b[38;2;{r};{g};{b}m"
    BG_COLOR = "\x1b[48;2;{r};{g};{b}m"
    
    @staticmethod
    def format_cell(char: str, fg_rgb: Tuple[int, int, int], bg_rgb: Tuple[int, int, int]) -> str:
        """Format a single cell with foreground/background colors."""
        fg_r, fg_g, fg_b = fg_rgb
        bg_r, bg_g, bg_b = bg_rgb
        
        return (
            f"\x1b[38;2;{fg_r};{fg_g};{fg_b}m"
            f"\x1b[48;2;{bg_r};{bg_g};{bg_b}m"
            f"{char}"
            f"\x1b[0m"
        )
    
    @staticmethod
    def get_basis_dimensions(basis: BASIS) -> Tuple[int, int]:
        """Get pixel dimensions for a BASIS level."""
        return basis.value


# Layer Zero and Footer Construction
# Single source of truth for MEOW file structure

import json as _json
from typing import Optional as _Optional


def build_layer_zero(canvas_metadata: dict, height: int) -> str:
    """
    Build layer zero structure for MEOW files.
    
    Layer zero reserves vertical space in the terminal and establishes
    a stable cursor origin for all visual layers.
    
    Args:
        canvas_metadata: Dictionary with canvas metadata (meow, size, basis, etc.)
        height: Canvas height in characters
    
    Returns:
        Layer zero string (single logical line)
    """
    canvas_json = _json.dumps(canvas_metadata, separators=(',', ':'), ensure_ascii=False)
    newlines = "\n" * height
    
    return (
        f'\x1b]{MEOW_OSC_NUMBER};{canvas_json}\x07'  # Canvas metadata (invisible)
        f'{newlines}'                                 # Reserve height lines
        f'\x1b[{height}A'                             # Move up to canvas top
        f'\x1b[s'                                     # Save cursor (origin)
    )


def build_footer(height: int) -> str:
    """
    Build footer for cursor cleanup.
    
    Args:
        height: Canvas height in characters
    
    Returns:
        Footer string (single line)
    """
    return f'\x1b[u\x1b[{height}B\n'
