#!/usr/bin/env python3
"""List the measurement runs that overlap a recorded window of outside load.

Reads ``results/analysis/load_windows.tsv`` (start_utc, end_utc, source, note: other projects'
jobs, system tasks and analysis jobs of this study on the measurement machine) and the
``runs.tsv`` of every re-measurement (``interleaved/*``) and bisection (``bisect/*``) directory.

Outputs (``results/analysis/``):

* ``load_window_runs.tsv``: every overlapping run (directory, run file, phase or role, times,
  sources of the windows it overlaps);
* ``load_window_bisect_steps.csv``: every bisection step with an overlapping run that entered
  the step statistic (warm-up runs excluded), with the step's f, verdict and decision.

The re-judgement without the overlapping re-measurement runs is
``step2b_judge.py --exclude-windows results/analysis/load_windows.tsv --suffix _nowin``.
Nothing is run on the machine; this only reads files.

Run: uv run --no-project --with pandas python3 -I scripts/analysis/load_window_check.py
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from step2b_judge import _utc

ANALYSIS = Path(__file__).resolve().parents[2] / "results" / "analysis"

logger = logging.getLogger(__name__)


def read_windows(path: Path) -> list[dict[str, str]]:
    """Rows of the windows file.

    Args:
        path: ``load_windows.tsv``.

    Returns:
        One dict per window with ``start_utc``, ``end_utc``, ``source`` and ``note``.
    """
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def overlapping_runs(run_dir: Path, windows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Runs of one directory whose start-to-finish span overlaps at least one window.

    Args:
        run_dir: Directory with ``runs.tsv``.
        windows: Rows from :func:`read_windows`.

    Returns:
        One record per overlapping run.
    """
    spans = [(_utc(w["start_utc"]), _utc(w["end_utc"]), w["source"]) for w in windows]
    out = []
    with (run_dir / "runs.tsv").open(newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            if not r.get("started_at_utc") or not r.get("finished_at_utc"):
                continue
            a, b = _utc(r["started_at_utc"]), _utc(r["finished_at_utc"])
            sources = sorted({src for start, end, src in spans if a < end and b > start})
            if sources:
                out.append({"kind": run_dir.parent.name, "dir": run_dir.name, "json_file": r["json_file"],
                            "phase": r.get("phase") or r.get("role", ""), "step": r.get("step", ""),
                            "started_at_utc": r["started_at_utc"], "finished_at_utc": r["finished_at_utc"],
                            "sources": ",".join(sources)})
    return out


def bisect_steps(analysis: Path, runs: list[dict[str, str]]) -> pd.DataFrame:
    """Bisection steps that contain an overlapping non-warm-up run, with their outcome.

    Args:
        analysis: The results/analysis directory.
        runs: Records from :func:`overlapping_runs` of the bisect directories.

    Returns:
        One row per (directory, step).
    """
    rows = []
    hits = pd.DataFrame([r for r in runs if r["kind"] == "bisect" and r["phase"] != "warmup"])
    if hits.empty:
        return pd.DataFrame(columns=["dir", "step", "n_runs", "sources", "f", "verdict", "decision"])
    for (d, step), g in hits.groupby(["dir", "step"]):
        steps = pd.read_csv(analysis / "bisect" / d / "steps.csv", dtype={"step": str})
        s = steps[steps.step == str(step)]
        rows.append({"dir": d, "step": step, "n_runs": len(g), "sources": ",".join(sorted(set(g.sources))),
                     "f": float(s.f.iloc[0]) if len(s) and pd.notna(s.f.iloc[0]) else None,
                     "verdict": s.verdict.iloc[0] if len(s) else "", "decision": s.decision.iloc[0] if len(s) else ""})
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the exit code."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--analysis", type=Path, default=ANALYSIS)
    ns = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    windows = read_windows(ns.analysis / "load_windows.tsv")
    runs: list[dict[str, str]] = []
    for kind in ("interleaved", "bisect"):
        for run_dir in sorted((ns.analysis / kind).glob("*/")):
            if (run_dir / "runs.tsv").is_file():
                runs.extend(overlapping_runs(run_dir, windows))
    pd.DataFrame(runs).to_csv(ns.analysis / "load_window_runs.tsv", sep="\t", index=False)
    steps = bisect_steps(ns.analysis, runs)
    steps.to_csv(ns.analysis / "load_window_bisect_steps.csv", index=False)
    n_inter = sum(r["kind"] == "interleaved" and r["phase"] != "warmup" for r in runs)
    logger.info("%d windows; %d overlapping runs (%d re-measurement runs that enter a statistic); "
                "%d bisection steps affected", len(windows), len(runs), n_inter, len(steps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
