#!/usr/bin/env bash
# Generate API reference markdown from source docstrings.
# Output goes to docs/api/traust.md — commit the result or pipe it to your site.
#
# Usage:
#   uv run --with pydoc-markdown bash scripts/generate_docs.sh
#
set -euo pipefail

OUTFILE="docs/api/traust.md"

echo "Generating $OUTFILE ..."
pydoc-markdown > "$OUTFILE"
echo "Done — $OUTFILE updated."
