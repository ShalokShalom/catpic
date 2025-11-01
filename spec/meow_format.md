# MEOW Format Specification v0.7

**M**osaic **E**ncoding **O**ver **W**ire - Terminal image format with protocol fallback

**Status:** Draft  
**Date:** 2025-10-30  
**Replaces:** MEOW v0.6 (2025-10-19)

---

## Overview

MEOW v0.7 extends v0.6 with protocol fallback support, enabling advanced terminal graphics protocols (Sixel, Kitty, iTerm2) while maintaining universal glyxel compatibility.

### What's New in v0.7

- **Source field**: Embedded PNG for protocol generation
- **Cached protocols**: Optional pre-encoded protocol data
- **Protocol-agnostic display**: Smart tools select optimal protocol
- **Backward compatible**: v0.6 files remain valid

### Design Principles

1. **cat-compatible** - Files display correctly using standard `cat` command (glyxel)
2. **Protocol-enhanced** - Smart tools (catpic) use advanced protocols when available
3. **Source of truth** - PNG source enables protocol generation on-demand
4. **Graceful degradation** - Always fallback to glyxel if protocol unsupported

---

## Changes from v0.6

### New Fields

**Layer metadata additions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source` | object | No | Source image for protocol generation |
| `source.format` | string | Yes* | Source format ('png') |
| `source.dims` | [int,int] | Yes* | Pixel dimensions [width, height] |
| `source.data` | string | Yes* | Base64-encoded source image |
| `source.hash` | string | No | SHA-256 hash for cache validation |
| `cached` | object | No | Pre-encoded protocol data |
| `cached.sixel` | string | No | Base64-encoded Sixel data |

*Required if `source` field present

### Compatibility

**v0.7 decoders:**
- MUST support v0.6 files (no `source` field)
- MUST display glyxel if protocol generation fails
- MAY ignore `source` and `cached` fields

**v0.6 decoders:**
- Will ignore `source` and `cached` fields
- Will display glyxel correctly (backward compatible)

---

## Source Field Specification

### Purpose

Enable protocol generation from embedded source image, avoiding need to store multiple protocol-specific representations.

### Schema

```json
{
  "source": {
    "format": "png",
    "dims": [160, 72],
    "data": "iVBORw0KGgoAAAANS...",
    "hash": "sha256:abc123..."
  }
}
```

### Field Details

**`format`** (required)
- Type: string
- Valid values: `"png"`
- Future: May support `"jpeg"`, `"webp"`
- Purpose: Identify source image format

**`dims`** (required)
- Type: [int, int]
- Format: [width_pixels, height_pixels]
- Purpose: Quick dimension check without decoding
- Validation: Must match actual image dimensions

**`data`** (required)
- Type: string (base64)
- Purpose: Source image bytes
- Encoding: Standard base64 (RFC 4648)
- Compression: PNG internal compression (not gzip)
- Purpose: Enable protocol generation

**`hash`** (optional)
- Type: string
- Format: `"sha256:{hex_digest}"`
- Purpose: Cache validation
- Validation: Hash of raw `data` bytes (before base64)

### Validation Rules

```python
# Pseudo-code validation
if 'source' in layer_metadata:
    assert 'format' in layer_metadata['source']
    assert 'dims' in layer_metadata['source']
    assert 'data' in layer_metadata['source']
    
    assert layer_metadata['source']['format'] == 'png'
    assert len(layer_metadata['source']['dims']) == 2
    assert all(d > 0 for d in layer_metadata['source']['dims'])
    
    # Validate base64
    try:
        png_bytes = base64.b64decode(layer_metadata['source']['data'])
    except:
        raise ValidationError("Invalid base64 in source.data")
    
    # Validate PNG signature
    assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    
    # Validate dimensions match
    import struct
    width, height = struct.unpack('>II', png_bytes[16:24])
    assert [width, height] == layer_metadata['source']['dims']
```

### Size Considerations

**PNG source should be BASIS-resolution:**
- For BASIS [2, 2]: 2 pixels per character cell
- For 80×24 canvas: ~160×48 pixels
- Typical size: 2-10 KB per layer (compressed PNG)

**Rationale:**
- Matches glyxel visual quality
- Fast protocol generation
- Reasonable file size
- Can always store higher-res in separate field if needed

### When to Include Source

**Include `source` when:**
- File will be displayed on multiple terminal types
- Protocol generation desired (Sixel, Kitty, iTerm2)
- File is for distribution (not just local display)

**Omit `source` when:**
- Display-only file (no editing/regeneration)
- File size is critical constraint
- Only glyxel display needed

---

## Cached Field Specification

### Purpose

Optional pre-encoded protocol data for performance optimization. Avoids re-encoding expensive protocols (especially Sixel).

### Schema

```json
{
  "cached": {
    "sixel": "G3JhIzA7MjsxMDA7MTAwOz...",
    "source_hash": "sha256:abc123..."
  }
}
```

### Field Details

**`cached.sixel`** (optional)
- Type: string (base64)
- Content: Pre-encoded Sixel graphics data
- Purpose: Skip expensive Sixel generation
- Generated by: `catpic display --embed-sixel`

**`cached.source_hash`** (optional)
- Type: string
- Format: `"sha256:{hex_digest}"`
- Purpose: Validate cache matches current source
- Validation: Must match `source.hash` if both present

**Future protocols:**
- `cached.kitty`: Not needed (PNG pass-through is fast)
- `cached.iterm2`: Not needed (PNG pass-through is fast)
- `cached.future_protocol`: May be added if protocol is expensive

### Cache Validation

```python
# Pseudo-code cache validation
if 'cached' in metadata and 'sixel' in metadata['cached']:
    # Check if cache is valid
    if 'source_hash' in metadata['cached']:
        if metadata['source']['hash'] != metadata['cached']['source_hash']:
            # Stale cache - regenerate
            regenerate = True
        else:
            # Valid cache - use it
            use_cached_sixel()
    else:
        # No hash - assume valid (trust encoder)
        use_cached_sixel()
```

### Cache Invalidation

**Cache becomes stale when:**
- `source.data` changes (different image)
- `source.hash` changes
- `cached.source_hash` doesn't match `source.hash`

**Decoder behavior on stale cache:**
1. Detect hash mismatch
2. Regenerate protocol from `source.data`
3. Optionally update cache if user requested

### When to Use Cached

**Use cached protocols when:**
- User explicitly requests: `--embed-sixel`
- File will be displayed repeatedly
- Sixel terminal is target environment
- Distribution scenario (avoid re-encoding)

**Skip cached protocols when:**
- File size is constraint
- Source image may change
- Protocol not supported by target terminals
- Development/testing (want fresh generation)

---

## Protocol Generation Semantics

### Generation Order

Smart display tools (like `catpic`) should:

1. **Detect terminal capabilities**
   - Query terminal for protocol support
   - Check environment variables
   - Use cached detection results

2. **Select protocol**
   - Kitty → iTerm2 → Sixel → Glyxel (priority order)
   - Based on detected capabilities

3. **Check for cached protocol**
   - If `cached.{protocol}` exists and valid: use it
   - Else: generate from source

4. **Generate protocol output**
   - Decode `source.data` (PNG bytes)
   - Generate protocol-specific output
   - Optionally cache result (if user requested)

5. **Display**
   - Write protocol output to terminal
   - On error: fallback to glyxel

### Fallback Chain

```
Protocol generation failed
    ↓
Try next protocol in priority list
    ↓
All protocols failed?
    ↓
Display glyxel from visible output
```

**Glyxel is always the final fallback.**

---

## File Structure Example

### Minimal v0.7 File (Glyxel Only)

```
\x1b]9876;{"meow":"0.7","size":[80,24]}\x07
\x1b]9876;{"id":"layer1","ctype":"ansi-art","cells":"..."}\x07
[Glyxel ANSI output]
```

No `source` field - display only, no protocol generation.

### Full v0.7 File (Protocol-Enabled)

```
\x1b]9876;{
  "meow": "0.7",
  "size": [80, 24],
  "basis": [2, 2]
}\x07

\x1b]9876;base64(gzip({
  "id": "layer1",
  "ctype": "ansi-art",
  "cells": "...",
  "source": {
    "format": "png",
    "dims": [160, 48],
    "data": "iVBORw0KGgoAAAANS...",
    "hash": "sha256:abc123..."
  }
}))\x07
[Glyxel ANSI output]
```

Has `source` - enables protocol generation on any terminal.

### v0.7 File with Cached Sixel

```
\x1b]9876;base64(gzip({
  "id": "layer1",
  "ctype": "ansi-art",
  "cells": "...",
  "source": {
    "format": "png",
    "dims": [160, 48],
    "data": "iVBORw0KGgo...",
    "hash": "sha256:abc123..."
  },
  "cached": {
    "sixel": "G3JhIzA7MjsxM...",
    "source_hash": "sha256:abc123..."
  }
}))\x07
[Glyxel ANSI output]
```

Has `source` and `cached.sixel` - optimized for Sixel terminals.

---

## Display Behavior

### POSIX cat

```bash
cat image.meow
```

**Behavior (unchanged from v0.6):**
- OSC 9876 metadata hidden
- Glyxel ANSI output displayed
- Ignores `source` and `cached` fields

**Result:** Universal display compatibility.

### Smart Display Tool (catpic)

```bash
catpic display image.meow
```

**Behavior:**
1. Parse metadata (including `source` and `cached`)
2. Detect terminal capabilities
3. Select optimal protocol
4. Generate or use cached protocol
5. Display protocol output
6. On error: fallback to glyxel

**Result:** Optimal display for terminal type.

### With Explicit Protocol

```bash
catpic display --protocol=sixel image.meow
```

**Behavior:**
1. Skip detection
2. Force Sixel protocol
3. Check for `cached.sixel`
4. If not cached: generate from `source`
5. Display Sixel output

**Result:** User-controlled protocol selection.

### With Cache Embedding

```bash
catpic display --embed-sixel image.meow
```

**Behavior:**
1. Detect terminal (or use --protocol)
2. Generate Sixel from `source`
3. Display Sixel
4. Write Sixel to `cached.sixel` in file
5. Update `cached.source_hash`

**Result:** File modified to include cached Sixel.

---

## Encoding Guidelines

### Single Image to MEOW

```bash
catpic encode image.png -o output.meow
```

**Encoder should:**
1. Generate glyxel rendering
2. Embed PNG source at BASIS-resolution
3. Store in `source` field
4. Include `source.hash` for cache validation
5. Write glyxel to visible output

**Result:** v0.7 file with protocol generation capability.

### With Pre-Cached Sixel

```bash
catpic encode --embed-sixel image.png -o output.meow
```

**Encoder should:**
1. Generate glyxel rendering
2. Embed PNG source
3. Generate Sixel from source
4. Store in `cached.sixel`
5. Include hash for validation

**Result:** v0.7 file optimized for Sixel terminals.

### Display-Only Encoding

```bash
catpic encode --no-source image.png -o output.meow
```

**Encoder should:**
1. Generate glyxel rendering only
2. Omit `source` field
3. Smaller file size
4. No protocol generation possible

**Result:** v0.6-compatible file (smaller, display-only).

---

## Migration from v0.6

### Backward Compatibility

**v0.6 files are valid v0.7 files:**
- No `source` field → display glyxel only
- All v0.6 semantics preserved
- No breaking changes

### Upgrading v0.6 to v0.7

```bash
catpic upgrade image-v06.meow -o image-v07.meow
```

**Process:**
1. Parse v0.6 file
2. Extract glyxel layer data
3. Reconstruct source image from glyxel (lossy)
4. Encode as PNG
5. Add `source` field
6. Write v0.7 file

**Limitations:**
- Glyxel → PNG is lossy reconstruction
- Quality limited by BASIS resolution
- Better to re-encode from original source

### Recommended Migration

**For important files:**
1. Keep original source images
2. Re-encode from source: `catpic encode original.png -o new-v07.meow`
3. Preserve layer metadata from v0.6

**For display-only files:**
- No migration needed (v0.6 works in v0.7 tools)

---

## Validation

### Required Validations

**Decoders MUST validate:**
1. `source.format` is recognized value
2. `source.data` is valid base64
3. `source.data` decodes to valid PNG
4. `source.dims` matches decoded PNG dimensions
5. `cached.source_hash` matches `source.hash` (if both present)

**Decoders SHOULD validate:**
1. PNG dimensions are reasonable (< 10000 pixels)
2. `source.hash` is correct SHA-256
3. Cached protocol data is valid base64

### Error Handling

**On validation failure:**
1. Log warning (if verbose mode)
2. Ignore invalid field
3. Continue with remaining valid data
4. Fallback to glyxel if protocol generation fails

**Decoders MUST NOT:**
- Crash on invalid metadata
- Refuse to display file
- Corrupt terminal state

---

## Exit Codes

Updated exit codes for v0.7:

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | File processed successfully |
| 1 | General error | Unspecified failure |
| 2 | Parse error | Invalid JSON, malformed OSC |
| 3 | No canvas size | Cannot determine dimensions |
| 4 | Invalid metadata | Required field missing, value out of range |
| 5 | File not found | Input file does not exist |
| 6 | Write error | Cannot write output file |
| 7 | Protocol error | Protocol generation failed (display still succeeded via fallback) |

**Note:** Exit code 7 is warning, not failure (glyxel fallback worked).

---

## Version History

**v0.7 (2025-10-30) - Draft**
- Source field for protocol generation
- Cached protocol data
- Protocol fallback semantics
- Backward compatible with v0.6

**v0.6 (2025-10-19)**
- Interleaved layer blocks
- OSC 9876 hidden metadata
- Stream-order z-ordering
- Translucency melding
- Animation support

---

## References

- MEOW v0.6 Specification (2025-10-19)
- Sixel Graphics: https://en.wikipedia.org/wiki/Sixel
- Kitty Graphics Protocol: https://sw.kovidgoyal.net/kitty/graphics-protocol/
- iTerm2 Inline Images: https://iterm2.com/documentation-images.html
- RFC 4648 - Base64 Encoding

---

## License

This specification is released into the public domain.
Implementations may use any license.
