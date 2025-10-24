# catpic

Turn images into terminal eye candy using Unicode mosaics and ANSI colors.

**The twist:** Save as MEOW format and display with `cat`. Yes, the POSIX command. No special viewer needed.

```bash
catpic photo.jpg -o photo.meow
cat photo.meow  # 🐱 Just works
```

## What are Glyxels?

**Glyxels** (glyph + pixels) are what happens when you treat each terminal character as a tiny canvas. catpic uses the EnGlyph algorithm to subdivide characters into grids—for example, BASIS 2×4 means each character represents 8 glyxels (2 wide, 4 tall).

The magic:
1. Slice your image into character-sized cells
2. Find the two most important colors in each cell
3. Pick the Unicode character that matches the glyxel pattern
4. Paint it with ANSI true-color

Result? A standard 80×24 terminal becomes a 160×96 glyxel display. Not bad for text.

## Features

- **`cat`-compatible format**: MEOW files display with standard POSIX `cat`
- **Multiple BASIS levels**: Trade speed for quality (1×2 to 2×4)
- **Smooth animations**: GIF playback with no flicker
- **Primitives API**: Build your own TUI graphics with composable functions
- **Environment aware**: Automatic terminal size and aspect ratio detection
- **Multi-language**: Python (stable), C (in development), Rust/Go (planned)

## Installation & Usage

**See [IMPLEMENTATION.md](IMPLEMENTATION.md) for installation instructions and API documentation for your language.**

Each implementation provides the same core functionality with language-appropriate APIs and conventions.

## Environment Variables

catpic respects these environment variables for configuration:

### `CATPIC_BASIS`

Set your preferred BASIS quality level:

```bash
export CATPIC_BASIS=2,4
catpic photo.jpg  # Uses ultra quality by default
```

**Supported formats:** `1,2` | `2,2` | `2,3` | `2,4`  
(You can also use `x` or `_` as separator: `2x4` or `2_4`)

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to make permanent.

### `CATPIC_CHAR_ASPECT`

Set terminal character aspect ratio to fix image proportions:

```bash
export CATPIC_CHAR_ASPECT=2.0
catpic photo.jpg
```

**Common values:**
- `2.0` - Most terminals (default)
- `1.8` - Wider fonts
- `2.2` - Narrower fonts

**Why this matters:** Terminal characters are typically taller than they are wide. If your images look squashed (too wide) or stretched (too tall), adjust this value to match your terminal's font proportions.

**Quick calibration:**

If you have a test image with a circle:
```bash
catpic circle.png

# If circle looks tall/narrow, decrease:
export CATPIC_CHAR_ASPECT=1.8
catpic circle.png

# If circle looks wide/squashed, increase:
export CATPIC_CHAR_ASPECT=2.2
catpic circle.png
```

Once calibrated for your terminal, add to your shell profile.

## How BASIS Works

BASIS (x, y) defines the glyxel grid per character:

- **1×2** (4 patterns): Fast, chunky. Good for large images or overviews.
- **2×2** (16 patterns): Balanced. Default for most use cases.
- **2×3** (64 patterns): Smooth gradients. Sextant blocks.
- **2×4** (256 patterns): Maximum detail. Braille patterns.

Higher BASIS = more glyxels per character = better quality, slower rendering.

## MEOW Format

**M**osaic **E**ncoding **O**ver **W**ire—glyxel images as plain text with ANSI escape codes.

MEOW files are `cat`-compatible: they're standard text with embedded metadata and ANSI color codes. No special viewer needed.

**Current version:** 0.6 (uses OSC 9876 escape sequences for metadata)

**Example usage:**
```bash
# Create
catpic sunset.jpg -o sunset.meow

# Display (any of these work)
cat sunset.meow
less -R sunset.meow
head -n 30 sunset.meow  # Preview
```

MEOW files contain:
- Canvas metadata (size, animation settings, BASIS)
- Layer metadata (position, transparency, frame timing)
- Standard ANSI escape codes for colors
- Unicode characters encoding glyxel patterns

**Format specification:** See [spec/meow_v06_specification.md](spec/meow_v06_specification.md)

## Project Structure

catpic is designed as a multi-language project with consistent behavior:

```
catpic/
├── python/              # Python reference implementation (stable)
├── c/                   # C implementation (in development)
├── rust/                # Rust implementation (planned)
├── go/                  # Go implementation (planned)
├── docs/                # Architecture and API documentation
├── spec/                # MEOW format and compliance specifications
└── benchmarks/          # Performance comparisons
```

All implementations:
- Support the identical MEOW format
- Pass the same compliance test suite
- Implement the EnGlyph algorithm consistently
- Support all BASIS levels

Language-specific APIs differ to match ecosystem conventions.

## Documentation

- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Installation and usage for each language
- **[docs/primitives_api.md](docs/primitives_api.md)** - Low-level API for TUI development
- **[spec/meow_v06_specification.md](spec/meow_v06_specification.md)** - Format specification
- **[spec/compliance.md](spec/compliance.md)** - Cross-language test requirements
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guidelines

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style and testing requirements
- How to add new BASIS levels
- Cross-language implementation guidelines
- Prospective features (Sixel/Kitty graphics, streaming, etc.)

## License

MIT—do whatever you want with it.

## See Also

- [EnGlyph](https://github.com/friscorose/textual-EnGlyph) - The Textual widget that inspired this
- [docs/primitives_api.md](docs/primitives_api.md) - Build your own TUI graphics

---

*Built with Claude (Anthropic) exploring terminal graphics techniques that don't suck.*
