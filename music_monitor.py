"""Monitor Apple Music playback state and current song info."""

import objc
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from Foundation import NSObject, NSDistributedNotificationCenter, NSTimer
from ScriptingBridge import SBApplication


@dataclass
class SongInfo:
    title: str = ""
    artist: str = ""
    album: str = ""
    duration: float = 0.0
    id: str = ""


class MusicMonitor:
    """Detects Apple Music playback and retrieves song info."""

    def __init__(self):
        self.current_song: Optional[SongInfo] = None
        self.is_playing: bool = False
        self.playback_time: float = 0.0
        self._on_song_changed: Optional[Callable] = None
        self._music_app = None
        self._timer = None
        self._last_song_id: str = ""
        self._observer = None

    def set_on_song_changed(self, callback: Callable):
        self._on_song_changed = callback

    def start(self):
        """Start monitoring Apple Music."""
        self._get_music_app()
        self._observe_distributed_notifications()
        self._start_polling()

    def stop(self):
        """Stop monitoring."""
        if self._timer:
            self._timer.invalidate()
            self._timer = None
        if self._observer:
            NSDistributedNotificationCenter.defaultCenter().removeObserver_(self._observer)

    def _get_music_app(self):
        """Get ScriptingBridge reference to Music.app."""
        try:
            self._music_app = SBApplication.applicationWithBundleIdentifier_("com.apple.Music")
        except Exception:
            self._music_app = None

    def _observe_distributed_notifications(self):
        """Listen for Apple Music player state changes."""
        center = NSDistributedNotificationCenter.defaultCenter()

        class Observer(NSObject):
            def initWithMonitor_(self, monitor):
                self = objc.super(Observer, self).init()
                if self is None:
                    return None
                self._monitor = monitor
                return self

            def handlePlayerInfo_(self, notification):
                self._monitor._on_notification(notification)

        self._observer = Observer.alloc().initWithMonitor_(self)
        center.addObserver_selector_name_object_(
            self._observer,
            "handlePlayerInfo:",
            "com.apple.Music.playerInfo",
            None,
        )

    def _on_notification(self, notification):
        """Handle distributed notification from Music.app."""
        info = notification.userInfo()
        if info is None:
            return

        state = info.get("Player State", "")
        if state == "Playing":
            self.is_playing = True
        elif state == "Paused":
            self.is_playing = False
        elif state == "Stopped":
            self.is_playing = False
            self.current_song = None
            self._last_song_id = ""
            return

        # Check for song change
        self._check_current_song()

    def _start_polling(self):
        """Start a timer that polls playback position."""
        # Use a background thread with a simple loop
        def poll_loop():
            import time
            while True:
                try:
                    self._update_state()
                except Exception:
                    pass
                time.sleep(0.2)

        thread = threading.Thread(target=poll_loop, daemon=True)
        thread.start()

    def _update_state(self):
        """Update playback state and position."""
        if self._music_app is None:
            self._get_music_app()
            if self._music_app is None:
                return

        try:
            player_state = self._music_app.playerState()
            # Music.app ScriptingBridge states:
            # 1800426320 (0x6B505350) = playing
            # 1800426352 (0x6B505370) = paused
            # 1800426323 (0x6B505353) = stopped
            # 0 = stopped (when app just launched)
            if player_state == 1800426320:
                self.is_playing = True
            else:
                self.is_playing = False

            if self.is_playing:
                self.playback_time = self._music_app.playerPosition()
            self._check_current_song()
        except Exception:
            self._music_app = None

    def _check_current_song(self):
        """Check if the current song has changed."""
        if self._music_app is None:
            return

        try:
            track = self._music_app.currentTrack()
            if track is None:
                if self.current_song is not None:
                    self.current_song = None
                    self._last_song_id = ""
                return

            # name() returns None when nothing is actually playing
            title = track.name()
            if not title:
                if self.current_song is not None:
                    self.current_song = None
                    self._last_song_id = ""
                return

            artist = track.artist() or ""
            album = track.album() or ""
            duration = track.duration() or 0
            persistent_id = track.persistentID() or ""

            song_id = f"{title}|{artist}"

            if song_id != self._last_song_id:
                self._last_song_id = song_id
                self.current_song = SongInfo(
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                    id=str(persistent_id),
                )
                if self._on_song_changed:
                    self._on_song_changed(self.current_song)
        except Exception:
            pass

    def toggle_play_pause(self):
        """Toggle play/pause."""
        if self._music_app:
            try:
                self._music_app.playpause()
            except Exception:
                pass

    def next_track(self):
        """Skip to next track."""
        if self._music_app:
            try:
                self._music_app.nextTrack()
            except Exception:
                pass

    def previous_track(self):
        """Skip to previous track."""
        if self._music_app:
            try:
                self._music_app.previousTrack()
            except Exception:
                pass
