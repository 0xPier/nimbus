"""Desktop cloud widget — a movable, resizable floating pet (AppKit, G5).

Drag it anywhere; resize from any edge (aspect locked). Position and size are
remembered in settings. Shows the big cloud, remaining % and the reset
countdown. Toggled from the menu bar dropdown.
"""

from __future__ import annotations

from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSFloatingWindowLevel,
    NSFont,
    NSImageView,
    NSMakeRect,
    NSMakeSize,
    NSPanel,
    NSScreen,
    NSTextAlignmentCenter,
    NSTextField,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
    NSWindowStyleMaskResizable,
)

from . import config
from .draw import cloud_image

W, H = 170.0, 200.0  # default size; user-resizable, aspect locked


class CloudWidget:
    def __init__(self):
        settings = config.load_settings()
        w, h = settings.get("widget_size") or (W, H)
        x, y = settings.get("widget_pos") or self._default_pos(w, h)
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, w, h),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
            | NSWindowStyleMaskResizable,
            NSBackingStoreBuffered, False)
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setLevel_(NSFloatingWindowLevel)
        self.panel.setMovableByWindowBackground_(True)  # drag anywhere
        self.panel.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces)
        self.panel.setHasShadow_(False)  # the cloud draws its own softness
        self.panel.setMinSize_(NSMakeSize(110, 129))
        self.panel.setMaxSize_(NSMakeSize(500, 588))
        self.panel.setContentAspectRatio_(NSMakeSize(W, H))

        content = self.panel.contentView()
        self.image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        content.addSubview_(self.image_view)
        self.pct_label = self._label(14.0, bold=True)
        self.sub_label = self._label(11.0)
        content.addSubview_(self.pct_label)
        content.addSubview_(self.sub_label)
        self.bob = 0.0
        self._layout()

    @staticmethod
    def _default_pos(w, h):
        frame = NSScreen.mainScreen().visibleFrame()
        return (frame.origin.x + frame.size.width - w - 24,
                frame.origin.y + frame.size.height - h - 24)

    @staticmethod
    def _label(size, bold=False):
        lbl = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 10, 10))
        lbl.setBezeled_(False)
        lbl.setDrawsBackground_(False)
        lbl.setEditable_(False)
        lbl.setSelectable_(False)
        lbl.setAlignment_(NSTextAlignmentCenter)
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        lbl.setFont_(font)
        lbl.setTextColor_(NSColor.labelColor())
        return lbl

    def _layout(self):
        """Scale everything to the panel's current size (resize support)."""
        size = self.panel.contentView().frame().size
        w, h = size.width, size.height
        scale = w / W
        cloud = min(w - 20 * scale, h - 50 * scale)
        self.cloud_size = max(60.0, cloud)
        self.image_view.setFrame_(
            NSMakeRect((w - self.cloud_size) / 2, h - self.cloud_size - 4 * scale,
                       self.cloud_size, self.cloud_size))
        self.pct_label.setFont_(NSFont.boldSystemFontOfSize_(19.0 * scale))
        self.pct_label.setFrame_(NSMakeRect(0, 26 * scale, w, 24 * scale))
        self.sub_label.setFont_(NSFont.systemFontOfSize_(11.0 * scale))
        self.sub_label.setFrame_(NSMakeRect(0, 8 * scale, w, 16 * scale))

    def update(self, remaining: float | None, state: str, subtitle: str,
               animate: bool = True) -> None:
        self._layout()
        if animate:
            self.bob = (self.bob + 0.125) % 1.0
        self.image_view.setImage_(
            cloud_image(self.cloud_size, remaining, state,
                        bob=self.bob if animate else 0.0))
        self.pct_label.setStringValue_(
            f"{remaining:.0f}%" if remaining is not None else {"recharging": "recharging…",
                                                               "disconnected": "offline"}.get(state, "–"))
        self.sub_label.setStringValue_(subtitle)

    def show(self):
        self.panel.orderFrontRegardless()

    def hide(self):
        self.save_geometry()
        self.panel.orderOut_(None)

    def save_geometry(self):
        frame = self.panel.frame()
        pos = [frame.origin.x, frame.origin.y]
        size = [frame.size.width, frame.size.height]
        settings = config.load_settings()
        if settings.get("widget_pos") != pos or settings.get("widget_size") != size:
            settings["widget_pos"] = pos
            settings["widget_size"] = size
            config.save_settings(settings)
