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


#def get_char_aspect() -> float:
#    """
#    get terminal character aspect ratio from environment or default.
#    
#    terminal characters are typically taller than wide. common values:
#    - 2.0: most terminals (default)
#    - 1.8: some wider fonts
#    - 2.2: some narrower fonts
#    
#    environment:
#        catpic_char_aspect: float value (e.g., "2.0", "1.8")
#    
#    returns:
#        character aspect ratio (height / width)
#    """
#    aspect_env = os.getenv('catpic_char_aspect')
#    if not aspect_env:
#        return default_char_aspect
#    
#    try:
#        aspect = float(aspect_env)
#        # sanity check: reasonable range
#        if 1.0 <= aspect <= 3.0:
#            return aspect
#    except (valueerror, typeerror):
#        pass
#    
#    return default_char_aspect


# Destination: src/catpic/core.py (UPDATE - add to existing file)

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
    
    Resolution order:
    1. Basis-specific env var (CATPIC_CHAR_ASPECT_2x4)
    2. Global env var (CATPIC_CHAR_ASPECT)
    3. Internal correction matrix
    4. Hardcoded default (2.0)
    
    Args:
        basis: BASIS enum value (if None, returns base aspect only)
    
    Returns:
        Corrected character aspect ratio for this basis
    """
    import os
    
    # Start with base aspect
    base_aspect = float(os.getenv('CATPIC_CHAR_ASPECT', BASE_CHAR_ASPECT))
    
    # If no basis specified, return base only
    if basis is None:
        return base_aspect
    
    # Check for basis-specific override
    basis_x, basis_y = basis.value
    basis_key = f"CATPIC_CHAR_ASPECT_{basis_x}x{basis_y}"
    basis_override = os.getenv(basis_key)
    
    if basis_override:
        return float(basis_override)
    
    # Apply internal correction matrix
    correction = BASIS_ASPECT_CORRECTIONS.get((basis_x, basis_y), 1.0)
    return base_aspect * correction


# Update existing get_char_aspect() function with this new implementation
# Remove the old simple version that just reads CATPIC_CHAR_ASPECT
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
