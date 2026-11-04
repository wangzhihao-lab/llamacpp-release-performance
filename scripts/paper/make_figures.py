#!/usr/bin/env python3
"""Generate Figures 1 and 3 to 7 of the paper (llama.cpp cross-version performance study).

Every number drawn or written in a figure is computed here from files under ``results/``;
``results/`` is only read.  The confirmed/noise verdicts, the A/A control, the visibility
matrix and the set cover use the same sources and the same excluded-cell list as
``scripts/paper/make_numbers.py`` (imported from it), so the figures agree with ``paper/numbers.tex``.

Outputs (``paper/figs/``), each as PDF and SVG, named by content so that the printed figure
numbers can change: ``motivation`` (Fig. 1), ``timeline``, ``methodology``, ``bisection``,
``visibility``, ``coverage`` (Figs. 3 to 7).  Fig. 2, the study overview, is drawn by
``scripts/paper/make_fig_overview.py``.

Sources:

* motivation: ``results/<tag>/records.csv`` (one series), ``candidate_events.csv`` (E25, E49),
  ``interleaved/judge_v11_events.csv`` and ``judge_v11_series.csv``, the fixed-phase run JSON files of the two events,
  ``bisect/E49_<series>/result.json``; the schematic parts are drawn with ``scripts/paper/glyphs.py``;
* timeline: ``results/progress.csv``, ``results/<tag>/records.csv``, ``results/analysis/candidate_events.csv``,
  ``changepoint_events.csv``, ``interleaved/judge_v11_events.csv``, ``step4_visibility.csv``;
* methodology: ``interleaved/judge_v11_series.csv`` (A/A rows), ``control_events.csv``,
  ``interleaved/*/runs.tsv`` and the per-run JSON files, the judge thresholds from ``scripts/analysis/step2b_judge.py``;
* bisection: ``bisect/<label>/runs.tsv``, ``steps.csv``, ``result.json``;
* visibility and coverage: ``step4_visibility.csv`` with the excluded cells of ``make_numbers.DEFAULT_EXCLUDED_CELLS``.

Run: taskpolicy -b nice -n 19 uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/paper/make_figures.py
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import figstyle as fs
import glyphs as gl
from make_numbers import (
    DEFAULT_EXCLUDED_CELLS,
    VISIBLE_STATES,
    apply_exclusions,
    cover,
    first_run_bias,
    read_visibility,
)

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
MODELS = ("tinyllama-1.1b", "qwen2.5-1.5b", "mistral-7b")
BACKENDS = ("metal", "cpu")
TESTS = ("pp512", "tg128")
# Column order of the visibility heat map and the coverage chart: test, then backend, then model.
SERIES_ORDER = tuple(f"{m}/{b}/{t}" for t in TESTS for b in BACKENDS for m in MODELS)
# Column labels of the heat map: short model names (the full names would collide at 13.7 cm width).
SHORT_MODEL = {"tinyllama-1.1b": "TinyLlama", "qwen2.5-1.5b": "Qwen", "mistral-7b": "Mistral"}
TEXT_MODEL = {"tinyllama-1.1b": "TinyLlama", "qwen2.5-1.5b": "Qwen2.5", "mistral-7b": "Mistral-7B"}  # names used in the text
CONFIRMED_COLOR = fs.ROSE
REJECTED_COLOR = fs.SAND
BISECT_TARGETS = ("E49_tinyllama-1.1b_metal_pp512", "E03_tinyllama-1.1b_cpu_pp512",
                  "E04_tinyllama-1.1b_cpu_pp512")


def series_label(series: str, short: bool = False) -> str:
    """'tinyllama-1.1b/metal/pp512' -> 'TinyLlama-1.1B Metal pp512' (short: as in the text, 'TinyLlama Metal pp512')."""
    m, b, t = series.split("/")
    name = TEXT_MODEL[m] if short else str(fs.MODEL_STYLE[m]["label"])
    return f"{name} {fs.BACKEND_STYLE[b]['label']} {t}"


def _ids(df: pd.DataFrame) -> list[str]:
    return [str(x) for x in df.event_id]


# --------------------------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------------------------


def load_campaign(root: Path) -> pd.DataFrame:
    """All ok campaign records of the tags in progress.csv, with a commit date column.

    Args:
        root: Project root.

    Returns:
        Frame with tag, date, model, backend, test, avg_ts.
    """
    prog = pd.read_csv(root / "results" / "progress.csv")
    frames = []
    for tag in prog.tag:
        f = root / "results" / str(tag) / "records.csv"
        if f.is_file() and f.stat().st_size > 0:
            frames.append(pd.read_csv(f))
    rec = pd.concat(frames, ignore_index=True)
    rec = rec[rec.status == "ok"].copy()
    rec["date"] = pd.to_datetime(rec.commit_date_utc, utc=True).dt.tz_localize(None)
    logger.info("campaign: %d ok records from %d tags", len(rec), rec.tag.nunique())
    return rec[["tag", "build_number", "date", "model", "backend", "test", "avg_ts"]]


def load_verdicts(root: Path) -> pd.Series:
    """verdict_v11 by event id from the judge."""
    ev = pd.read_csv(root / "results" / "analysis" / "interleaved" / "judge_v11_events.csv")
    return ev.set_index("event_id").verdict_v11.astype(str)


def event_series(row: pd.Series) -> set[str]:
    """Series listed for a step-1 or change-point event (from series_json)."""
    try:
        return {d["series"] for d in json.loads(row.series_json)}
    except (TypeError, ValueError, KeyError):
        return set(str(row.series).split(";"))


def judge_thresholds(root: Path) -> tuple[float, float]:
    """Defaults of --min-rel and --z-min parsed from scripts/analysis/step2b_judge.py.

    Returns:
        (min_rel, z_min).

    Raises:
        RuntimeError: If either default cannot be found.
    """
    src = (root / "scripts" / "analysis" / "step2b_judge.py").read_text()
    vals = []
    for opt in ("--min-rel", "--z-min"):
        m = re.search(rf'"{opt}".*?default=([0-9.]+)', src)
        if not m:
            raise RuntimeError(f"cannot find default of {opt} in step2b_judge.py")
        vals.append(float(m.group(1)))
    return vals[0], vals[1]


# --------------------------------------------------------------------------------------------
# Motivation (introduction): two jumps in one series, measured once and re-measured
# --------------------------------------------------------------------------------------------

MOTIVATION_SERIES = "tinyllama-1.1b/metal/pp512"
MOTIVATION_EVENTS = ("E25", "E49")  # same series, campaign jumps of similar size: one rejected, one confirmed


def remeasured_runs(root: Path, event_id: str, series: str) -> pd.DataFrame:
    """Fixed-phase runs of one series in the interleaved re-measurement of an event.

    Args:
        root: Project root.
        event_id: Event id (one directory ``interleaved/<event_id>_*``).
        series: ``model/backend/test``.

    Returns:
        Frame with side (A older, B newer), tag, round and y = ln(median tokens/s), the run
        statistic of the decision rule (``step2b_judge.run_value``).

    Raises:
        FileNotFoundError: If the event directory or its plan is missing.
    """
    sys.path.insert(0, str(root / "scripts" / "analysis"))
    import step2b_judge  # the decision rule's own run statistic
    model, backend, test = series.split("/")
    dirs = sorted((root / "results" / "analysis" / "interleaved").glob(f"{event_id}_*/plan.json"))
    if not dirs:
        raise FileNotFoundError(f"no interleaved directory for {event_id}")
    plan = json.loads(dirs[0].read_text())
    rows = []
    for g in plan["groups"]:
        if g["model"] != model or g["backend"] != backend:
            continue
        for r in g["runs"]:
            if r["phase"] != "fixed":
                continue
            y = step2b_judge.run_value(dirs[0].parent / f"{r['stem']}.json", test)
            if y is not None:
                rows.append({"side": r["side"], "tag": r["tag"], "round": int(r["round"]), "y": y})
    return pd.DataFrame(rows)


MOTIVATION_HEIGHT_CM = 5.15
MOTIVATION_PANEL = (0.45, 2.4)  # bottom and height (cm) of the two charts


def draw_problem(ax: plt.Axes, y0: float, y1: float, newest_tag: str) -> None:
    """Top of Figure 1: the triage problem as four boxed labels under icons, joined by hollow arrows.

    A rounded frame, an icon over each boxed label, hollow block arrows between the labels.

    Args:
        ax: Axes in cm coordinates spanning the whole figure.
        y0: Bottom of the frame.
        y1: Top of the frame.
        newest_tag: Release written on the front tag of the release icon.
    """
    width = fs.FULL_WIDTH_CM
    ax.add_patch(FancyBboxPatch((0.08, y0), width - 0.16, y1 - y0, boxstyle="round,pad=0,rounding_size=0.25",
                                fc="white", ec=gl.INK, lw=1.1, zorder=1))
    labels = ("llama.cpp\nreleases", "Benchmark once\nper release", "Speed\nhistory", "Real change?\nWhich commit?")
    box_w, box_h, gap = 2.5, 0.6, 1.05
    left = (width - (len(labels) * box_w + (len(labels) - 1) * gap)) / 2
    yb = y0 + 0.14
    centers = []
    for k, lab in enumerate(labels):
        x = left + k * (box_w + gap)
        centers.append(x + box_w / 2)
        gl.rounded_box(ax, x, yb, box_w, box_h, lab, fontsize=7.5, radius=0.05, lw=0.9)
        if k:
            gl.hollow_arrow(ax, x - gap + 0.17, x - 0.17, yb + box_h / 2)
    icon_bot, icon_top = yb + box_h + 0.12, y1 - 0.1
    gl.tag_stack(ax, centers[0] - 0.78, icon_bot + 0.02, 1.3, 0.4, ("", "", newest_tag), fill=gl.tint(fs.LIGHT_BLUE))
    gl.laptop(ax, centers[1], icon_bot, 1.05, icon_top - icon_bot, screen_fc=gl.tint(fs.LIGHT_BLUE))
    gl.chart_icon(ax, centers[2] - 0.6, icon_bot + 0.04, 1.2, icon_top - icon_bot - 0.08, line=fs.INDIGO)
    r = 0.25
    gl.magnifier(ax, centers[3] - 0.1, icon_top - r - 0.02, r, mark=fs.WINE)


def fig_motivation(root: Path, out: Path) -> dict[str, object]:
    """Figure 1: the triage problem of a release-by-release benchmark history, with one example.

    Top: the problem (releases benchmarked once each give a speed history; which jumps are real, and
    which commit caused them?).  Bottom: (a) campaign throughput of ``MOTIVATION_SERIES`` per sampled
    release, with the intervals of the two events shaded as in the timeline figure (rose: confirmed,
    sand: not confirmed) and their campaign change; (b) the fixed-phase runs of the interleaved
    re-measurement of the same two release pairs, relative to the mean of the older release, with the
    judge's change; then the boundary of the bisection of the confirmed event (its ``result.json``).

    Args:
        root: Project root.
        out: Output directory.

    Returns:
        Campaign and re-measured changes per event and the bisection result, for the log.
    """
    rec = load_campaign(root)
    model, backend, test = MOTIVATION_SERIES.split("/")
    d = rec[(rec.model == model) & (rec.backend == backend) & (rec.test == test)].sort_values("build_number")
    an = root / "results" / "analysis"
    cand = pd.read_csv(an / "candidate_events.csv").set_index("event_id")
    judged = pd.read_csv(an / "interleaved" / "judge_v11_series.csv")
    verdict = load_verdicts(root)

    width, height = fs.FULL_WIDTH_CM, MOTIVATION_HEIGHT_CM
    fig = plt.figure(figsize=(fs.cm(width), fs.cm(height)))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")
    draw_problem(ax, 3.42, height - 0.04, str(rec.sort_values("build_number").tag.iloc[-1]))
    pb, ph = MOTIVATION_PANEL

    def place(x: float, y: float, w: float, h: float) -> plt.Axes:
        a = fig.add_axes((x / width, y / height, w / width, h / height))
        a.set_facecolor("none")
        return a

    # (a) one measurement per release
    axa = place(1.12, pb, 4.1, ph)
    axa.plot(d.date, d.avg_ts, color=fs.INDIGO, marker="o", ms=1.8, mew=0, lw=0.7, zorder=3)
    summary: dict[str, object] = {}
    for eid in MOTIVATION_EVENTS:
        ev = cand.loc[eid]
        lr = next(s["log_ratio"] for s in json.loads(ev.series_json) if s["series"] == MOTIVATION_SERIES)
        confirmed = verdict.get(eid, "") == "C"
        d0, d1 = pd.to_datetime(ev.date_old), pd.to_datetime(ev.date_new)
        axa.axvspan(d0, d1, color=CONFIRMED_COLOR if confirmed else REJECTED_COLOR, alpha=0.6, lw=0, zorder=1)
        axa.annotate(f"{eid} {fmt_pct(100 * math.expm1(lr))}%", xy=(d0, 0.97), xycoords=("data", "axes fraction"),
                     xytext=(-2, 0), textcoords="offset points", ha="right", va="top", fontsize=6.5,
                     fontweight="bold", color=fs.WINE if confirmed else "0.3")
        summary[eid] = {"campaign_pct": round(100 * math.expm1(lr), 1), "commits_between": int(ev.commits_between)}
    axa.set_ylim(0, d.avg_ts.max() * 1.14)
    axa.set_yticks([0, 2000, 4000])
    axa.set_ylabel("Throughput (tokens/s)", fontsize=6.3, labelpad=2)
    axa.xaxis.set_major_locator(mdates.YearLocator())
    axa.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(4, 7, 10)))
    axa.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axa.tick_params(labelsize=6.5)
    axa.set_title("(a) Measured once per release", loc="left", fontsize=7, pad=3)

    gl.hollow_arrow(ax, 5.42, 6.22, pb + ph / 2 + 0.05)
    ax.text(5.82, pb + ph / 2 - 0.25, "re-measure\nside by side", ha="center", va="top", fontsize=6.0, fontweight="bold",
            color=gl.INK, linespacing=1.1)

    # (b) the same release pairs side by side
    axb = place(7.18, pb, 3.07, ph)
    lo_rel, hi_rel = 0.75, 2.35
    ticks, ticklabels = [], []
    newer_top = {}
    for k, eid in enumerate(MOTIVATION_EVENTS):
        runs = remeasured_runs(root, eid, MOTIVATION_SERIES)
        base = runs[runs.side == "A"].y.mean()
        row = judged[(judged.event_id == eid) & (judged.series == MOTIVATION_SERIES)].iloc[0]
        confirmed = verdict.get(eid, "") == "C"
        x0 = 2.6 * k
        axb.axvspan(x0 - 0.5, x0 + 1.5, color=CONFIRMED_COLOR if confirmed else REJECTED_COLOR, alpha=0.25, lw=0,
                    zorder=0)
        for j, (side, col, mk) in enumerate((("A", fs.INDIGO, "v"), ("B", fs.TEAL, "^"))):
            r = runs[runs.side == side]
            rel = np.exp(r.y - base)
            xs = x0 + j + np.linspace(-0.13, 0.13, len(rel))
            axb.scatter(xs, rel, s=9, marker=mk, color=col, lw=0, zorder=3)
            axb.plot([x0 + j - 0.3, x0 + j + 0.3], [rel.mean()] * 2, color=col, lw=0.9, zorder=2)
            ticks.append(x0 + j)
            ticklabels.append(str(r.tag.iloc[0]))
            if side == "B":
                newer_top[eid] = float(rel.mean())
        pct = 100 * math.expm1(float(row.fixed_lr))
        axb.text(x0 + 0.5, 0.97, f"{eid} {fmt_pct(pct)}%", transform=axb.get_xaxis_transform(), ha="center",
                 va="top", fontsize=6.5, fontweight="bold", color=fs.WINE if confirmed else "0.3")
        axb.text(x0 + 0.5, 0.87, "confirmed" if confirmed else "not confirmed", transform=axb.get_xaxis_transform(),
                 ha="center", va="top", fontsize=6.0, color=fs.WINE if confirmed else "0.3")
        summary[eid].update({"remeasured_pct": round(pct, 1), "z": round(float(row.fixed_z), 1), "runs": len(runs)})
    axb.axhline(1.0, color="0.55", lw=0.5, ls=":", zorder=1)
    axb.set_xticks(ticks)
    axb.set_xticklabels(ticklabels, fontsize=5.8)
    axb.tick_params(axis="x", length=0, pad=2)
    axb.tick_params(axis="y", labelsize=6.5)
    axb.set_xlim(-0.5, 2.6 * (len(MOTIVATION_EVENTS) - 1) + 1.5)
    axb.set_ylim(lo_rel, hi_rel)
    axb.yaxis.set_major_formatter(lambda v, _: f"\u00d7{v:.1f}")  # relative to the older release
    axb.set_title("(b) Re-measured", loc="left", fontsize=7, pad=3)

    # the confirmed event, bisected
    confirmed_ids = [e for e in MOTIVATION_EVENTS if verdict.get(e, "") == "C"]
    if confirmed_ids:
        eid = confirmed_ids[-1]
        res = json.loads((an / "bisect" / f"{eid}_{MOTIVATION_SERIES.replace('/', '_')}" / "result.json").read_text())
        y_new = pb + (newer_top[eid] - lo_rel) / (hi_rel - lo_rel) * ph
        gl.hollow_arrow(ax, 10.36, 10.98, y_new, shaft=0.16, head=0.36, head_len=0.22)
        ax.text(10.67, y_new + 0.24, "bisect", ha="center", va="bottom", fontsize=6.2, fontweight="bold",
                color=gl.INK)
        prs = ", ".join(f"#{p}" for p in res["prs"])
        text = f"{res['n_commits']} of {summary[eid]['commits_between']} commits\n({prs}) fixes a\ncapability probe"
        gl.rounded_box(ax, 11.08, y_new - 0.55, 2.52, 1.1, text, fontsize=6.5, fc=gl.tint(CONFIRMED_COLOR, 0.15),
                       ec=fs.WINE, radius=0.08, lw=0.8)
        summary[eid].update({"bisect_n_commits": res["n_commits"], "prs": res["prs"]})
    fs.save_figure(fig, out, "motivation")
    return summary


# --------------------------------------------------------------------------------------------
# Campaign timeline (RQ1)
# --------------------------------------------------------------------------------------------


def fig_timeline(root: Path, out: Path, vis: pd.DataFrame) -> None:
    """Campaign throughput of the 12 series with confirmed and rejected event intervals.

    Args:
        root: Project root.
        out: Output directory.
        vis: Visibility frame after exclusions.
    """
    rec = load_campaign(root)
    an = root / "results" / "analysis"
    cand = pd.read_csv(an / "candidate_events.csv")
    cps = pd.read_csv(an / "changepoint_events.csv")
    verdict = load_verdicts(root)
    events = pd.concat([cand, cps], ignore_index=True)
    events["d0"] = pd.to_datetime(events.date_old)
    events["d1"] = pd.to_datetime(events.date_new)

    fig, axes = plt.subplots(2, 2, figsize=(fs.cm(fs.FULL_WIDTH_CM), fs.cm(8.4)), sharex=True)
    for i, b in enumerate(BACKENDS):
        for j, t in enumerate(TESTS):
            ax = axes[i, j]
            panel_series = {f"{m}/{b}/{t}" for m in MODELS}
            labels = []
            for _, ev in events.iterrows():
                v = verdict.get(ev.event_id, "")
                if v == "C":
                    seen = set(vis[(vis.event_id == ev.event_id) & vis.state.isin(VISIBLE_STATES)].series)
                    if seen & panel_series:
                        ax.axvspan(ev.d0, ev.d1, color=CONFIRMED_COLOR, alpha=0.55, lw=0, zorder=1)
                        labels.append((ev.d0 + (ev.d1 - ev.d0) / 2, ev.event_id))
                elif v == "noise" and event_series(ev) & panel_series:
                    ax.axvspan(ev.d0, ev.d1, color=REJECTED_COLOR, alpha=0.45, lw=0, zorder=0)
            for m in MODELS:
                st = fs.MODEL_STYLE[m]
                d = rec[(rec.model == m) & (rec.backend == b) & (rec.test == t)].sort_values("build_number")
                ax.plot(d.date, d.avg_ts, color=st["color"], ls=st["ls"], marker=st["marker"], ms=2.0,
                        mew=0, lw=0.8, label=st["label"], zorder=3)
            ax.set_yscale("log")
            ax.set_title(f"{fs.BACKEND_STYLE[b]['label']}, {t}", loc="left", pad=17)
            if j == 0:
                ax.set_ylabel("Throughput (tokens/s)")
            # event ids above the axes, two staggered rows so neighbouring ids do not collide
            labels.sort()
            for k, (x, eid) in enumerate(labels):
                ax.annotate(eid, xy=(x, 1.0), xycoords=("data", "axes fraction"),
                            xytext=(0, 1.5 + 6.5 * (k % 2)), textcoords="offset points",
                            ha="center", va="bottom", fontsize=6, color=fs.WINE)
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=(4, 7, 10)))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    lo, hi = rec.date.min(), rec.date.max()
    pad = (hi - lo) * 0.01
    axes[0, 0].set_xlim(lo - pad, hi + pad)
    for ax in axes[1]:
        ax.set_xlabel("Commit date of the release")
    handles = [Line2D([], [], color=fs.MODEL_STYLE[m]["color"], ls=fs.MODEL_STYLE[m]["ls"],
                      marker=fs.MODEL_STYLE[m]["marker"], ms=3, mew=0, label=fs.MODEL_STYLE[m]["label"])
               for m in MODELS]
    handles += [Patch(color=CONFIRMED_COLOR, alpha=0.55, lw=0, label="Confirmed event interval"),
                Patch(color=REJECTED_COLOR, alpha=0.45, lw=0, label="Candidate not confirmed by re-measurement")]
    # two legend rows (models, then interval shading) so the legend fits the 13.7 cm text width;
    # matplotlib fills legend columns first, so interleave the two rows
    handles = [h for pair in zip(handles[:3], handles[3:] + [None]) for h in pair if h is not None]
    fig.legend(handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0), handlelength=2.2,
               columnspacing=1.4)
    fig.tight_layout(rect=(0, 0.09, 1, 1), h_pad=0.8, w_pad=1.5)
    fs.save_figure(fig, out, "timeline")


# --------------------------------------------------------------------------------------------
# A/A control and first-run bias (RQ1)
# --------------------------------------------------------------------------------------------


def fig_methodology(root: Path, out: Path) -> dict[str, object]:
    """(a) A/A control effects with +-z_min SE; (b) first-run deviation of unwarmed groups.

    Args:
        root: Project root.
        out: Output directory.

    Returns:
        Summary numbers for the log.
    """
    an = root / "results" / "analysis"
    se = pd.read_csv(an / "interleaved" / "judge_v11_series.csv")
    control = pd.read_csv(an / "control_events.csv")
    aa = se[se.event_id.isin(list(control.event_id))].copy()
    min_rel, z_min = judge_thresholds(root)
    aa["order"] = aa.series.map({s: i for i, s in enumerate(SERIES_ORDER)})
    aa = aa.sort_values("order")
    bias = first_run_bias(root)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(fs.cm(fs.FULL_WIDTH_CM), fs.cm(6.3)),
                                   gridspec_kw={"width_ratios": [1.0, 1.15]})
    # (a) A/A forest plot
    y = np.arange(len(aa))[::-1]
    eff = (np.exp(aa.fixed_lr) - 1) * 100
    lo = (np.exp(aa.fixed_lr - z_min * aa.fixed_se) - 1) * 100
    hi = (np.exp(aa.fixed_lr + z_min * aa.fixed_se) - 1) * 100
    floor = min_rel * 100
    ax1.axvspan(-floor, floor, color=fs.LIGHT_BLUE, alpha=0.35, lw=0)
    ax1.axvline(0, color="black", lw=0.5)
    for yy, (_, r), e, a, b in zip(y, aa.iterrows(), eff, lo, hi):
        bk = r.series.split("/")[1]
        st = fs.BACKEND_STYLE[bk]
        ax1.errorbar(e, yy, xerr=[[e - a], [b - e]], fmt=str(st["marker"]), color=st["color"], ms=3,
                     elinewidth=0.8, capsize=1.5, capthick=0.6)
    ax1.set_yticks(y, [series_label(s, short=True) for s in aa.series])
    ax1.set_xlabel(f"Effect of b{aa.tag_a.iloc[0].lstrip('b')} vs itself (%),\nbars ±{z_min:g} SE")
    ax1.tick_params(axis="y", length=0)
    n_fp = int((aa.verdict == "aa_false_positive").sum())
    ax1.set_title(f"(a) A/A control, {n_fp} of {len(aa)} flagged", loc="left")
    ax1.text(floor + 0.5, y.max() + 0.9, f"±{floor:g}% floor", ha="left", va="bottom", fontsize=6,
             color="0.3")
    ax1.set_ylim(-0.7, len(aa) + 0.3)
    xm = float(max(abs(lo.min()), abs(hi.max()), floor)) * 1.15
    ax1.set_xlim(-xm, xm)

    # (b) first-run deviation, strip plot by backend x test
    first = bias[bias.role == "first"]
    ref = bias[bias.role == "reference"]
    cats = [(b, t) for t in TESTS for b in BACKENDS]
    rng = np.random.default_rng(20261014)
    for k, (b, t) in enumerate(cats):
        col = fs.BACKEND_STYLE[b]["color"]
        for role, dfr, off, filled in (("first", first, -0.19, True), ("reference", ref, 0.19, False)):
            sub = dfr[(dfr.backend == b) & (dfr.test == t)]
            if sub.empty:
                continue
            for m in MODELS:
                dm = sub[sub.model == m].dev * 100
                xs = k + off + rng.uniform(-0.1, 0.1, len(dm))
                ax2.scatter(xs, dm, s=9, marker=str(fs.MODEL_STYLE[m]["marker"]), lw=0.6,
                            facecolor=col if filled else "white", edgecolor=col, zorder=3)
            d = sub.dev * 100
            med = float(np.median(d))
            ax2.hlines(med, k + off - 0.14, k + off + 0.14, color="black", lw=1.0, zorder=4)
    ax2.axhline(0, color="black", lw=0.5)
    ax2.axhspan(-floor, floor, color=fs.LIGHT_BLUE, alpha=0.35, lw=0)
    ax2.set_xticks(range(len(cats)), [f"{fs.BACKEND_STYLE[b]['label']}\n{t}" for b, t in cats])
    ax2.set_ylabel("Deviation from the other runs\nof the same version (%)")
    n_groups = len(first[first.test == "pp512"])
    ax2.set_title(f"(b) No warm-up ({n_groups} groups, {first.event.nunique()} events)", loc="left")
    ax2.tick_params(axis="x", length=0)
    handles = [Line2D([], [], ls="", marker="s", mfc="0.3", mec="0.3", ms=3.5, label="First run of the group"),
               Line2D([], [], ls="", marker="s", mfc="white", mec="0.3", ms=3.5,
                      label="First run of the other version"),
               Line2D([], [], color="black", lw=1.0, label="Median")]
    handles += [Line2D([], [], ls="", marker=str(fs.MODEL_STYLE[m]["marker"]), mfc="0.5", mec="0.5", ms=3.5,
                       label=str(fs.MODEL_STYLE[m]["label"])) for m in MODELS]
    # legend below both panels, in two rows (markings, then models), so it neither leaves the page nor
    # covers the points; matplotlib fills legend columns first, so interleave the two rows
    handles = [h for pair in zip(handles[:3], handles[3:]) for h in pair]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=3, handlelength=1.2,
               fontsize=6.5, columnspacing=1.2)
    ax2.set_xlim(-0.55, len(cats) - 0.45)
    ytop = float(max(first.dev.max(), ref.dev.max())) * 100
    ax2.set_ylim(top=ytop * 1.08)
    fig.tight_layout(rect=(0, 0.1, 1, 1), w_pad=1.5)
    fs.save_figure(fig, out, "methodology")
    summ: dict[str, object] = {"aa_fp": n_fp, "aa_n": len(aa), "z_min": z_min, "min_rel": min_rel,
                               "groups": n_groups, "events": int(first.event.nunique())}
    for b, t in cats:
        d = first[(first.backend == b) & (first.test == t)].dev * 100
        r = ref[(ref.backend == b) & (ref.test == t)].dev * 100
        summ[f"{b}/{t}"] = (float(d.median()), float(r.median()), len(d))
    return summ


# --------------------------------------------------------------------------------------------
# Bisection steps (RQ2)
# --------------------------------------------------------------------------------------------


def boundary_text(res: dict) -> str:
    """Short boundary label: releases and the commits that carry a PR number."""
    commits = res.get("commits", [])
    prs = [c for c in commits if c.get("pr")]
    others = [c for c in commits if not c.get("pr")]
    txt = f"{res['lo']} to {res['hi']}\n" + ", ".join(f"{c['sha'][:9]} (#{c['pr']})" for c in prs)
    if others:
        doc_only = all(f.endswith(".md") for c in others for f in c.get("files", []))
        kind = "docs-only" if doc_only else "other"
        txt += f"\n+{len(others)} {kind} commit{'s' if len(others) > 1 else ''}"
    return txt


def fig_bisection(root: Path, out: Path) -> list[dict[str, object]]:
    """Step plots of three bisections: per-run throughput of lo, mid and hi, and the candidates left.

    One row of panels; each step's tick label gives the step and, below it, the candidate releases
    left before it.  The boundaries are in Table 3 of the paper, not in the figure.

    Args:
        root: Project root.
        out: Output directory.

    Returns:
        Per-target summary for the log.
    """
    bdir = root / "results" / "analysis" / "bisect"
    fig, axes = plt.subplots(1, len(BISECT_TARGETS), figsize=(fs.cm(fs.FULL_WIDTH_CM), fs.cm(5.8)))
    roles = {"lo": (fs.INDIGO, "v", "Older end (lo)"), "mid": (fs.ROSE, "o", "Midpoint (mid)"),
             "hi": (fs.TEAL, "^", "Newer end (hi)")}
    summ = []
    for j, label in enumerate(BISECT_TARGETS):
        d = bdir / label
        runs = pd.read_csv(d / "runs.tsv", sep="\t")
        runs = runs[(runs.role != "warmup") & (runs.ok == 1)]
        steps = pd.read_csv(d / "steps.csv")
        res = json.loads((d / "result.json").read_text())
        ax = axes[j]
        offs = {"lo": -0.22, "mid": 0.0, "hi": 0.22}
        for role, (col, mk, _) in roles.items():
            r = runs[runs.role == role]
            ax.scatter(r.step + offs[role], r.median_ts, s=10, marker=mk, color=col, lw=0, zorder=3)
            means = r.groupby("step").median_ts.mean()
            ax.plot(means.index + offs[role], means.values, color=col, lw=0.6, alpha=0.6, zorder=2)
        for _, s in steps.iterrows():
            ax.annotate(f"{s.mid} ({s.verdict})", (s.step, 0.985), xycoords=("data", "axes fraction"),
                        ha="center", va="top", fontsize=5.5, color="0.25", rotation=90)
        ax.set_ylim(0, runs.median_ts.max() * 1.75)
        _, backend, test = res["series"].split("/")  # every target is TinyLlama (named in the caption)
        ax.set_title(f"({'abc'[j]}) {res['event_id']}, {'Metal' if backend == 'metal' else 'CPU'} {test}", loc="left")
        ax.set_xticks(list(steps.step), [f"{int(s)}\n{int(n)}" for s, n in zip(steps.step, steps.n_candidates)])
        ax.set_xlim(0.5, int(steps.step.max()) + 0.6)
        ax.set_xlabel("Step (candidates left)")
        if j == 0:
            ax.set_ylabel("Throughput (tokens/s)")
        summ.append({"label": label, "event": res["event_id"], "series": res["series"], "lo": res["lo"],
                     "hi": res["hi"], "steps": len(steps), "builds": res.get("builds"),
                     "prs": ",".join(res.get("prs", [])), "n0": int(steps.n_candidates.iloc[0]),
                     "boundary": boundary_text(res).replace("\n", "; ")})
    handles = [Line2D([], [], ls="", marker=mk, color=col, ms=3.5, label=lab) for col, mk, lab in roles.values()]
    fig.legend(handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=1.2)
    fs.save_figure(fig, out, "bisection")
    return summ


# --------------------------------------------------------------------------------------------
# Visibility heat map (RQ3)
# --------------------------------------------------------------------------------------------


def fmt_pct(pct: float) -> str:
    """Signed whole percent without a negative zero: 12.4 -> '+12', -0.3 -> '0'."""
    r = round(pct)
    return f"{r:+d}".replace("-", "\u2212") if r else "0"


def fig_visibility(out: Path, vis_raw: pd.DataFrame, vis: pd.DataFrame) -> dict[str, int]:
    """Event x series heat map of the change in percent, with distinct marks for non-visible cells.

    Args:
        out: Output directory.
        vis_raw: Visibility frame before exclusions (gives the measured value of excluded cells).
        vis: Visibility frame after exclusions.

    Returns:
        Cell counts by state for the log.
    """
    events = sorted(vis.event_id.unique(), key=lambda e: int(e[1:]))
    cmap = fs.diverging_cmap()
    lr = np.log1p(vis_raw.lr_pct.dropna() / 100)
    lim = float(np.ceil(np.abs(lr).max() * 10) / 10)
    norm = Normalize(-lim, lim)
    fig = plt.figure(figsize=(fs.cm(fs.FULL_WIDTH_CM), fs.cm(6.6)))
    ax = fig.add_axes((0.05, 0.19, 0.845, 0.66))
    cax = fig.add_axes((0.905, 0.19, 0.013, 0.66))
    counts: dict[str, int] = {}
    for i, ev in enumerate(events):
        for j, s in enumerate(SERIES_ORDER):
            cell = vis[(vis.event_id == ev) & (vis.series == s)]
            raw = vis_raw[(vis_raw.event_id == ev) & (vis_raw.series == s)]
            state = str(cell.state.iloc[0]) if len(cell) else ""
            state = state if state else "untested"
            counts[state] = counts.get(state, 0) + 1
            pct = float(raw.lr_pct.iloc[0]) if len(raw) and not pd.isna(raw.lr_pct.iloc[0]) else math.nan
            x, y = j, len(events) - 1 - i
            kw = {"lw": 0.4, "edgecolor": "white"}
            if state in VISIBLE_STATES:
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=cmap(norm(math.log1p(pct / 100))), **kw))
                col = "white" if abs(math.log1p(pct / 100)) > 0.55 * lim else "black"
                ax.text(x, y, fmt_pct(pct), ha="center", va="center", fontsize=6.5, color=col, fontweight="bold")
            elif state == "none":
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor="0.93", **kw))
                ax.text(x, y, fmt_pct(pct), ha="center", va="center", fontsize=5.5, color="0.45")
            elif state == "n/a":
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor="white", hatch="//////",
                                       edgecolor="0.7", lw=0))
                ax.text(x, y, "n/a", ha="center", va="center", fontsize=5.5, color="0.35",
                        bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.6})
            elif state == "excluded":
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor="0.93", **kw))
                ax.plot([x - 0.42, x + 0.42], [y - 0.42, y + 0.42], color="0.55", lw=0.6)
                ax.plot([x - 0.42, x + 0.42], [y + 0.42, y - 0.42], color="0.55", lw=0.6)
                ax.text(x, y, f"({fmt_pct(pct)})", ha="center", va="center", fontsize=5.5, color="0.2",
                        bbox={"facecolor": "0.93", "edgecolor": "none", "pad": 0.6})
            else:  # untested
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor="white", edgecolor="0.6", lw=0.4,
                                       ls=":"))
                ax.text(x, y, "?", ha="center", va="center", fontsize=6, color="0.4")
    ax.set_xlim(-0.5, len(SERIES_ORDER) - 0.5)
    ax.set_ylim(-0.5, len(events) - 0.5)
    ax.set_yticks(range(len(events)), events[::-1])
    ax.set_xticks(range(len(SERIES_ORDER)), [SHORT_MODEL[s.split("/")[0]] for s in SERIES_ORDER], fontsize=6.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0)
    # group headers: backend over three columns, test over six
    n_m = len(MODELS)
    for g, (t, b) in enumerate([(t, b) for t in TESTS for b in BACKENDS]):
        x0 = g * n_m - 0.5
        ax.annotate(fs.BACKEND_STYLE[b]["label"], xy=(x0 + n_m / 2, len(events) - 0.5), xytext=(0, 2),
                    textcoords="offset points", ha="center", va="bottom", fontsize=7)
        if g:
            ax.axvline(x0, color="black", lw=0.9 if g % len(BACKENDS) == 0 else 0.4)
    for k, t in enumerate(TESTS):
        span = n_m * len(BACKENDS)
        ax.annotate(t, xy=(k * span - 0.5 + span / 2, len(events) - 0.5), xytext=(0, 12),
                    textcoords="offset points", ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax)
    ticks_pct = [p for p in (-75, -50, -25, 0, 50, 100, 200, 300) if abs(math.log1p(p / 100)) <= lim]
    cb.set_ticks([math.log1p(p / 100) for p in ticks_pct], labels=[fmt_pct(p) for p in ticks_pct])
    cb.set_label("Change (%), log scale")
    cb.outline.set_linewidth(0.4)
    handles = [Patch(facecolor=cmap(norm(lim * 0.7)), edgecolor="none", label="Visible change (%)"),
               Patch(facecolor="0.93", edgecolor="none", label="Not visible (value in gray)"),
               Patch(facecolor="white", edgecolor="0.7", hatch="//////", label="Model not supported (n/a)"),
               Patch(facecolor="0.93", edgecolor="0.55", label="Excluded, crossed out (value in brackets)")]
    if counts.get("untested"):
        handles.append(Patch(facecolor="white", edgecolor="0.6", ls=":", label="Not measured"))
    fig.legend(handles=handles, loc="lower center", ncol=math.ceil(len(handles) / 2), bbox_to_anchor=(0.5, 0.0),
               handlelength=1.4, columnspacing=1.2)
    fs.save_figure(fig, out, "visibility")
    return counts


# --------------------------------------------------------------------------------------------
# Coverage (RQ4)
# --------------------------------------------------------------------------------------------


def fig_coverage(out: Path, vis: pd.DataFrame) -> dict[str, object]:
    """Confirmed events seen by each single series, sorted, plus the smallest covering set(s).

    Args:
        out: Output directory.
        vis: Visibility frame after exclusions.

    Returns:
        Summary for the log.
    """
    cv = cover(vis)
    sees: dict[str, set[str]] = cv["sees"]
    n_ev = len(cv["events"])
    best = cv["best"]
    order = sorted(SERIES_ORDER, key=lambda s: (-len(sees[s]), SERIES_ORDER.index(s)))
    in_best = {s for c in best for s in c}
    labels = [" + ".join(series_label(s, short=True).replace(" pp512", "") for s in c) for c in best]  # all pp512
    rows = [(lab, len(set().union(*(sees[s] for s in c))), "best") for lab, c in zip(labels, best)]
    rows += [(series_label(s, short=True), len(sees[s]), "in" if s in in_best else "out") for s in order]
    h = 1.4 + 0.36 * len(rows)
    fig, ax = plt.subplots(figsize=(fs.cm(fs.COLUMN_WIDTH_CM), fs.cm(h)))
    y = np.arange(len(rows))[::-1].astype(float)
    y[: len(best)] += 0.4  # gap between the combined bar(s) and the single series
    colors = {"best": fs.GREEN, "in": fs.INDIGO, "out": fs.LIGHT_BLUE}
    hatches = {"best": "", "in": "", "out": ""}
    for yy, (lab, n, kind) in zip(y, rows):
        ax.barh(yy, n, color=colors[kind], edgecolor="black", lw=0.4, height=0.66, hatch=hatches[kind])
        if kind == "best":  # the set is named inside its bar (one line), the count stays outside
            ax.text(0.12, yy, lab, va="center", ha="left", fontsize=6.0, color="white")
            ax.text(n + 0.12, yy, str(n), va="center", fontsize=7)
        elif n >= n_ev:
            ax.text(n - 0.15, yy, str(n), va="center", ha="right", fontsize=7, color="white", fontweight="bold")
        else:
            ax.text(n + 0.12, yy, str(n), va="center", fontsize=7)
    ax.axvline(n_ev, color=fs.ROSE, ls="--", lw=0.8)
    ax.text(n_ev - 0.1, y.max() + 0.62, f"all {n_ev} confirmed", ha="right", va="bottom", fontsize=6.5, color=fs.WINE)
    ax.set_yticks(y, ["" if r[2] == "best" else r[0] for r in rows])
    ax.set_xlim(0, n_ev + 1.2)
    ax.set_ylim(y.min() - 0.6, y.max() + 1.3)
    ax.set_xticks(range(0, n_ev + 1, 2 if n_ev > 6 else 1))
    ax.set_xlabel("Confirmed events visible in the series")
    ax.tick_params(axis="y", length=0)
    many = len(best) > 1
    handles = [Patch(facecolor=fs.GREEN, edgecolor="black", lw=0.4,
                     label="Smallest covering set" + ("s" if many else "")),
               Patch(facecolor=fs.INDIGO, edgecolor="black", lw=0.4, label="Series in " + ("such a set" if many else "that set")),
               Patch(facecolor=fs.LIGHT_BLUE, edgecolor="black", lw=0.4, label="Other series")]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.2, 0.0), handlelength=1.4)
    fig.tight_layout()
    fs.save_figure(fig, out, "coverage")
    return {"k": cv["k"], "best": labels, "single_max": cv["single_max"], "single": cv["single_series"],
            "n_events": n_ev, "zero": sum(len(sees[s]) == 0 for s in SERIES_ORDER)}


# --------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Build all figures.

    Args:
        argv: Command-line arguments (default sys.argv).

    Returns:
        Exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=None, help="output directory (default <root>/paper/figs)")
    ap.add_argument("-v", "--verbose", action="store_true")
    ns = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if ns.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    root: Path = ns.root
    out: Path = ns.out or root / "paper" / "figs"
    fs.apply_style()
    vis_raw = read_visibility(root / "results" / "analysis" / "step4_visibility.csv")
    vis = apply_exclusions(vis_raw, DEFAULT_EXCLUDED_CELLS)
    logger.info("motivation: %s", fig_motivation(root, out))
    fig_timeline(root, out, vis)
    logger.info("methodology: %s", fig_methodology(root, out))
    logger.info("bisection: %s", fig_bisection(root, out))
    logger.info("visibility: %s", fig_visibility(out, vis_raw, vis))
    logger.info("coverage: %s", fig_coverage(out, vis))
    return 0


if __name__ == "__main__":
    sys.exit(main())
