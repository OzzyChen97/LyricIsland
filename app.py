"""LyricIsland - Floating lyrics for Apple Music on macOS."""

import objc

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
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

from config import settings
from core.music_monitor import MusicMonitor
from core.lyrics_fetcher import fetch_lyrics_async
from core.sync_engine import SyncEngine
from ui.floating_window import FloatingWindow, LyricsContentView, _ns, _attrs
from ui.home_window import HomeWindowController
from ui.touchbar import TouchBarLyricDelegate

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
                delay_s = settings.lyric_delay_ms / 1000.0
                adjusted_time = mm.get_playback_time() + delay_s
                self._ctl.sync_engine.update(adjusted_time)
                idx, text = self._ctl.sync_engine.get_current()
                self._ctl.content_view.set_current_line(text, idx)
                self._ctl.content_view.set_line_progress(self._ctl.sync_engine.line_progress)
                lines = self._ctl.sync_engine.lines
                if 0 <= idx < len(lines) - 1:
                    self._ctl.content_view.set_next_line(lines[idx + 1].text)
                else:
                    self._ctl.content_view.set_next_line("")
                self._ctl.content_view.set_playing(True)

                if self._ctl._touchbar_delegate and settings.show_touchbar_lyrics:
                    self._ctl._touchbar_delegate.setLyric_(text)
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


class LyricIslandController(NSObject):
    window = None
    content_view = None
    status_item = None
    _home_ctrl = None
    _touchbar_delegate = None
    music_monitor = None
    sync_engine = None
    current_lines = None
    is_expanded = False

    def init(self):
        self = objc.super(LyricIslandController, self).init()
        if self is None:
            return None
        self.music_monitor = MusicMonitor()
        self.sync_engine = SyncEngine()
        self.current_lines = []
        return self

    def start(self):
        self._create_status_item()
        self._create_floating_window()
        self._create_home_window()
        self._create_touchbar()
        self.music_monitor.set_on_song_changed(self._on_song_changed)
        self.music_monitor.set_on_art_ready(self._on_art_ready)
        self.music_monitor.set_on_state_changed(self._on_state_changed)
        self.music_monitor.start()
        self._start_poll_timer()
        self._start_sync_timer()
        self._start_animation_timer()

    def stop(self):
        self.music_monitor.stop()
        if self._touchbar_delegate:
            self._touchbar_delegate.deactivate()

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

        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "\u2699 \u8bbe\u7f6e...", "showSettings:", "s"
        )
        settings_item.setTarget_(self)
        menu.addItem_(settings_item)

        menu.addItem_(NSMenuItem.separatorItem())

        quit = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit LyricIsland", "terminate:", "q"
        )
        menu.addItem_(quit)
        self.status_item.setMenu_(menu)

    def showSettings_(self, sender):
        if self._home_ctrl:
            self._home_ctrl.show_window()

    def _create_floating_window(self):
        cv = LyricsContentView.alloc().initWithFrame_(((0, 0), (settings.compact_width, settings.compact_height)))
        cv.set_callbacks(on_toggle_expand=self._on_toggle_expand)
        self.window = FloatingWindow.alloc().initWithContent_(cv)
        self.content_view = cv
        self.window.orderFront_(None)

    def _create_home_window(self):
        self._home_ctrl = HomeWindowController.alloc().init()
        self._home_ctrl.set_callbacks(
            on_size_changed=self._on_size_changed,
            on_delay_changed=self._on_delay_changed,
            on_color_changed=self._on_color_changed,
            on_ktv_changed=self._on_ktv_changed,
            on_touchbar_changed=self._on_touchbar_setting_changed,
        )

    def _create_touchbar(self):
        self._touchbar_delegate = TouchBarLyricDelegate.alloc().init()
        if settings.show_touchbar_lyrics:
            self._touchbar_delegate.activate()

    def _on_size_changed(self, w, h):
        if self.content_view:
            self.content_view.update_compact_size(w, h)

    def _on_delay_changed(self, val):
        pass

    def _on_color_changed(self, key, hex_str):
        if self.content_view:
            self.content_view.setNeedsDisplay_(True)

    def _on_ktv_changed(self, enabled):
        if self.content_view:
            self.content_view.setNeedsDisplay_(True)

    def _on_touchbar_setting_changed(self, enabled):
        if self._touchbar_delegate:
            if enabled:
                self._touchbar_delegate.activate()
            else:
                self._touchbar_delegate.deactivate()

    def _start_poll_timer(self):
        t = _PollTarget.alloc().initWithCtl_(self)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.5, t, "tick:", None, True
        )
        self._poll_target = t

    def _start_sync_timer(self):
        t = _SyncTarget.alloc().initWithCtl_(self)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.04, t, "tick:", None, True
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
        if self._touchbar_delegate:
            self._touchbar_delegate.updateSongInfo_artist_(song.title, song.artist)
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
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    ctl = LyricIslandController.alloc().init()
    ctl.retain()
    ctl.start()

    app.run()


if __name__ == "__main__":
    main()
