"""Configuration constants and settings manager for LyricIsland."""

import json
import os
import threading
from pathlib import Path

APP_NAME = "LyricIsland"
VERSION = "1.2.0"

DEFAULT_COMPACT_WIDTH = 400
DEFAULT_COMPACT_HEIGHT = 68
EXPANDED_WIDTH = 400
EXPANDED_HEIGHT = 500
CORNER_RADIUS = 24
EXPANDED_CORNER_RADIUS = 16

POLL_INTERVAL = 0.1

LRCLIB_BASE_URL = "https://lrclib.net/api"

BG_COLOR = (0.0, 0.0, 0.0, 0.75)
TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)
DIM_TEXT_COLOR = (1.0, 1.0, 1.0, 0.4)
ACCENT_COLOR = (0.3, 0.5, 1.0, 1.0)

FONT_TITLE = ("SF Pro Display", 12)
FONT_LYRIC = ("SF Pro Display", 11)
FONT_ACTIVE_LINE = ("SF Pro Display", 20)
FONT_NORMAL_LINE = ("SF Pro Display", 16)

FLOAT_PRESETS = [
    ("标准", 400, 68),
    ("宽大", 520, 80),
    ("超大", 640, 90),
]

_DELAY_MIN = -500
_DELAY_MAX = 500
_DELAY_STEP = 50


def _settings_path():
    return Path.home() / ".lyricisland" / "settings.json"


_DEFAULT_SETTINGS = {
    "compact_width": DEFAULT_COMPACT_WIDTH,
    "compact_height": DEFAULT_COMPACT_HEIGHT,
    "lyric_delay_ms": 0,
    "ktv_mode": False,
    "lyric_color": "#FFFFFF",
    "ktv_color": "#5B8CFF",
    "show_touchbar_lyrics": True,
}


class SettingsManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = dict(_DEFAULT_SETTINGS)
        self._callbacks = []
        self._load()

    def _load(self):
        p = _settings_path()
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for k in _DEFAULT_SETTINGS:
                    if k in saved:
                        self._data[k] = saved[k]
            except Exception:
                pass

    def _save(self):
        p = _settings_path()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key, value):
        with self._lock:
            self._data[key] = value
            self._save()
        for cb in self._callbacks:
            try:
                cb(key, value)
            except Exception:
                pass

    def on_change(self, callback):
        self._callbacks.append(callback)

    @property
    def compact_width(self):
        return self.get("compact_width", DEFAULT_COMPACT_WIDTH)

    @property
    def compact_height(self):
        return self.get("compact_height", DEFAULT_COMPACT_HEIGHT)

    @property
    def lyric_delay_ms(self):
        return self.get("lyric_delay_ms", 0)

    @property
    def ktv_mode(self):
        return self.get("ktv_mode", False)

    @property
    def lyric_color(self):
        return self.get("lyric_color", "#FFFFFF")

    @property
    def ktv_color(self):
        return self.get("ktv_color", "#5B8CFF")

    @property
    def show_touchbar_lyrics(self):
        return self.get("show_touchbar_lyrics", True)


settings = SettingsManager()
