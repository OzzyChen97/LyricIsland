"""LyricIsland - Floating lyrics for Apple Music on macOS."""

import sys
import time
import threading

from AppKit import (
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import (
    NSDate,
    NSObject,
    NSRunLoop,
    NSTimer,
)

from config import APP_NAME, POLL_INTERVAL
from music_monitor import MusicMonitor, SongInfo
from lyrics_fetcher import fetch_lyrics_async, LyricLine
from sync_engine import SyncEngine
from floating_window import FloatingWindow, LyricsContentView


class AppDelegate(NSObject):
    """Main application delegate - handles menu actions."""

    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self._controller = None
        return self

    def setController_(self, controller):
        self._controller = controller

    def togglePanel_(self, sender):
        if self._controller:
            self._controller.toggle_panel()

    def quit_(self, sender):
        if self._controller:
            self._controller.stop()
        NSApp.terminate_(None)


class LyricIslandController:
    """Main controller that wires everything together."""

    def __init__(self):
        self.music_monitor = MusicMonitor()
        self.sync_engine = SyncEngine()
        self.current_lines = []
        self.is_expanded = False
        self.window = None
        self.content_view = None
        self.status_item = None

    def start(self):
        """Initialize and start the app."""
        self._create_status_item()
        self._create_floating_window()

        # Wire callbacks
        self.music_monitor.set_on_song_changed(self._on_song_changed)

        # Start monitoring
        self.music_monitor.start()

        # Start sync timer
        self._start_sync_timer()

        # Start animation timer (for bars)
        self._start_animation_timer()

    def stop(self):
        """Stop the app."""
        self.music_monitor.stop()

    def _create_status_item(self):
        """Create menu bar status item."""
        status_bar = NSStatusBar.systemStatusBar()
        self.status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)

        # Set icon
        image = NSImage.imageNamed_("NSApplicationIcon")
        if image:
            image.setSize_((18, 18))
            self.status_item.button().setImage_(image)

        # Create menu
        menu = NSMenu.alloc().init()

        show_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show / Hide Lyrics", "togglePanel:", "l"
        )
        show_item.setKeyEquivalentModifierMask_(1 << 3)  # Cmd
        menu.addItem_(show_item)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit LyricIsland", "quit:", "q"
        )
        quit_item.setKeyEquivalentModifierMask_(1 << 3)  # Cmd
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)

    def _create_floating_window(self):
        """Create the floating lyrics window."""
        content_view = LyricsContentView.alloc().initWithFrame_(
            ((0, 0), (400, 48))
        )

        content_view.set_callbacks(
            on_tap=self._on_panel_tap,
            on_expand=self._on_expand,
            on_collapse=self._on_collapse,
        )

        self.window = FloatingWindow.alloc().initWithContent_(content_view)
        self.content_view = content_view
        self.window.orderFront_(None)

    def _start_sync_timer(self):
        """Timer that updates sync engine and redraws UI."""
        def tick():
            while True:
                try:
                    self._update_sync()
                except Exception:
                    pass
                time.sleep(POLL_INTERVAL)

        thread = threading.Thread(target=tick, daemon=True)
        thread.start()

    def _start_animation_timer(self):
        """Timer for animating playback bars."""
        def tick():
            while True:
                try:
                    if self.music_monitor.is_playing and self.content_view:
                        self.content_view.setNeedsDisplay_(True)
                except Exception:
                    pass
                time.sleep(0.15)

        thread = threading.Thread(target=tick, daemon=True)
        thread.start()

    def _update_sync(self):
        """Update sync engine with current playback position."""
        if self.music_monitor.is_playing:
            self.sync_engine.update(self.music_monitor.playback_time)
            idx = self.sync_engine.current_index
            if 0 <= idx < len(self.sync_engine.lines):
                text = self.sync_engine.lines[idx].text
                self._call_on_main(self.content_view.set_current_line, text, idx)
            else:
                self._call_on_main(self.content_view.set_current_line, "", -1)

    def _on_song_changed(self, song: SongInfo):
        """Called when a new song starts playing."""
        # Update UI
        self._call_on_main(self.content_view.set_song, song.title, song.artist)
        self._call_on_main(self.content_view.set_playing, True)

        # Fetch lyrics
        fetch_lyrics_async(
            song.title,
            song.artist,
            song.album,
            song.duration,
            callback=lambda lines: self._on_lyrics_fetched(lines),
        )

    def _on_lyrics_fetched(self, lines: list[LyricLine]):
        """Called when lyrics are fetched."""
        self.current_lines = lines
        self.sync_engine.set_lyrics(lines)
        self._call_on_main(self.content_view.set_lyrics, lines)

    def _call_on_main(self, func, *args):
        """Execute a function on the main thread."""
        def do_call():
            func(*args)

        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0, self, "_timerCallback:", do_call, False
        )

    def _timerCallback_(self, timer):
        """NSTimer callback that runs a function."""
        callback = timer.userInfo()
        if callable(callback):
            callback()

    # -- Panel callbacks --

    def toggle_panel(self):
        self.is_expanded = not self.is_expanded
        self.content_view.set_expanded(self.is_expanded)
        self.window.set_expanded(self.is_expanded)

    def _on_panel_tap(self):
        self.toggle_panel()

    def _on_expand(self):
        self.is_expanded = True
        self.content_view.set_expanded(True)
        self.window.set_expanded(True)

    def _on_collapse(self):
        self.is_expanded = False
        self.content_view.set_expanded(False)
        self.window.set_expanded(False)


import objc


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    # Create delegate for menu actions
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    # Create and start controller
    controller = LyricIslandController()
    delegate.setController_(controller)
    controller.start()

    # Keep the app running
    try:
        while True:
            NSRunLoop.currentRunLoop().runUntilDate_(
                NSDate.dateWithTimeIntervalSinceNow_(0.1)
            )
    except KeyboardInterrupt:
        controller.stop()


if __name__ == "__main__":
    main()
