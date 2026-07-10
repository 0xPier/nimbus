"""Desktop cloud widget — a movable, borderless floating pet (AppKit, G5).

Drag it anywhere (position is remembered in settings). Shows the big cloud,
remaining % and the reset countdown. Toggled from the menu bar dropdown.
"""

from __future__ import annotations

from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSFloatingWindowLevel,
    NSFont,
    NSImageView,
    NSMakeRect,
    NSPanel,
    NSScreen,
    NSTextAlignmentCenter,
    NSTextField,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)

from . import config
from .draw import cloud_image

CLOUD_SIZE = 150.0
W, H = 170.0, 200.0


class CloudWidget:
    def __init__(self):
        settings = config.load_settings()
        x, y = settings.get("widget_pos") or self._default_pos()
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, W, H),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered, False)
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setLevel_(NSFloatingWindowLevel)
        self.panel.setMovableByWindowBackground_(True)  # drag anywhere
        self.panel.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces)
        self.panel.setHasShadow_(False)  # the cloud draws its own softness

        content = self.panel.contentView()
        self.image_view = NSImageView.alloc().initWithFrame_(
            NSMakeRect((W - CLOUD_SIZE) / 2, H - CLOUD_SIZE - 4, CLOUD_SIZE, CLOUD_SIZE))
        content.addSubview_(self.image_view)

        self.pct_label = self._label(NSMakeRect(0, 26, W, 24), 19.0, bold=True)
        self.sub_label = self._label(NSMakeRect(0, 8, W, 16), 11.0)
        content.addSubview_(self.pct_label)
        content.addSubview_(self.sub_label)
        self.bob = 0.0

    @staticmethod
    def _default_pos():
        frame = NSScreen.mainScreen().visibleFrame()
        return (frame.origin.x + frame.size.width - W - 24,
                frame.origin.y + frame.size.height - H - 24)

    @staticmethod
    def _label(rect, size, bold=False):
        lbl = NSTextField.alloc().initWithFrame_(rect)
        lbl.setBezeled_(False)
        lbl.setDrawsBackground_(False)
        lbl.setEditable_(False)
        lbl.setSelectable_(False)
        lbl.setAlignment_(NSTextAlignmentCenter)
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        lbl.setFont_(font)
        lbl.setTextColor_(NSColor.labelColor())
        return lbl

    def update(self, remaining: float | None, state: str, subtitle: str,
               animate: bool = True) -> None:
        if animate:
            self.bob = (self.bob + 0.125) % 1.0
        self.image_view.setImage_(
            cloud_image(CLOUD_SIZE, remaining, state, bob=self.bob if animate else 0.0))
        self.pct_label.setStringValue_(
            f"{remaining:.0f}%" if remaining is not None else {"recharging": "recharging…",
                                                               "disconnected": "offline"}.get(state, "–"))
        self.sub_label.setStringValue_(subtitle)

    def show(self):
        self.panel.orderFrontRegardless()

    def hide(self):
        self.save_position()
        self.panel.orderOut_(None)

    def save_position(self):
        origin = self.panel.frame().origin
        settings = config.load_settings()
        settings["widget_pos"] = [origin.x, origin.y]
        config.save_settings(settings)
