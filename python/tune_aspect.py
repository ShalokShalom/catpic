#!/usr/bin/env python3
# Destination: tune_aspect.py (root of python/ dir)

"""
Quick aspect ratio tuning utility.

Usage:
    python tune_aspect.py <image> <basis> <aspect_value>
    
Example:
    python tune_aspect.py tests/fixtures/bounce_medium.gif 2,4 0.85
    python tune_aspect.py tests/fixtures/bounce_medium.gif 2,4 0.90
    python tune_aspect.py tests/fixtures/bounce_medium.gif 2,4 0.80
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from catpic.encoder import CatpicEncoder
from catpic.core import BASIS


def main():
    if len(sys.argv) != 4:
        print("Usage: tune_aspect.py <image> <basis> <correction>")
        print("Example: tune_aspect.py bounce.gif 2,4 0.85")
        sys.exit(1)
    
    image_path = sys.argv[1]
    basis_str = sys.argv[2]
    correction = float(sys.argv[3])
    
    # Parse basis
    bx, by = map(int, basis_str.split(','))
    basis = BASIS((bx, by))
    
    # Set correction via env var
    os.environ[f'CATPIC_CHAR_ASPECT_{bx}x{by}'] = str(2.0 * correction)
    
    # Encode and print
    encoder = CatpicEncoder(basis=basis)
    output = encoder.encode_image(image_path, protocol='glyxel_only')
    
    print(f"\n=== BASIS {bx}x{by} with correction {correction} ===")
    print(output)


if __name__ == '__main__':
    main()
