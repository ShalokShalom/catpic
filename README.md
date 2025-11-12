# catpic

Turn images into terminal eye candy using Unicode mosaics and ANSI colors.

**The twist:** Save as MEOW format and display with `cat`. Yes, the POSIX command. No special viewer needed.

```bash
catpic photo.jpg -o photo.meow
cat photo.meow  # 🐱 Just works
```

> **Note:** This is v0.9.0 Release Candidate. While core functionality is stable and well-tested, some features (multi-language implementations, iTerm2 protocol on non-Mac platforms, edge cases across terminal emulators) are still being validated. We'd love your feedback, bug reports, terminal compatibility notes, or just a "hey, this worked great!" on [GitHub Issues](https://github.com/friscorose/catpic/issues). Early adopters welcome! 🎉

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
- **Multiple protocols**: Kitty Graphics, Sixel, iTerm2, and Glyxel (Unicode mosaic)
- **Multiple BASIS levels**: Trade speed for quality (1×2 to 2×4)
- **Smooth animations**: GIF playback with no flicker
- **Auto-detection**: Picks the best protocol for your terminal
- **Primitives API**: Build your own TUI graphics with composable functions
- **Environment aware**: Automatic terminal size and aspect ratio detection
- **Multi-language**: Python (stable), C (in development), Rust/Go (planned)

## Installation & Usage

**See [IMPLEMENTATION.md](IMPLEMENTATION.md) for installation instructions and API documentation for your language.**

Each implementation provides the same core functionality with language-appropriate APIs and conventions.

**Current status:**
- **Python:** Stable, fully functional (reference implementation)
- **C, Rust, Go:** Planned (architecture designed for multi-language support)

## Graphics Protocols

catpic supports multiple terminal graphics protocols with automatic detection and fallback:

| Protocol | Terminals | Quality | Speed | Testing Status |
|----------|-----------|---------|-------|----------------|
| **Kitty** | Kitty | Excellent | Very Fast | ✅ Verified in Kitty terminal |
| **iTerm2** | iTerm2, VSCode<sup>†</sup>, WezTerm, Tabby | Excellent | Very Fast | ⚠️ Needs Mac hardware testing |
| **Sixel** | xterm<sup>‡</sup>, mlterm, foot, WezTerm | Good | Fast | ✅ Verified in xterm, VSCode |
| **Glyxel** | All terminals | Fair | Fast | ✅ Universal fallback |

<sup>†</sup> Requires `terminal.integrated.enableImages` setting  
<sup>‡</sup> Requires `xterm -ti vt340` or sixel compile option

**Auto-detection priority:** Kitty > iTerm2 > Sixel > Glyxel

**Testing note:** iTerm2 protocol generates valid escape sequences (verified in tests) but needs validation on native iTerm2/Mac hardware. VSCode terminal image support varies by configuration.

```bash
# Auto-detect best protocol
catpic photo.jpg

# Force specific protocol
catpic photo.jpg --protocol kitty
catpic photo.jpg --protocol sixel
catpic photo.jpg --protocol iterm2
catpic photo.jpg --protocol glyxel

# Detect capabilities for your terminal
catpic --detect
```

### Terminal Configuration

#### VSCode Integrated Terminal

VSCode supports iTerm2 inline images and Sixel graphics. For optimal display:

**Required Settings:**

1. **Enable Image Support** (for iTerm2 protocol):
   - Settings → Search "terminal images"
   - Enable: `Terminal › Integrated: Enable Images`

2. **Fix Aspect Ratio** (prevents distortion):
   - `Terminal › Integrated: Minimum Contrast Ratio` → `1`  
     _(Default adjusts contrast; set to 1 for "Do Nothing")_
   - `Terminal › Integrated: Line Height` → `1`  
     _(Default 1.1 causes aspect ratio distortion)_

3. **Performance** (optional):
   - `Terminal › Integrated: GPU Acceleration` → `on`

**Without these settings:**
- Images may display with incorrect aspect ratios
- Colors may be adjusted unexpectedly
- Line spacing may create visual gaps

#### xterm Sixel Support

xterm requires VT340 emulation mode for Sixel graphics:

```bash
# Run with Sixel support
xterm -ti vt340

# Or compile xterm with sixel support
./configure --enable-sixel-graphics
```

#### tmux Configuration

tmux requires passthrough configuration for graphics protocols:

```bash
# ~/.tmux.conf
set -g allow-passthrough on
```

Then reload:
```bash
tmux source-file ~/.tmux.conf
```

**Note:** Inside tmux, some terminal-specific environment variables (like `KITTY_WINDOW_ID`) may not propagate. Use `catpic --detect` to see available protocols, or force a specific protocol with `--protocol`.

**Reference:** https://tmuxai.dev/tmux-allow-passthrough/

## Configuration

catpic uses a unified JSON configuration via the `CATPIC_CONFIG` environment variable:

```bash
export CATPIC_CONFIG='{"protocol":"sixel","basis":"2,4","aspect 2x4":2.0}'
catpic photo.jpg  # Uses your configuration
```

**Auto-detect and persist:**

```bash
# Detect optimal settings for your terminal
catpic --detect

# Example output with command to persist:
export CATPIC_CONFIG='{"protocol":"sixel","basis":"2,2","aspect base":2.0,...}'

# Add to your shell profile to make permanent:
echo 'eval "$(catpic --detect)"' >> ~/.bashrc
```

**Configuration keys:**

| Key | Values | Default | Description |
|-----|--------|---------|-------------|
| `protocol` | `kitty`, `sixel`, `iterm2`, `glyxel`, `auto` | `auto` | Graphics protocol to use |
| `basis` | `1,2`, `2,2`, `2,3`, `2,4` | `2,2` | Quality level (see BASIS section) |
| `aspect base` | float | `2.0` | Base character aspect ratio |
| `aspect 1x2` | float | `2.0` | Aspect correction for BASIS 1×2 |
| `aspect 2x2` | float | `0.9` | Aspect correction for BASIS 2×2 |
| `aspect 2x3` | float | `1.5` | Aspect correction for BASIS 2×3 |
| `aspect 2x4` | float | `2.0` | Aspect correction for BASIS 2×4 |

**Session overrides:**

You can override configuration per-command without changing your environment:

```bash
# Override protocol (doesn't modify CATPIC_CONFIG)
catpic photo.jpg --protocol kitty

# Override basis
catpic photo.jpg --basis 2,4

# Show current configuration
catpic --config
```

## How BASIS Works

BASIS (x, y) defines the glyxel grid per character:

**Available BASIS levels:**

| BASIS | Patterns | Quality | Unicode Requirement |
|-------|----------|---------|---------------------|
| `1,2` | 4 | Fast, chunky | Basic (block elements) |
| `2,2` | 16 | Balanced (default) | Unicode 13.0+ (2020) |
| `2,3` | 64 | Smooth gradients | Unicode 13.0+ (2020) |
| `2,4` | 256 | Maximum detail | Unicode 3.0 (Braille) |

Higher BASIS = more glyxels per character = better quality, slower rendering.

**Terminal compatibility:** Most modern terminals support all BASIS levels. If you see missing characters or boxes, your terminal may need:
- Updated Unicode fonts (for 2×2 and 2×3 quadrant/sextant blocks)
- Braille pattern support (for 2×4)

**Setting BASIS:**

```bash
# Via configuration (recommended)
export CATPIC_CONFIG='{"basis":"2,4",...}'

# Per-command override
catpic photo.jpg --basis 2,4

# Legacy environment variable
export CATPIC_BASIS=2,4
```

## MEOW Format

**M**osaic **E**ncoding **O**ver **W**ire—glyxel images as plain text with ANSI escape codes.

MEOW files are `cat`-compatible: they're standard text with embedded metadata and ANSI color codes. No special viewer needed.

**Current version:** 0.9 (supports multiple graphics protocols with embedded PNG)

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
- Protocol-specific data (PNG for Kitty/Sixel/iTerm2, glyxel for universal fallback)
- Standard ANSI escape codes for colors
- Unicode characters encoding glyxel patterns

**Format specification:** See [spec/meow_specification.md](spec/meow_specification.md)

## Troubleshooting

### Protocol Issues

**Images don't display:**
- Check supported protocols: `catpic --detect`
- Try forcing glyxel: `catpic image.jpg --protocol glyxel`
- Verify terminal configuration (see Terminal Configuration above)

**Sixel shows garbled output:**
- xterm: Use `xterm -ti vt340` or compile with `--enable-sixel-graphics`
- Some terminals claim xterm compatibility but lack sixel rendering
- Sixel detection works but rendering depends on terminal build options

**iTerm2 in VSCode doesn't work:**
- Enable `terminal.integrated.enableImages` setting
- May require GPU acceleration (check VSCode docs)
- Fallback: Use `--protocol sixel` (auto-detected and works reliably)

**Kitty graphics in tmux:**
- Configure tmux passthrough: `set -g allow-passthrough on`
- Or use catpic outside tmux
- Fallback protocols (sixel/glyxel) work in tmux

### Display Quality

**Images look squashed or stretched:**
- Adjust `CATPIC_CHAR_ASPECT` (see Environment Variables)
- Try different protocols: `--protocol kitty` or `--protocol sixel`

**Missing characters or boxes:**
- Update terminal font (Unicode 13.0+ support)
- Try lower BASIS: `--basis 1,2`
- Check terminal Unicode support

**Colors look wrong:**
- VSCode: Set `Minimum Contrast Ratio` to 1
- Verify 24-bit color support: `echo $COLORTERM` should show `truecolor`

## Project Structure

catpic is designed as a multi-language project with consistent behavior:

```
catpic/
├── python/              # Python reference implementation (stable, v0.9.0)
├── c/                   # C implementation (planned)
├── rust/                # Rust implementation (planned)
├── go/                  # Go implementation (planned)
├── docs/                # Architecture and API documentation
├── spec/                # MEOW format and compliance specifications
└── benchmarks/          # Performance comparisons
```

**Multi-language goal:** All implementations will:
- Support the identical MEOW format
- Pass the same compliance test suite
- Implement the EnGlyph algorithm consistently
- Support all BASIS levels
- Support all graphics protocols (Kitty, Sixel, iTerm2, Glyxel)

Language-specific APIs will differ to match ecosystem conventions.

**Current status:** Python implementation is complete and serves as the reference. C/Rust/Go implementations are part of the roadmap.

## Documentation

- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Installation and usage for each language
- **[docs/primitives_api.md](docs/primitives_api.md)** - Low-level API for TUI development
- **[spec/meow_v06_specification.md](spec/meow_v06_specification.md)** - Format specification
- **[spec/compliance.md](spec/compliance.md)** - Cross-language test requirements
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guidelines

## Related Projects

- **[timg](https://github.com/hzeller/timg/)** - Terminal image and video viewer with similar goals
- **[viu](https://github.com/atanunq/viu)** - Terminal image viewer in Rust
- **[chafa](https://hpjansson.org/chafa/)** - Character art facsimile generator
- **[EnGlyph](https://github.com/friscorose/textual-EnGlyph)** - The Textual widget that inspired this

**What makes catpic different:**
- **MEOW format** - Stored, layered, animated terminal graphics that work with `cat`
- **Multi-protocol** - Automatic fallback across terminal capabilities
- **Basis-aware rendering** - Quality vs. size tradeoffs with consistent API
- **Multi-language** - Consistent behavior across Python, C, Rust, Go implementations

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style and testing requirements
- How to add new BASIS levels
- Cross-language implementation guidelines
- Protocol support (Kitty, Sixel, iTerm2, future protocols)
- Prospective features (streaming, video playback, etc.)

## License

MIT—do whatever you want with it.

## See Also

- [EnGlyph](https://github.com/friscorose/textual-EnGlyph) - The Textual widget that inspired this
- [docs/primitives_api.md](docs/primitives_api.md) - Build your own TUI graphics

---

*Built with Claude (Anthropic) exploring terminal graphics techniques that don't suck.*
