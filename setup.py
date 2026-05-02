"""py2app setup script for LyricIsland."""

from setuptools import setup

APP = ['app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'includes': [
        'objc',
        'AppKit',
        'Foundation',
        'Quartz',
        'ScriptingBridge',
        'requests',
        'config',
        'music_monitor',
        'lyrics_fetcher',
        'sync_engine',
        'floating_window',
    ],
    'excludes': [
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
    ],
    'plist': {
        'CFBundleName': 'LyricIsland',
        'CFBundleDisplayName': 'LyricIsland',
        'CFBundleIdentifier': 'com.lyricisland.app',
        'CFBundleVersion': '1.1.0',
        'CFBundleShortVersionString': '1.1.0',
        'LSMinimumSystemVersion': '12.0',
        'LSUIElement': True,  # Hide from Dock
        'NSHighResolutionCapable': True,
    },
    'iconfile': None,  # Can add .icns file later
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
