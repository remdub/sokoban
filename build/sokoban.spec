# sokoban.spec — PyInstaller spec file
# Usage: pyinstaller build/sokoban.spec

import sys
import os
block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=[os.path.abspath('../')],
    binaries=[],
    datas=[
        ('../assets', 'assets'),
        ('../levels',  'levels'),
    ],
    hiddenimports=['pygame._sdl2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'distutils', 'pydoc', 'doctest', 'pdb'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sokoban',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,    # no console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='sokoban',
)
