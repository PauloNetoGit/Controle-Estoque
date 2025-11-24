# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['estoqueMax.py'],
    pathex=[],
    binaries=[],
    datas=[('img', 'img'), ('estoque.db', '.'), ('font', 'font'), ('C:/Users/Teste/AppData/Local/Programs/Python/Python314/Lib/site-packages/barcode/fonts', 'barcode/fonts')],
    hiddenimports=['PIL', 'barcode', 'qrcode', 'reportlab'],
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
    name='estoqueMax',
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
    icon=['img\\supermarket.ico'],
)
