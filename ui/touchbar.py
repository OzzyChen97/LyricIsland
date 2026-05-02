"""Touch Bar lyrics display for LyricIsland."""

import objc
from Foundation import NSObject, NSString, NSDictionary
from AppKit import (
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSApplication,
    NSTextField,
)


def _ns(text):
    return NSString.stringWithString_(text)


def _attrs(font, color):
    return NSDictionary.dictionaryWithObjects_forKeys_(
        [font, color],
        [NSFontAttributeName, NSForegroundColorAttributeName],
    )


_HAS_TOUCHBAR = False
try:
    from AppKit import NSTouchBar, NSCustomTouchBarItem
    _HAS_TOUCHBAR = True
except ImportError:
    pass


_TouchBarId = "com.lyricisland.touchbar"
_LyricItemId = f"{_TouchBarId}.lyric"
_SongItemId = f"{_TouchBarId}.song"


class TouchBarLyricDelegate(NSObject):
    _lyric_label = None
    _song_label = None
    _is_active = False
    _current_lyric = ""
    _current_song = ""

    def init(self):
        self = objc.super(TouchBarLyricDelegate, self).init()
        if self is None:
            return None
        self._lyric_label = None
        self._song_label = None
        self._is_active = False
        self._current_lyric = ""
        self._current_song = ""
        return self

    def setLyric_(self, text):
        self._current_lyric = text or ""
        if self._lyric_label is not None:
            try:
                self._lyric_label.setStringValue_(_ns(self._current_lyric[:60]))
            except Exception:
                pass

    def updateSongInfo_artist_(self, title, artist):
        self._current_song = f"{title} \u2022 {artist}" if artist else (title or "")
        if self._song_label is not None:
            try:
                self._song_label.setStringValue_(_ns(self._current_song[:40]))
            except Exception:
                pass

    def activate(self):
        if not _HAS_TOUCHBAR:
            return
        self._is_active = True
        self._setupTouchbar()

    def deactivate(self):
        self._is_active = False
        if not _HAS_TOUCHBAR:
            return
        app = NSApplication.sharedApplication()
        try:
            app.setTouchBar_(None)
        except Exception:
            pass

    def _setupTouchbar(self):
        if not self._is_active or not _HAS_TOUCHBAR:
            return

        app = NSApplication.sharedApplication()
        try:
            tb = NSTouchBar.alloc().init()
            tb.setDelegate_(self)
            tb.setDefaultItemIdentifiers_([_SongItemId, _LyricItemId])
            app.setTouchBar_(tb)
        except Exception:
            pass

    def touchBar_makeItemForIdentifier_(self, touchbar, identifier):
        if not _HAS_TOUCHBAR:
            return None
        try:
            if identifier == _LyricItemId:
                item = NSCustomTouchBarItem.alloc().initWithIdentifier_(_LyricItemId)
                label = NSTextField.labelWithString_(_ns(self._current_lyric[:60] or "\u266a LyricIsland"))
                label.setFont_(NSFont.systemFontOfSize_(14))
                label.setTextColor_(NSColor.whiteColor())
                label.setAlignment_(1)
                label.setWidth_(400)
                item.setView_(label)
                self._lyric_label = label
                return item

            if identifier == _SongItemId:
                item = NSCustomTouchBarItem.alloc().initWithIdentifier_(_SongItemId)
                label = NSTextField.labelWithString_(
                    _ns(self._current_song[:40] or "LyricIsland")
                )
                label.setFont_(NSFont.systemFontOfSize_weight_(13, 600))
                label.setTextColor_(NSColor.systemYellowColor())
                label.setAlignment_(1)
                label.setWidth_(200)
                item.setView_(label)
                self._song_label = label
                return item
        except Exception:
            pass
        return None
