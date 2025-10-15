#!/bin/bash
# Copy root reference materials to all language implementation directories
# 
# This script is used:
# 1. Manually before building packages
# 2. Automatically in CI/CD pipeline (see .github/workflows/*)
#
# Copies:
# - README.md (with link rewrites to point to GitHub)
# - docs/ directory (shared documentation)
# - spec/ directory (specifications)
#
# The copied files contain links to IMPLEMENTATION.md which will
# automatically point to the correct language-specific file.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

echo "Copying reference materials to language directories..."
echo ""

# Language directories that should receive the references
# Add new languages here as they're implemented
LANG_DIRS=("python")

# Future: Add these when ready
# LANG_DIRS=("python" "c" "rust" "go")

for lang in "${LANG_DIRS[@]}"; do
    if [ -d "$lang" ]; then
        echo "→ Copying to $lang/"
        
        # Copy README.md
        cp README.md "$lang/README.md"
        
        # Rewrite relative links to absolute GitHub URLs
        # This makes links work when the package is distributed
        # Note: IMPLEMENTATION.md link stays relative (points to lang-specific file)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS sed syntax
            sed -i '' \
                -e "s|](docs/|](https://github.com/friscorose/catpic/blob/main/docs/|g" \
                -e "s|](spec/|](https://github.com/friscorose/catpic/blob/main/spec/|g" \
                -e "s|](CONTRIBUTING.md)|](https://github.com/friscorose/catpic/blob/main/CONTRIBUTING.md)|g" \
                "$lang/README.md"
        else
            # Linux sed syntax
            sed -i \
                -e "s|](docs/|](https://github.com/friscorose/catpic/blob/main/docs/|g" \
                -e "s|](spec/|](https://github.com/friscorose/catpic/blob/main/spec/|g" \
                -e "s|](CONTRIBUTING.md)|](https://github.com/friscorose/catpic/blob/main/CONTRIBUTING.md)|g" \
                "$lang/README.md"
        fi
        
        # Copy docs/ directory
        if [ -d "docs" ]; then
            rm -rf "$lang/docs"
            cp -r docs "$lang/docs"
            echo "  ✓ docs/ copied"
        fi
        
        # Copy spec/ directory
        if [ -d "spec" ]; then
            rm -rf "$lang/spec"
            cp -r spec "$lang/spec"
            echo "  ✓ spec/ copied"
        fi
        
        echo "  ✓ README.md copied (links rewritten for package distribution)"
    else
        echo "  ⊘ Directory $lang/ doesn't exist, skipping"
    fi
done

echo ""
echo "✓ Reference materials copied to all language directories"
echo ""
echo "Note: IMPLEMENTATION.md link stays relative, pointing to each"
echo "      language's specific documentation file."
echo ""
echo "Files updated:"
for lang in "${LANG_DIRS[@]}"; do
    if [ -d "$lang" ]; then
        echo "  - $lang/README.md"
        [ -d "$lang/docs" ] && echo "  - $lang/docs/"
        [ -d "$lang/spec" ] && echo "  - $lang/spec/"
    fi
done
echo ""
echo "To use in CI/CD, add this to your workflow:"
echo "  - name: Copy references to language dirs"
echo "    run: ./scripts/copy_references.sh"
