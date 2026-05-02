"""LyricIsland - Floating lyrics for Apple Music on macOS."""

import objc

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyProhibited,
    NSColor,
    NSFont,
    NSImage,
    NSMakePoint,
    NSMenu,
    NSMenuItem,
    NSSize,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject, NSTimer

from config import POLL_INTERVAL, COMPACT_WIDTH, COMPACT_HEIGHT
from music_monitor import MusicMonitor
from lyrics_fetcher import fetch_lyrics_async
from sync_engine import SyncEngine
from floating_window import FloatingWindow, LyricsContentView, _ns, _attrs

_pending = []


class _Dispatcher(NSObject):
    def initWithCallback_(self, cb):
        self = objc.super(_Dispatcher, self).init()
        if self is None:
            return None
        self._cb = cb
        return self

    def invoke_(self, _=None):
        if self in _pending:
            _pending.remove(self)
        if self._cb:
            self._cb()
            self._cb = None


def _on_main(fn, *args):
    def call():
        fn(*args)
    d = _Dispatcher.alloc().initWithCallback_(call)
    _pending.append(d)
    d.performSelectorOnMainThread_withObject_waitUntilDone_("invoke:", None, False)


class _PollTarget(NSObject):
    def initWithCtl_(self, ctl):
        self = objc.super(_PollTarget, self).init()
        if self is None:
            return None
        self._ctl = ctl
        return self

    def tick_(self, timer):
        try:
            self._ctl.music_monitor.poll()
        except Exception:
            pass


class _SyncTarget(NSObject):
    def initWithCtl_(self, ctl):
        self = objc.super(_SyncTarget, self).init()
        if self is None:
            return None
        self._ctl = ctl
        return self

    def tick_(self, timer):
        try:
            mm = self._ctl.music_monitor
            if mm.is_playing:
                self._ctl.sync_engine.update(mm.playback_time)
                idx, text = self._ctl.sync_engine.get_current()
                self._ctl.content_view.set_current_line(text, idx)
                lines = self._ctl.sync_engine.lines
                if 0 <= idx < len(lines) - 1:
                    self._ctl.content_view.set_next_line(lines[idx + 1].text)
                else:
                    self._ctl.content_view.set_next_line("")
                self._ctl.content_view.set_playing(True)
        except Exception:
            pass


class _AnimTarget(NSObject):
    def initWithCtl_(self, ctl):
        self = objc.super(_AnimTarget, self).init()
        if self is None:
            return None
        self._ctl = ctl
        return self

    def tick_(self, timer):
        try:
            cv = self._ctl.content_view
            mm = self._ctl.music_monitor
            if cv:
                cv.set_needs_animation(mm.is_playing)
        except Exception:
            pass


class LyricIslandController:
    def __init__(self):
        self.music_monitor = MusicMonitor()
        self.sync_engine = SyncEngine()
        self.current_lines = []
        self.is_expanded = False
        self.window = None
        self.content_view = None
        self.status_item = None

    def start(self):
        self._create_status_item()
        self._create_floating_window()
        self.music_monitor.set_on_song_changed(self._on_song_changed)
        self.music_monitor.set_on_art_ready(self._on_art_ready)
        self.music_monitor.set_on_state_changed(self._on_state_changed)
        self.music_monitor.start()
        self._start_poll_timer()
        self._start_sync_timer()
        self._start_animation_timer()

    def stop(self):
        self.music_monitor.stop()

    def _create_status_item(self):
        status_bar = NSStatusBar.systemStatusBar()
        self.status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        font = NSFont.systemFontOfSize_(16)
        size = NSSize(20, 20)
        image = NSImage.alloc().initWithSize_(size)
        image.lockFocus()
        color = NSColor.whiteColor()
        t = _ns("\u266a")
        a = _attrs(font, color)
        ts = t.sizeWithAttributes_(a)
        t.drawAtPoint_withAttributes_(
            NSMakePoint((size.width - ts.width) / 2, (size.height - ts.height) / 2),
            a,
        )
        image.unlockFocus()
        image.setSize_((18, 18))
        self.status_item.button().setImage_(image)

        menu = NSMenu.alloc().init()
        quit = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit LyricIsland", "terminate:", "q"
        )
        menu.addItem_(quit)
        self.status_item.setMenu_(menu)

    def _create_floating_window(self):
        cv = LyricsContentView.alloc().initWithFrame_(((0, 0), (COMPACT_WIDTH, COMPACT_HEIGHT)))
        cv.set_callbacks(on_toggle_expand=self._on_toggle_expand)
        self.window = FloatingWindow.alloc().initWithContent_(cv)
        self.content_view = cv
        self.window.orderFront_(None)

    def _start_poll_timer(self):
        t = _PollTarget.alloc().initWithCtl_(self)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.5, t, "tick:", None, True
        )
        self._poll_target = t

    def _start_sync_timer(self):
        t = _SyncTarget.alloc().initWithCtl_(self)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            POLL_INTERVAL, t, "tick:", None, True
        )
        self._sync_target = t

    def _start_animation_timer(self):
        t = _AnimTarget.alloc().initWithCtl_(self)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, t, "tick:", None, True
        )
        self._anim_target = t

    def _on_song_changed(self, song):
        _on_main(self._update_ui_for_song, song)

    def _on_art_ready(self, art_path):
        _on_main(self._apply_album_art, art_path)

    def _on_state_changed(self, is_playing):
        _on_main(self._apply_play_state, is_playing)

    def _update_ui_for_song(self, song):
        self.content_view.set_song(song.title, song.artist)
        self.content_view.set_playing(True)
        self.content_view.set_album_art(song.art_path)
        fetch_lyrics_async(
            song.title, song.artist, song.album, song.duration,
            callback=self._on_lyrics_fetched,
        )

    def _on_lyrics_fetched(self, lines):
        _on_main(self._apply_lyrics, lines)

    def _apply_lyrics(self, lines):
        self.current_lines = lines
        self.sync_engine.set_lyrics(lines)
        self.content_view.set_lyrics(lines)

    def _apply_album_art(self, art_path):
        self.content_view.set_album_art(art_path)

    def _apply_play_state(self, is_playing):
        self.content_view.set_playing(is_playing)

    def _on_toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.content_view.set_expanded(self.is_expanded)
        self.window.set_expanded(self.is_expanded)


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

    ctl = LyricIslandController()
    ctl.start()

    app.run()


if __name__ == "__main__":
    main()
