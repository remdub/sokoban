#!/usr/bin/env bash
# build_windows.sh — Cross-build for Windows 7 via Wine + Python 3.8
# Requires: wine, Python 3.8.x Windows installer downloaded
set -e

PYTHON_INSTALLER="${1:-python-3.8.20.exe}"
wine_python() { script -qefc "wine python.exe $*" /dev/null; }
WINE_PYTHON=wine_python

echo "Installing Python 3.8 under Wine..."
wine "$PYTHON_INSTALLER" /quiet InstallAllUsers=0 PrependPath=1 || true

$WINE_PYTHON -m pip install --quiet pygame-ce==2.1.4 pyinstaller==5.13.2

cd "$(dirname "$0")/.."
$WINE_PYTHON -m PyInstaller build/sokoban.spec --distpath dist_win --workpath build/work_win --noconfirm

echo ""
echo "Windows build complete: dist_win/sokoban/"
echo "Zip and distribute: zip -r sokoban_win.zip dist_win/sokoban/"
