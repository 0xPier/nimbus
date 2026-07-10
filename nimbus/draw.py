"""Cloud rendering (AppKit, ships with rumps — G5).

One drawing routine powers both the menu bar icon and the desktop widget:
a cloud that is filled orange while usage remains and drains to grey as the
window fills up. State accents: bolt (discharged), green bolt (recharging),
red slash (disconnected).
"""

from __future__ import annotations

import math

from AppKit import (
    NSBezierPath,
    NSColor,
    NSGradient,
    NSImage,
    NSMakeRect,
    NSPoint,
)

ORANGE_TOP = (1.00, 0.72, 0.20)
ORANGE_BOTTOM = (1.00, 0.55, 0.05)
GREY_CLOUD = (0.62, 0.64, 0.68)
GREY_LIGHT = (0.80, 0.82, 0.85)

# cloud geometry in unit coords (y up); cloud body spans y 0.24 .. 0.82
_CIRCLES = [
    (0.31, 0.47, 0.175),
    (0.52, 0.58, 0.235),
    (0.72, 0.47, 0.170),
]
_BASE = (0.15, 0.24, 0.72, 0.26)  # x, y, w, h rounded base
_Y_MIN, _Y_MAX = 0.24, 0.82


def _cloud_path(s: float) -> NSBezierPath:
    path = NSBezierPath.bezierPath()
    for cx, cy, r in _CIRCLES:
        path.appendBezierPathWithOvalInRect_(
            NSMakeRect((cx - r) * s, (cy - r) * s, 2 * r * s, 2 * r * s))
    x, y, w, h = _BASE
    path.appendBezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(x * s, y * s, w * s, h * s), 0.12 * s, 0.12 * s)
    return path


def _bolt_path(s: float) -> NSBezierPath:
    pts = [(0.54, 0.72), (0.38, 0.46), (0.50, 0.46), (0.42, 0.24),
           (0.64, 0.52), (0.51, 0.52), (0.60, 0.72)]
    path = NSBezierPath.bezierPath()
    path.moveToPoint_(NSPoint(pts[0][0] * s, pts[0][1] * s))
    for x, y in pts[1:]:
        path.lineToPoint_(NSPoint(x * s, y * s))
    path.closePath()
    return path


def _rgb(c, alpha=1.0):
    return NSColor.colorWithSRGBRed_green_blue_alpha_(c[0], c[1], c[2], alpha)


def draw_cloud_into(size: float, remaining: float | None, state: str) -> None:
    """Draw into the current graphics context (size x size points)."""
    s = size
    cloud = _cloud_path(s)

    # soft grey body (the "empty" cloud) with a gentle drop shadow
    from AppKit import NSGraphicsContext, NSShadow
    NSGraphicsContext.saveGraphicsState()
    shadow = NSShadow.alloc().init()
    shadow.setShadowOffset_((0, -s * 0.015))
    shadow.setShadowBlurRadius_(s * 0.05)
    shadow.setShadowColor_(_rgb((0.1, 0.1, 0.15), 0.35))
    shadow.set()
    _rgb(GREY_LIGHT, 1.0).setFill()
    cloud.fill()
    NSGraphicsContext.restoreGraphicsState()

    # orange charge level, clipped to the remaining fraction from the bottom
    if remaining is not None and remaining > 0 and state not in ("disconnected",):
        from AppKit import NSGraphicsContext
        frac = max(0.0, min(1.0, remaining / 100.0))
        top = (_Y_MIN + frac * (_Y_MAX - _Y_MIN)) * s
        NSGraphicsContext.saveGraphicsState()
        NSBezierPath.clipRect_(NSMakeRect(0, 0, s, top))
        gradient = NSGradient.alloc().initWithStartingColor_endingColor_(
            _rgb(ORANGE_BOTTOM), _rgb(ORANGE_TOP))
        gradient.drawInBezierPath_angle_(cloud, 90.0)
        NSGraphicsContext.restoreGraphicsState()


    # accents
    if state == "discharged":
        _rgb((1.0, 0.85, 0.10)).setFill()
        bolt = _bolt_path(s)
        bolt.fill()
        _rgb((0.55, 0.40, 0.0), 0.8).setStroke()
        bolt.setLineWidth_(max(1.0, s * 0.02))
        bolt.stroke()
    elif state == "recharging":
        _rgb((0.20, 0.80, 0.35)).setFill()
        _bolt_path(s).fill()
    elif state == "disconnected":
        _rgb(GREY_CLOUD).setFill()
        _cloud_path(s).fill()
        slash = NSBezierPath.bezierPath()
        slash.moveToPoint_(NSPoint(0.22 * s, 0.24 * s))
        slash.lineToPoint_(NSPoint(0.78 * s, 0.74 * s))
        slash.setLineWidth_(max(1.5, s * 0.07))
        _rgb((0.90, 0.25, 0.20)).setStroke()
        slash.stroke()


def cloud_image(size: float, remaining: float | None, state: str,
                bob: float = 0.0) -> NSImage:
    """Render a cloud NSImage. `bob` (0..1) adds a gentle float offset for
    pet-mode animation."""
    img = NSImage.alloc().initWithSize_((size, size))
    img.lockFocus()
    if bob:
        offset = math.sin(bob * 2 * math.pi) * size * 0.03
        from AppKit import NSAffineTransform
        t = NSAffineTransform.transform()
        t.translateXBy_yBy_(0, offset)
        t.concat()
    draw_cloud_into(size, remaining, state)
    img.unlockFocus()
    return img
