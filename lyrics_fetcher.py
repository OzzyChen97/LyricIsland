"""Fetch synced lyrics from LRCLIB, Netease, and Apple Music."""

import re
import subprocess
import threading
from dataclasses import dataclass

import requests

from config import LRCLIB_BASE_URL


@dataclass
class LyricLine:
    time: float
    text: str


def _parse_timestamp(ts: str) -> float:
    m = re.match(r"(\d{2}):(\d{2})\.(\d{2,3})", ts)
    if not m:
        return -1
    minutes = int(m.group(1))
    seconds = int(m.group(2))
    millis = int(m.group(3))
    if len(m.group(3)) == 2:
        millis *= 10
    return minutes * 60 + seconds + millis / 1000.0


def parse_lrc(lrc_text: str) -> list[LyricLine]:
    lines = []
    tag_pattern = re.compile(r"\[(\d{2}:\d{2}\.\d{2,3})\]")
    for raw_line in lrc_text.strip().split("\n"):
        tags = tag_pattern.findall(raw_line)
        if not tags:
            continue
        last_tag_end = raw_line.rfind("]") + 1
        text = raw_line[last_tag_end:].strip()
        if not text:
            continue
        for tag in tags:
            t = _parse_timestamp(tag)
            if t >= 0:
                lines.append(LyricLine(time=t, text=text))
    lines.sort(key=lambda l: l.time)
    return lines


def _fetch_apple_music_lyrics(duration: float = 0) -> list[LyricLine]:
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "Music" to get lyrics of current track'],
            capture_output=True, text=True, timeout=5,
        )
        text = result.stdout.strip()
        if not text or "got an error" in text.lower():
            return []
        lines_list = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines_list:
            return []
        if duration > 0 and len(lines_list) > 1:
            step = duration / len(lines_list)
            return [LyricLine(time=i * step, text=t) for i, t in enumerate(lines_list)]
        return [LyricLine(time=0, text=t) for t in lines_list]
    except Exception:
        return []


def _fetch_netease_lyrics(title: str, artist: str) -> list[LyricLine]:
    try:
        keyword = f"{title} {artist}"
        resp = requests.post(
            "https://music.163.com/api/search/get/web",
            data={"s": keyword, "type": 1, "limit": 5},
            headers={"Referer": "https://music.163.com/"},
            timeout=8,
        )
        if resp.status_code != 200:
            return []
        songs = resp.json().get("result", {}).get("songs", [])
        if not songs:
            return []
        song_id = songs[0]["id"]
        lrc_resp = requests.get(
            f"https://music.163.com/api/song/lyric?id={song_id}&lv=1&kv=1&tv=-1",
            headers={"Referer": "https://music.163.com/"},
            timeout=8,
        )
        if lrc_resp.status_code != 200:
            return []
        lrc_text = lrc_resp.json().get("lrc", {}).get("lyric", "")
        if not lrc_text:
            return []
        lines_list = parse_lrc(lrc_text)
        if lines_list:
            return lines_list
        return []
    except Exception:
        return []


def fetch_lyrics(title: str, artist: str, album: str = "", duration: float = 0) -> list[LyricLine]:
    result = _fetch_netease_lyrics(title, artist)
    if result:
        return result

    try:
        params: dict[str, str | int] = {
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
            plain = data.get("plainLyrics")
            if plain:
                plain_lines = [line for line in plain.split("\n") if line.strip()]
                if duration > 0 and len(plain_lines) > 1:
                    step = duration / len(plain_lines)
                    return [LyricLine(time=i * step, text=t)
                            for i, t in enumerate(plain_lines)]
                return [LyricLine(time=0, text=t) for t in plain_lines]

        resp = requests.get(f"{LRCLIB_BASE_URL}/search", params=params, timeout=5)
        if resp.status_code == 200:
            results = resp.json()
            if results:
                synced = results[0].get("syncedLyrics")
                if synced:
                    return parse_lrc(synced)
    except Exception:
        pass

    return _fetch_apple_music_lyrics(duration)


def fetch_lyrics_async(title: str, artist: str, album: str = "", duration: float = 0,
                       callback=None):
    """Fetch lyrics in a background thread."""
    def _fetch():
        lines = fetch_lyrics(title, artist, album, duration)
        if callback:
            callback(lines)

    thread = threading.Thread(target=_fetch, daemon=True)
    thread.start()
