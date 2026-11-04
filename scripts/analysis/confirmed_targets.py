#!/usr/bin/env python3
"""List the events step 2 confirmed, one series each, for bisection (continuous_chain.sh).

Reads ``results/analysis/interleaved/judge_v11_series.csv`` (written by step2b_judge.py) and
prints one line per event that has at least one series judged C under rule v1.1:
``EVENT<TAB>SERIES``.  SERIES is the event's C series with the largest |fixed_z| (the change
that is easiest to tell from noise, so every bisection step is decided most reliably; ties go
to the larger |fixed_lr|).  Events are printed by their largest |fixed_lr| among C series,
biggest change first.  Standard library only; nothing is measured.

Run: python3 -I scripts/analysis/confirmed_targets.py [--judge PATH] [--exclude E49,E50]
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
JUDGE_SERIES = ROOT / "results" / "analysis" / "interleaved" / "judge_v11_series.csv"
REQUIRED = ("event_id", "series", "verdict", "fixed_lr", "fixed_z")


def _num(text: str | None) -> float:
    """Float of a CSV cell; NaN for empty or unparsable cells."""
    try:
        return float(text) if text not in (None, "") else math.nan
    except ValueError:
        return math.nan


def confirmed_targets(path: Path, exclude: frozenset[str] = frozenset()) -> list[tuple[str, str]]:
    """Events with a v1.1 C verdict and the series to bisect for each.

    Args:
        path: judge_v11_series.csv.
        exclude: Event ids to leave out.

    Returns:
        (event_id, series) pairs, biggest change first.

    Raises:
        FileNotFoundError: If the judge file does not exist.
        KeyError: If a required column is missing.
    """
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise KeyError(f"{path}: missing columns {', '.join(missing)}")
        rows = [r for r in reader if r["verdict"] == "C" and r["event_id"] not in exclude]
    best: dict[str, tuple[float, float, str]] = {}
    size: dict[str, float] = {}
    for r in rows:
        z, lr = abs(_num(r["fixed_z"])), abs(_num(r["fixed_lr"]))
        z, lr = (0.0 if math.isnan(z) else z), (0.0 if math.isnan(lr) else lr)
        ev = r["event_id"]
        if ev not in best or (z, lr) > best[ev][:2]:
            best[ev] = (z, lr, r["series"])
        size[ev] = max(size.get(ev, 0.0), lr)
    order = sorted(best, key=lambda ev: (-size[ev], ev))
    return [(ev, best[ev][2]) for ev in order]


def main(argv: list[str] | None = None) -> int:
    """Print EVENT<TAB>SERIES lines; return 1 if the judge file is missing or malformed."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--judge", type=Path, default=JUDGE_SERIES)
    ap.add_argument("--exclude", default="", help="comma-separated event ids to leave out")
    ns = ap.parse_args(argv)
    exclude = frozenset(x.strip() for x in ns.exclude.split(",") if x.strip())
    try:
        targets = confirmed_targets(ns.judge, exclude)
    except (FileNotFoundError, KeyError) as exc:
        logger.error("%s", exc)
        return 1
    for ev, series in targets:
        sys.stdout.write(f"{ev}\t{series}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
