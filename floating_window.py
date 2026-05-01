"""Floating lyrics window using AppKit NSPanel."""

import math
import objc
from typing import Optional

from AppKit import (
    NSBackingStoreBuffered,
    NSBorderlessWindowMask,
    NSColor,
    NSFont,
    NSGraphicsContext,
    NSMakeRect,
    NSFloatingWindowLevel,
    NSScreen,
    NSView,
    NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSAnimationContext,
)
from Foundation import (
    NSBundle,
    NSNotificationCenter,
    NSObject,
    NSRunLoop,
    NSRunLoopCommonModes,
    NSDate,
    NSMakePoint,
    NSZeroPoint,
)
from Quartz import (
    CGColorCreateGenericRGB,
    CGPathCreateWithRoundedRect,
    CGRectMake,
)

from config import (
    COMPACT_WIDTH,
    COMPACT_HEIGHT,
    EXPANDED_WIDTH,
    EXPANDED_HEIGHT,
    CORNER_RADIUS,
    EXPANDED_CORNER_RADIUS,
)


class FloatingWindow(NSWindow):
    """A borderless floating panel that displays lyrics."""

    def initWithContent_(self, content_view):
        screen = NSScreen.mainScreen()
        frame = NSMakeRect(
            (screen.frame().size.width - COMPACT_WIDTH) / 2,
            screen.frame().size.height - COMPACT_HEIGHT - 40,
            COMPACT_WIDTH,
            COMPACT_HEIGHT,
        )

        self = objc.super(FloatingWindow, self).initWithContentRect_styleMask_backing_defer_(
            frame,
            NSBorderlessWindowMask,
            NSBackingStoreBuffered,
            False,
        )
        if self is None:
            return None

        # Floating above everything
        self.setLevel_(NSFloatingWindowLevel)
        self.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        # Transparent, no shadow
        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self.setHasShadow_(False)
        self.setHidesOnDeactivate_(False)
        self.setMovableByWindowBackground_(False)
        self.setCanHide_(False)

        # Content
        self._content_view = content_view
        self.setContentView_(content_view)

        # State
        self._is_expanded = False

        return self

    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return False

    def toggle_expand(self):
        self._is_expanded = not self._is_expanded
        self._animate_resize()

    def set_expanded(self, expanded):
        if self._is_expanded != expanded:
            self._is_expanded = expanded
            self._animate_resize()

    def _animate_resize(self):
        screen = NSScreen.mainScreen()
        if self._is_expanded:
            w, h = EXPANDED_WIDTH, EXPANDED_HEIGHT
        else:
            w, h = COMPACT_WIDTH, COMPACT_HEIGHT

        x = (screen.frame().size.width - w) / 2
        y = screen.frame().size.height - h - 40
        target = NSMakeRect(x, y, w, h)

        NSAnimationContext.beginGrouping()
        ctx = NSAnimationContext.currentContext()
        ctx.setDuration_(0.3)
        self.animator().setFrame_display_(target, True)
        NSAnimationContext.endGrouping()

        self._content_view.setNeedsDisplay_(True)


class LyricsContentView(NSView):
    """Custom view that draws lyrics."""

    def initWithFrame_(self, frame):
        self = objc.super(LyricsContentView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._song_title = "LyricIsland"
        self._artist = ""
        self._current_line_text = ""
        self._lines = []
        self._current_index = -1
        self._is_playing = False
        self._is_expanded = False
        self._on_tap = None
        self._on_expand = None
        self._on_collapse = None
        self._scroll_offset = 0.0

        # Enable layer backing for blur effect
        self.setWantsLayer_(True)

        return self

    # -- Public API --

    def set_song(self, title, artist):
        self._song_title = title or "LyricIsland"
        self._artist = artist or ""
        self.setNeedsDisplay_(True)

    def set_current_line(self, text, index):
        self._current_line_text = text or ""
        self._current_index = index
        self.setNeedsDisplay_(True)

    def set_lyrics(self, lines):
        self._lines = lines or []
        self._scroll_offset = 0.0
        self.setNeedsDisplay_(True)

    def set_playing(self, playing):
        self._is_playing = playing
        self.setNeedsDisplay_(True)

    def set_expanded(self, expanded):
        self._is_expanded = expanded
        self.setNeedsDisplay_(True)

    def set_callbacks(self, on_tap=None, on_expand=None, on_collapse=None):
        self._on_tap = on_tap
        self._on_expand = on_expand
        self._on_collapse = on_collapse

    # -- Drawing --

    def drawRect_(self, rect):
        ctx = NSGraphicsContext.currentContext().CGContext()
        bounds = self.bounds()
        w, h = bounds.size.width, bounds.size.height

        # Background with rounded corners
        radius = EXPANDED_CORNER_RADIUS if self._is_expanded else CORNER_RADIUS
        path = CGPathCreateWithRoundedRect(
            CGRectMake(0, 0, w, h), radius, radius
        )
        ctx.addPath(path)
        ctx.setFillColor(CGColorCreateGenericRGB(0, 0, 0, 0.78))
        ctx.fillPath()

        # Subtle border
        ctx.addPath(path)
        ctx.setStrokeColor(CGColorCreateGenericRGB(1, 1, 1, 0.08))
        ctx.setLineWidth(0.5)
        ctx.strokePath()

        if self._is_expanded:
            self._draw_expanded(ctx, w, h)
        else:
            self._draw_compact(ctx, w, h)

    def _draw_compact(self, ctx, w, h):
        """Draw compact capsule view."""
        # Song title (top)
        title_font = NSFont.systemFontOfSize_weight_(12, 600)  # semibold
        title_attrs = {
            "NSFont": title_font,
            "NSColor": NSColor.whiteColor(),
        }
        title_str = self._song_title
        if len(title_str) > 30:
            title_str = title_str[:28] + "..."
        title_size = title_str.sizeWithAttributes_(title_attrs)
        title_y = h - 16 - title_size.height / 2
        title_str.drawAtPoint_withAttributes_(
            NSMakePoint(48, title_y), title_attrs
        )

        # Current lyric line (bottom)
        if self._current_line_text:
            lyric_font = NSFont.systemFontOfSize_(11)
            lyric_attrs = {
                "NSFont": lyric_font,
                "NSColor": NSColor.colorWithWhite_alpha_(1.0, 0.8),
            }
            lyric_str = self._current_line_text
            if len(lyric_str) > 40:
                lyric_str = lyric_str[:38] + "..."
            lyric_y = 8
            lyric_str.drawAtPoint_withAttributes_(
                NSMakePoint(48, lyric_y), lyric_attrs
            )
        elif self._is_playing:
            font = NSFont.systemFontOfSize_(11)
            attrs = {
                "NSFont": font,
                "NSColor": NSColor.colorWithWhite_alpha_(1.0, 0.4),
            }
            "Music playing...".drawAtPoint_withAttributes_(
                NSMakePoint(48, 8), attrs
            )

        # Music note icon (left)
        icon_font = NSFont.systemFontOfSize_(16)
        icon_attrs = {
            "NSFont": icon_font,
            "NSColor": NSColor.colorWithWhite_alpha_(1.0, 0.6),
        }
        note = "♪"
        note_size = note.sizeWithAttributes_(icon_attrs)
        note.drawAtPoint_withAttributes_(
            NSMakePoint(14, (h - note_size.height) / 2),
            icon_attrs,
        )

        # Playing indicator (right)
        if self._is_playing:
            self._draw_bars(ctx, w - 30, h / 2 - 5, 10)

        # Expand hint
        chevron = "⌄"
        chevron_font = NSFont.systemFontOfSize_(10)
        chevron_attrs = {
            "NSFont": chevron_font,
            "NSColor": NSColor.colorWithWhite_alpha_(1.0, 0.3),
        }
        cs = chevron.sizeWithAttributes_(chevron_attrs)
        chevron.drawAtPoint_withAttributes_(
            NSMakePoint(w - 16, (h - cs.height) / 2),
            chevron_attrs,
        )

    def _draw_expanded(self, ctx, w, h):
        """Draw expanded lyrics view."""
        # Header area
        header_h = 60

        # Song title (header)
        title_font = NSFont.systemFontOfSize_weight_(14, 600)
        title_attrs = {
            "NSFont": title_font,
            "NSColor": NSColor.whiteColor(),
        }
        title = self._song_title
        if len(title) > 35:
            title = title[:33] + "..."
        title.drawAtPoint_withAttributes_(
            NSMakePoint(16, h - 24), title_attrs
        )

        # Artist
        artist_font = NSFont.systemFontOfSize_(12)
        artist_attrs = {
            "NSFont": artist_font,
            "NSColor": NSColor.colorWithWhite_alpha_(1.0, 0.5),
        }
        self._artist.drawAtPoint_withAttributes_(
            NSMakePoint(16, h - 44), artist_attrs
        )

        # Collapse button (top right)
        collapse = "⌃"
        c_font = NSFont.systemFontOfSize_(12)
        c_attrs = {
            "NSFont": c_font,
            "NSColor": NSColor.colorWithWhite_alpha_(1.0, 0.4),
        }
        cs = collapse.sizeWithAttributes_(c_attrs)
        collapse.drawAtPoint_withAttributes_(
            NSMakePoint(w - 28, h - 30), c_attrs
        )

        # Separator line
        ctx.setStrokeColor(CGColorCreateGenericRGB(1, 1, 1, 0.08))
        ctx.setLineWidth(0.5)
        ctx.moveToPoint(12, h - header_h)
        ctx.addLineToPoint(w - 12, h - header_h)
        ctx.strokePath()

        # Lyrics area
        if not self._lines:
            # No lyrics message
            msg_font = NSFont.systemFontOfSize_(13)
            msg_attrs = {
                "NSFont": msg_font,
                "NSColor": NSColor.colorWithWhite_alpha_(1.0, 0.4),
            }
            msg = "Play a song to see lyrics"
            ms = msg.sizeWithAttributes_(msg_attrs)
            msg.drawAtPoint_withAttributes_(
                NSMakePoint((w - ms.width) / 2, h / 2 - ms.height),
                msg_attrs,
            )
            return

        # Draw lyric lines
        lyrics_top = h - header_h - 20
        line_y = lyrics_top
        line_spacing = 8

        for i, line in enumerate(self._lines):
            is_active = i == self._current_index
            is_past = i < self._current_index

            if is_active:
                font = NSFont.systemFontOfSize_weight_(20, 700)  # bold
                alpha = 1.0
            elif is_past:
                font = NSFont.systemFontOfSize_(16)
                alpha = 0.35
            else:
                font = NSFont.systemFontOfSize_(16)
                alpha = 0.6

            attrs = {
                "NSFont": font,
                "NSColor": NSColor.colorWithWhite_alpha_(1.0, alpha),
            }

            text = line.text
            text_size = text.sizeWithAttributes_(attrs)

            # Active line highlight bar
            if is_active:
                bar_color = CGColorCreateGenericRGB(0.3, 0.5, 1.0, 0.12)
                ctx.setFillColor(bar_color)
                ctx.fillRect(
                    CGRectMake(8, line_y - 4, w - 16, text_size.height + 8)
                )

            # Active line accent indicator
            if is_active:
                ctx.setFillColor(CGColorCreateGenericRGB(0.3, 0.5, 1.0, 0.8))
                ctx.fillRect(CGRectMake(4, line_y + 2, 3, text_size.height - 4))

            text.drawAtPoint_withAttributes_(
                NSMakePoint(16, line_y), attrs
            )

            line_y += text_size.height + line_spacing

            # Stop if we've gone past the visible area
            if line_y < 60:
                break

        # Auto-scroll: center the active line
        if self._current_index >= 0:
            self._scroll_to_active(h, header_h)

    def _scroll_to_active(self, view_h, header_h):
        """Calculate scroll to keep active line centered."""
        # This is handled by the timer-based redraw
        pass

    def _draw_bars(self, ctx, x, y, height):
        """Draw animated playback bars."""
        import time
        t = time.time()
        for i in range(3):
            bar_h = 4 + abs(math.sin(t * 3 + i * 0.8)) * (height - 4)
            bar_x = x + i * 4
            bar_y = y + (height - bar_h) / 2
            ctx.setFillColor(CGColorCreateGenericRGB(1, 1, 1, 0.5))
            ctx.fillRect(CGRectMake(bar_x, bar_y, 2, bar_h))

    # -- Mouse handling --

    def mouseDown_(self, event):
        """Handle click - toggle expand/collapse."""
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        w, h = self.bounds().size.width, self.bounds().size.height

        if self._is_expanded:
            # Check if click is on collapse button area
            if loc.x > w - 40 and loc.y > h - 45:
                if self._on_collapse:
                    self._on_collapse()
                return

        # Toggle on click
        if self._on_tap:
            self._on_tap()
