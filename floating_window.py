"""Floating lyrics window using AppKit."""

import math
import time
import objc

from AppKit import (
    NSBackingStoreBuffered,
    NSBezierPath,
    NSBorderlessWindowMask,
    NSColor,
    NSCompositingOperationSourceOver,
    NSCursor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGraphicsContext,
    NSImage,
    NSMakeRect,
    NSFloatingWindowLevel,
    NSScreen,
    NSTrackingArea,
    NSView,
    NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSAnimationContext,
    NSTrackingMouseEnteredAndExited,
    NSTrackingActiveAlways,
    NSTrackingInVisibleRect,
)
from Foundation import (
    NSDictionary,
    NSMakePoint,
    NSSize,
    NSString,
    NSAffineTransform,
)

from config import (
    COMPACT_WIDTH,
    COMPACT_HEIGHT,
    EXPANDED_WIDTH,
    EXPANDED_HEIGHT,
    CORNER_RADIUS,
    EXPANDED_CORNER_RADIUS,
)

_HEADER_H = 80
_ARROW_SIZE = 36


def _attrs(font, color):
    return NSDictionary.dictionaryWithObjects_forKeys_(
        [font, color],
        [NSFontAttributeName, NSForegroundColorAttributeName],
    )


def _ns(text):
    return NSString.stringWithString_(text)


def _primary_screen():
    screens = NSScreen.screens()
    if not screens:
        return NSScreen.mainScreen()
    for s in screens:
        f = s.frame()
        if f.origin.x == 0 and f.origin.y == 0:
            return s
    return screens[0]


class FloatingWindow(NSWindow):

    def initWithContent_(self, content_view):
        screen = _primary_screen()
        vf = screen.visibleFrame()
        frame = NSMakeRect(
            vf.origin.x + (vf.size.width - COMPACT_WIDTH) / 2,
            vf.origin.y + vf.size.height - COMPACT_HEIGHT - 8,
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

        self.setLevel_(NSFloatingWindowLevel)
        self.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self.setHasShadow_(True)
        self.setHidesOnDeactivate_(False)
        self.setMovableByWindowBackground_(False)
        self.setCanHide_(False)
        self.setAcceptsMouseMovedEvents_(True)

        self._content_view = content_view
        self.setContentView_(content_view)
        self._is_expanded = False
        self.makeKeyAndOrderFront_(None)

        return self

    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return False

    def set_expanded(self, expanded):
        if self._is_expanded != expanded:
            self._is_expanded = expanded
            self._animate_resize()

    def _animate_resize(self):
        if self._is_expanded:
            w, h = EXPANDED_WIDTH, EXPANDED_HEIGHT
        else:
            w, h = COMPACT_WIDTH, COMPACT_HEIGHT

        cur_frame = self.frame()
        x = cur_frame.origin.x + (cur_frame.size.width - w) / 2
        y = cur_frame.origin.y + cur_frame.size.height - h

        screen = _primary_screen()
        vf = screen.visibleFrame()
        if y < vf.origin.y:
            y = vf.origin.y
        if y > vf.origin.y + vf.size.height - h:
            y = vf.origin.y + vf.size.height - h
        target = NSMakeRect(x, y, w, h)

        NSAnimationContext.beginGrouping()
        ctx = NSAnimationContext.currentContext()
        ctx.setDuration_(0.3)
        self.animator().setFrame_display_(target, True)
        NSAnimationContext.endGrouping()

        self._content_view.setFrame_(((0, 0), (w, h)))
        self._content_view.setNeedsDisplay_(True)


class LyricsContentView(NSView):

    def initWithFrame_(self, frame):
        self = objc.super(LyricsContentView, self).initWithFrame_(frame)
        if self is None:
            return None

        self._song_title = "LyricIsland"
        self._artist = ""
        self._current_line_text = ""
        self._next_line_text = ""
        self._lines = []
        self._current_index = -1
        self._is_playing = False
        self._is_expanded = False
        self._on_toggle_expand = None
        self._album_art = None
        self._vinyl_angle = 0.0
        self._last_anim_time = 0.0
        self._scroll_offset = 0.0

        self._hover_arrow = False
        self._setup_tracking()

        return self

    def acceptsFirstResponder(self):
        return True

    def acceptsFirstMouse_(self, event):
        return True

    def _setup_tracking(self):
        opts = NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways | NSTrackingInVisibleRect
        tracking = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(), opts, self, None
        )
        self.addTrackingArea_(tracking)

    def mouseEntered_(self, event):
        self._update_cursor(event)

    def mouseMoved_(self, event):
        self._update_cursor(event)

    def mouseExited_(self, event):
        NSCursor.arrowCursor().set()
        self._hover_arrow = False

    def _update_cursor(self, event):
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        arrow_rect = self._arrow_hit_rect()

        was_hover = self._hover_arrow
        self._hover_arrow = arrow_rect.origin.x <= loc.x <= arrow_rect.origin.x + arrow_rect.size.width \
            and arrow_rect.origin.y <= loc.y <= arrow_rect.origin.y + arrow_rect.size.height

        if self._hover_arrow:
            NSCursor.pointingHandCursor().set()
        elif not self._is_expanded:
            NSCursor.openHandCursor().set()
        elif loc.y > self.bounds().size.height - _HEADER_H:
            NSCursor.openHandCursor().set()
        else:
            NSCursor.arrowCursor().set()

        if was_hover != self._hover_arrow:
            self.setNeedsDisplay_(True)

    def _arrow_hit_rect(self):
        bounds = self.bounds()
        w, h = bounds.size.width, bounds.size.height
        s = _ARROW_SIZE
        return NSMakeRect(w - s - 8, (h - s) / 2, s, s)

    def set_song(self, title, artist):
        self._song_title = title or "LyricIsland"
        self._artist = artist or ""
        self.setNeedsDisplay_(True)

    def set_current_line(self, text, index):
        self._current_line_text = text or ""
        self._current_index = index
        self._auto_scroll_to_current()
        self.setNeedsDisplay_(True)

    def set_next_line(self, text):
        self._next_line_text = text or ""
        self.setNeedsDisplay_(True)

    def set_lyrics(self, lines):
        self._lines = lines or []
        self._scroll_offset = 0.0
        self.setNeedsDisplay_(True)

    def set_playing(self, playing):
        self._is_playing = playing
        self._last_anim_time = time.time()
        self.setNeedsDisplay_(True)

    def set_needs_animation(self, is_playing):
        if is_playing:
            self.setNeedsDisplay_(True)

    def set_expanded(self, expanded):
        self._is_expanded = expanded
        if expanded:
            self._scroll_offset = 0.0
            self._auto_scroll_to_current()
        else:
            NSCursor.arrowCursor().set()
        self.setNeedsDisplay_(True)

    def set_album_art(self, art_path):
        if art_path:
            try:
                img = NSImage.alloc().initWithContentsOfFile_(art_path)
                if img:
                    self._album_art = img
                    self.setNeedsDisplay_(True)
                    return
            except Exception:
                pass
        self._album_art = None
        self.setNeedsDisplay_(True)

    def set_callbacks(self, on_toggle_expand=None, **kwargs):
        self._on_toggle_expand = on_toggle_expand

    def _auto_scroll_to_current(self):
        if not self._is_expanded or not self._lines or self._current_index < 0:
            return
        bounds = self.bounds()
        h = bounds.size.height
        line_h = 32
        content_h = len(self._lines) * line_h
        visible_h = h - _HEADER_H - 20
        if content_h <= visible_h:
            return
        target_y = self._current_index * line_h
        center = target_y - visible_h / 2 + line_h / 2
        max_scroll = max(0, content_h - visible_h)
        self._scroll_offset = min(max(0, center), max_scroll)

    def mouseDown_(self, event):
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        arrow_rect = self._arrow_hit_rect()
        in_arrow = (arrow_rect.origin.x <= loc.x <= arrow_rect.origin.x + arrow_rect.size.width
                     and arrow_rect.origin.y <= loc.y <= arrow_rect.origin.y + arrow_rect.size.height)

        if in_arrow:
            if self._on_toggle_expand:
                self._on_toggle_expand()
            return

        self.window().performWindowDragWithEvent_(event)

    def mouseDragged_(self, event):
        pass

    def mouseUp_(self, event):
        pass

    def scrollWheel_(self, event):
        if not self._is_expanded or not self._lines:
            return
        bounds = self.bounds()
        h = bounds.size.height
        line_h = 32
        content_h = len(self._lines) * line_h
        visible_h = h - _HEADER_H - 20
        if content_h <= visible_h:
            return
        max_scroll = content_h - visible_h
        self._scroll_offset -= event.scrollingDeltaY() * 0.8
        self._scroll_offset = max(0, min(self._scroll_offset, max_scroll))
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        bounds = self.bounds()
        w, h = bounds.size.width, bounds.size.height

        radius = EXPANDED_CORNER_RADIUS if self._is_expanded else CORNER_RADIUS
        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            NSMakeRect(0, 0, w, h), radius, radius
        )
        NSColor.colorWithWhite_alpha_(0, 0.80).set()
        bg_path.fill()

        NSColor.colorWithWhite_alpha_(1, 0.1).set()
        bg_path.setLineWidth_(0.5)
        bg_path.stroke()

        if self._is_expanded:
            self._draw_expanded(w, h)
        else:
            self._draw_compact(w, h)

        self._draw_arrow(w, h)

    def _draw_arrow(self, w, h):
        arrow_rect = self._arrow_hit_rect()
        cx = arrow_rect.origin.x + arrow_rect.size.width / 2
        cy = arrow_rect.origin.y + arrow_rect.size.height / 2
        arrow_w = 10
        arrow_h = 6

        if self._hover_arrow:
            bg = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(arrow_rect.origin.x + 4, arrow_rect.origin.y + 4,
                           arrow_rect.size.width - 8, arrow_rect.size.height - 8),
                6, 6
            )
            NSColor.colorWithWhite_alpha_(1, 0.1).set()
            bg.fill()

        if self._is_expanded:
            NSColor.colorWithWhite_alpha_(1, 0.6).set()
            path = NSBezierPath.bezierPath()
            path.moveToPoint_(NSMakePoint(cx - arrow_w / 2, cy + arrow_h / 2))
            path.lineToPoint_(NSMakePoint(cx, cy - arrow_h / 2))
            path.lineToPoint_(NSMakePoint(cx + arrow_w / 2, cy + arrow_h / 2))
            path.setLineWidth_(2.0)
            path.stroke()
        else:
            NSColor.colorWithWhite_alpha_(1, 0.6).set()
            path = NSBezierPath.bezierPath()
            path.moveToPoint_(NSMakePoint(cx - arrow_w / 2, cy - arrow_h / 2))
            path.lineToPoint_(NSMakePoint(cx, cy + arrow_h / 2))
            path.lineToPoint_(NSMakePoint(cx + arrow_w / 2, cy - arrow_h / 2))
            path.setLineWidth_(2.0)
            path.stroke()

    def _draw_vinyl_record(self, x, y, size):
        center_x = x + size / 2
        center_y = y + size / 2

        now = time.time()
        if self._is_playing:
            dt = now - self._last_anim_time if self._last_anim_time > 0 else 0.05
            self._vinyl_angle += dt * 0.8
        self._last_anim_time = now

        NSGraphicsContext.saveGraphicsState()

        transform = NSAffineTransform.alloc().init()
        transform.translateXBy_yBy_(center_x, center_y)
        transform.rotateByRadians_(-self._vinyl_angle)
        transform.translateXBy_yBy_(-center_x, -center_y)
        transform.concat()

        art_inset = size * 0.18
        art_size = size - 2 * art_inset

        NSColor.colorWithWhite_alpha_(0.06, 1.0).set()
        disc = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(x, y, size, size))
        disc.fill()

        for i in range(8):
            groove_r = art_inset * 0.6 + i * (size * 0.04)
            if groove_r > size / 2 - 2:
                break
            NSColor.colorWithWhite_alpha_(1, 0.025 + i * 0.003).set()
            groove = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(center_x - groove_r, center_y - groove_r, groove_r * 2, groove_r * 2)
            )
            groove.setLineWidth_(0.3)
            groove.stroke()

        if self._album_art:
            art_rect = NSMakeRect(x + art_inset, y + art_inset, art_size, art_size)
            NSGraphicsContext.saveGraphicsState()
            clip = NSBezierPath.bezierPathWithOvalInRect_(art_rect)
            clip.addClip()
            self._album_art.drawInRect_fromRect_operation_fraction_(
                art_rect,
                NSMakeRect(0, 0, self._album_art.size().width, self._album_art.size().height),
                NSCompositingOperationSourceOver,
                1.0,
            )
            NSGraphicsContext.restoreGraphicsState()

            NSColor.colorWithWhite_alpha_(1, 0.06).set()
            art_outline = NSBezierPath.bezierPathWithOvalInRect_(art_rect)
            art_outline.setLineWidth_(0.5)
            art_outline.stroke()
        else:
            NSColor.colorWithWhite_alpha_(0.15, 1.0).set()
            inner = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(x + art_inset, y + art_inset, art_size, art_size)
            )
            inner.fill()

            note_size = art_size * 0.4
            a = _attrs(
                NSFont.systemFontOfSize_(note_size),
                NSColor.colorWithWhite_alpha_(1.0, 0.3),
            )
            note = _ns("\u266a")
            ns = note.sizeWithAttributes_(a)
            note.drawAtPoint_withAttributes_(
                NSMakePoint(center_x - ns.width / 2, center_y - ns.height / 2), a
            )

        NSGraphicsContext.restoreGraphicsState()

    def _draw_compact(self, w, h):
        vinyl_size = h - 14
        self._draw_vinyl_record(8, 7, vinyl_size)

        text_x = 8 + vinyl_size + 10
        text_w = w - text_x - _ARROW_SIZE - 16

        a = _attrs(NSFont.systemFontOfSize_weight_(12, 600), NSColor.whiteColor())
        title_text = self._song_title
        title = _ns(title_text)
        if title.sizeWithAttributes_(a).width > text_w:
            while title.sizeWithAttributes_(a).width > text_w and len(title_text) > 5:
                title_text = title_text[:-1]
                title = _ns(title_text)
            title_text = title_text[:-2] + "..."
            title = _ns(title_text)
        ts = title.sizeWithAttributes_(a)
        title.drawAtPoint_withAttributes_(NSMakePoint(text_x, h - ts.height - 8), a)

        if self._current_line_text:
            a = _attrs(NSFont.systemFontOfSize_(12), NSColor.colorWithWhite_alpha_(1.0, 0.9))
            txt = self._current_line_text
            lyric = _ns(txt)
            ls = lyric.sizeWithAttributes_(a)
            max_w = text_w
            if ls.width > max_w:
                while lyric.sizeWithAttributes_(a).width > max_w and len(txt) > 3:
                    txt = txt[:-1]
                txt = txt[:-2] + "..."
                lyric = _ns(txt)
            lyric.drawAtPoint_withAttributes_(NSMakePoint(text_x, 26), a)

            next_text = self._get_next_line_text()
            if next_text:
                a2 = _attrs(NSFont.systemFontOfSize_(10), NSColor.colorWithWhite_alpha_(1.0, 0.4))
                nt = next_text
                ntn = _ns(nt)
                if ntn.sizeWithAttributes_(a2).width > max_w:
                    while ntn.sizeWithAttributes_(a2).width > max_w and len(nt) > 3:
                        nt = nt[:-1]
                    nt = nt[:-2] + "..."
                _ns(nt).drawAtPoint_withAttributes_(NSMakePoint(text_x, 10), a2)
        elif self._is_playing:
            a = _attrs(NSFont.systemFontOfSize_(11), NSColor.colorWithWhite_alpha_(1.0, 0.4))
            _ns("Music playing...").drawAtPoint_withAttributes_(NSMakePoint(text_x, 26), a)
        else:
            a = _attrs(NSFont.systemFontOfSize_(11), NSColor.colorWithWhite_alpha_(1.0, 0.35))
            _ns("Waiting for music...").drawAtPoint_withAttributes_(NSMakePoint(text_x, 26), a)

        if self._is_playing:
            self._draw_bars(w - _ARROW_SIZE - 20, h / 2 - 6, 12)

    def _get_next_line_text(self):
        if self._next_line_text:
            return self._next_line_text
        if not self._lines or self._current_index < 0:
            return ""
        ni = self._current_index + 1
        if ni < len(self._lines):
            return self._lines[ni].text
        return ""

    def _draw_expanded(self, w, h):
        header_h = _HEADER_H
        vinyl_size = 56
        vinyl_x = 14
        vinyl_y = h - header_h + 12

        self._draw_vinyl_record(vinyl_x, vinyl_y, vinyl_size)

        text_x = vinyl_x + vinyl_size + 10
        a = _attrs(NSFont.systemFontOfSize_weight_(14, 600), NSColor.whiteColor())
        title_text = self._song_title
        title = _ns(title_text)
        max_title_w = w - text_x - _ARROW_SIZE - 16
        if title.sizeWithAttributes_(a).width > max_title_w:
            while title.sizeWithAttributes_(a).width > max_title_w and len(title_text) > 5:
                title_text = title_text[:-1]
            title_text = title_text[:-2] + "..."
            title = _ns(title_text)
        title.drawAtPoint_withAttributes_(NSMakePoint(text_x, h - 30), a)

        a = _attrs(NSFont.systemFontOfSize_(12), NSColor.colorWithWhite_alpha_(1.0, 0.5))
        artist = _ns(self._artist)
        if artist.sizeWithAttributes_(a).width > max_title_w:
            at = self._artist
            while artist.sizeWithAttributes_(a).width > max_title_w and len(at) > 3:
                at = at[:-1]
            at = at[:-2] + "..."
            artist = _ns(at)
        artist.drawAtPoint_withAttributes_(NSMakePoint(text_x, h - 50), a)

        sep = NSBezierPath.bezierPath()
        sep.moveToPoint_(NSMakePoint(12, h - header_h))
        sep.lineToPoint_(NSMakePoint(w - 12, h - header_h))
        NSColor.colorWithWhite_alpha_(1, 0.08).set()
        sep.setLineWidth_(0.5)
        sep.stroke()

        if not self._lines:
            a = _attrs(NSFont.systemFontOfSize_(13), NSColor.colorWithWhite_alpha_(1.0, 0.4))
            msg = _ns("Play a song to see lyrics")
            ms = msg.sizeWithAttributes_(a)
            msg.drawAtPoint_withAttributes_(NSMakePoint((w - ms.width) / 2, h / 2 - ms.height), a)
            return

        clip_y = h - header_h
        clip_h = clip_y - 10
        NSGraphicsContext.saveGraphicsState()
        NSBezierPath.bezierPathWithRect_(NSMakeRect(0, 10, w, clip_h)).addClip()

        line_y = clip_y - 16 + self._scroll_offset
        line_spacing = 32

        for i, line in enumerate(self._lines):
            if line_y > clip_y + 50:
                line_y -= line_spacing
                continue
            if line_y < -40:
                line_y -= line_spacing
                continue

            is_active = i == self._current_index
            is_past = i < self._current_index

            if is_active:
                font = NSFont.systemFontOfSize_weight_(20, 700)
                alpha = 1.0
            elif is_past:
                font = NSFont.systemFontOfSize_(16)
                alpha = 0.3
            else:
                font = NSFont.systemFontOfSize_(16)
                alpha = 0.55

            a = _attrs(font, NSColor.colorWithWhite_alpha_(1.0, alpha))
            text = _ns(line.text)
            text_size = text.sizeWithAttributes_(a)

            if is_active:
                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.3, 0.5, 1.0, 0.1).set()
                NSBezierPath.fillRect_(NSMakeRect(8, line_y - 4, w - 16, text_size.height + 8))

                NSColor.colorWithCalibratedRed_green_blue_alpha_(0.3, 0.5, 1.0, 0.7).set()
                NSBezierPath.fillRect_(NSMakeRect(4, line_y + 2, 3, text_size.height - 4))

            text.drawAtPoint_withAttributes_(NSMakePoint(16, line_y), a)

            line_y -= line_spacing

        NSGraphicsContext.restoreGraphicsState()

        content_total = len(self._lines) * line_spacing
        if content_total > clip_h:
            bar_h = max(20, clip_h * clip_h / content_total)
            scroll_range = content_total - clip_h
            scroll_pct = self._scroll_offset / scroll_range if scroll_range > 0 else 0
            bar_y = 10 + clip_h - bar_h - scroll_pct * (clip_h - bar_h)
            NSColor.colorWithWhite_alpha_(1, 0.12).set()
            bar = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(w - 6, bar_y, 3, bar_h), 1.5, 1.5
            )
            bar.fill()

    def _draw_bars(self, x, y, height):
        t = time.time()
        for i in range(3):
            bar_h = 4 + abs(math.sin(t * 3 + i * 0.8)) * (height - 4)
            bar_x = x + i * 4
            bar_y = y + (height - bar_h) / 2
            NSColor.colorWithWhite_alpha_(1, 0.5).set()
            NSBezierPath.fillRect_(NSMakeRect(bar_x, bar_y, 2, bar_h))
