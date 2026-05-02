"""Configuration constants for LyricIsland."""

APP_NAME = "LyricIsland"
VERSION = "1.0.0"

# Window dimensions
COMPACT_WIDTH = 400
COMPACT_HEIGHT = 68
EXPANDED_WIDTH = 400
EXPANDED_HEIGHT = 500
CORNER_RADIUS = 24
EXPANDED_CORNER_RADIUS = 16

# Sync engine
POLL_INTERVAL = 0.1  # seconds between playback position checks

# LRCLIB API
LRCLIB_BASE_URL = "https://lrclib.net/api"

# Colors (dark theme)
BG_COLOR = (0.0, 0.0, 0.0, 0.75)  # RGBA
TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)
DIM_TEXT_COLOR = (1.0, 1.0, 1.0, 0.4)
ACCENT_COLOR = (0.3, 0.5, 1.0, 1.0)

# Fonts
FONT_TITLE = ("SF Pro Display", 12)
FONT_LYRIC = ("SF Pro Display", 11)
FONT_ACTIVE_LINE = ("SF Pro Display", 20)
FONT_NORMAL_LINE = ("SF Pro Display", 16)
