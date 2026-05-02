"""Home settings window for LyricIsland using AppKit and WKWebView."""

import os
import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSMakeRect,
    NSObject,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
    NSApplication,
)
from Foundation import NSString, NSURL
from WebKit import WKWebView, WKUserContentController, WKWebViewConfiguration

from config import settings, APP_NAME


def _ns(text):
    return NSString.stringWithString_(text)


_HOME_HTML = os.path.join(os.path.dirname(__file__), "home.html")


def _load_html():
    if os.path.exists(_HOME_HTML):
        with open(_HOME_HTML, "r", encoding="utf-8") as f:
            return f.read()
    return "<html><body style='background:#141418;color:#eaeaea;padding:40px'><h1>LyricIsland</h1><p>无法加载 home.html</p></body></html>"


class HomeWindowController(NSObject):
    _window = None
    _webview = None
    _callbacks = {}

    def init(self):
        self = objc.super(HomeWindowController, self).init()
        if self is None:
            return None
        return self

    def set_callbacks(self, on_size_changed=None, on_delay_changed=None,
                      on_color_changed=None, on_ktv_changed=None,
                      on_touchbar_changed=None):
        HomeWindowController._callbacks = {
            "size": on_size_changed,
            "delay": on_delay_changed,
            "color": on_color_changed,
            "ktv": on_ktv_changed,
            "touchbar": on_touchbar_changed,
        }

    def show_window(self):
        if self._window is not None:
            try:
                self._window.orderOut_(None)
                self._window.close()
            except Exception:
                pass
            self._window = None
            self._webview = None
        self._build_ui()
        self._window.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def _build_ui(self):
        W, H = 520, 600
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, W, H), style, NSBackingStoreBuffered, False
        )
        self._window.setTitle_(_ns(f"{APP_NAME} 设置"))
        self._window.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.08, 0.08, 0.10, 1.0)
        )
        self._window.retain()

        cfg = WKWebViewConfiguration.alloc().init()
        ucc = WKUserContentController.alloc().init()
        handler = _Handler.alloc().init()
        ucc.addScriptMessageHandler_name_(handler, "bridge")
        cfg.setUserContentController_(ucc)

        self._webview = WKWebView.alloc().initWithFrame_configuration_(
            NSMakeRect(0, 0, W, H), cfg
        )
        self._webview.setAutoresizingMask_(18)

        html_str = _load_html()
        init_js = (
            '<script>window.__INIT__={'
            f'compact_width:{settings.compact_width},'
            f'compact_height:{settings.compact_height},'
            f'lyric_delay_ms:{settings.lyric_delay_ms},'
            f'lyric_color:"{settings.lyric_color}",'
            f'ktv_color:"{settings.ktv_color}",'
            f'ktv_mode:{"true" if settings.ktv_mode else "false"},'
            f'show_touchbar_lyrics:{"true" if settings.show_touchbar_lyrics else "false"}'
            '};</script>'
        )
        html_str = html_str.replace('</head>', init_js + '</head>')
        self._webview.loadHTMLString_baseURL_(_ns(html_str), None)

        self._window.setContentView_(self._webview)
        self._window.center()


class _Handler(NSObject):
    def init(self):
        self = objc.super(_Handler, self).init()
        if self is None:
            return None
        return self

    def userContentController_didReceiveScriptMessage_(self, controller, message):
        try:
            body = message.body()
            action = body.get("action")
            payload = body.get("payload") or {}
            cb = HomeWindowController._callbacks
            if action == "set_compact_size":
                w = int(payload.get("w", settings.compact_width))
                h = int(payload.get("h", settings.compact_height))
                settings.set("compact_width", w)
                settings.set("compact_height", h)
                if cb.get("size"):
                    cb["size"](w, h)
            elif action == "set_lyric_delay_ms":
                val = int(payload.get("value", 0))
                settings.set("lyric_delay_ms", val)
                if cb.get("delay"):
                    cb["delay"](val)
            elif action == "set_lyric_color":
                hx = payload.get("hex") or "#FFFFFF"
                settings.set("lyric_color", hx)
                if cb.get("color"):
                    cb["color"]("lyric_color", hx)
            elif action == "set_ktv_color":
                hx = payload.get("hex") or "#5B8CFF"
                settings.set("ktv_color", hx)
                if cb.get("color"):
                    cb["color"]("ktv_color", hx)
            elif action == "set_ktv_mode":
                on = bool(payload.get("value"))
                settings.set("ktv_mode", on)
                if cb.get("ktv"):
                    cb["ktv"](on)
            elif action == "set_show_touchbar_lyrics":
                on = bool(payload.get("value"))
                settings.set("show_touchbar_lyrics", on)
                if cb.get("touchbar"):
                    cb["touchbar"](on)
        except Exception:
            pass
