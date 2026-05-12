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
    name='PauseRemover',
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
    name='PauseRemover',
)

app = BUNDLE(
    coll,
    name='PauseRemover.app',
    icon=None,
    bundle_identifier='com.michxlai.pauseremover',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleName': 'Pause Remover',
        'NSHumanReadableCopyright': '2025 michxlai',
    },
)
