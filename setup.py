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
        'core',
        'core.music_monitor',
        'core.lyrics_fetcher',
        'core.sync_engine',
        'ui',
        'ui.floating_window',
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
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
    },
    'iconfile': None,
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
