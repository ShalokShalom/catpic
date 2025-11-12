# Python Implementation

The Python implementation is the reference implementation for catpic. It's stable, well-documented, and available on PyPI.

**Current version:** 0.9.0 (Release Candidate)

## Installation

### As a CLI Tool (Recommended)

For standalone command-line use:

```bash
uv tool install catpic
```

This installs `catpic` as an isolated tool, available system-wide.

### As a Library

To use catpic in your Python project:

```bash
# With pip
pip install catpic

# With uv
uv add catpic
```

**Requirements**: Python 3.9 or later

## Quick Start

### Command Line

```bash
# Display an image (auto-detects best protocol)
catpic photo.jpg

# Save as MEOW format
catpic photo.jpg -o photo.meow

# Play an animation
catpic animation.gif

# Force specific protocol
catpic photo.jpg --protocol kitty
catpic photo.jpg --protocol sixel
catpic photo.jpg --protocol iterm2
catpic photo.jpg --protocol glyxel

# Detect terminal capabilities
catpic --detect

# Show detailed information
catpic photo.jpg --info
```

See the [main README](README.md) for complete CLI documentation, graphics protocols, BASIS levels, and MEOW format details.

### Python API

#### High-Level API

```python
from catpic import render_image_ansi, save_meow, load_meow
from PIL import Image

# Render image to ANSI string (uses glyxel protocol)
img = Image.open('photo.jpg')
ansi = render_image_ansi(img, width=60, basis=(2, 4))
print(ansi)

# Save as MEOW file (includes multiple protocol data)
save_meow('output.meow', img, width=60, basis=(2, 4))

# Load MEOW file
frames, metadata = load_meow('output.meow')
print(frames[0])
```

#### Protocol API

```python
from catpic.protocols import get_generator, list_protocols
from catpic.detection import detect_best_protocol, get_detector
from catpic.protocols.core import encode_png
from PIL import Image

# List available protocols
protocols = list_protocols()  # ['glyxel', 'kitty', 'sixel', 'iterm2']

# Auto-detect best protocol
protocol = detect_best_protocol()  # Returns 'kitty', 'sixel', 'iterm2', or 'glyxel'

# Check specific protocol support
detector = get_detector()
if detector.supports_protocol('kitty'):
    print("Kitty graphics supported!")

# Generate protocol-specific output
img = Image.open('photo.jpg')
png_data = encode_png(img)

generator = get_generator('kitty')
kitty_output = generator.generate(png_data)
print(kitty_output.decode())  # Display with Kitty protocol

# Or use sixel
generator = get_generator('sixel')
sixel_output = generator.generate(png_data)
print(sixel_output.decode())  # Display with Sixel protocol
```

#### Primitives API

For TUI framework integration and advanced use cases:

```python
from catpic import (
    Cell, 
    get_full_glut, 
    get_pips_glut,
    image_to_cells, 
    cells_to_ansi_lines,
    BASIS
)
from PIL import Image

# Get character lookup table
glut = get_full_glut(BASIS.BASIS_2_4)

# Convert image to cell grid
img = Image.open('photo.jpg')
cells = image_to_cells(img, width=80, height=40, glut=glut)

# Cells is a 2D array of Cell objects
# Each Cell has: char, fg_rgb, bg_rgb, pattern

# Convert cells to ANSI
lines = cells_to_ansi_lines(cells)
print('\n'.join(lines))
```

## API Reference

### High-Level Functions

#### `render_image_ansi(image, width, height, basis, pips)`

Render an image to ANSI string for terminal display (using glyxel protocol).

**Parameters:**
- `image`: PIL Image object or path to image file
- `width`: Output width in characters (default: 80)
- `height`: Output height in characters (default: auto from aspect ratio)
- `basis`: BASIS level as tuple `(x, y)` - e.g., `(2, 2)`, `(2, 4)` (default: `(2, 2)`)
- `pips`: Use pip/dot characters instead of blocks (default: `False`)

**Returns:** ANSI-formatted string

#### `save_meow(filepath, image, width, height, basis)`

Save an image as MEOW format file (includes protocol data for multiple formats).

#### `load_meow(filepath)`

Load a MEOW format file.

**Returns:** Tuple of `(frames, metadata)`

### Protocol API

#### `get_generator(protocol: str) -> ProtocolGenerator`

Get a protocol generator instance.

**Parameters:**
- `protocol`: Protocol name - `'glyxel'`, `'kitty'`, `'sixel'`, `'iterm2'`

**Returns:** ProtocolGenerator instance

**Raises:** `ValueError` if protocol unknown

#### `list_protocols() -> list[str]`

List all available protocol names.

#### `detect_best_protocol() -> str`

Auto-detect the best available protocol for current terminal.

**Returns:** Protocol name (checks in order: kitty → iterm2 → sixel → glyxel)

#### `ProtocolGenerator.generate(png_data: bytes, config: ProtocolConfig) -> bytes`

Generate protocol-specific escape sequences.

**Parameters:**
- `png_data`: PNG-encoded image data
- `config`: Optional configuration (max_width, max_height, quality)

**Returns:** Protocol-specific escape sequence as bytes

### Primitives API

For complete primitives reference, see [docs/primitives_api.md](docs/primitives_api.md).

**Core types:**
- `Cell(char, fg_rgb, bg_rgb, pattern)` - Single terminal cell
- `BASIS` - Enum for basis levels

**Character tables:**
- `get_full_glut(basis)` - Full block characters
- `get_pips_glut(x, y)` - Pip/dot characters

**Image processing:**
- `image_to_cells(image, width, height, glut, basis)` - Convert image to cell grid
- `cells_to_ansi_lines(cells)` - Convert cells to ANSI strings

See [docs/primitives_api.md](docs/primitives_api.md) for complete details.

## Graphics Protocols

The Python implementation supports four graphics protocols:

### Kitty Graphics Protocol
- **Best for:** Kitty terminal
- **Quality:** Excellent (true-color, no quantization)
- **Speed:** Very fast (native protocol)
- **Detection:** `KITTY_WINDOW_ID` environment variable

### iTerm2 Inline Images
- **Best for:** iTerm2, VSCode (with settings), WezTerm, Tabby
- **Quality:** Excellent (base64 PNG)
- **Speed:** Very fast
- **Detection:** `TERM_PROGRAM=iTerm.app` or `LC_TERMINAL=iTerm2`

### Sixel Graphics
- **Best for:** xterm, mlterm, foot, many others
- **Quality:** Good (256-color palette)
- **Speed:** Fast
- **Detection:** `$TERM` heuristics (xterm, mlterm, foot, etc.)
- **Note:** Requires terminal with Sixel support enabled

### Glyxel (Unicode Mosaic)
- **Best for:** Any terminal
- **Quality:** Fair (depends on BASIS level)
- **Speed:** Fast
- **Detection:** Always available (universal fallback)

See the [main README](README.md) for terminal configuration and troubleshooting.

## Performance

### Default (PIL only)
- Static image: ~500-1000ms for 80×24 render
- Animation: 2-3fps
- Adequate for most terminal use cases

### Optional Acceleration with Numba

Install Numba for 2-3x speedup:

```bash
pip install catpic[fast]
# or
pip install numba
```

With Numba:
- Static image: ~200-300ms
- Animation: 5-10fps
- JIT compilation to native code
- CUDA support if GPU available

Numba is **optional** - catpic works without it.

## Dependencies

### Required
- **pillow** (≥9.0.0) - Image loading and processing
- **click** (≥8.0.0) - CLI interface

### Optional
- **numba** (≥0.56.0) - JIT acceleration (install with `[fast]` extra)

### Development
- **pytest** - Testing
- **black** - Formatting
- **ruff** - Linting
- **mypy** - Type checking

## Development

### Setup

```bash
git clone https://github.com/friscorose/catpic
cd catpic/python
uv sync --all-extras
```

### Running Tests

```bash
# All tests
uv run pytest -v

# Specific protocol tests
uv run pytest tests/test_protocols_kitty.py -v
uv run pytest tests/test_protocols_sixel.py -v
uv run pytest tests/test_protocols_iterm2.py -v

# Detection tests
uv run pytest tests/test_detection.py -v
```

### Building

The build process automatically includes shared documentation:

```bash
# Build wheel (includes docs/ and spec/ directories)
uv build

# Publish to PyPI
uv publish
```

After installation, users have offline access to:
- Python-specific documentation (`IMPLEMENTATION.md`)
- Shared reference docs (`docs/primitives_api.md`, etc.)
- Format specifications (`spec/meow_format.md`, etc.)

## Python-Specific Features

- **Native PIL Image support** - Pass Image objects directly to functions
- **Type hints** - Full type coverage for IDE support
- **Optional Numba acceleration** - Install with `[fast]` extra for speedup
- **Protocol abstraction** - Clean API for working with multiple graphics protocols
- **Auto-detection** - Automatically selects best protocol for current terminal
- **Clean exception handling** - Clear error messages for common issues

## Troubleshooting

### Python-Specific Issues

**ImportError: No module named 'catpic'**
- Ensure installation: `pip install catpic` or `uv tool install catpic`
- Check Python version: `python --version` (requires 3.9+)

**ModuleNotFoundError: No module named 'PIL'**
- Pillow not installed: `pip install pillow`
- Usually auto-installed with catpic

**Slow rendering / Poor animation performance**
- Install Numba: `pip install catpic[fast]`
- Check CPU usage during render
- Try lower BASIS level: `--basis 2,2` instead of `2,4`

**Protocol detection returns wrong protocol**
- Force specific protocol: `catpic --protocol <name>`
- Check environment: `catpic --detect`
- Verify terminal configuration (see main README)

For terminal configuration and graphics protocol issues, see the [main README](README.md) Troubleshooting section.

## Compatibility

### Python Versions
- Python 3.9+ (tested on 3.9, 3.10, 3.11, 3.12)

### Platforms
- Linux (all distributions)
- macOS (Intel and Apple Silicon)
- Windows (WSL, Windows Terminal, PowerShell)

## See Also

- [Project overview](README.md) - Graphics protocols, BASIS system, MEOW format, troubleshooting
- [Primitives API reference](docs/primitives_api.md) - Complete low-level API
- [MEOW format specification](spec/meow_v09_specification.md) - Format details
- [API specification](spec/api.md) - Cross-language API consistency
- [Getting started guide](docs/getting-started.md) - Tutorials and examples

## Version History

- **0.9.0** (2025-11) - Release candidate: Four graphics protocols (Kitty, Sixel, iTerm2, Glyxel), auto-detection, unified configuration
- **0.7.0** (2025-11) - Protocol foundation: Kitty and Sixel support, capability detection
- **0.6.0** (2025-10) - MEOW v0.6: Dual content encoding, animation support
- **0.5.0** (2025-09) - Initial PyPI release: Core glyxel rendering, BASIS system
