#!/usr/bin/env python3
"""Visibility re-test events: every confirmed event on the model/backend groups step 2 did not measure.

Step 2 re-measured each event only on the (model, backend) groups whose series the step-1
detector listed.  Step 4 asks which series can see a confirmed change at all, so this script
writes ``results/analysis/visibility_events.csv``: one row ``V<event>`` per event that the latest
v1.1 judgement (``interleaved/judge_v11_events.csv``) confirms (verdict C), with the event's own
tag pair and, as listed series, both tests of every (model, backend) group of the 3 x 2 matrix
that step 2 did not measure.  ``log_ratio`` is the campaign's value for the pair (0 if a side is
missing); step2b_judge.py judges V events two-sided (``visible`` / ``not_visible``).  Re-measure
events (``E01R`` ...) are skipped when their original is also confirmed.  Nothing is measured.

Run: uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/make_visibility_events.py
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step2_interleaved as s2

logger = logging.getLogger(__name__)

ANALYSIS = s2.RESULTS / "analysis"
SOURCES = ("candidate_events.csv", "changepoint_events.csv", "remeasure_events.csv")
BACKENDS = ("metal", "cpu")
TESTS = ("pp512", "tg128")


def measured_groups(series_json: str) -> set[tuple[str, str]]:
    """(model, backend) groups step 2 measured for an event (those of its listed series)."""
    return {(s["model"], s["backend"]) for s in json.loads(series_json)}


def missing_series(row: dict[str, str], models: tuple[str, ...]) -> list[dict[str, Any]]:
    """Listed series of the V event: both tests of every group the event did not measure.

    Args:
        row: The confirmed event's row (tag_old, tag_new, series_json).
        models: Model names of the matrix.

    Returns:
        Series dicts in step 1's format (series, model, backend, test, tag_old, tag_new, log_ratio).
    """
    done = measured_groups(row["series_json"])
    out = []
    for model in models:
        for backend in BACKENDS:
            if (model, backend) in done:
                continue
            for test in TESTS:
                a = s2.campaign_mean(row["tag_old"], model, backend, test)
                b = s2.campaign_mean(row["tag_new"], model, backend, test)
                lr = math.log(b / a) if a > 0 and b > 0 else 0.0
                out.append({"series": f"{model}/{backend}/{test}", "model": model, "backend": backend, "test": test,
                            "tag_old": row["tag_old"], "tag_new": row["tag_new"], "log_ratio": lr})
    return out


def confirmed_events(judge_events: Path) -> list[str]:
    """Event ids with verdict_v11 == C, without V events and without re-measures of confirmed originals."""
    with judge_events.open(newline="") as fh:
        ids = [r["event_id"] for r in csv.DictReader(fh) if r["verdict_v11"] == "C"]
    keep = [e for e in ids if not e.startswith("V")]
    return [e for e in keep if not (e.endswith("R") and e[:-1] in keep)]


def main(argv: list[str] | None = None) -> int:
    """Write visibility_events.csv; return 1 when the judgement or an event row is missing."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--judge-events", type=Path, default=ANALYSIS / "interleaved" / "judge_v11_events.csv")
    ap.add_argument("--out", type=Path, default=ANALYSIS / "visibility_events.csv")
    ns = ap.parse_args(argv)
    if not ns.judge_events.is_file():
        logger.error("%s missing: run step2b_judge.py first", ns.judge_events)
        return 1
    rows: dict[str, dict[str, str]] = {}
    fields: list[str] = []
    for name in SOURCES:
        path = ANALYSIS / name
        if path.is_file():
            with path.open(newline="") as fh:
                reader = csv.DictReader(fh)
                fields = fields or list(reader.fieldnames or [])
                rows.update({r["event_id"]: r for r in reader})
    models = tuple(s2.MODEL_FILES)
    out = []
    for ev in confirmed_events(ns.judge_events):
        if ev not in rows:
            logger.error("%s: no event row in %s", ev, ", ".join(SOURCES))
            return 1
        series = missing_series(rows[ev], models)
        if not series:
            logger.info("%s: every group already measured", ev)
            continue
        out.append({**rows[ev], "event_id": f"V{ev}", "class": "V", "n_series": str(len(series)),
                    "series": ";".join(s["series"] for s in series), "series_json": json.dumps(series),
                    "reason": f"visibility re-test of {ev}: groups step 2 did not measure"})
        logger.info("V%s %s->%s: %d series", ev, rows[ev]["tag_old"], rows[ev]["tag_new"], len(series))
    with ns.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    logger.info("%d visibility events -> %s", len(out), ns.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
