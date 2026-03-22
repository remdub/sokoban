#!/usr/bin/env bash
# build_linux.sh — Build Sokoban for Linux using Python 3.8+
set -e

cd "$(dirname "$0")/.."

# Create venv if needed
if [ ! -d venv ]; then
    python3.8 -m venv venv || python3 -m venv venv
fi

source venv/bin/activate
pip install --quiet pygame-ce==2.1.4 pyinstaller==5.13.2

pyinstaller build/sokoban.spec --distpath dist --workpath build/work --noconfirm

echo ""
echo "Build complete: dist/sokoban/"
echo "Run with: dist/sokoban/sokoban"
