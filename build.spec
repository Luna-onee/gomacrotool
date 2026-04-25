# -*- mode: python ; coding: utf-8 -*-
import os
icon_file = 'C:\\Users\\Jaide\\Documents\\Projects\\macrotool\\icon.ico'
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('_native.pyd', '.'),
        ('icon.ico', '.'),
        ('modules/gui/__qss_cache', 'modules/gui/__qss_cache'),
    ],
    hiddenimports=['ckdl'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Jaide's Macro Tool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='C:\\Users\\Jaide\\Documents\\Projects\\macrotool\\icon.ico',
)
