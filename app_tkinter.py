"""LyricIsland - Floating lyrics for Apple Music using tkinter + PyObjC status bar."""

import math
import queue
import time
import tkinter as tk

from config import APP_NAME, POLL_INTERVAL, COMPACT_WIDTH, COMPACT_HEIGHT, EXPANDED_WIDTH, EXPANDED_HEIGHT
from core.music_monitor import MusicMonitor, SongInfo
from core.lyrics_fetcher import fetch_lyrics_async, LyricLine
from core.sync_engine import SyncEngine


class LyricsWindow:
    """Floating lyrics window using tkinter."""

    def __init__(self):
        self.root = None
        self.is_expanded = False
        self._current_lines = []
        self._current_index = -1
        self._song_title = "LyricIsland"
        self._artist = ""
        self._is_playing = False

    def create(self):
        """Create the floating window."""
        self.root = tk.Tk()
        self.root.title("")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.configure(bg="#1a1a1a")

        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - COMPACT_WIDTH) // 2
        y = 40
        self.root.geometry(f"{COMPACT_WIDTH}x{COMPACT_HEIGHT}+{x}+{y}")

        # Compact frame
        self.compact_frame = tk.Frame(self.root, bg="#1a1a1a", highlightthickness=0)
        self.compact_frame.pack(fill=tk.BOTH, expand=True)

        self.title_label = tk.Label(
            self.compact_frame, text="LyricIsland", fg="white", bg="#1a1a1a",
            font=("SF Pro Display", 12, "bold"), anchor="w",
        )
        self.title_label.pack(side=tk.TOP, padx=(48, 10), fill=tk.X)

        self.lyric_label = tk.Label(
            self.compact_frame, text="Play a song in Apple Music", fg="#cccccc",
            bg="#1a1a1a", font=("SF Pro Display", 11), anchor="w",
        )
        self.lyric_label.pack(side=tk.TOP, padx=(48, 10), fill=tk.X)

        self.icon_label = tk.Label(
            self.compact_frame, text="♪", fg="#999999", bg="#1a1a1a",
            font=("SF Pro Display", 16),
        )
        self.icon_label.place(x=14, y=12)

        self.bars_canvas = tk.Canvas(
            self.compact_frame, width=12, height=16, bg="#1a1a1a", highlightthickness=0,
        )
        self.bars_canvas.place(x=COMPACT_WIDTH - 40, y=16)

        self.compact_frame.bind("<Button-1>", lambda e: self.toggle_expand())
        self.title_label.bind("<Button-1>", lambda e: self.toggle_expand())
        self.lyric_label.bind("<Button-1>", lambda e: self.toggle_expand())

        # Expanded frame
        self.expanded_frame = tk.Frame(self.root, bg="#1a1a1a", highlightthickness=0)

        self.exp_header = tk.Frame(self.expanded_frame, bg="#1a1a1a")
        self.exp_header.pack(fill=tk.X, padx=16, pady=(12, 8))

        self.exp_title = tk.Label(
            self.exp_header, text="LyricIsland", fg="white", bg="#1a1a1a",
            font=("SF Pro Display", 14, "bold"), anchor="w",
        )
        self.exp_title.pack(side=tk.LEFT)

        self.collapse_btn = tk.Label(
            self.exp_header, text="⌃", fg="#666666", bg="#1a1a1a",
            font=("SF Pro Display", 14), cursor="hand2",
        )
        self.collapse_btn.pack(side=tk.RIGHT)
        self.collapse_btn.bind("<Button-1>", lambda e: self.collapse())

        sep = tk.Frame(self.expanded_frame, bg="#333333", height=1)
        sep.pack(fill=tk.X, padx=12, pady=4)

        self.lyrics_text = tk.Text(
            self.expanded_frame, bg="#1a1a1a", fg="#aaaaaa",
            font=("SF Pro Display", 16), relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED, padx=16, pady=8, spacing3=6,
        )
        self.lyrics_text.pack(fill=tk.BOTH, expand=True)

        self.lyrics_text.tag_configure("active", foreground="white", font=("SF Pro Display", 20, "bold"))
        self.lyrics_text.tag_configure("past", foreground="#555555")
        self.lyrics_text.tag_configure("future", foreground="#999999")

        controls = tk.Frame(self.expanded_frame, bg="#222222")
        controls.pack(fill=tk.X, side=tk.BOTTOM)

        self.prev_btn = tk.Label(
            controls, text="⏮", fg="white", bg="#222222",
            font=("SF Pro Display", 16), cursor="hand2", padx=20, pady=8
        )
        self.prev_btn.pack(side=tk.LEFT, expand=True)

        self.play_btn = tk.Label(
            controls, text="▶", fg="white", bg="#222222",
            font=("SF Pro Display", 18), cursor="hand2", padx=20, pady=8
        )
        self.play_btn.pack(side=tk.LEFT, expand=True)

        self.next_btn = tk.Label(
            controls, text="⏭", fg="white", bg="#222222",
            font=("SF Pro Display", 16), cursor="hand2", padx=20, pady=8
        )
        self.next_btn.pack(side=tk.LEFT, expand=True)

        self._animate_bars()

    def toggle_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self.is_expanded = True
        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - EXPANDED_WIDTH) // 2
        self.root.geometry(f"{EXPANDED_WIDTH}x{EXPANDED_HEIGHT}+{x}+40")
        self.compact_frame.pack_forget()
        self.expanded_frame.pack(fill=tk.BOTH, expand=True)
        self._update_expanded_lyrics()

    def collapse(self):
        self.is_expanded = False
        screen_w = self.root.winfo_screenwidth()
        x = (screen_w - COMPACT_WIDTH) // 2
        self.root.geometry(f"{COMPACT_WIDTH}x{COMPACT_HEIGHT}+{x}+40")
        self.expanded_frame.pack_forget()
        self.compact_frame.pack(fill=tk.BOTH, expand=True)

    def set_song(self, title, artist):
        self._song_title = title or "LyricIsland"
        self._artist = artist or ""
        if self.root:
            self.title_label.config(text=self._song_title[:30])
            self.exp_title.config(text=self._song_title[:35])

    def set_current_line(self, text, index):
        self._current_line_text = text or ""
        self._current_index = index
        if self.root:
            display = text[:40] + "..." if text and len(text) > 40 else (text or "")
            self.lyric_label.config(text=display)
            if self.is_expanded:
                self._highlight_line(index)

    def set_lyrics(self, lines):
        self._current_lines = lines or []
        if self.root and self.is_expanded:
            self._update_expanded_lyrics()

    def set_playing(self, playing):
        self._is_playing = playing
        if self.root:
            if playing:
                self.play_btn.config(text="⏸")
            else:
                self.play_btn.config(text="▶")

    def _update_expanded_lyrics(self):
        self.lyrics_text.config(state=tk.NORMAL)
        self.lyrics_text.delete("1.0", tk.END)
        for i, line in enumerate(self._current_lines):
            self.lyrics_text.insert(tk.END, line.text + "\n")
        self.lyrics_text.config(state=tk.DISABLED)
        if self._current_index >= 0:
            self._highlight_line(self._current_index)

    def _highlight_line(self, index):
        if not self._current_lines or index < 0 or index >= len(self._current_lines):
            return
        self.lyrics_text.tag_remove("active", "1.0", tk.END)
        self.lyrics_text.tag_remove("past", "1.0", tk.END)
        self.lyrics_text.tag_remove("future", "1.0", tk.END)
        for i in range(len(self._current_lines)):
            line_start = f"{i + 1}.0"
            line_end = f"{i + 1}.end"
            if i < index:
                self.lyrics_text.tag_add("past", line_start, line_end)
            elif i == index:
                self.lyrics_text.tag_add("active", line_start, line_end)
            else:
                self.lyrics_text.tag_add("future", line_start, line_end)
        self.lyrics_text.see(f"{index + 1}.0")

    def _animate_bars(self):
        if self.root:
            self.bars_canvas.delete("all")
            if self._is_playing:
                t = time.time()
                for i in range(3):
                    h = 4 + abs(math.sin(t * 3 + i * 0.8)) * 8
                    x = i * 4
                    y = 16 - h
                    self.bars_canvas.create_rectangle(x, y, x + 2, 16, fill="white", outline="")
            self.root.after(150, self._animate_bars)

    def update_playback_controls(self, on_prev, on_play, on_next):
        self.prev_btn.bind("<Button-1>", lambda e: on_prev())
        self.play_btn.bind("<Button-1>", lambda e: on_play())
        self.next_btn.bind("<Button-1>", lambda e: on_next())


def _create_status_icon():
    """Create a minimal menu bar icon using PyObjC (no rumps)."""
    try:
        from AppKit import (
            NSApplication, NSStatusBar, NSMenu, NSMenuItem,
            NSVariableStatusItemLength, NSImage,
        )

        status_bar = NSStatusBar.systemStatusBar()
        status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        image = NSImage.imageNamed_("NSApplicationIcon")
        if image:
            image.setSize_((18, 18))
            status_item.button().setImage_(image)

        menu = NSMenu.alloc().init()
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit LyricIsland", "terminate:", "q"
        )
        menu.addItem_(quit_item)
        status_item.setMenu_(menu)

        return status_item
    except Exception:
        return None


class LyricIslandApp:
    """Main application controller."""

    def __init__(self):
        self.music_monitor = MusicMonitor()
        self.sync_engine = SyncEngine()
        self.window = LyricsWindow()
        self._ui_queue = queue.Queue()
        self._status_item = None

        self.window.create()
        self.window.update_playback_controls(
            on_prev=self.music_monitor.previous_track,
            on_play=self.music_monitor.toggle_play_pause,
            on_next=self.music_monitor.next_track,
        )

        self.music_monitor.set_on_song_changed(self._on_song_changed)
        self.music_monitor.start()

        # Start polling via tkinter's after()
        self.window.root.after(int(POLL_INTERVAL * 1000), self._tick)

        # Process UI queue
        self.window.root.after(50, self._process_queue)

    def _tick(self):
        """Poll music state and update sync engine."""
        try:
            self.music_monitor.poll()
            if self.music_monitor.is_playing:
                self.sync_engine.update(self.music_monitor.playback_time)
                idx = self.sync_engine.current_index
                if 0 <= idx < len(self.sync_engine.lines):
                    self.window.set_current_line(self.sync_engine.lines[idx].text, idx)
                else:
                    self.window.set_current_line("", -1)
        except Exception:
            pass
        self.window.root.after(int(POLL_INTERVAL * 1000), self._tick)

    def _process_queue(self):
        """Process UI updates queued from background threads."""
        try:
            while True:
                func, args = self._ui_queue.get_nowait()
                func(*args)
        except queue.Empty:
            pass
        self.window.root.after(50, self._process_queue)

    def _on_song_changed(self, song: SongInfo):
        """Called when a new song starts playing (main thread via poll)."""
        self._ui_queue.put((self.window.set_song, (song.title, song.artist)))
        self._ui_queue.put((self.window.set_playing, (True,)))

        fetch_lyrics_async(
            song.title, song.artist, song.album, song.duration,
            callback=self._on_lyrics_fetched,
        )

    def _on_lyrics_fetched(self, lines: list[LyricLine]):
        """Called when lyrics are fetched (background thread)."""
        self.sync_engine.set_lyrics(lines)
        self._ui_queue.put((self.window.set_lyrics, (lines,)))

    def run(self):
        """Start the tkinter main loop."""
        self._status_item = _create_status_icon()
        self.window.root.mainloop()


def main():
    app = LyricIslandApp()
    app.run()


if __name__ == "__main__":
    main()
