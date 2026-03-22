# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(os.getcwd())

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
pil_datas, pil_binaries, pil_hiddenimports = collect_all("PIL")

datas = []
datas += ctk_datas
datas += pil_datas

binaries = []
binaries += ctk_binaries
binaries += pil_binaries

hiddenimports = []
hiddenimports += ctk_hiddenimports
hiddenimports += pil_hiddenimports
hiddenimports += ["fitz"]

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(project_root / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BankTrace",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "bank_trace.ico"),
    version=str(project_root / "version_info.txt"),
)