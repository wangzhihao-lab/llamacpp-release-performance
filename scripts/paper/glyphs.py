"""Schematic glyphs for the two drawn figures of the paper (Figure 1 and Figure 2).

The shapes are flow-chart document stacks with counts, a repository cylinder, hollow block
arrows and simple icons over boxed labels.  Every function draws on an axes whose data
coordinates are centimetres with equal aspect, so circles and ellipses stay round.

Imported by ``scripts/paper/make_figures.py`` and ``scripts/paper/make_fig_overview.py``; not meant to be run on its own.
Run: taskpolicy -b nice -n 19 uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/paper/make_fig_overview.py
"""

from __future__ import annotations

import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import to_hex, to_rgb
from matplotlib.patches import (
    Arc,
    Circle,
    Ellipse,
    FancyArrowPatch,
    FancyBboxPatch,
    Polygon,
    Rectangle,
)

__all__ = [
    "INK",
    "arrow",
    "chart_icon",
    "cylinder",
    "doc_stack",
    "elbow_arrow",
    "hollow_arrow",
    "laptop",
    "magnifier",
    "rounded_box",
    "tag_stack",
    "tint",
]

INK = "0.12"  # outline and text colour of the schematic parts


def tint(color: str, amount: float = 0.3) -> str:
    """Mix a colour with white.

    Args:
        color: Any matplotlib colour.
        amount: Share of the colour (0 gives white, 1 the colour itself).

    Returns:
        Hex colour.
    """
    return to_hex(tuple(1 - amount * (1 - c) for c in to_rgb(color)))


def rounded_box(ax: Axes, x: float, y: float, w: float, h: float, text: str = "", *, fontsize: float = 7.0,
                fc: str = "white", ec: str = INK, lw: float = 0.8, radius: float = 0.12, bold: bool = True,
                zorder: float = 2) -> None:
    """Rounded rectangle with centred text.

    Args:
        ax: Axes in cm coordinates.
        x: Left edge.
        y: Bottom edge.
        w: Width.
        h: Height.
        text: Label, lines separated by newlines.
        fontsize: Label size in pt.
        fc: Fill colour.
        ec: Edge colour.
        lw: Edge width in pt.
        radius: Corner radius in cm.
        bold: Whether the label is bold.
        zorder: Drawing order.
    """
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}", fc=fc, ec=ec, lw=lw,
                                zorder=zorder))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, color=INK,
                fontweight="bold" if bold else "normal", linespacing=1.15, zorder=zorder + 0.5)


def _document_outline(x: float, y: float, w: float, h: float, wave: float) -> np.ndarray:
    """Vertices of a flow-chart document symbol: straight top and sides, one sine period at the bottom."""
    xs = np.linspace(x + w, x, 40)
    ys = y + wave * (1 - np.sin(2 * np.pi * (xs - x) / w))
    return np.vstack([[x, y + h], [x + w, y + h], *np.column_stack([xs, ys])])


def doc_stack(ax: Axes, x: float, y: float, w: float, h: float, text: str, *, n: int = 3, dx: float = 0.09,
              dy: float = 0.08, fontsize: float = 7.0, fc: str = "white", ec: str = INK, lw: float = 0.8,
              zorder: float = 2) -> tuple[float, float, float, float]:
    """Stack of documents carrying a label (a data set and its count).

    The front page has its lower-left corner at (x, y); the pages behind it are shifted up and to the left.

    Args:
        ax: Axes in cm coordinates.
        x: Left edge of the front page.
        y: Bottom of the front page (lowest point of its wave).
        w: Page width.
        h: Page height.
        text: Label on the front page.
        n: Number of pages.
        dx: Leftward shift per page behind.
        dy: Upward shift per page behind.
        fontsize: Label size in pt.
        fc: Fill of the front page.
        ec: Edge colour.
        lw: Edge width in pt.
        zorder: Drawing order.

    Returns:
        Bounding box of the whole stack as (left, bottom, right, top).
    """
    wave = 0.07 * h
    for k in reversed(range(n)):
        pts = _document_outline(x - k * dx, y + k * dy, w, h, wave)
        ax.add_patch(Polygon(pts, closed=True, fc=fc if k == 0 else "white", ec=ec, lw=lw, joinstyle="round",
                             zorder=zorder + (n - k) * 0.01))
    ax.text(x + w / 2, y + h / 2 + wave * 0.6, text, ha="center", va="center", fontsize=fontsize, color=INK,
            fontweight="bold", linespacing=1.15, zorder=zorder + 0.5)
    return x - (n - 1) * dx, y, x + w, y + h + (n - 1) * dy


def cylinder(ax: Axes, x: float, y: float, w: float, h: float, text: str, *, fontsize: float = 7.0,
             fc: str = "white", ec: str = INK, lw: float = 0.8, zorder: float = 2) -> None:
    """Repository cylinder with a label.

    Args:
        ax: Axes in cm coordinates.
        x: Left edge.
        y: Bottom (lowest point of the bottom arc).
        w: Width.
        h: Height including both arcs.
        text: Label.
        fontsize: Label size in pt.
        fc: Fill colour.
        ec: Edge colour.
        lw: Edge width in pt.
        zorder: Drawing order.
    """
    e = 0.13 * h  # vertical half-axis of the end ellipses
    ax.add_patch(Rectangle((x, y + e), w, h - 2 * e, fc=fc, ec="none", zorder=zorder))
    ax.add_patch(Ellipse((x + w / 2, y + e), w, 2 * e, fc=fc, ec="none", zorder=zorder))
    ax.add_patch(Arc((x + w / 2, y + e), w, 2 * e, theta1=180, theta2=360, ec=ec, lw=lw, zorder=zorder + 0.1))
    ax.plot([x, x], [y + e, y + h - e], color=ec, lw=lw, zorder=zorder + 0.1, solid_capstyle="butt")
    ax.plot([x + w, x + w], [y + e, y + h - e], color=ec, lw=lw, zorder=zorder + 0.1, solid_capstyle="butt")
    ax.add_patch(Ellipse((x + w / 2, y + h - e), w, 2 * e, fc=fc, ec=ec, lw=lw, zorder=zorder + 0.2))
    ax.text(x + w / 2, y + (h - 2 * e) / 2, text, ha="center", va="center", fontsize=fontsize, color=INK,
            fontweight="bold", linespacing=1.15, zorder=zorder + 0.5)  # between the bottom arc and the top ellipse


def arrow(ax: Axes, start: tuple[float, float], end: tuple[float, float], *, color: str = INK, lw: float = 0.8,
          zorder: float = 3) -> None:
    """Straight arrow with a filled head.

    Args:
        ax: Axes in cm coordinates.
        start: Tail point.
        end: Head point.
        color: Line colour.
        lw: Line width in pt.
        zorder: Drawing order.
    """
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>,head_length=0.45,head_width=0.22", mutation_scale=10,
                                 color=color, lw=lw, shrinkA=0, shrinkB=0, zorder=zorder))


def elbow_arrow(ax: Axes, points: list[tuple[float, float]], *, color: str = INK, lw: float = 0.8,
                zorder: float = 3) -> None:
    """Polyline connector whose last segment ends in an arrow head.

    Args:
        ax: Axes in cm coordinates.
        points: Corner points from tail to head (at least two).
        color: Line colour.
        lw: Line width in pt.
        zorder: Drawing order.

    Raises:
        ValueError: If fewer than two points are given.
    """
    if len(points) < 2:
        raise ValueError("an elbow arrow needs at least two points")
    xs, ys = zip(*points[:-1])
    if len(points) > 2:
        ax.plot(xs, ys, color=color, lw=lw, zorder=zorder, solid_joinstyle="miter", solid_capstyle="butt")
    arrow(ax, points[-2], points[-1], color=color, lw=lw, zorder=zorder)


def hollow_arrow(ax: Axes, x0: float, x1: float, y: float, *, shaft: float = 0.2, head: float = 0.46,
                 head_len: float = 0.3, ec: str = INK, fc: str = "white", lw: float = 0.9,
                 zorder: float = 3) -> None:
    """Hollow block arrow pointing right.

    Args:
        ax: Axes in cm coordinates.
        x0: Tail x.
        x1: Tip x.
        y: Centre line.
        shaft: Shaft height.
        head: Head height.
        head_len: Head length.
        ec: Edge colour.
        fc: Fill colour.
        lw: Edge width in pt.
        zorder: Drawing order.
    """
    xh = x1 - head_len
    pts = [(x0, y - shaft / 2), (xh, y - shaft / 2), (xh, y - head / 2), (x1, y), (xh, y + head / 2),
           (xh, y + shaft / 2), (x0, y + shaft / 2)]
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, joinstyle="miter", zorder=zorder))


def tag_stack(ax: Axes, x: float, y: float, w: float, h: float, labels: tuple[str, ...], *, dx: float = 0.13,
              dy: float = 0.13, fill: str = "white", ec: str = INK, lw: float = 0.8, fontsize: float = 6.5,
              zorder: float = 2) -> None:
    """Stack of label tags, the release-tag icon of Figure 1.

    Args:
        ax: Axes in cm coordinates.
        x: Left tip of the front tag.
        y: Bottom of the front tag.
        w: Tag width.
        h: Tag height.
        labels: Texts from the backmost to the front tag (one tag per label).
        dx: Rightward shift per tag behind.
        dy: Upward shift per tag behind.
        fill: Fill colour.
        ec: Edge colour.
        lw: Edge width in pt.
        fontsize: Text size in pt.
        zorder: Drawing order.
    """
    n = len(labels)
    for k, lab in enumerate(labels):
        back = n - 1 - k
        x0, y0 = x + back * dx, y + back * dy
        pts = [(x0, y0 + h / 2), (x0 + 0.32 * h, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0 + 0.32 * h, y0 + h)]
        z = zorder + k * 0.1
        ax.add_patch(Polygon(pts, closed=True, fc=fill, ec=ec, lw=lw, joinstyle="round", zorder=z))
        ax.add_patch(Circle((x0 + 0.34 * h, y0 + h / 2), 0.07 * h + 0.02, fc="white", ec=ec, lw=lw * 0.8,
                            zorder=z + 0.01))
        if back == 0:
            ax.text(x0 + 0.55 * h + (w - 0.55 * h) / 2, y0 + h / 2, lab, ha="center", va="center",
                    fontsize=fontsize, fontweight="bold", color=INK, zorder=z + 0.02)


def laptop(ax: Axes, xc: float, y: float, w: float, h: float, *, screen_fc: str = "white", ec: str = INK,
           lw: float = 0.8, zorder: float = 2) -> None:
    """Laptop icon: a screen with three text lines over a keyboard base.

    Args:
        ax: Axes in cm coordinates.
        xc: Horizontal centre.
        y: Bottom of the base.
        w: Screen width (the base is wider).
        h: Total height.
        screen_fc: Fill of the display area.
        ec: Edge colour.
        lw: Edge width in pt.
        zorder: Drawing order.
    """
    base_h = 0.13 * h
    lid_y = y + base_h
    lid_h = h - base_h
    ax.add_patch(FancyBboxPatch((xc - w / 2, lid_y), w, lid_h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc="white", ec=ec, lw=lw, zorder=zorder))
    m = 0.09
    ax.add_patch(Rectangle((xc - w / 2 + m, lid_y + m), w - 2 * m, lid_h - 2 * m, fc=screen_fc, ec=ec, lw=lw * 0.6,
                           zorder=zorder + 0.1))
    for k, frac in enumerate((0.62, 0.45, 0.78)):  # terminal lines of different length
        yy = lid_y + lid_h - m - (k + 1) * (lid_h - 2 * m) / 4
        x0 = xc - w / 2 + 2 * m
        ax.plot([x0, x0 + frac * (w - 4 * m)], [yy, yy], color=ec, lw=lw * 0.9, solid_capstyle="round",
                zorder=zorder + 0.2)
    ext = 0.12 * w
    ax.add_patch(Polygon([(xc - w / 2 - ext, y), (xc + w / 2 + ext, y), (xc + w / 2, lid_y), (xc - w / 2, lid_y)],
                         closed=True, fc="white", ec=ec, lw=lw, joinstyle="round", zorder=zorder))


def chart_icon(ax: Axes, x: float, y: float, w: float, h: float, *, line: str = INK, ec: str = INK,
               lw: float = 0.8, zorder: float = 2) -> None:
    """Generic line-chart icon: two axes and a jagged line with jumps.

    Args:
        ax: Axes in cm coordinates.
        x: Left edge (the vertical axis).
        y: Bottom edge (the horizontal axis).
        w: Width.
        h: Height.
        line: Colour of the data line.
        ec: Colour of the axes.
        lw: Line width in pt.
        zorder: Drawing order.
    """
    ax.plot([x, x, x + w], [y + h, y, y], color=ec, lw=lw, zorder=zorder, solid_joinstyle="miter")
    shape = (0.22, 0.34, 0.25, 0.4, 0.3, 0.62, 0.48, 0.66, 0.55, 0.88, 0.8)  # a schematic, not data
    xs = np.linspace(x + 0.08 * w, x + 0.95 * w, len(shape))
    ax.plot(xs, [y + s * h for s in shape], color=line, lw=lw * 1.2, zorder=zorder + 0.1, solid_joinstyle="round")


def magnifier(ax: Axes, xc: float, yc: float, r: float, *, ec: str = INK, mark: str = INK, lw: float = 1.0,
              fontsize: float = 11.0, zorder: float = 2) -> None:
    """Magnifying glass with a question mark, the icon of the open question in Figure 1.

    Args:
        ax: Axes in cm coordinates.
        xc: Centre of the lens.
        yc: Centre of the lens.
        r: Lens radius.
        ec: Colour of the lens and handle.
        mark: Colour of the question mark.
        lw: Line width in pt.
        fontsize: Size of the question mark in pt.
        zorder: Drawing order.
    """
    ax.add_patch(Circle((xc, yc), r, fc="white", ec=ec, lw=lw, zorder=zorder))
    c = np.cos(np.pi / 4)
    ax.plot([xc + r * c, xc + 1.75 * r * c], [yc - r * c, yc - 1.75 * r * c], color=ec, lw=lw * 2.4,
            solid_capstyle="round", zorder=zorder - 0.1)
    ax.text(xc, yc, "?", ha="center", va="center", fontsize=fontsize, fontweight="bold", color=mark,
            zorder=zorder + 0.1)
