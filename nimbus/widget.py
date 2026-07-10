"""Desktop cloud widget — a movable, resizable floating pet (AppKit, G5).

Drag anywhere on the cloud to move it; drag the grip in the bottom-right
corner to resize (aspect locked). Geometry is remembered in settings.
Toggled from the menu bar dropdown.
"""

from __future__ import annotations

import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSEvent,
    NSFloatingWindowLevel,
    NSFont,
    NSImageView,
    NSMakeRect,
    NSPanel,
    NSPoint,
    NSScreen,
    NSTextAlignmentCenter,
    NSTextField,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)

from . import config
from .draw import cloud_image

W, H = 170.0, 200.0  # default size; aspect W:H is kept on resize
MIN_W, MAX_W = 110.0, 500.0
GRIP = 26.0  # resize-corner hit zone (points)


class _PetView(NSView):
    """Captures all mouse events: corner drag resizes, anywhere else moves."""

    def hitTest_(self, point):
        view = objc.super(_PetView, self).hitTest_(point)
        return self if view is not None else None

    def mouseDown_(self, event):
        p = self.convertPoint_fromView_(event.locationInWindow(), None)
        size = self.frame().size
        self._resizing = (p.x > size.width - GRIP and p.y < GRIP)
        self._start_frame = self.window().frame()
        self._start_mouse = NSEvent.mouseLocation()
        if not self._resizing:
            self.window().performWindowDragWithEvent_(event)

    def mouseDragged_(self, event):
        if not getattr(self, "_resizing", False):
            return
        cur = NSEvent.mouseLocation()
        dx = cur.x - self._start_mouse.x
        new_w = max(MIN_W, min(MAX_W, self._start_frame.size.width + dx))
        new_h = new_w * H / W
        top = self._start_frame.origin.y + self._start_frame.size.height
        self.window().setFrame_display_(
            NSMakeRect(self._start_frame.origin.x, top - new_h, new_w, new_h), True)
        owner = getattr(self, "owner", None)
        if owner is not None:
            owner.rerender()

    def mouseUp_(self, event):
        self._resizing = False
        owner = getattr(self, "owner", None)
        if owner is not None:
            owner.rerender()
            owner.save_geometry()

    def drawRect_(self, rect):
        # subtle resize grip: three diagonal lines, bottom-right
        size = self.frame().size
        NSColor.colorWithSRGBRed_green_blue_alpha_(0.5, 0.5, 0.55, 0.55).setStroke()
        for i in (8.0, 13.0, 18.0):
            path = NSBezierPath.bezierPath()
            path.moveToPoint_(NSPoint(size.width - i, 3.0))
            path.lineToPoint_(NSPoint(size.width - 3.0, i))
            path.setLineWidth_(1.2)
            path.stroke()


class CloudWidget:
    def __init__(self):
        settings = config.load_settings()
        w, h = settings.get("widget_size") or (W, H)
        x, y = settings.get("widget_pos") or self._default_pos(w, h)
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, w, h),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered, False)
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setLevel_(NSFloatingWindowLevel)
        self.panel.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces)
        self.panel.setHasShadow_(False)  # the cloud draws its own softness

        self.container = _PetView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        self.container.owner = self
        self.panel.setContentView_(self.container)

        self.image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        self.container.addSubview_(self.image_view)
        self.pct_label = self._label(bold=True)
        self.sub_label = self._label()
        self.container.addSubview_(self.pct_label)
        self.container.addSubview_(self.sub_label)
        self.bob = 0.0
        self.last = (None, "disconnected", "")
        self._layout()

    @staticmethod
    def _default_pos(w, h):
        frame = NSScreen.mainScreen().visibleFrame()
        return (frame.origin.x + frame.size.width - w - 24,
                frame.origin.y + frame.size.height - h - 24)

    @staticmethod
    def _label(bold=False):
        lbl = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 10, 10))
        lbl.setBezeled_(False)
        lbl.setDrawsBackground_(False)
        lbl.setEditable_(False)
        lbl.setSelectable_(False)
        lbl.setAlignment_(NSTextAlignmentCenter)
        lbl.setFont_(NSFont.boldSystemFontOfSize_(19) if bold else NSFont.systemFontOfSize_(11))
        lbl.setTextColor_(NSColor.labelColor())
        return lbl

    def _layout(self):
        """Scale everything to the panel's current size."""
        size = self.panel.contentView().frame().size
        w, h = size.width, size.height
        scale = w / W
        self.cloud_size = max(60.0, min(w - 16 * scale, h - 52 * scale))
        self.image_view.setFrame_(
            NSMakeRect((w - self.cloud_size) / 2, h - self.cloud_size - 4 * scale,
                       self.cloud_size, self.cloud_size))
        self.pct_label.setFont_(NSFont.boldSystemFontOfSize_(19.0 * scale))
        self.pct_label.setFrame_(NSMakeRect(0, 26 * scale, w, 26 * scale))
        self.sub_label.setFont_(NSFont.systemFontOfSize_(11.0 * scale))
        self.sub_label.setFrame_(NSMakeRect(0, 8 * scale, w, 16 * scale))

    def rerender(self):
        """Re-layout and redraw at the current size using the last data."""
        remaining, state, subtitle = self.last
        self._layout()
        self.image_view.setImage_(cloud_image(self.cloud_size, remaining, state))
        self.container.setNeedsDisplay_(True)

    def update(self, remaining: float | None, state: str, subtitle: str,
               animate: bool = True) -> None:
        self.last = (remaining, state, subtitle)
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
