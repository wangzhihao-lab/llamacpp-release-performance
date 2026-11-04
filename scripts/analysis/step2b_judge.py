#!/usr/bin/env python3
"""Root-cause protocol, step 2b: decision rule v1.1 for the interleaved re-measurements.

Reads every ``results/analysis/interleaved/<event>_<old>_<new>/plan.json`` written by
``step2_interleaved.py`` together with the llama-bench JSON files of its runs, and judges
each series with decision rule v1.1 of the protocol (Section 3 of the paper):

* run statistic: y = ln(median(samples_ts)) of one llama-bench process;
* effect: lr = mean(y_B) - mean(y_A);
* noise, fixed phase: s = max(sigma_fixed[model, backend, test], pooled within-side SD of
  this group), where sigma_fixed pools the within-side SD of every group of every event
  (A/A control included);
* noise, default phase (one run per side): sigma_default[model, backend, test] = SD over
  all (event, side) of ln(default re-run / campaign run) divided by sqrt(2) (two runs of the
  same binary and configuration in separate sessions);
* SE = s * sqrt(1/n_A + 1/n_B), z = lr / SE;
* a phase confirms when |lr| >= ln(1 + min_rel) (5%), |z| >= z_min (3) and the sign equals
  the step-1 sign; the same with the opposite sign is "reversed";
* series verdict: C (fixed confirms), reversed (fixed reversed), A (only default confirms),
  noise, incomplete (< 2 fixed runs on a side); C with |lr_fixed| < half of the step-1 effect
  is flagged ``attenuated``.  Event verdict: C > A > reversed > noise > incomplete.

Series that ran along without being listed by the detector (the other test of the same
runs) and the A/A control get a two-sided ``info``/``aa`` judgment only; so do the
visibility re-tests (event ids ``V<event>``, ``visibility_events.csv``: a confirmed event on the
(model, back end) groups step 2 did not measure), judged ``visible``/``not_visible``.

Outputs (``results/analysis/interleaved/``): ``judge_v11_series.csv``,
``judge_v11_events.csv``, ``noise_model_v11.csv``, ``MEMO_v11.md`` (``--suffix`` is appended
to the names).  Nothing is run on the machine; this only reads files.

Sensitivity analysis (added after the first events were measured): ``--drop-round1-unwarmed``
leaves out fixed round 1 of every group measured without the v1.2 warm-up run, because the
first run of a group could deviate from the later runs by tens of percent;
the remaining B A A B runs are balanced in position.  Warm-up runs never enter any statistic.

Sensitivity analysis: ``--exclude-windows results/analysis/load_windows.tsv``
leaves out every run whose start-to-finish span (``runs.tsv``) overlaps a recorded window of
outside load (unrelated jobs, system tasks, analysis jobs of this study on the same machine).

Run: uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step2b_judge.py
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from step2_interleaved import load_bench_json, test_samples

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
ANALYSIS = RESULTS / "analysis"
EVENT_FILES = ("candidate_events.csv", "control_events.csv", "changepoint_events.csv", "remeasure_events.csv",
               "visibility_events.csv")
TESTS = ("pp512", "tg128")
VERDICT_ORDER = ("C", "A", "reversed", "noise", "incomplete")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunValue:
    """One measured run.

    Attributes:
        event_id: Event id.
        model: Model name.
        backend: metal or cpu.
        tag_a: Older tag of the group.
        tag_b: Newer tag of the group.
        phase: fixed, default or warmup (v1.2; no statistic uses it).
        rnd: Round.
        side: A or B.
        tag: Tag of the binary.
        test: pp512 or tg128.
        y: ln(median samples_ts).
    """

    event_id: str
    model: str
    backend: str
    tag_a: str
    tag_b: str
    phase: str
    rnd: int
    side: str
    tag: str
    test: str
    y: float


def run_value(path: Path, test: str) -> float | None:
    """ln(median(samples_ts)) of one llama-bench JSON for ``test``; None if missing.

    Args:
        path: JSON file.
        test: pp512 or tg128.

    Returns:
        The log median, or None.
    """
    st = test_samples(load_bench_json(path)).get(test)
    if st is None:
        return None
    samples = [x for x in st[1] if x > 0]
    value = float(np.median(samples)) if samples else st[0]
    return math.log(value) if value > 0 else None


def campaign_value(results: Path, tag: str, model: str, backend: str, test: str) -> float | None:
    """Same statistic for the campaign run of (tag, model, backend), main parameter set."""
    return run_value(results / tag / f"{model}_{backend}.json", test)


def _utc(stamp: str) -> datetime:
    """Parse an ISO 8601 UTC time stamp such as ``2026-10-14T14:22:40Z``."""
    return datetime.strptime(stamp.strip().rstrip("Z")[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)


def load_windows(path: Path) -> list[tuple[datetime, datetime]]:
    """Windows of recorded outside load.

    Args:
        path: TSV with the columns ``start_utc`` and ``end_utc`` (other columns are notes).

    Returns:
        (start, end) pairs in UTC.
    """
    with path.open(newline="") as fh:
        return [(_utc(r["start_utc"]), _utc(r["end_utc"])) for r in csv.DictReader(fh, delimiter="\t")]


def overlapping_stems(out: Path, windows: list[tuple[datetime, datetime]]) -> set[str]:
    """Stems of the runs of one event directory whose start-to-finish span overlaps a window.

    Args:
        out: Event directory with ``runs.tsv``.
        windows: (start, end) pairs from :func:`load_windows`.

    Returns:
        JSON file stems; empty without windows or ``runs.tsv``.
    """
    path = out / "runs.tsv"
    if not windows or not path.is_file():
        return set()
    stems: set[str] = set()
    with path.open(newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            if not r.get("started_at_utc") or not r.get("finished_at_utc"):
                continue
            a, b = _utc(r["started_at_utc"]), _utc(r["finished_at_utc"])
            if any(a < end and b > start for start, end in windows):
                stems.add(Path(r["json_file"]).stem)
    return stems


def collect(interleaved: Path, windows: list[tuple[datetime, datetime]] | None = None
            ) -> tuple[list[RunValue], list[dict[str, Any]]]:
    """Read all event directories.

    Args:
        interleaved: The interleaved/ directory.
        windows: Optional windows of outside load; runs overlapping one are left out.

    Returns:
        (run values, group descriptors with the listed series of every group).
    """
    values: list[RunValue] = []
    groups: list[dict[str, Any]] = []
    for plan_path in sorted(interleaved.glob("*/plan.json")):
        plan = json.loads(plan_path.read_text())
        out = plan_path.parent
        skip = overlapping_stems(out, windows or [])
        if skip:
            logger.info("%s: left out %d runs that overlap a load window", out.name, len(skip))
        for g in plan["groups"]:
            warmed = any(r["phase"] == "warmup" and run_value(out / f"{r['stem']}.json", t) is not None
                         for r in g["runs"] for t in TESTS)
            groups.append({"event_id": plan["event_id"], "tag_a": g["tag_a"], "tag_b": g["tag_b"],
                           "model": g["model"], "backend": g["backend"], "series": g["series"],
                           "equivalent": g.get("equivalent", True), "warmed": warmed})
            for r in g["runs"]:
                if r["stem"] in skip:
                    continue
                for test in TESTS:
                    y = run_value(out / f"{r['stem']}.json", test)
                    if y is not None:
                        values.append(RunValue(plan["event_id"], g["model"], g["backend"], g["tag_a"], g["tag_b"],
                                               r["phase"], int(r["round"]), r["side"], r["tag"], test, y))
    return values, groups


def expected_lr(analysis: Path) -> dict[tuple[str, ...], float]:
    """Step-1 log ratio of every listed series of the event files.

    Keyed by (event_id, series, tag_old, tag_new), and by (event_id, series) for the last pair
    listed; an event can list one series for two adjacent pairs with opposite signs (E14).
    """
    out: dict[tuple[str, ...], float] = {}
    for name in EVENT_FILES:
        path = analysis / name
        if not path.is_file():
            continue
        for _, ev in pd.read_csv(path).iterrows():
            for s in json.loads(ev["series_json"]):
                lr = float(s.get("log_ratio", 0.0))
                out[(ev["event_id"], s["series"])] = lr
                if s.get("tag_old") and s.get("tag_new"):
                    out[(ev["event_id"], s["series"], s["tag_old"], s["tag_new"])] = lr
    return out


def noise_model(df: pd.DataFrame, results: Path) -> pd.DataFrame:
    """Per (model, backend, test): sigma_fixed (pooled within-side SD) and sigma_default.

    Args:
        df: Run values as a frame.
        results: results/ directory (campaign JSON).

    Returns:
        Frame with sigma_fixed, df_fixed, sigma_default, n_default.
    """
    rows = []
    for (model, backend, test), sub in df.groupby(["model", "backend", "test"]):
        fx = sub[sub.phase == "fixed"]
        ss, dof = 0.0, 0
        for _, side in fx.groupby(["event_id", "tag_a", "tag_b", "side"]):
            if len(side) >= 2:
                ss += float(((side.y - side.y.mean()) ** 2).sum())
                dof += len(side) - 1
        diffs = []
        for _, r in sub[sub.phase == "default"].iterrows():
            c = campaign_value(results, r.tag, model, backend, test)
            if c is not None:
                diffs.append(r.y - c)
        rows.append({"model": model, "backend": backend, "test": test,
                     "sigma_fixed": math.sqrt(ss / dof) if dof else float("nan"), "df_fixed": dof,
                     "sigma_default": float(np.std(diffs, ddof=1)) / math.sqrt(2) if len(diffs) >= 3 else float("nan"),
                     "n_default": len(diffs),
                     "repro_mean": float(np.mean(diffs)) if diffs else float("nan")})
    return pd.DataFrame(rows)


def phase_test(a: np.ndarray, b: np.ndarray, sigma_ref: float, use_own: bool) -> dict[str, float]:
    """Effect, noise and z for one phase.

    Args:
        a: y values of side A.
        b: y values of side B.
        sigma_ref: Reference run-level SD for this (model, backend, test, phase).
        use_own: Also use this group's pooled within-side SD (fixed phase).

    Returns:
        Dict with lr, s, se, z, n_a, n_b (NaN when a side is empty).
    """
    if len(a) == 0 or len(b) == 0:
        return {"lr": float("nan"), "s": float("nan"), "se": float("nan"), "z": float("nan"),
                "n_a": len(a), "n_b": len(b)}
    lr = float(b.mean() - a.mean())
    s = sigma_ref if not math.isnan(sigma_ref) else 0.0
    if use_own and len(a) + len(b) > 2:
        dof = (len(a) - 1) + (len(b) - 1)
        if dof > 0:
            own = math.sqrt((float(((a - a.mean()) ** 2).sum()) + float(((b - b.mean()) ** 2).sum())) / dof)
            s = max(s, own)
    se = s * math.sqrt(1 / len(a) + 1 / len(b))
    return {"lr": lr, "s": s, "se": se, "z": lr / se if se > 0 else float("nan"), "n_a": len(a), "n_b": len(b)}


def confirms(res: dict[str, float], sign: float, ns: argparse.Namespace) -> tuple[bool, bool]:
    """(confirmed with the expected sign, confirmed with the opposite sign)."""
    if math.isnan(res["z"]):
        return False, False
    big = abs(res["lr"]) >= math.log1p(ns.min_rel) and abs(res["z"]) >= ns.z_min
    return bool(big and np.sign(res["lr"]) == sign), bool(big and np.sign(res["lr"]) == -sign)


def judge(values: list[RunValue], groups: list[dict[str, Any]], expected: dict[tuple[str, ...], float],
          noise: pd.DataFrame, ns: argparse.Namespace) -> pd.DataFrame:
    """Series-level verdicts.

    Args:
        values: Run values.
        groups: Group descriptors.
        expected: Step-1 log ratios of listed series.
        noise: Noise model.
        ns: Parsed arguments.

    Returns:
        One row per (event, group, test).
    """
    df = pd.DataFrame([v.__dict__ for v in values])
    nz = noise.set_index(["model", "backend", "test"])
    rows = []
    for g in groups:
        for test in TESTS:
            series = f"{g['model']}/{g['backend']}/{test}"
            key = (g["model"], g["backend"], test)
            sub = df[(df.event_id == g["event_id"]) & (df.model == g["model"]) & (df.backend == g["backend"])
                     & (df.tag_a == g["tag_a"]) & (df.tag_b == g["tag_b"]) & (df.test == test)] if len(df) else df
            sig_f = float(nz.loc[key, "sigma_fixed"]) if key in nz.index else float("nan")
            sig_d = float(nz.loc[key, "sigma_default"]) if key in nz.index else float("nan")
            res = {}
            for phase, sig, own in (("fixed", sig_f, True), ("default", sig_d, False)):
                p = sub[sub.phase == phase] if len(sub) else sub
                a = p[p.side == "A"].y.to_numpy() if len(p) else np.array([])
                b = p[p.side == "B"].y.to_numpy() if len(p) else np.array([])
                res[phase] = phase_test(a, b, sig, own)
            listed = series in g["series"]
            step1 = expected.get((g["event_id"], series, g["tag_a"], g["tag_b"]),
                                 expected.get((g["event_id"], series), float("nan")))
            row: dict[str, Any] = {"event_id": g["event_id"], "tag_a": g["tag_a"], "tag_b": g["tag_b"],
                                   "series": series, "listed": int(listed), "fixed_equivalent": int(g["equivalent"]),
                                   "step1_lr": step1}
            for phase in ("fixed", "default"):
                for k, v in res[phase].items():
                    row[f"{phase}_{k}"] = v
            hit_f = abs(res["fixed"]["z"]) >= ns.z_min and abs(res["fixed"]["lr"]) >= math.log1p(ns.min_rel) \
                if not math.isnan(res["fixed"]["z"]) else False
            if g["event_id"].startswith("AA"):
                row["verdict"] = "aa_false_positive" if hit_f else "aa_ok"
            elif g["event_id"].startswith("V"):
                # visibility re-test of a confirmed event on the (model, back end) groups step 2 did not
                # measure: two-sided, does this series see the change at all
                complete = res["fixed"]["n_a"] >= 2 and res["fixed"]["n_b"] >= 2
                row["verdict"] = "incomplete" if not complete else "visible" if hit_f else "not_visible"
            elif not listed or math.isnan(step1):
                ok, _ = confirms(res["fixed"], float(np.sign(res["fixed"]["lr"]) or 1.0), ns)
                row["verdict"] = "info_change" if ok else "info_none"
            elif res["fixed"]["n_a"] < 2 or res["fixed"]["n_b"] < 2:
                row["verdict"] = "incomplete"
            else:
                sign = 1.0 if step1 >= 0 else -1.0
                f_ok, f_rev = confirms(res["fixed"], sign, ns)
                d_ok, _ = confirms(res["default"], sign, ns)
                row["verdict"] = "C" if f_ok else "reversed" if f_rev else "A" if d_ok else "noise"
            row["attenuated"] = int(row["verdict"] == "C" and abs(res["fixed"]["lr"]) < 0.5 * abs(step1))
            rows.append(row)
    return pd.DataFrame(rows)


def event_table(series: pd.DataFrame, v1: pd.DataFrame | None) -> pd.DataFrame:
    """Event verdicts (v1.1, and v1 from step2's summary.csv when available)."""
    rows = []
    for ev, sub in series.groupby("event_id", sort=False):
        listed = sub[sub.listed == 1]
        verdicts = list(listed.verdict)
        if ev.startswith("AA"):
            verdict = f"aa: {int((sub.verdict == 'aa_false_positive').sum())}/{len(sub)} false positives"
        elif ev.startswith("V"):
            verdict = f"vis: {int((sub.verdict == 'visible').sum())}/{len(sub)} series visible"
        else:
            verdict = next((v for v in VERDICT_ORDER[:3] if v in verdicts), None) or \
                ("noise" if verdicts and all(v == "noise" for v in verdicts) else "incomplete")
        v1_verdict = ""
        if v1 is not None and not v1.empty:
            s1 = v1[(v1.event_id == ev) & (v1.listed == 1)]
            if not s1.empty:
                vs = list(s1.verdict)
                v1_verdict = next((v for v in ("C", "A", "reversed") if v in vs), None) or \
                    ("noise" if all(v == "noise" for v in vs) else "incomplete")
        rows.append({"event_id": ev, "pair": f"{sub.tag_a.iloc[0]}→{sub.tag_b.iloc[0]}", "verdict_v11": verdict,
                     "verdict_v1": v1_verdict,
                     "series": "; ".join(f"{s}:{v}{'(att)' if a else ''}" for s, v, a in
                                         zip(listed.series, listed.verdict, listed.attenuated))})
    return pd.DataFrame(rows)


def write_memo(path: Path, series: pd.DataFrame, events: pd.DataFrame, noise: pd.DataFrame) -> None:
    """Human-readable summary."""
    def pct(x: float) -> str:
        return "n/a" if pd.isna(x) else f"{math.expm1(x):+.1%}"

    lines = ["# Step 2b: decision rule v1.1", "",
             ("Generated by `scripts/analysis/step2b_judge.py` (the rule of protocol v1.1 is given in Section 3 of "
              "the paper)."), "",
             "## Noise model (per run, log scale)", "",
             "| Model/back end/test | σ_fixed | df | σ_default | n | Mean re-measurement − campaign |",
             "|---|---|---|---|---|---|"]
    for _, r in noise.iterrows():
        lines.append(f"| {r.model}/{r.backend}/{r.test} | {r.sigma_fixed:.3f} | {r.df_fixed} | {r.sigma_default:.3f} | "
                     f"{r.n_default} | {pct(r.repro_mean)} |")
    lines += ["", "## Events", "", "| Event | Interval | v1.1 | v1 | Series |", "|---|---|---|---|---|"]
    lines += [f"| {e.event_id} | {e.pair} | {e.verdict_v11} | {e.verdict_v1} | {e.series} |" for e in events.itertuples()]
    lines += ["", "## Series details (listed series)", "",
              "| Event | Series | Step-1 Δ | Fixed Δ (z) | Default Δ (z) | Verdict |", "|---|---|---|---|---|---|"]
    for r in series[series.listed == 1].itertuples():
        lines.append(f"| {r.event_id} | {r.series} | {pct(r.step1_lr)} | {pct(r.fixed_lr)} ({r.fixed_z:.1f}) | "
                     f"{pct(r.default_lr)} ({r.default_z:.1f}) | {r.verdict}{', attenuated' if r.attenuated else ''} |")
    path.write_text("\n".join(lines) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command-line interface."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--interleaved", type=Path, default=ANALYSIS / "interleaved")
    ap.add_argument("--analysis", type=Path, default=ANALYSIS)
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--min-rel", type=float, default=0.05, help="practical floor: |lr| >= ln(1 + min_rel)")
    ap.add_argument("--z-min", type=float, default=3.0)
    ap.add_argument("--drop-round1-unwarmed", action="store_true",
                    help="sensitivity analysis: leave out fixed round 1 of every group measured without a warm-up "
                         "run (the first 2026-10-14 events); the rest, B A A B, is balanced in position")
    ap.add_argument("--exclude-windows", type=Path, default=None,
                    help="sensitivity analysis: TSV of outside-load windows (start_utc, end_utc); runs that "
                         "overlap one are left out")
    ap.add_argument("--suffix", default="", help="appended to the output names, e.g. _norm1")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the exit code."""
    ns = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    values, groups = collect(ns.interleaved, load_windows(ns.exclude_windows) if ns.exclude_windows else None)
    if ns.drop_round1_unwarmed:
        cold = {(g["event_id"], g["model"], g["backend"], g["tag_a"], g["tag_b"]) for g in groups if not g["warmed"]}
        before = len(values)
        values = [v for v in values if not (v.phase == "fixed" and v.rnd == 1
                                            and (v.event_id, v.model, v.backend, v.tag_a, v.tag_b) in cold)]
        logger.info("sensitivity: left out %d fixed round-1 values of %d groups without a warm-up",
                    before - len(values), len(cold))
    if not values:
        logger.error("no measured runs under %s", ns.interleaved)
        return 1
    df = pd.DataFrame([v.__dict__ for v in values])
    noise = noise_model(df, ns.results)
    series = judge(values, groups, expected_lr(ns.analysis), noise, ns)
    # v1 verdicts from each event directory's own summary.csv: step2 rewrites the global
    # interleaved/summary.csv with the events of its latest invocation only.
    per_event = [pd.read_csv(f) for f in sorted(ns.interleaved.glob("*/summary.csv"))]
    v1 = pd.concat(per_event, ignore_index=True) if per_event else None
    events = event_table(series, v1)
    sfx = ns.suffix
    noise.to_csv(ns.interleaved / f"noise_model_v11{sfx}.csv", index=False)
    series.to_csv(ns.interleaved / f"judge_v11_series{sfx}.csv", index=False)
    events.to_csv(ns.interleaved / f"judge_v11_events{sfx}.csv", index=False)
    write_memo(ns.interleaved / f"MEMO_v11{sfx}.md", series, events, noise)
    logger.info("%d runs, %d groups, %d events -> %s", len(values), len(groups), len(events),
                ns.interleaved / f"MEMO_v11{sfx}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
