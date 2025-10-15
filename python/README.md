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
- **Environment aware**: `CATPIC_BASIS` sets your preferred quality
- **Multi-language**: Python (stable), C (in development), Rust/Go (planned)

## Installation & Usage

**See [IMPLEMENTATION.md](IMPLEMENTATION.md) for installation instructions and API documentation for your language.**

Each implementation provides the same core functionality with language-appropriate APIs and conventions.

### Environment Variables

**`CATPIC_BASIS`** - Set default BASIS level for all operations:

```bash
export CATPIC_BASIS=2,4
catpic photo.jpg  # Uses BASIS 2×4

# Also accepts: 2x4, 2_4
```

## How BASIS Works

BASIS (x, y) defines the glyxel grid per character:

- **1×2** (4 patterns): Fast, chunky. Good for large images or overviews.
- **2×2** (16 patterns): Balanced. Default for most use cases.
- **2×3** (64 patterns): Smooth gradients. Sextant blocks.
- **2×4** (256 patterns): Maximum detail. Braille patterns.

Higher BASIS = more glyxels per character = better quality, slower rendering.

## MEOW Format

**M**osaic **E**ncoding **O**ver **W**ire—glyxel images in plain text:

```
MEOW/1.0
WIDTH:80
HEIGHT:24
BASIS:2,4
DATA:
[ANSI-colored character grid with embedded glyxels]
```

The beauty: it's just ANSI escape codes and Unicode. Use `cat`, `less`, `grep`, version control—standard POSIX tools work out of the box.

**Example:**
```bash
# Create
catpic sunset.jpg -o sunset.meow

# Display (any of these work)
cat sunset.meow
less -R sunset.meow
head -n 30 sunset.meow  # Preview

# Share
git add sunset.meow     # Version control friendly
echo "sunset.meow" | xargs cat  # Standard text processing
```

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
- **[docs/primitives_api.md](https://github.com/friscorose/catpic/blob/main/docs/primitives_api.md)** - Low-level API for TUI development
- **[spec/meow_format.md](https://github.com/friscorose/catpic/blob/main/spec/meow_format.md)** - Format specification
- **[spec/compliance.md](https://github.com/friscorose/catpic/blob/main/spec/compliance.md)** - Cross-language test requirements
- **[CONTRIBUTING.md](https://github.com/friscorose/catpic/blob/main/CONTRIBUTING.md)** - Development guidelines

## Contributing

Contributions welcome! See [CONTRIBUTING.md](https://github.com/friscorose/catpic/blob/main/CONTRIBUTING.md) for:
- Code style and testing requirements
- How to add new BASIS levels
- Cross-language implementation guidelines
- Prospective features (Sixel/Kitty graphics, streaming, etc.)

## License

MIT—do whatever you want with it.

## See Also

- [EnGlyph](https://github.com/friscorose/textual-EnGlyph) - The Textual widget that inspired this
- [docs/primitives_api.md](https://github.com/friscorose/catpic/blob/main/docs/primitives_api.md) - Build your own TUI graphics

---

*Built with Claude (Anthropic) exploring terminal graphics techniques that don't suck.*
