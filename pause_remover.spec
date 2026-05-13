# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[
        ('bin/ffmpeg', 'bin'),
        ('bin/ffprobe', 'bin'),
    ],
    datas=[],
    hiddenimports=[
        'scripts.core',
        'scripts.build_segments',
        'scripts.cut_merge',
        'scripts.detect_silence',
        'scripts.logger',
        'scripts.probe',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['faster_whisper'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VideoEditor',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='VideoEditor',
)

app = BUNDLE(
    coll,
    name='Video Editor.app',
    icon='AppIcon.icns',
    bundle_identifier='com.michxlai.videoeditor',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.1.0',
        'CFBundleName': 'Video Editor',
        'NSHumanReadableCopyright': '2025 michxlai',
    },
)
