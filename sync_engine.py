"""Sync engine: matches playback position to lyric lines."""

import threading

from lyrics_fetcher import LyricLine


class SyncEngine:
    """Tracks which lyric line is currently active."""

    def __init__(self):
        self._lock = threading.Lock()
        self.lines: list[LyricLine] = []
        self.current_index: int = -1
        self.line_progress: float = 0.0  # 0.0 to 1.0
        self._has_timing: bool = False

    def set_lyrics(self, lines: list[LyricLine]):
        """Set new lyrics and reset state."""
        with self._lock:
            self.lines = lines
            self._has_timing = any(l.time > 0 for l in lines)
            self.current_index = -1
            self.line_progress = 0.0

    def clear(self):
        """Clear all lyrics."""
        with self._lock:
            self.lines = []
            self.current_index = -1
            self.line_progress = 0.0
            self._has_timing = False

    def update(self, playback_time: float):
        """Update the current line based on playback position."""
        with self._lock:
            if not self.lines or not self._has_timing:
                return

            new_index = self._find_line_index(playback_time)
            self.current_index = new_index

            if 0 <= new_index < len(self.lines):
                line = self.lines[new_index]
                if new_index < len(self.lines) - 1:
                    end_time = self.lines[new_index + 1].time
                else:
                    end_time = line.time + 5.0

                duration = end_time - line.time
                if duration > 0:
                    self.line_progress = min(1.0, max(0.0, (playback_time - line.time) / duration))
                else:
                    self.line_progress = 0.0
            else:
                self.line_progress = 0.0

    def get_current(self) -> tuple[int, str]:
        """Thread-safe snapshot of current index and text."""
        with self._lock:
            idx = self.current_index
            if 0 <= idx < len(self.lines):
                return idx, self.lines[idx].text
            return -1, ""

    def _find_line_index(self, time: float) -> int:
        """Binary search for the current lyric line."""
        if not self.lines:
            return -1

        low, high = 0, len(self.lines) - 1
        result = -1

        while low <= high:
            mid = (low + high) // 2
            if self.lines[mid].time <= time:
                result = mid
                low = mid + 1
            else:
                high = mid - 1

        return result
