# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

certifi_data = collect_data_files("certifi")

a = Analysis(
    ["launcher_beta.py"],
    pathex=[],
    binaries=[],
    datas=certifi_data,
    hiddenimports=["keyauth_helper", "loading_assets"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FiveM-Farming-Beta-Launcher",
    icon=["app-icon.ico"],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
