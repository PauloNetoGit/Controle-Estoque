# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['estoqueMax.py'],
    pathex=[],
    binaries=[],
    datas=[('img', 'img'), ('estoque.db', '.'), ('font', 'font'), ('C:/Users/Teste/AppData/Local/Programs/Python/Python38/lib/site-packages/barcode/fonts', 'barcode/fonts')],
    hiddenimports=['PIL', 'barcode', 'qrcode', 'reportlab'],
    hookspath=[],
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
    a.binaries,
    a.zipfiles,
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
