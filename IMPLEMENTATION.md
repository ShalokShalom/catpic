# Language Implementations

catpic is designed as a multi-language project. All implementations share the MEOW format specification and pass identical compliance tests, ensuring consistent behavior across platforms.

## Quick Links

Choose your language for installation instructions and API documentation:

- **[Python](#python)** - Reference implementation, stable on PyPI
- **[C](#c)** - High-performance native implementation (in development)
- **[Rust](#rust)** - Memory-safe systems programming (planned)
- **[Go](#go)** - Simple deployment, great concurrency (planned)

---

## Python

**Status**: ✅ Stable (v0.5.1 on PyPI)

The reference implementation. Fully featured, well-documented, and production-ready.

### Installation

```bash
# As a CLI tool (recommended)
uv tool install catpic

# As a library
pip install catpic
# or
uv add catpic
```

**Requirements**: Python 3.8+

### Quick Example

```bash
catpic photo.jpg
catpic photo.jpg -o photo.meow
cat photo.meow
```

**Full Documentation**: [python/IMPLEMENTATION.md](python/IMPLEMENTATION.md)

**Best For**:
- General terminal use
- Python scripting and automation
- Integration with data science tools
- Quick prototyping

---

## C

**Status**: 🚧 In Development

High-performance native implementation using libvips for image processing.

### Installation

```bash
# From source
git clone https://github.com/friscorose/catpic
cd catpic/c
make
sudo make install
```

**Requirements**: 
- C compiler (gcc/clang)
- libvips (or use minimal build with stb_image)

### Quick Example

```bash
catpic photo.jpg
catpic photo.jpg --basis 2,4
```

**Full Documentation**: [c/IMPLEMENTATION.md](c/IMPLEMENTATION.md)

**Best For**:
- Performance-critical applications
- Embedded systems
- Server-side batch processing
- Systems programming

---

## Rust

**Status**: 📋 Planned

Memory-safe implementation using the image-rs ecosystem.

### Planned Installation

```bash
cargo install catpic
```

**Requirements**: Rust 1.70+

### Planned Features

- Pure Rust (no C dependencies)
- Safe concurrency via rayon
- Zero-cost abstractions
- Native integration with Rust TUI frameworks

**Full Documentation**: [rust/IMPLEMENTATION.md](rust/IMPLEMENTATION.md) (coming soon)

**Best For**:
- Systems programming with safety guarantees
- High-performance TUI applications
- Memory-constrained environments
- Learning Rust through a real-world project

---

## Go

**Status**: 📋 Planned

Simple, efficient implementation using Go's standard library.

### Planned Installation

```bash
go install github.com/friscorose/catpic@latest
```

**Requirements**: Go 1.20+

### Planned Features

- Minimal dependencies
- Single binary deployment
- Goroutine-based parallelization
- Native HTTP server integration

**Full Documentation**: [go/IMPLEMENTATION.md](go/IMPLEMENTATION.md) (coming soon)

**Best For**:
- Server applications
- Microservices
- Cross-compilation needs
- Simple deployment scenarios

---

## Implementation Parity

All implementations guarantee:

| Feature | Python | C | Rust | Go |
|---------|--------|---|------|-----|
| MEOW format read/write | ✅ | 🚧 | 📋 | 📋 |
| BASIS 1×2, 2×2, 2×3, 2×4 | ✅ | 🚧 | 📋 | 📋 |
| Static image display | ✅ | 🚧 | 📋 | 📋 |
| Animated GIF support | ✅ | 🚧 | 📋 | 📋 |
| Primitives API | ✅ | 🚧 | 📋 | 📋 |
| Compliance tests | ✅ | 🚧 | 📋 | 📋 |

✅ Stable | 🚧 In Development | 📋 Planned

## Performance Comparison

Approximate render times for 80×24 terminal (1920 cells):

| Implementation | Static Image | Animation (30fps) | Notes |
|----------------|--------------|-------------------|-------|
| Python (PIL) | ~500ms | 2-3fps | Good enough for most use cases |
| Python + Numba | ~200ms | 5-10fps | Optional acceleration |
| C (libvips) | ~100ms | 10-20fps | Multi-threaded |
| Rust (image-rs) | ~150ms | 7-15fps | Estimated, safe parallelism |
| Go (stdlib) | ~200ms | 5-10fps | Estimated, simple concurrency |

*Performance varies by image complexity and hardware. These are rough benchmarks.*

## Choosing an Implementation

### Use Python if:
- You're already using Python
- You want the most stable, documented version
- Installation simplicity is priority
- Performance is "good enough" (~500ms renders)

### Use C if:
- You need maximum performance
- You're building a server-side service
- You have experience with C build systems
- Embedded/resource-constrained deployment

### Use Rust if:
- You want performance + safety guarantees
- You're building a TUI application in Rust
- You prefer strong type systems
- Memory safety is critical

### Use Go if:
- You want simple deployment (single binary)
- You're building web services
- You value code simplicity
- Cross-compilation is important

## Contributing a New Implementation

Want to add support for another language? See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Key requirements:

1. Pass all compliance tests in `spec/test-vectors.json`
2. Support MEOW format read/write
3. Implement all BASIS levels (1×2, 2×2, 2×3, 2×4)
4. Follow language ecosystem conventions
5. Provide IMPLEMENTATION.md with clear examples

Languages we'd love to see:
- Zig (native performance, modern tooling)
- JavaScript/TypeScript (browser + Node.js)
- Swift (macOS/iOS native integration)
- Julia (scientific computing integration)

## Cross-Language Consistency

All implementations share:

**MEOW Format**: Text-based format defined in [spec/meow_format.md](spec/meow_format.md)

**Test Vectors**: Shared test suite in [spec/test-vectors.json](spec/test-vectors.json) ensures identical behavior

**EnGlyph Algorithm**: Mathematical specification, not code-dependent

**Character Tables**: All use identical Unicode character sets for each BASIS level

What differs across languages:
- API design (matches language idioms)
- Performance characteristics
- Dependency management
- Build systems

## Support

- **Issues**: [GitHub Issues](https://github.com/friscorose/catpic/issues)
- **Discussions**: [GitHub Discussions](https://github.com/friscorose/catpic/discussions)
- **Documentation**: [docs/](docs/)

For language-specific questions, see the IMPLEMENTATION.md file in that language's directory.
