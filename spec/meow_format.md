# MEOW Format Specification v0.9

## Version History

- **v0.9** (2025-11): Protocol-aware animation, timing model, loop semantics (beta)
- **v0.6** (2025-10): Dual content encoding (PNG + glyxel)
- **v0.5** (2025-09): Initial specification

## Overview

MEOW (**M**osaic **E**ncoding **O**ver **W**ire) is a terminal graphics format that embeds image data in plain text using ANSI escape sequences and optional protocol-specific data.

**Version 0.9 Status:** Beta release. Specification is stable for testing but may have minor adjustments based on early adopter feedback before v1.0.

**Key features:**
- `cat`-compatible (displays without special viewer)
- Multiple graphics protocols (Kitty, Sixel, iTerm2, Glyxel)
- Frame timing for animation
- Looping support
- Backward compatible

## Format Structure

MEOW files consist of:
1. Canvas metadata (OSC 9876 escape sequence)
2. Layer metadata (OSC 9876 escape sequences)
3. Layer content (protocol-specific + glyxel fallback)

### Canvas Metadata

```
ESC ] 9876 ; canvas ; <metadata-json> BEL
```

**Metadata JSON:**
```json
{
  "version": "0.9",
  "size": [80, 24],
  "basis": [2, 2],
  "loop": 1
}
```

**Fields:**
- `version` (string, required): MEOW format version
- `size` (array, required): Canvas size in characters [width, height]
- `basis` (array, required): Glyxel basis [x, y] - e.g., [2, 2], [2, 4]
- `loop` (integer, optional): Loop count (0=forever, 1=once, N=N times). Default: 1

### Layer Metadata

```
ESC ] 9876 ; layer ; <metadata-json> BEL
```

**Metadata JSON:**
```json
{
  "ctype": "png",
  "render_at_ms": 0
}
```

**Fields:**
- `ctype` (string, optional): Content type ('png' or null for glyxel-only)
- `render_at_ms` (integer, optional): When to display (milliseconds from start). Default: 0

**Timing Model:**
- `render_at_ms` is cumulative from animation start
- Frame 0: `render_at_ms: 0` (immediate)
- Frame 1: `render_at_ms: 100` (display at 100ms)
- Frame 2: `render_at_ms: 200` (display at 200ms)
- Renderer sleeps between frames to maintain timing

### Layer Content

Each layer contains:

1. **Protocol-specific data** (optional):
   ```
   ESC ] 9876 ; cells ; <base64-encoded-data> BEL
   ```
   - For PNG content (`ctype: "png"`): Base64-encoded PNG image
   - Enables native protocol rendering (Kitty, Sixel, iTerm2)

2. **Glyxel fallback** (always present):
   - ANSI escape sequences with Unicode characters
   - Ensures `cat` compatibility
   - Used by glyxel protocol or as fallback

## Loop Semantics

The `loop` field in canvas metadata controls repetition:

- `loop: 0` - Infinite loop (display until interrupted)
- `loop: 1` - Display once (default)
- `loop: N` - Display N times

**For multi-frame content:**
- Each complete sequence counts as one loop iteration
- After final frame, loop restarts from first frame
- Timing resets for each loop iteration

**For single-frame content:**
- `loop` has no effect (displays once)

## Animation Timing

**Frame timing** uses `render_at_ms` to specify when each frame should display:

```json
// Frame sequence example
[
  {"render_at_ms": 0},    // Frame 0: Immediate
  {"render_at_ms": 100},  // Frame 1: Display at 100ms
  {"render_at_ms": 200},  // Frame 2: Display at 200ms
  {"render_at_ms": 350}   // Frame 3: Display at 350ms (150ms delay)
]
```

**Renderer behavior:**
1. Record start time when rendering begins
2. For each frame, wait until `start_time + render_at_ms`
3. Clear previous frame (protocol-specific)
4. Render new frame
5. If looping, reset timing and repeat

**Protocol-specific clearing:**
- **Glyxel:** ANSI clear screen (`ESC[H ESC[2J`)
- **Kitty/Sixel/iTerm2:** Image replacement (no explicit clear)

## Protocol Support

MEOW files can contain data for multiple protocols:

| Protocol | Content Type | Fallback |
|----------|--------------|----------|
| Kitty | PNG in `cells` | Glyxel |
| Sixel | PNG in `cells` | Glyxel |
| iTerm2 | PNG in `cells` | Glyxel |
| Glyxel | ANSI + Unicode | Always available |

**Rendering priority:**
1. Check for protocol-specific data (`ctype: "png"` + `cells`)
2. If available and protocol supports it, use native protocol
3. Otherwise, fall back to glyxel (ANSI + Unicode)

## Example: Animated GIF

```
ESC ] 9876 ; canvas ; {"version":"0.9","size":[40,20],"basis":[2,2],"loop":0} BEL

ESC ] 9876 ; layer ; {"ctype":"png","render_at_ms":0} BEL
ESC ] 9876 ; cells ; <base64-png-frame-0> BEL
<glyxel-ansi-frame-0>

ESC ] 9876 ; layer ; {"ctype":"png","render_at_ms":100} BEL
ESC ] 9876 ; cells ; <base64-png-frame-1> BEL
<glyxel-ansi-frame-1>

ESC ] 9876 ; layer ; {"ctype":"png","render_at_ms":200} BEL
ESC ] 9876 ; cells ; <base64-png-frame-2> BEL
<glyxel-ansi-frame-2>
```

**Result:** 3-frame animation, looping forever, 100ms between frames.

## Design Principles

1. **Minimal format** - Only what base catpic needs
2. **Separation of concerns** - Format stores data, renderer handles behavior
3. **Extensible** - New fields can be added without breaking old parsers
4. **Protocol-agnostic** - Works across all terminal capabilities

## Future Extensions (Not in v1.0)

Possible future additions (all backward compatible):
- `position`: Spatial offsets for multi-layer composition
- `blend_mode`: Compositing modes (alpha, add, multiply)
- `loop_regions`: Sub-sequences with different loop counts
- `damage_regions`: Optimization hints (computed by renderer, not stored)

These are **not** in the format yet - renderers that need them compute them dynamically or use external metadata.

## Backward Compatibility

**v1.0 changes from v0.6:**
- Added: `loop` in canvas metadata
- Added: `render_at_ms` in layer metadata
- Changed: Timing model (cumulative vs. per-frame delay)

**Compatibility:**
- v1.0 parsers can read v0.6 files (missing fields use defaults)
- v0.6 parsers can read v1.0 files (ignore unknown fields)
- Glyxel fallback ensures universal compatibility

## Reference Implementation

Python reference implementation: https://github.com/friscorose/catpic

Compliance test suite: `spec/compliance.md`
