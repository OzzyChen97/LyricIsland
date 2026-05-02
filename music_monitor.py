"""Monitor Apple Music playback state using osascript (no PyObjC/ScriptingBridge)."""

import os
import subprocess
import threading
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class SongInfo:
    title: str = ""
    artist: str = ""
    album: str = ""
    duration: float = 0.0
    id: str = ""
    art_path: str = ""


_SCRIPT = '''
tell application "Music"
    if it is running then
        set playerState to player state as string
        set pos to player position
        if player state is playing or player state is paused then
            set t to name of current track
            set a to artist of current track
            set al to album of current track
            set d to duration of current track
            return playerState & "\\n" & (pos as string) & "\\n" & t & "\\n" & a & "\\n" & al & "\\n" & (d as string)
        else
            return playerState & "\\n0\\n\\n\\n\\n0"
        end if
    else
        return "stopped\\n0\\n\\n\\n\\n0"
    end if
end tell
'''


class MusicMonitor:
    """Detects Apple Music playback using osascript subprocess calls.

    Polls in a background thread to avoid blocking the main run loop.
    """

    def __init__(self):
        self.current_song: Optional[SongInfo] = None
        self.is_playing: bool = False
        self.playback_time: float = 0.0
        self._on_song_changed: Optional[Callable] = None
        self._on_art_ready: Optional[Callable] = None
        self._on_state_changed: Optional[Callable] = None
        self._last_song_id: str = ""
        self._last_playing: bool = False
        self._polling = False
        self._lock = threading.Lock()

    def set_on_song_changed(self, callback: Callable):
        self._on_song_changed = callback

    def set_on_art_ready(self, callback: Callable):
        self._on_art_ready = callback

    def set_on_state_changed(self, callback: Callable):
        self._on_state_changed = callback

    def start(self):
        pass

    def stop(self):
        self._polling = False

    def poll(self):
        """Kick off a background poll if one isn't already running."""
        if self._polling:
            return
        self._polling = True
        threading.Thread(target=self._do_poll, daemon=True).start()

    def _do_poll(self):
        try:
            result = subprocess.run(
                ["osascript", "-e", _SCRIPT],
                capture_output=True, text=True, timeout=3,
            )
            output = result.stdout.strip()
        except Exception:
            output = ""
        finally:
            self._polling = False

        if not output:
            return

        parts = output.split("\n", 5)
        if len(parts) < 6:
            return

        state_str, pos_str, title, artist, album, dur_str = parts

        with self._lock:
            was_playing = self.is_playing
            self.is_playing = (state_str == "playing")
            try:
                self.playback_time = float(pos_str)
            except ValueError:
                self.playback_time = 0.0

            state_cb = None
            if was_playing != self.is_playing:
                self._last_playing = self.is_playing
                state_cb = self._on_state_changed

            if title:
                song_id = f"{title}|{artist}"
                if song_id != self._last_song_id:
                    self._last_song_id = song_id
                    try:
                        duration = float(dur_str)
                    except ValueError:
                        duration = 0.0
                    self.current_song = SongInfo(
                        title=title, artist=artist, album=album, duration=duration,
                    )
                    threading.Thread(target=self._fetch_album_art, daemon=True).start()
                    cb = self._on_song_changed
                else:
                    cb = None
            else:
                if self.current_song is not None:
                    self.current_song = None
                    self._last_song_id = ""
                cb = None

        if cb:
            cb(self.current_song)

        if state_cb:
            state_cb(self.is_playing)

    def _fetch_album_art(self):
        art_path = "/tmp/lyric_island_art.jpg"
        try:
            os.remove(art_path)
        except OSError:
            pass
        script = (
            'tell application "Music"\n'
            '    if player state is playing or player state is paused then\n'
            '        tell artwork 1 of current track\n'
            '            set d to raw data\n'
            '        end tell\n'
            '        set f to POSIX file "' + art_path + '"\n'
            '        set fp to open for access f with write permission\n'
            '        write d to fp\n'
            '        close access fp\n'
            '        return "ok"\n'
            '    end if\n'
            '    return "no"\n'
            'end tell'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5,
            )
            if os.path.exists(art_path) and os.path.getsize(art_path) > 0:
                with self._lock:
                    if self.current_song:
                        self.current_song.art_path = art_path
                if self._on_art_ready:
                    self._on_art_ready(art_path)
        except Exception:
            pass

    def toggle_play_pause(self):
        threading.Thread(
            target=lambda: subprocess.run(
                ["osascript", "-e", 'tell application "Music" to playpause'],
                capture_output=True, timeout=3,
            ),
            daemon=True,
        ).start()

    def next_track(self):
        threading.Thread(
            target=lambda: subprocess.run(
                ["osascript", "-e", 'tell application "Music" to next track'],
                capture_output=True, timeout=3,
            ),
            daemon=True,
        ).start()

    def previous_track(self):
        threading.Thread(
            target=lambda: subprocess.run(
                ["osascript", "-e", 'tell application "Music" to previous track'],
                capture_output=True, timeout=3,
            ),
            daemon=True,
        ).start()
