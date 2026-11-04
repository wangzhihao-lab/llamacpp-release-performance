"""Shared matplotlib style for the paper figures (elsarticle preprint single-column page, 13.7 cm text width).

Science-magazine colour palette (indigo, green, teal, light blue, sand, rose, purple, wine) in this fixed order,
Times New Roman 7 to 8 pt text, editable SVG text and TrueType-embedded PDF.

Imported by ``scripts/paper/make_figures.py``; not meant to be run on its own.
Run: taskpolicy -b nice -n 19 uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/paper/make_figures.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.figure import Figure

__all__ = [
    "BACKEND_STYLE",
    "COLUMN_WIDTH_CM",
    "FULL_WIDTH_CM",
    "GREEN",
    "INDIGO",
    "LIGHT_BLUE",
    "MODEL_STYLE",
    "PALETTE",
    "PURPLE",
    "ROSE",
    "SAND",
    "TEAL",
    "WINE",
    "apply_style",
    "cm",
    "diverging_cmap",
    "panel_label",
    "save_figure",
]

logger = logging.getLogger(__name__)

PALETTE: tuple[str, ...] = ("#332288", "#117733", "#44AA99", "#88CCEE", "#DDCC77", "#CC6677", "#AA4499",
                            "#882255")
INDIGO, GREEN, TEAL, LIGHT_BLUE, SAND, ROSE, PURPLE, WINE = PALETTE

FULL_WIDTH_CM = 13.7  # elsarticle preprint text width (single column)
COLUMN_WIDTH_CM = 8.4

# Model and backend encodings: colour plus marker plus line style, so series stay apart in greyscale.
MODEL_STYLE: dict[str, dict[str, object]] = {
    "tinyllama-1.1b": {"label": "TinyLlama-1.1B", "color": INDIGO, "marker": "o", "ls": "-"},
    "qwen2.5-1.5b": {"label": "Qwen2.5-1.5B", "color": GREEN, "marker": "s", "ls": "--"},
    "mistral-7b": {"label": "Mistral-7B", "color": TEAL, "marker": "^", "ls": ":"},
}
BACKEND_STYLE: dict[str, dict[str, object]] = {
    "metal": {"label": "Metal", "color": INDIGO, "marker": "o"},
    "cpu": {"label": "CPU", "color": ROSE, "marker": "D"},
}


def cm(x: float) -> float:
    """Centimetres to inches.

    Args:
        x: Length in cm.

    Returns:
        Length in inches.
    """
    return x / 2.54


def apply_style() -> None:
    """Set the rcParams shared by every figure (fonts, sizes, palette, vector text)."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",  # Times-like maths if a label ever uses $...$
        "font.size": 7.5,
        "axes.titlesize": 8,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "legend.frameon": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.width": 0.4,
        "ytick.minor.width": 0.4,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.minor.size": 1.5,
        "ytick.minor.size": 1.5,
        "lines.linewidth": 0.9,
        "lines.markersize": 3,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": matplotlib.cycler(color=list(PALETTE)),
        "hatch.color": "0.45",
        "hatch.linewidth": 0.5,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.dpi": 300,
        "figure.dpi": 150,
    })


def diverging_cmap(neg: str = INDIGO, pos: str = WINE) -> LinearSegmentedColormap:
    """Diverging colour map from the two end colours of the palette through white.

    Args:
        neg: Colour of the most negative value.
        pos: Colour of the most positive value.

    Returns:
        A 256-step colour map.
    """
    return LinearSegmentedColormap.from_list("science_div", [to_rgb(neg), (1.0, 1.0, 1.0), to_rgb(pos)], N=256)


def panel_label(ax: plt.Axes, text: str, x: float = -0.02, y: float = 1.02) -> None:
    """Bold panel letter such as '(a)' at the top-left corner of an axes."""
    ax.text(x, y, text, transform=ax.transAxes, fontsize=8, fontweight="bold", ha="right", va="bottom")


def save_figure(fig: Figure, out_dir: Path, stem: str) -> list[Path]:
    """Write ``<stem>.pdf`` and ``<stem>.svg`` and close the figure.

    Args:
        fig: Figure to save.
        out_dir: Output directory (created if missing).
        stem: File name without extension.

    Returns:
        The written paths.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("pdf", "svg"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p, metadata={"Creator": None} if ext == "svg" else {"Creator": None, "Producer": None})
        paths.append(p)
    w, h = fig.get_size_inches()
    logger.info("wrote %s (%.1f x %.1f cm)", ", ".join(str(p) for p in paths), w * 2.54, h * 2.54)
    plt.close(fig)
    return paths
