# Python Implementation

The Python implementation is the reference implementation for catpic. It's stable, well-documented, and available on PyPI.

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

**Requirements**: Python 3.8 or later

## Quick Start

### Command Line

```bash
# Display an image
catpic photo.jpg

# Save as MEOW format
catpic photo.jpg -o photo.meow

# Play an animation
catpic animation.gif
```

See the [main README](README.md) for complete CLI documentation, BASIS levels, and MEOW format details.

### Python API

#### High-Level API

```python
from catpic import render_image_ansi, save_meow, load_meow
from PIL import Image

# Render image to ANSI string
img = Image.open('photo.jpg')
ansi = render_image_ansi(img, width=60, basis=(2, 4))
print(ansi)

# Save as MEOW file
save_meow('output.meow', img, width=60, basis=(2, 4))

# Load MEOW file
frames, metadata = load_meow('output.meow')
print(frames[0])
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

Render an image to ANSI string for terminal display.

**Parameters:**
- `image`: PIL Image object or path to image file
- `width`: Output width in characters (default: 80)
- `height`: Output height in characters (default: auto from aspect ratio)
- `basis`: BASIS level as tuple `(x, y)` - e.g., `(2, 2)`, `(2, 4)` (default: `(2, 2)`)
- `pips`: Use pip/dot characters instead of blocks (default: `False`)

**Returns:** ANSI-formatted string

#### `save_meow(filepath, image, width, height, basis)`

Save an image as MEOW format file.

#### `load_meow(filepath)`

Load a MEOW format file.

**Returns:** Tuple of `(frames, metadata)`

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
uv run pytest -v
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
- **Clean exception handling** - Clear error messages for common issues

## Compatibility

### Python Versions
- Python 3.8+ (tested on 3.8, 3.9, 3.10, 3.11, 3.12)

### Platforms
- Linux (all distributions)
- macOS (Intel and Apple Silicon)
- Windows (WSL, Windows Terminal, PowerShell)

## See Also

- [Project overview](README.md) - BASIS system, MEOW format, environment variables
- [Primitives API reference](docs/primitives_api.md) - Complete low-level API
- [MEOW format specification](spec/meow_format.md) - Format details
- [API specification](spec/api.md) - Cross-language API consistency
- [Getting started guide](docs/getting-started.md) - Tutorials and examples
