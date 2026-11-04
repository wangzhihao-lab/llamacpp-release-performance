#!/usr/bin/env python3
"""Root-cause protocol, steps 4-5: visibility of the confirmed events and the compact test matrix.

Reads ``results/analysis/interleaved/judge_v11_series.csv`` and ``judge_v11_events.csv``
(step2b_judge.py).  For every event that rule v1.1 confirms (verdict C; the original events
``E..``, not the re-measurements ``E..R``, the visibility re-tests ``V..``, the A/A control or the
change-point events), the 3 x 2 x 2 matrix of series (model x back end x test) is filled from three
sources, in this order of preference: the protocol-v1.2 re-measurement of the event (``E..R``), the
step-2 measurement of the event, and the visibility re-test (``V<event>``).  Two cells that were
re-tested on their own in step 3b (T04 = E04 on mistral-7b/cpu/tg128
with tg128 alone, T50 = E50 on mistral-7b/metal/pp512, six rounds each) take that re-test instead,
as fixed before it ran (``results/analysis/switch/comparisons.csv``, arms A -> B).

Every cell uses the judge's own thresholds, two-sided: ``up``/``down`` when |lr| >= ln(1 + min_rel)
and |z| >= z_min in the fixed configuration (lr = ln of newer over older throughput), ``none``
when measured on both sides without such a change, ``n/a`` when a side has fewer than 2 valid runs
(e.g. the model is not supported by that version), and empty when the series was not measured.

Step 5 treats each series as a test and each confirmed event as an element to detect: it lists
the events every single series sees, finds the smallest sets of series that see all events
(exhaustive search over the 12 series), and counts what a one-series test would miss.

Outputs (``results/analysis/``): ``step4_visibility.csv`` (one row per event and series),
``step4_visibility.md`` (the matrix), ``step5_test_matrix.md``.  Nothing is measured.

Run: uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step4_visibility.py
"""

from __future__ import annotations

import argparse
import itertools
import logging
import math
import sys
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "results" / "analysis"
MODELS = ("tinyllama-1.1b", "qwen2.5-1.5b", "mistral-7b")
BACKENDS = ("metal", "cpu")
TESTS = ("pp512", "tg128")
SERIES = tuple(f"{m}/{b}/{t}" for b in BACKENDS for m in MODELS for t in TESTS)
SHORT = {"tinyllama-1.1b": "tiny", "qwen2.5-1.5b": "qwen", "mistral-7b": "mistral"}
RETESTS = {("E04", "mistral-7b/cpu/tg128"): "T04", ("E50", "mistral-7b/metal/pp512"): "T50"}
SWITCH_CMP = ANALYSIS / "switch" / "comparisons.csv"


def short(series: str) -> str:
    """'tinyllama-1.1b/metal/pp512' -> 'tiny/metal/pp512'."""
    m, b, t = series.split("/")
    return f"{SHORT.get(m, m)}/{b}/{t}"


def cell_state(row: pd.Series, min_rel: float, z_min: float) -> str:
    """up / down / none / n/a for one judged series (two-sided, fixed configuration)."""
    if row["fixed_n_a"] < 2 or row["fixed_n_b"] < 2:
        return "n/a"
    lr, z = row["fixed_lr"], row["fixed_z"]
    if any(isinstance(v, float) and math.isnan(v) for v in (lr, z)):
        return "n/a"
    if abs(lr) >= math.log1p(min_rel) and abs(z) >= z_min:
        return "up" if lr > 0 else "down"
    return "none"


def confirmed_events(events: pd.DataFrame) -> list[str]:
    """Original step-1 events with a v1.1 C verdict, in numeric order."""
    ids = [e for e in events.loc[events.verdict_v11 == "C", "event_id"]
           if e.startswith("E") and e[1:].isdigit()]
    return sorted(ids, key=lambda e: int(e[1:]))


def visibility(series: pd.DataFrame, events: list[str], min_rel: float, z_min: float) -> pd.DataFrame:
    """One row per (event, series) of the matrix with state, lr, z and the source event id.

    Args:
        series: judge_v11_series.csv.
        events: Confirmed event ids.
        min_rel: Practical floor (judge default 0.05).
        z_min: z threshold (judge default 3).

    Returns:
        Frame with event_id, series, state, lr_pct, z, source (empty state when not measured).
    """
    by_id = {e: g.set_index("series") for e, g in series.groupby("event_id")}
    rows = []
    for ev in events:
        for s in SERIES:
            src = next((cand for cand in (f"{ev}R", ev, f"V{ev}") if cand in by_id and s in by_id[cand].index), "")
            if not src:
                rows.append({"event_id": ev, "series": s, "state": "", "lr_pct": math.nan, "z": math.nan,
                             "source": ""})
                continue
            r = by_id[src].loc[s]
            state = cell_state(r, min_rel, z_min)
            rows.append({"event_id": ev, "series": s, "state": state,
                         "lr_pct": math.expm1(r["fixed_lr"]) * 100 if state != "n/a" else math.nan,
                         "z": r["fixed_z"] if state != "n/a" else math.nan, "source": src})
    return pd.DataFrame(rows)


def apply_retests(vis: pd.DataFrame, path: Path, min_rel: float, z_min: float) -> pd.DataFrame:
    """Replace the cells of RETESTS by their step-3b re-test (A -> B), when it has two runs per side.

    Args:
        vis: Output of :func:`visibility`.
        path: results/analysis/switch/comparisons.csv.
        min_rel: Practical floor.
        z_min: z threshold.

    Returns:
        A copy of ``vis`` with those cells replaced (source T04/T50).
    """
    out = vis.copy()
    if not path.is_file():
        return out
    cmp_ = pd.read_csv(path)
    for (ev, s), exp in RETESTS.items():
        hit = cmp_[(cmp_.exp == exp) & (cmp_.series == s) & (cmp_.x == "A") & (cmp_.y == "B")]
        if hit.empty or hit.n_x.iloc[0] < 2 or hit.n_y.iloc[0] < 2:
            continue
        lr, z = float(hit.lr.iloc[0]), float(hit.z.iloc[0])
        state = ("up" if lr > 0 else "down") if abs(lr) >= math.log1p(min_rel) and abs(z) >= z_min else "none"
        mask = (out.event_id == ev) & (out.series == s)
        out.loc[mask, ["state", "lr_pct", "z", "source"]] = [state, math.expm1(lr) * 100, z, exp]
    return out


def matrix_md(vis: pd.DataFrame) -> str:
    """Markdown matrix: events as rows, series as columns, '+12%' / '-23%' for visible cells."""
    head = "| Event | " + " | ".join(short(s) for s in SERIES) + " |"
    lines = [head, "|" + "---|" * (len(SERIES) + 1)]
    for ev, g in vis.groupby("event_id", sort=False):
        cells = []
        for s in SERIES:
            r = g[g.series == s].iloc[0]
            if r.state in ("up", "down"):
                cells.append(f"**{r.lr_pct:+.0f}%**")
            elif r.state == "none":
                cells.append("·")
            else:
                cells.append(r.state or "")
        lines.append(f"| {ev} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def cover_sets(vis: pd.DataFrame) -> tuple[dict[str, set[str]], list[tuple[str, ...]], set[str]]:
    """Events each series sees, the smallest series sets that see all detectable events, the undetectable ones."""
    sees = {s: set(vis[(vis.series == s) & vis.state.isin(["up", "down"])].event_id) for s in SERIES}
    universe = set(vis.event_id)
    detectable = set().union(*sees.values())
    for k in range(1, len(SERIES) + 1):
        best = [c for c in itertools.combinations(SERIES, k) if set().union(*(sees[s] for s in c)) >= detectable]
        if best:
            return sees, best, universe - detectable
    return sees, [], universe - detectable


def main(argv: list[str] | None = None) -> int:
    """Write the visibility table and the test-matrix report; return 1 without a judgment."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--interleaved", type=Path, default=ANALYSIS / "interleaved")
    ap.add_argument("--out", type=Path, default=ANALYSIS)
    ap.add_argument("--min-rel", type=float, default=0.05)
    ap.add_argument("--z-min", type=float, default=3.0)
    ns = ap.parse_args(argv)
    sp, ep = ns.interleaved / "judge_v11_series.csv", ns.interleaved / "judge_v11_events.csv"
    if not (sp.is_file() and ep.is_file()):
        logger.error("judge outputs missing under %s: run step2b_judge.py first", ns.interleaved)
        return 1
    events = confirmed_events(pd.read_csv(ep))
    vis = apply_retests(visibility(pd.read_csv(sp), events, ns.min_rel, ns.z_min), SWITCH_CMP, ns.min_rel, ns.z_min)
    vis.to_csv(ns.out / "step4_visibility.csv", index=False)
    seen = vis[vis.state.isin(["up", "down"])].groupby("event_id").series.count()
    (ns.out / "step4_visibility.md").write_text(
        "# Step 4: visibility matrix of the confirmed events (thresholds of the v1.1 rule, two-sided)\n\n"
        "Each cell: a visible change shows its percentage (newer release relative to the older one, fixed phase), "
        "· means measured but not visible, n/a means not applicable (for example the release does not "
        "support the model), and an empty cell means not measured. Data sources in order of preference: the dedicated "
        "re-tests of step 3b (the two cells T04 and T50) > the v1.2 re-measurements (E..R) > step 2 > the visibility "
        "re-measurements (V..).\n\n"
        + matrix_md(vis) + "\n\n"
        + "\n".join(f"- {ev}: visible in {int(seen.get(ev, 0))} series" for ev in events) + "\n")
    sees, best, undetectable = cover_sets(vis)
    lines = ["# Step 5: compact test matrix (set cover)", "",
             f"{len(events)} confirmed events: {', '.join(events)}. Events seen by each series (model/back end/test):", ""]
    for s in sorted(SERIES, key=lambda x: (-len(sees[x]), x)):
        lines.append(f"- {short(s)}: {len(sees[s])} {sorted(sees[s], key=lambda e: int(e[1:]))}")
    k = len(best[0]) if best else 0
    lines += ["", f"Smallest number of series that see all detectable events: {k}; there are {len(best)} such sets:", ""]
    lines += [f"- {' + '.join(short(s) for s in c)}" for c in best[:20]]
    if undetectable:
        lines += ["", f"Events seen by no series: {sorted(undetectable)}"]
    single = max(SERIES, key=lambda x: len(sees[x]))
    lines += ["", (f"A single series sees at most {len(sees[single])} events ({short(single)}) and misses at least "
                   f"{len(events) - len(sees[single])}.")]
    (ns.out / "step5_test_matrix.md").write_text("\n".join(lines) + "\n")
    logger.info("%d confirmed events; smallest covering set has %d series (%d options) -> %s", len(events), k,
                len(best), ns.out / "step5_test_matrix.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
