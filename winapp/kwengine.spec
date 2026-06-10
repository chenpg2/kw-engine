# PyInstaller (>= 6.0) spec — builds dist/KWEngine.exe (onefile, windowed).
# Run from the winapp/ directory:  pyinstaller kwengine.spec --noconfirm

a = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=[("assets/icon.png", "assets"), ("assets/icon.ico", "assets")],
    hiddenimports=["keyring.backends.Windows"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "PIL"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="KWEngine",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/icon.ico",
)
