# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

a = Analysis(
    ['ygt.py'],
    pathex=[],
    binaries=[],
    datas=[('ygt/icons/*.png', 'icons'), ('ygt/fonts/*.ttf', 'fonts')],
    hiddenimports=['xgridfit.xgridfit', 'xgridfit.ygridfit', 'xgridfit.xgfUFOWriter'],
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='ygt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ygt',
)
app = BUNDLE(
    coll,
    name='ygt.app',
    icon='icons/ygt.ico',
    bundle_identifier=None,
)
