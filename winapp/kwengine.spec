# PyInstaller spec — builds dist/KWEngine.exe (onefile, windowed).
# Run from the winapp/ directory:  pyinstaller kwengine.spec --noconfirm

import os

block_cipher = None
here = os.path.dirname(os.path.abspath(SPECPATH)) if os.path.isfile(SPECPATH) else SPECPATH

a = Analysis(
    ["src/kwengine_app/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[("assets/icon.png", "assets"), ("assets/icon.ico", "assets")],
    hiddenimports=[
        "keyring.backends.Windows",
        "keyring.backends.SecretService",
        "keyring.backends.macOS",
        "win32ctypes.pywin32",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "PIL"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="KWEngine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)
