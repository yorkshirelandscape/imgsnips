# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('imgsnips.png', '.'), ('fonts', 'fonts'),
        # icons/source/ holds the editable Inkscape originals, not needed at
        # runtime -- only the Qt-rendered SVGs actually get bundled.
        ('icons/flip-horizontal.svg', 'icons'), ('icons/flip-vertical.svg', 'icons'),
        ('icons/rotate-right.svg', 'icons'), ('icons/rotate-left.svg', 'icons'),
    ],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='ImgSnips',
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
    icon=['packaging/icon/imgsnips.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ImgSnips',
)
app = BUNDLE(
    coll,
    name='ImgSnips.app',
    icon='packaging/icon/imgsnips.icns',
    bundle_identifier='com.yorkshirelandscape.imgsnips',
    info_plist={
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'PDF Document',
                # 'Viewer', not 'Editor': ImgSnips reads a PDF to pull
                # images out of it, it doesn't edit/save the PDF itself.
                'CFBundleTypeRole': 'Viewer',
                # 'Alternate', not 'Owner'/'Default': appear in Finder's
                # "Open With" list without trying to become the default
                # PDF handler, which would be surprising for a niche tool.
                'LSHandlerRank': 'Alternate',
                'LSItemContentTypes': ['com.adobe.pdf'],
            },
        ],
    },
)
