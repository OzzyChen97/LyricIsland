"""Fetch synced lyrics from LRCLIB API."""

import re
import threading
from dataclasses import dataclass, field
from typing import Optional

import requests

from config import LRCLIB_BASE_URL


@dataclass
class LyricLine:
    time: float  # seconds
    text: str


def parse_lrc(lrc_text: str) -> list[LyricLine]:
    """Parse LRC format lyrics into a list of timed lines."""
    lines = []
    pattern = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")

    for raw_line in lrc_text.strip().split("\n"):
        match = pattern.match(raw_line)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            millis = int(match.group(3))
            if len(match.group(3)) == 2:
                millis *= 10
            time = minutes * 60 + seconds + millis / 1000.0
            text = match.group(4).strip()
            if text:
                lines.append(LyricLine(time=time, text=text))

    lines.sort(key=lambda l: l.time)
    return lines


def fetch_lyrics(title: str, artist: str, album: str = "", duration: float = 0) -> list[LyricLine]:
    """Fetch synced lyrics from LRCLIB. Returns empty list if not found."""
    try:
        params = {
            "track_name": title,
            "artist_name": artist,
        }
        if album:
            params["album_name"] = album
        if duration > 0:
            params["duration"] = int(duration)

        resp = requests.get(f"{LRCLIB_BASE_URL}/get", params=params, timeout=5)

        if resp.status_code == 200:
            data = resp.json()
            synced = data.get("syncedLyrics")
            if synced:
                return parse_lrc(synced)
            # Fall back to plain lyrics (no timing)
            plain = data.get("plainLyrics")
            if plain:
                return [LyricLine(time=0, text=line) for line in plain.split("\n") if line.strip()]

        # Try search endpoint as fallback
        resp = requests.get(f"{LRCLIB_BASE_URL}/search", params=params, timeout=5)
        if resp.status_code == 200:
            results = resp.json()
            if results:
                synced = results[0].get("syncedLyrics")
                if synced:
                    return parse_lrc(synced)

    except Exception:
        pass

    return []


def fetch_lyrics_async(title: str, artist: str, album: str = "", duration: float = 0,
                       callback=None):
    """Fetch lyrics in a background thread."""
    def _fetch():
        lines = fetch_lyrics(title, artist, album, duration)
        if callback:
            callback(lines)

    thread = threading.Thread(target=_fetch, daemon=True)
    thread.start()
