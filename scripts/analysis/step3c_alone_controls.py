#!/usr/bin/env python3
"""D1 root-cause protocol, step 3c: tg128 alone on the confirmed events, and first against last release.

Fixed before any run (2026-11-05).

* ``G`` groups measure tg128 alone (``-p 0 -n 128``) on the sampled pair of each confirmed event, on the
  event's own back end, because in the re-measurements tg128 followed pp512 in the same process.
* ``F`` groups measure the first sampled release that loads a model against the newest sampled release,
  on all twelve series, each test in a process of its own.

Four groups of Qwen2.5 CPU tg128 ran right after a Mistral-7B CPU group, while the machine was still
cooling, so they are repeated after 300 s of idle time (``GE16R``, ``GE19R``, ``GE46R``, ``FR``; amendment
of the plan).  Those cells take the repeat, and the first groups stay in the tables.  ``FS`` repeats the four
first-to-last groups of Qwen2.5 and TinyLlama CPU that other load had disturbed.

Timed runs follow step 3b: one process per run, a warm-up run of arm A before each group, a 20 s cooldown
and the wait for a quiet machine of ``step2_interleaved.wait_quiet``.  Two arms alternate AB BA for four
rounds.  Options come from ``step2_interleaved.fixed_args``.  Completed runs are skipped on a restart.

Statistics: y = ln(median(samples_ts)) per run, lr = mean(y_B) - mean(y_A), s = max(sigma_fixed of the
series, pooled within-arm SD), SE = s sqrt(1/n_A + 1/n_B), z = lr / SE; a difference meets the rule when
|lr| >= ln 1.05 and |z| >= 3.  For ``F``, P is the product of the effects of the visible cells of the
series and D = lr - ln P is judged with SE_D = sqrt(SE^2 + SE_P^2).

Outputs (``results/analysis/alone/``): one directory per group with runs.tsv and a JSON and log per run,
``cells.csv``, ``first_last.csv``, the same two without the runs that overlap ``load_windows.tsv``
(``*_nowin.csv``), ``MEMO.md``, ``activity.log``.  ``--dry-run`` prints the plan,
``--smoke`` runs each arm once with ``-r 1`` into ``smoke/`` and ``--summarize-only`` rebuilds the tables.

Run: nice -n 10 uv run --no-project --with pandas --with numpy python3 -B -I scripts/analysis/step3c_alone_controls.py
"""

from __future__ import annotations

import argparse
import csv
import logging
import math
import signal
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step2_interleaved as s2
import step3b_switch_controls as s3
from step2b_judge import phase_test, run_value

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "analysis" / "alone"
VISIBILITY = ROOT / "results" / "analysis" / "step4_visibility.csv"
WINDOWS = ROOT / "results" / "analysis" / "load_windows.tsv"
JUDGED = ROOT / "results" / "analysis" / "interleaved" / "judge_v11_series.csv"
ROUNDS = 4
THREADS = {"metal": 4, "cpu": 8}
BATCH = 512
NEWEST = "b11559"
EXCLUDED = {("E01", "mistral-7b/cpu/pp512")}
T, Q, M = "tinyllama-1.1b", "qwen2.5-1.5b", "mistral-7b"
FIRST = {T: "b1137", M: "b1137", Q: "b1939"}
EVENTS = (
    ("E03", "b1505", "b1561", "cpu", (M, T)),
    ("E04", "b1561", "b1621", "cpu", (T,)),
    ("E16", "b3130", "b3222", "cpu", (M, Q, T)),
    ("E19", "b3610", "b3665", "cpu", (M, Q, T)),
    ("E46", "b7100", "b7245", "cpu", (M, Q, T)),
    ("E01", "b1137", "b1245", "metal", (M, T)),
    ("E49", "b8545", "b8740", "metal", (M, Q, T)),
    ("E50", "b8916", "b9076", "metal", (M, Q, T)),
)

logger = logging.getLogger(__name__)


def make_group(exp: str, model: str, backend: str, test: str, tag_a: str, tag_b: str, caps: dict[str, s2.Caps]) -> s3.Group:
    """One two-arm group with the fixed configuration of its pair of releases.

    Args:
        exp: Experiment id, used in the directory name.
        model: Model name.
        backend: cpu or metal.
        test: pp512 or tg128.
        tag_a: Older release.
        tag_b: Newer release.
        caps: Cache of binary capabilities.

    Returns:
        The group.
    """
    for tag in (tag_a, tag_b):
        if tag not in caps:
            caps[tag] = s2.binary_caps(tag, allow_exec=True)
    args_a, args_b, _, _ = s2.fixed_args(caps[tag_a], caps[tag_b], backend, THREADS, BATCH, BATCH)
    arms = (s3.Arm("A", tag_a, tuple(args_a), tag_a), s3.Arm("B", tag_b, tuple(args_b), tag_b))
    return s3.Group(exp, model, backend, test, ROUNDS, arms)


def all_groups() -> list[s3.Group]:
    """The G groups, then the F groups, in the order of measurement."""
    caps: dict[str, s2.Caps] = {}
    groups = [make_group(f"G{e}", m, b, "tg128", a, n, caps) for e, a, n, b, models in EVENTS for m in models]
    for model in (M, Q, T):
        for backend in ("cpu", "metal"):
            for test in ("pp512", "tg128"):
                groups.append(make_group("F", model, backend, test, FIRST[model], NEWEST, caps))
    for exp, tag_a, tag_b in (("GE16R", "b3130", "b3222"), ("GE19R", "b3610", "b3665"), ("GE46R", "b7100", "b7245"),
                              ("FR", FIRST[Q], NEWEST)):
        groups.append(make_group(exp, Q, "cpu", "tg128", tag_a, tag_b, caps))
    for model in (Q, T):  # second and third amendments: these groups were disturbed by other load
        for test in ("pp512", "tg128"):
            groups.append(make_group("FS", model, "cpu", test, FIRST[model], NEWEST, caps))
    return groups


def load_windows() -> list[tuple[str, str]]:
    """(start, end) of the recorded windows of other load, as ISO strings in UTC."""
    with WINDOWS.open(newline="") as fh:
        return [(r["start_utc"], r["end_utc"]) for r in csv.DictReader(fh, delimiter="\t")]


def arm_values(group: s3.Group, windows: list[tuple[str, str]] | None = None) -> dict[str, np.ndarray]:
    """Log throughput of the fixed runs of each arm; a repeated file counts once.

    Args:
        group: The group.
        windows: Runs that overlap one of these windows are left out.

    Returns:
        Values per arm.
    """
    path = OUT / group.name / "runs.tsv"
    values: dict[str, list[float]] = {"A": [], "B": []}
    if not path.is_file():
        return {k: np.array(v) for k, v in values.items()}
    seen: set[str] = set()
    with path.open(newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row["phase"] != "fixed" or row["json_file"] in seen:
                continue
            if any(row["started_at_utc"] < end and row["finished_at_utc"] > start for start, end in windows or ()):
                continue
            y = run_value(OUT / group.name / row["json_file"], group.test)
            if y is not None:
                values[row["side"]].append(y)
                seen.add(row["json_file"])
    return {k: np.array(v) for k, v in values.items()}


def judged(group: s3.Group, floor: dict[tuple[str, str, str], float],
           windows: list[tuple[str, str]] | None = None) -> dict[str, float | int | bool | str] | None:
    """Rule of step 3b for one group.

    Args:
        group: The group.
        floor: sigma_fixed per (model, backend, test).
        windows: Runs that overlap one of these windows are left out.

    Returns:
        A table row, or None when an arm has no run.
    """
    ys = arm_values(group, windows)
    if not len(ys["A"]) or not len(ys["B"]):
        return None
    res = phase_test(ys["A"], ys["B"], floor[(group.model, group.backend, group.test)], use_own=True)
    meets = not math.isnan(res["z"]) and abs(res["lr"]) >= math.log1p(s3.MIN_REL) and abs(res["z"]) >= s3.Z_MIN
    return {"exp": group.exp, "series": f"{group.model}/{group.backend}/{group.test}", "tag_a": group.arms[0].tag,
            "tag_b": group.arms[1].tag, "n_a": res["n_a"], "n_b": res["n_b"], "ts_a": float(np.exp(ys["A"].mean())),
            "ts_b": float(np.exp(ys["B"].mean())), "lr": res["lr"], "pct": 100 * math.expm1(res["lr"]), "s": res["s"],
            "se": res["se"], "z": res["z"], "meets_rule": bool(meets)}


def confirmed_product(series: str, vis: pd.DataFrame) -> tuple[float, float, int]:
    """Log product of the visible cells of a series and its standard error.

    Args:
        series: model/backend/test.
        vis: step4_visibility.csv.

    Returns:
        (sum of log effects, its standard error, number of cells).
    """
    rows = vis[(vis.series == series) & vis.state.isin(["up", "down"])]
    rows = rows.loc[[(e, series) not in EXCLUDED for e in rows.event_id]]
    logs = np.log1p(rows.lr_pct.astype(float) / 100)
    ses = (logs / rows.z.astype(float)).abs()
    return float(logs.sum()), float(np.sqrt((ses ** 2).sum())), len(rows)


def after_pp(series_df: pd.DataFrame, event: str, series: str) -> tuple[float, float]:
    """Change and z of a cell when tg128 followed pp512, from the same sources as the matrix.

    Args:
        series_df: judge_v11_series.csv.
        event: Event id.
        series: model/backend/test.

    Returns:
        (percent, z), NaN when the cell has no such measurement.
    """
    for source in (f"{event}R", event, f"V{event}"):
        rows = series_df[(series_df.event_id == source) & (series_df.series == series)].dropna(subset=["fixed_lr", "fixed_z"])
        if len(rows):
            return 100 * math.expm1(float(rows.fixed_lr.iloc[0])), float(rows.fixed_z.iloc[0])
    return math.nan, math.nan


def summarize(groups: list[s3.Group], windows: list[tuple[str, str]] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tables of the G cells and of the first-to-last comparison.

    Args:
        groups: All groups.
        windows: Runs that overlap one of these windows are left out.

    Returns:
        (cells, first_last).
    """
    floor = s3.noise_floor()
    vis = pd.read_csv(VISIBILITY, keep_default_na=False)
    vis["lr_pct"] = pd.to_numeric(vis.lr_pct, errors="coerce")
    vis["z"] = pd.to_numeric(vis.z, errors="coerce")
    series_df = pd.read_csv(JUDGED)
    cells, ends = [], []
    for g in groups:
        row = judged(g, floor, windows)
        if row is None:
            continue
        if g.exp.startswith("G"):
            event = g.exp[1:].removesuffix("R")
            pct, z = after_pp(series_df, event, str(row["series"]))
            row = {**row, "event_id": event, "after_pp_pct": pct, "after_pp_z": z}
            cells.append(row)
            continue
        log_p, se_p, n_cells = confirmed_product(str(row["series"]), vis)
        d = float(row["lr"]) - log_p
        se_d = math.hypot(float(row["se"]), se_p)
        ends.append({**row, "factor": math.exp(float(row["lr"])), "n_cells": n_cells, "product": math.exp(log_p),
                     "se_log_product": se_p, "d": d, "se_d": se_d, "z_d": d / se_d if se_d else math.nan,
                     "unexplained": abs(d) >= math.log1p(s3.MIN_REL) and se_d > 0 and abs(d / se_d) >= s3.Z_MIN})
    return pd.DataFrame(cells), pd.DataFrame(ends)


def write_tables(groups: list[s3.Group]) -> None:
    """Write cells.csv, first_last.csv and MEMO.md."""
    cells, ends = summarize(groups)
    cells.to_csv(OUT / "cells.csv", index=False)
    ends.to_csv(OUT / "first_last.csv", index=False)
    cells_nowin, ends_nowin = summarize(groups, load_windows())
    cells_nowin.to_csv(OUT / "cells_nowin.csv", index=False)
    ends_nowin.to_csv(OUT / "first_last_nowin.csv", index=False)
    lines = ["# Step 3c: tg128 alone and first against last release", "",
             "|lr| >= ln 1.05 and |z| >= 3 meets the rule.", ""]
    if not cells.empty:
        lines += ["## tg128 alone", "", s3.md_table(cells), ""]
    if not ends.empty:
        lines += ["## First against last", "", s3.md_table(ends), ""]
    (OUT / "MEMO.md").write_text("\n".join(lines) + "\n")


def smoke(groups: list[s3.Group], ns: argparse.Namespace) -> int:
    """Run every arm once with ``-r 1``, outside the statistics; returns the number of failures."""
    failures = 0
    done: set[tuple[str, str, str, str]] = set()
    for g in groups:
        if g.model == M:  # the options are those of the small models; one small model per release is enough
            continue
        for arm in g.arms:
            key = (arm.tag, g.model, g.backend, g.test)
            if key in done:
                continue
            done.add(key)
            run = s3.make_run(g, arm, "smoke", 0, s3.command(g, arm, 1), {})
            run = s2.Run(**{**run.__dict__, "stem": f"{g.model}_{g.backend}_{g.test}_{arm.tag}"})
            out = OUT / "smoke"
            out.mkdir(parents=True, exist_ok=True)
            row = s2.execute_run(run, out, ns)
            ok = str(row.get("exit_code")) == "0" and s3.has_test(out / f"{run.stem}.json", g.test)
            failures += not ok
            logger.info("%s %s", "ok" if ok else "FAILED", run.stem)
    return failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command-line interface; the waiting options are those of step 2."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--only", type=lambda s: [x.strip() for x in s.split(",") if x.strip()], default=None,
                    help="experiment prefixes to run, for example G or F")
    ap.add_argument("--cooldown", type=float, default=20.0)
    ap.add_argument("--idle-min", type=float, default=80.0)
    ap.add_argument("--thermal-max", type=int, default=1)
    ap.add_argument("--load-max", type=float, default=0.0)
    ap.add_argument("--load-wait-max", type=float, default=1800.0)
    ap.add_argument("--on-load-timeout", choices=("proceed", "skip", "stop"), default="proceed")
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--settle", type=float, default=0.0, help="idle seconds before each group")
    ap.add_argument("--force", action="store_true", help="re-run runs whose output exists")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--summarize-only", action="store_true")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the exit code."""
    ns = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    s3.OUT = OUT
    groups = all_groups()
    chosen = [g for g in groups if ns.only is None or any(g.exp.startswith(p) for p in ns.only)]
    if ns.dry_run:
        for g in chosen:
            runs = s3.group_runs(g)
            print(f"{g.name}: {len(runs)} runs, order {' '.join(lab for _, lab in s3.order(g))}")
            for run in runs[1:3]:
                print(" ", run.side, " ".join(run.argv[3:]).replace(str(s2.MODELS_DIR) + "/", ""))
        print(f"{len(chosen)} groups, {sum(len(s3.group_runs(g)) for g in chosen)} runs")
        return 0
    if ns.summarize_only:
        write_tables(groups)
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    if ns.smoke:
        return 1 if smoke(chosen, ns) else 0
    signal.signal(signal.SIGTERM, s2.handle_signal)
    signal.signal(signal.SIGINT, s2.handle_signal)
    stop = threading.Event()
    thread = threading.Thread(target=s3.sampler, args=(OUT / "activity.log", stop), daemon=True)
    thread.start()
    try:
        for g in chosen:
            if s2.STOP["flag"]:
                break
            finished = all((OUT / g.name / f"{r.stem}.json").is_file() for r in s3.group_runs(g))
            if ns.settle and not finished:
                logger.info("%s: idle for %.0f s", g.name, ns.settle)
                time.sleep(ns.settle)
            s3.run_group(g, ns)
    finally:
        stop.set()
        thread.join(timeout=5)
    write_tables(groups)
    logger.info("done%s", " (stopped)" if s2.STOP["flag"] else "")
    return 1 if s2.STOP["flag"] else 0


if __name__ == "__main__":
    sys.exit(main())
