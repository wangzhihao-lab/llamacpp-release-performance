#!/usr/bin/env python3
"""Root-cause protocol, step 1: candidate events and their first classification.

Twelve series (3 models x 2 back ends x {pp512, tg128}) are ordered by build number.
Between adjacent measured tags of a series the change is measured on the log scale
(so that a rise and the matching fall are treated alike):

    lr = ln(mean_new / mean_old),   reported as delta = exp(lr) - 1,

and the pair is a candidate if ``|lr| >= tau`` with

    tau = max(ln(1 + MIN_REL), K_SD * s_pooled),
    s_pooled = sqrt(((n_old-1) s_old^2 + (n_new-1) s_new^2) / (n_old + n_new - 2)),

s = standard deviation of ln(samples_ts) of the 5 repetitions (cv = stddev/avg when the
JSON samples are missing).  "10 %" therefore means a rise of +10 % or a fall of -9.1 %.
Candidates of different series whose tag intervals overlap are merged into one event
interval.  Each interval is given a first class from the step-0 configuration changes
inside it:

* A: a runtime configuration/default change (likely/possible effect, matching scope),
* B: a build-option change (same rule, and no A change),
* C: no configuration change explains it (possibly an implementation change),
* D: noise suspected, when every series in the interval is near the threshold
  (|lr| < NEAR * tau), or measured after a high load (load1_before above the Tukey fence
  Q3 + LOAD_K * IQR of that model x back end) with a change that does not persist, or part
  of a one-tag spike of a single model (the next sampled tag returns to the old level
  within tau, no other model spikes there in the same direction, no config change is
  reverted with it).

Inputs: results/<tag>/records.csv, results/<tag>/*.json (samples, for the drift note),
results/analysis/config_changes.csv (step 0), data/releases.csv.
Outputs (results/analysis/): candidate_events.csv, candidate_events.md,
timeline.pdf, timeline.svg.

Run from the repository root: uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step1_candidate_events.py
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT_DIR = RESULTS / "analysis"
RELEASES = ROOT / "data" / "releases.csv"

MODELS = ("tinyllama-1.1b", "mistral-7b", "qwen2.5-1.5b")
SHORT = {"tinyllama-1.1b": "tiny", "mistral-7b": "mistral", "qwen2.5-1.5b": "qwen"}
BACKENDS = ("metal", "cpu")
TESTS = ("pp512", "tg128")
PALETTE = ("#332288", "#117733", "#44AA99", "#88CCEE", "#DDCC77", "#CC6677", "#AA4499", "#882255")
MODEL_COLOR = {m: PALETTE[i] for i, m in enumerate(MODELS)}
MODEL_MARKER = {"tinyllama-1.1b": "o", "mistral-7b": "s", "qwen2.5-1.5b": "^"}
CLASS_COLOR = {"A": PALETTE[4], "B": PALETTE[3], "C": PALETTE[5], "D": PALETTE[6]}
CLASS_ALPHA = {"A": 0.35, "B": 0.35, "C": 0.30, "D": 0.12}
CLASS_NAME = {"A": "A runtime config/default change", "B": "B build-option change", "C": "C unexplained",
              "D": "D noise suspected"}
CLASS_NAME_EN = {"A": "A: runtime config/default change", "B": "B: build-option change", "C": "C: unexplained",
                 "D": "D: noise suspected"}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Params:
    """Thresholds of the event rule.

    Attributes:
        min_rel: Floor of the relative threshold (0.10 = 10 %).
        k_sd: Multiplier of the pooled coefficient of variation.
        near: An event with |delta| < near * tau is "near the threshold".
        load_k: Tukey fence multiplier for load1_before outliers.
        drift: |last2/first2 - 1| above this marks within-run drift (note only).
    """

    min_rel: float = 0.10
    k_sd: float = 3.0
    near: float = 1.25
    load_k: float = 1.5
    drift: float = 0.15


def series_name(model: str, backend: str, test: str) -> str:
    """Canonical series id, e.g. ``mistral-7b/metal/pp512``."""
    return f"{model}/{backend}/{test}"


def short_name(series: str) -> str:
    """Short label, e.g. ``mistral/metal/pp512``."""
    model, backend, test = series.split("/")
    return f"{SHORT.get(model, model)}/{backend}/{test}"


def load_json_samples(path: Path) -> dict[str, list[float]]:
    """Read samples_ts per test from a llama-bench JSON file.

    Args:
        path: ``<model>_<backend>.json``.

    Returns:
        test name ('pp512'/'tg128') -> samples.
    """
    if not path.is_file():
        return {}
    text = path.read_text(errors="replace")
    start = text.find("[")
    if start < 0:
        return {}
    try:
        recs, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return {}
    out: dict[str, list[float]] = {}
    for r in recs if isinstance(recs, list) else []:
        if not isinstance(r, dict):
            continue
        name = f"pp{r.get('n_prompt')}" if r.get("n_gen", 0) == 0 else f"tg{r.get('n_gen')}"
        samples = r.get("samples_ts")
        if samples is None and r.get("samples_ns"):
            tokens = r.get("n_prompt", 0) or r.get("n_gen", 0)
            samples = [tokens * 1e9 / ns for ns in r["samples_ns"] if ns]
        if samples:
            out[name] = [float(x) for x in samples]
    return out


def load_measurements() -> pd.DataFrame:
    """All ok pp512/tg128 records of every tag, with sample drift.

    Returns:
        DataFrame with one row per tag x model x back end x test.
    """
    frames = []
    for path in sorted(RESULTS.glob("b*/records.csv")):
        df = pd.read_csv(path)
        if df.empty:
            continue
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df = df[(df.status == "ok") & (df.param_set == "main") & (df.test.isin(TESTS))].copy()
    for c in ("avg_ts", "stddev_ts", "n_samples", "load1_before", "idle_pct_before", "waited_s", "build_number"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["cv"] = df.stddev_ts / df.avg_ts
    df["series"] = [series_name(m, b, t) for m, b, t in zip(df.model, df.backend, df.test)]
    df["date"] = pd.to_datetime(df.commit_date_utc, utc=True).dt.tz_convert(None)
    drift, sd_log = [], []
    cache: dict[Path, dict[str, list[float]]] = {}
    for r in df.itertuples():
        p = RESULTS / r.tag / f"{r.model}_{r.backend}.json"
        if p not in cache:
            cache[p] = load_json_samples(p)
        s = [x for x in cache[p].get(r.test, []) if x > 0]
        drift.append(float(np.mean(s[-2:]) / np.mean(s[:2]) - 1.0) if len(s) >= 4 else float("nan"))
        sd_log.append(float(np.std(np.log(s), ddof=1)) if len(s) >= 2 else float(r.cv))
    df["drift"] = drift
    df["sd_log"] = sd_log
    return df.sort_values(["series", "build_number"]).reset_index(drop=True)


def load_fences(df: pd.DataFrame, k: float) -> dict[tuple[str, str], float]:
    """Tukey upper fence of load1_before per model x back end (one value per run).

    Args:
        df: Measurements.
        k: IQR multiplier.

    Returns:
        (model, backend) -> fence.
    """
    runs = df.drop_duplicates(["tag", "model", "backend"])
    out = {}
    for (m, b), g in runs.groupby(["model", "backend"]):
        q1, q3 = np.nanpercentile(g.load1_before, [25, 75])
        out[(m, b)] = float(q3 + k * (q3 - q1))
    return out


def pair_events(df: pd.DataFrame, prm: Params) -> pd.DataFrame:
    """All adjacent-tag pairs of every series with delta, tau and flags.

    Args:
        df: Measurements.
        prm: Thresholds.

    Returns:
        One row per adjacent pair; ``is_event`` marks the candidates.
    """
    fences = load_fences(df, prm.load_k)
    rows: list[dict[str, Any]] = []
    for series, g in df.groupby("series", sort=False):
        g = g.sort_values("build_number").reset_index(drop=True)
        for i in range(1, len(g)):
            a, b = g.iloc[i - 1], g.iloc[i]
            n0, n1 = max(int(a.n_samples), 2), max(int(b.n_samples), 2)
            pooled = math.sqrt(((n0 - 1) * a.sd_log ** 2 + (n1 - 1) * b.sd_log ** 2) / (n0 + n1 - 2))
            tau = max(math.log1p(prm.min_rel), prm.k_sd * pooled)
            lr = math.log(b.avg_ts / a.avg_ts)
            nxt = g.iloc[i + 1] if i + 1 < len(g) else None
            prv = g.iloc[i - 2] if i >= 2 else None
            fence = fences[(a.model, a.backend)]
            rows.append({
                "series": series, "model": a.model, "backend": a.backend, "test": a.test,
                "tag_old": a.tag, "tag_new": b.tag, "b_old": int(a.build_number), "b_new": int(b.build_number),
                "date_old": a.date, "date_new": b.date,
                "mean_old": a.avg_ts, "mean_new": b.avg_ts, "cv_old": a.cv, "cv_new": b.cv,
                "sd_log_old": a.sd_log, "sd_log_new": b.sd_log,
                "pooled_sd_log": pooled, "tau": tau, "tau_pct": math.expm1(tau),
                "delta": math.expm1(lr), "log_ratio": lr,
                "is_event": abs(lr) >= tau,
                "near": abs(lr) < prm.near * tau,
                "load_old": a.load1_before, "load_new": b.load1_before, "load_fence": fence,
                "high_load": bool(a.load1_before > fence or b.load1_before > fence),
                "drift_old": a.drift, "drift_new": b.drift,
                "drift_flag": bool(abs(a.drift) > prm.drift or abs(b.drift) > prm.drift)
                if not (math.isnan(a.drift) or math.isnan(b.drift)) else False,
                "next_tag": nxt.tag if nxt is not None else "",
                "lr_next_vs_old": math.log(nxt.avg_ts / a.avg_ts) if nxt is not None else float("nan"),
                "lr_new_vs_prev": math.log(b.avg_ts / prv.avg_ts) if prv is not None else float("nan"),
            })
    return pd.DataFrame(rows)


def mark_spikes(pairs: pd.DataFrame, changes: pd.DataFrame) -> pd.DataFrame:
    """Flag one-tag spikes and decide which of them are isolated (noise-like).

    A spike at tag X of a series: the pair (prev -> X) and (X -> next) are both events of
    opposite sign and next returns to prev within tau.  It is *isolated* (noise-like)
    when every series that spikes at X in the same direction belongs to the same model
    (one model's measurement session at X looks disturbed while the other models do not
    move) and no A/B configuration column changes into and out of X.  Spikes shared by
    several models stay non-noise: they may be a regression fixed before the next sample.

    The load flag counts as noise only when the change does not persist to the next
    sampled tag (a persistent level shift is corroborated by a later, separate run).

    Args:
        pairs: Output of pair_events().
        changes: config_changes.csv (step 0).

    Returns:
        ``pairs`` with columns spike_at, spike_dir, spike_models, spike_isolated,
        persistent, load_noise, noise.
    """
    pairs = pairs.copy()
    pairs["spike_at"] = ""
    pairs["spike_dir"] = 0
    spikes: list[tuple[str, str, int]] = []
    for series, g in pairs.groupby("series", sort=False):
        idx = list(g.index)
        for k in range(len(idx) - 1):
            p, q = pairs.loc[idx[k]], pairs.loc[idx[k + 1]]
            if not (p.is_event and q.is_event) or np.sign(p.log_ratio) == np.sign(q.log_ratio):
                continue
            back = math.log(q.mean_new / p.mean_old)
            if abs(back) < p.tau:  # same criterion as "not persistent" below
                d = int(np.sign(p.delta))
                pairs.loc[[idx[k], idx[k + 1]], "spike_at"] = p.tag_new
                pairs.loc[[idx[k], idx[k + 1]], "spike_dir"] = d
                spikes.append((series, p.tag_new, d))
    models_at: dict[tuple[str, int], set[str]] = {}
    for series, tag, d in spikes:
        models_at.setdefault((tag, d), set()).add(series.split("/")[0])
    reverted = set()
    if not changes.empty:
        for _, g in changes[changes.kind.isin(["A", "B"])].groupby("column"):
            reverted |= set(g.tag) & set(g.prev_tag)  # the column changes into and out of this tag
    iso, spike_models = [], []
    for r in pairs.itertuples():
        if not r.spike_at:
            iso.append(False)
            spike_models.append("")
            continue
        models = models_at[(r.spike_at, r.spike_dir)]
        spike_models.append(",".join(SHORT.get(m, m) for m in sorted(models)))
        iso.append(len(models) == 1 and r.spike_at not in reverted)
    pairs["spike_isolated"] = iso
    pairs["spike_models"] = spike_models
    persistent = []
    for r in pairs.itertuples():
        if not r.is_event or math.isnan(r.lr_next_vs_old):
            persistent.append("")
            continue
        persistent.append("yes" if abs(r.lr_next_vs_old) >= r.tau and np.sign(r.lr_next_vs_old) == np.sign(r.log_ratio)
                          else "no")
    pairs["persistent"] = persistent
    pairs["load_noise"] = pairs.high_load & (pairs.persistent != "yes")
    pairs["noise"] = pairs.near | pairs.load_noise | pairs.spike_isolated
    return pairs


def merge_intervals(ev: pd.DataFrame) -> list[list[int]]:
    """Group series events whose (b_old, b_new] intervals overlap.

    Args:
        ev: Series-level events.

    Returns:
        Lists of row indices of ``ev``, one list per event interval.
    """
    order = ev.sort_values(["b_old", "b_new"]).index.tolist()
    groups: list[list[int]] = []
    cur: list[int] = []
    cur_end = -1
    for i in order:
        r = ev.loc[i]
        if cur and r.b_old < cur_end:
            cur.append(i)
            cur_end = max(cur_end, int(r.b_new))
        else:
            if cur:
                groups.append(cur)
            cur, cur_end = [i], int(r.b_new)
    if cur:
        groups.append(cur)
    return groups


def scope_match(change: pd.Series, backends: set[str], tests: set[str]) -> bool:
    """Whether a configuration change can affect any of the given back ends/tests."""
    b_ok = change.backends == "both" or change.backends in backends
    t_ok = change.tests == "both" or change.tests in {t[:2] for t in tests}
    return bool(b_ok and t_ok)


def releases_between(rel: pd.DataFrame, b_old: int, b_new: int) -> tuple[int, int]:
    """Number of release tags and commits in (b_old, b_new]."""
    sub = rel[(rel.build_number > b_old) & (rel.build_number <= b_new)]
    return len(sub), int(sub.commits_since_prev.fillna(0).sum())


def classify(groups: list[list[int]], ev: pd.DataFrame, changes: pd.DataFrame,
             rel: pd.DataFrame) -> pd.DataFrame:
    """Build the event-interval table with classes and reasons.

    Each non-noise series of an interval is "explained" by the A/B changes (expected
    likely/possible) inside the interval whose back end/test scope covers it.  The
    interval is A or B only if every non-noise series is explained (A if any A change
    explains one); otherwise C, with ``class_candidates`` naming partial explanations.
    An interval whose series all carry noise flags is D.

    Args:
        groups: Output of merge_intervals().
        ev: Series-level events.
        changes: config_changes.csv.
        rel: releases.csv.

    Returns:
        One row per event interval (chronological ids E01, E02, ...).
    """
    rows = []
    for k, idx in enumerate(groups, 1):
        g = ev.loc[idx].sort_values("log_ratio", key=np.abs, ascending=False)
        b_old, b_new = int(g.b_old.min()), int(g.b_new.max())
        non_noise = g[~g.noise]
        inside = changes[(changes.prev_build < b_new) & (changes.build > b_old)] if not changes.empty else changes
        usable = inside[inside.kind.isin(["A", "B"]) & inside.expected.isin(["likely", "possible"])] \
            if not inside.empty else inside
        expl: dict[int, list[str]] = {}
        for i, r in g.iterrows():
            expl[i] = [c.change_id for _, c in usable.iterrows() if scope_match(c, {r.backend}, {r.test})]
        used_ids = sorted({cid for i in non_noise.index for cid in expl[i]}) if not non_noise.empty else \
            sorted({cid for i in g.index for cid in expl[i]})
        relevant = usable[usable.change_id.isin(used_ids)] if not usable.empty else usable
        others = inside[~inside.change_id.isin(used_ids)] if not inside.empty else inside
        kinds_by_series = {i: {usable.set_index("change_id").at[c, "kind"] for c in expl[i]} for i in g.index}
        if non_noise.empty:
            cls = "D"
        elif all(kinds_by_series[i] for i in non_noise.index):
            cls = "A" if any("A" in kinds_by_series[i] for i in non_noise.index) else "B"
        else:
            cls = "C"
        cands = "".join(sorted({kd for i in non_noise.index for kd in kinds_by_series[i]}))
        n_rel, n_commits = releases_between(rel, b_old, b_new)
        details = []
        for i, r in g.iterrows():
            flags = [f for f, on in (("near", r.near), ("load", r.load_noise),
                                     (f"spike@{r.spike_at}", r.spike_isolated),
                                     (f"shared-spike@{r.spike_at}[{r.spike_models}]",
                                      bool(r.spike_at) and not r.spike_isolated),
                                     ("drift", r.drift_flag)) if on]
            if r.high_load and not r.load_noise:
                flags.append("load-but-persistent")
            ex = "expl=" + "+".join(expl[i]) if expl[i] else "expl=-"
            details.append(f"{short_name(r.series)}:{r.delta:+.1%}(tau={r.tau_pct:.1%},cv={r.cv_old:.1%}/{r.cv_new:.1%},"
                           f"load={r.load_old:.1f}/{r.load_new:.1f}"
                           f"{',' + '+'.join(flags) if flags else ''}"
                           f"{',persist=' + r.persistent if r.persistent else ''},{ex})")
        unexplained = [short_name(r.series) for i, r in non_noise.iterrows() if not expl[i]]
        series_json = json.dumps([{
            "series": r.series, "model": r.model, "backend": r.backend, "test": r.test,
            "tag_old": r.tag_old, "tag_new": r.tag_new, "mean_old": round(float(r.mean_old), 4),
            "mean_new": round(float(r.mean_new), 4), "log_ratio": round(float(r.log_ratio), 5),
            "delta": round(float(r.delta), 5), "tau": round(float(r.tau), 5), "noise": bool(r.noise),
            "explained_by": expl[i]} for i, r in g.iterrows()], ensure_ascii=False)
        rows.append({
            "event_id": f"E{k:02d}", "tag_old": f"b{b_old}", "tag_new": f"b{b_new}", "b_old": b_old, "b_new": b_new,
            "date_old": g.date_old.min().strftime("%Y-%m-%d"), "date_new": g.date_new.max().strftime("%Y-%m-%d"),
            "releases_between": n_rel, "commits_between": n_commits,
            "n_series": len(g), "series": ";".join(g.series),
            "n_noise_series": int(g.noise.sum()),
            "directions": ";".join("+" if d > 0 else "-" for d in g.delta),
            "max_delta_signed": float(g.delta.iloc[0]),
            "max_abs_log_ratio": float(g.log_ratio.abs().max()),
            "min_tau_pct": float(g.tau_pct.min()),
            "class": cls, "class_candidates": cands,
            "unexplained_series": ";".join(unexplained),
            "config_changes": ";".join(f"{c.change_id}:{c.kind}:{c.label}" for c in relevant.itertuples()),
            "other_changes_in_interval": ";".join(f"{c.change_id}:{c.kind}:{c.label}({c.expected})"
                                                  for c in others.itertuples()) if not others.empty else "",
            "series_detail": " ; ".join(details),
            "series_json": series_json,
            "reason": reason_text(cls, g, non_noise, relevant, others, unexplained),
        })
    return pd.DataFrame(rows)


def reason_text(cls: str, g: pd.DataFrame, non_noise: pd.DataFrame, relevant: pd.DataFrame,
                others: pd.DataFrame, unexplained: list[str]) -> str:
    """One-sentence reason for the class.

    Args:
        cls: Class letter.
        g: Series events of the interval.
        non_noise: The non-noise subset.
        relevant: Changes that explain at least one series.
        others: Other changes inside the interval.
        unexplained: Short names of non-noise series without an explanation.

    Returns:
        Reason text.
    """
    def items(df: pd.DataFrame) -> str:
        return ", ".join(f"{c.change_id} {c.label} ({c.old} → {c.new})" for c in df.itertuples())

    shared = sorted({f"{r.spike_at}[{r.spike_models}]" for r in non_noise.itertuples()
                     if r.spike_at and not r.spike_isolated})
    tail = (f"; {', '.join(shared)}: one-tag spike shared by several models (recovered at the next sample: a regression "
            "that was then fixed, or an abnormal measurement period at that tag)") if shared else ""
    if cls == "D":
        why = []
        if g.near.any():
            why.append("change close to the threshold")
        if g.load_noise.any():
            why.append("high load1_before at an end and the change did not persist")
        if g.spike_isolated.any():
            why.append("one-tag spike of a single model that recovered at the next sample")
        return "Noise suspected: " + ", ".join(why)
    if cls in ("A", "B"):
        return (f"All non-noise series lie within the scope of {'runtime configuration' if cls == 'A' else 'build option'} "
                f"changes: {items(relevant)}") + tail
    part = f"; some series may be explained by {items(relevant)}" if not relevant.empty else ""
    extra = f"; other changes in the interval are expected to have no effect: {', '.join(others.change_id)}" \
        if not others.empty else ""
    return f"No configuration or build change explains {', '.join(unexplained)}" + part + extra + tail


def write_markdown(events: pd.DataFrame, pairs: pd.DataFrame, prm: Params, path: Path,
                   load_fail: pd.DataFrame) -> None:
    """Write candidate_events.md.

    Args:
        events: Event-interval table.
        pairs: All adjacent pairs (for statistics).
        prm: Thresholds.
        path: Output path.
        load_fail: Model-support changes (load_failed tags) to mention.
    """
    ev_rows = pairs[pairs.is_event]
    counts = events["class"].value_counts().to_dict()
    lines = [
        "# Step 1: candidate events",
        "",
        ("Generated by `scripts/analysis/step1_candidate_events.py`. Rule (protocol step 1): 12 series (3 models × "
        "2 back ends × pp512/tg128) are ordered by build number, and the change between adjacent measured tags is "
        f"compared on the log scale (Δ = ln(new/old), so rises and falls are symmetric): a pair with |ln(new/old)| ≥ τ = "
        f"max(ln(1+{prm.min_rel:.0%}), {prm.k_sd:g} × pooled SD) is a candidate, where the pooled SD pools the SDs of "
        "ln(throughput) over the 5 repetitions at each end. In the tables Δ is shown as the percentage exp(ln ratio)−1 "
        f"and τ as exp(τ)−1 ({prm.min_rel:.0%} means a rise of +{prm.min_rel:.0%} or a fall of "
        f"−{1 - 1 / (1 + prm.min_rel):.1%}). Candidates with overlapping intervals are merged into event intervals."),
        "",
        f"- Adjacent tag pairs: {len(pairs)} (12 series); candidates (series level): {len(ev_rows)}; event intervals: {len(events)}.",
        "- Class counts: " + ", ".join(f"{CLASS_NAME[c]} {counts.get(c, 0)}" for c in "ABCD") + ".",
        (f"- Noise flags: near = |ln ratio| < {prm.near:g}τ; load = load1_before at either end exceeds the Tukey upper "
        f"fence Q3 + {prm.load_k:g}·IQR of the same model × back end and the change does not persist to the next sample "
        "(a persistent change is marked load-but-persistent and is not noise); spike = one-tag spike of a single model "
        "(the next sample returns to within ±τ of the old level, all series with a spike in the same direction at that "
        "tag belong to one model, and no A/B configuration item changes at that tag and back). A one-tag spike shared "
        "by several models is marked shared-spike and is not noise."),
        ("- Classes: all series of the interval carry noise flags → D. Otherwise each non-noise series is checked against "
        "the likely/possible step-0 changes in the interval whose back end and test scope cover it: all explained → A "
        "(an A change is involved) or B; any series unexplained → C, and `class_candidates` lists the classes that "
        "explain some of the series. drift (the mean of the last 2 repetitions of a run differs from that of the first "
        f"2 by > {prm.drift:.0%}) and persist (the next sample still deviates from the old level by ≥ τ) are notes only."),
        "- Figure: `timeline.pdf` / `timeline.svg` (logarithmic y axis, error bars ±1 SD, bands are candidate intervals colored by class).",
        "",
        "## Event intervals (sorted by largest |Δ|)",
        "",
        "| Event | Interval | Dates | Releases/commits | Series | Series involved (Δ) | Largest Δ | Class | Reason |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    order = events.sort_values("max_abs_log_ratio", ascending=False)
    for _, e in order.iterrows():
        ser = ", ".join(f"{short_name(s)} {d}" for s, d in zip(e["series"].split(";"), _deltas(e["series_detail"])))
        lines.append(f"| {e['event_id']} | {e['tag_old']} → {e['tag_new']} | {e['date_old']} → {e['date_new']} | "
                     f"{e['releases_between']}/{e['commits_between']} | {e['n_series']} | {ser} | "
                     f"{e['max_delta_signed']:+.1%} | {e['class']} | {e['reason']} |")
    lines += ["", "## Interval details (same order)", ""]
    for _, e in order.iterrows():
        lines.append(paragraph(e.to_dict()))
        lines.append("")
    if not load_fail.empty:
        lines += ["## Non-performance events: model load failures", ""]
        for r in load_fail.itertuples():
            lines.append(f"- {r.tag}: {r.models} (load_failed, recorded as not supported by this release, not a candidate event).")
        lines.append("")
    stats = pairs.groupby("series").agg(pairs=("delta", "size"), events=("is_event", "sum"),
                                        noise=("noise", lambda x: int((x & pairs.loc[x.index, "is_event"]).sum())),
                                        median_cv=("cv_new", "median"), median_tau=("tau_pct", "median"))
    lines += ["## Noise level and candidates per series", "",
              "| Series | Adjacent pairs | Candidates | With noise flags | Median CV | Median τ |", "|---|---|---|---|---|---|"]
    for s, r in stats.iterrows():
        lines.append(f"| {short_name(s)} | {int(r.pairs)} | {int(r.events)} | {int(r.noise)} | {r.median_cv:.1%} | "
                     f"{r.median_tau:.1%} |")
    lines += [
        "",
        "## Limitations",
        "",
        ("- Sparse sampling: only changes visible between sampled releases can be seen. A regression fixed inside an "
        "interval, or several changes that cancel out, are not seen, and the duration of an event is known only as an "
        "interval (from the previous sampled tag to the next one)."),
        ("- Each point is one llama-bench call (5 repetitions), so the pooled variation reflects within-run noise only, "
        "not noise across measurement periods. Within-run variation of tinyllama/metal and qwen/metal/pp512 often exceeds "
        "10% (the GPU frequency drops during a run), so candidates in these series depend on the re-measurement of step 2."),
        ("- Classes A and B only say that a possible configuration or build explanation exists in the interval, not that "
        "it is proven. A class B change still looks like an implementation change under the fixed configuration of "
        "step 2; separating B from C would need rebuilds with uniform compile options."),
        ("- The measurement order is fixed (tinyllama/metal first at every tag) and the first measurement follows the "
        "build directly, so load1_before is generally high. The load flag catches only outliers at the same position."),
        "",
    ]
    path.write_text("\n".join(lines))


def _deltas(detail: str) -> list[str]:
    """Pull the signed percentages out of a series_detail string."""
    out = []
    for part in detail.split(" ; "):
        _, _, rest = part.partition(":")
        out.append(rest.split("(")[0])
    return out


def paragraph(e: dict[str, Any]) -> str:
    """One paragraph describing an event interval."""
    parts = e["series_detail"].split(" ; ")
    ser_txt = "; ".join(parts)
    txt = (f"**{e['event_id']}** ({e['tag_old']} → {e['tag_new']}, {e['date_old']} → {e['date_new']}, "
           f"{e['releases_between']} releases and {e['commits_between']} commits in the interval): {e['n_series']} series "
           f"above the threshold ({e['n_noise_series']} with noise flags): {ser_txt}.")
    if e["config_changes"]:
        txt += f" Related changes in the interval: {e['config_changes'].replace(';', '; ')}."
    if e["other_changes_in_interval"]:
        txt += f" Other changes (not used for the class): {e['other_changes_in_interval'].replace(';', '; ')}."
    txt += f" First class **{e['class']}**: {e['reason']}."
    return txt


def plot_timeline(df: pd.DataFrame, events: pd.DataFrame, pairs: pd.DataFrame, out_base: Path) -> None:
    """Draw the 12 series (3 x 4 panels) with candidate intervals shaded by class.

    Args:
        df: Measurements.
        events: Event-interval table.
        pairs: Pair table (to know which series each event touches).
        out_base: Output path without suffix.
    """
    plt.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 8,
                         "axes.prop_cycle": matplotlib.cycler(color=list(PALETTE))})
    cols = [(b, t) for b in BACKENDS for t in TESTS]
    fig, axes = plt.subplots(len(MODELS), len(cols), figsize=(15, 9), sharex=True)
    tag_date = df.drop_duplicates("tag").set_index("tag").date
    for i, model in enumerate(MODELS):
        for j, (backend, test) in enumerate(cols):
            ax = axes[i][j]
            s = series_name(model, backend, test)
            g = df[df.series == s].sort_values("build_number")
            n_lab = 0
            for _, e in events.sort_values("b_old").iterrows():
                if s not in e["series"].split(";"):
                    continue
                x0, x1 = tag_date.get(e["tag_old"]), tag_date.get(e["tag_new"])
                cls = e["class"]
                ax.axvspan(x0, x1, color=CLASS_COLOR[cls], alpha=CLASS_ALPHA[cls], lw=0)
                if cls != "D":
                    ax.text(x0 + (x1 - x0) / 2, 1.01 + 0.055 * (n_lab % 3), e["event_id"],
                            transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=5.5,
                            color="#333333")
                    n_lab += 1
            ax.errorbar(g.date, g.avg_ts, yerr=g.stddev_ts, color=MODEL_COLOR[model], marker=MODEL_MARKER[model],
                        ms=2.6, lw=0.9, elinewidth=0.6, capsize=0)
            ax.set_yscale("log")
            plain = mticker.FuncFormatter(lambda v, _: f"{v:g}")
            ax.yaxis.set_major_formatter(plain)
            lo, hi = g.avg_ts.min(), g.avg_ts.max()
            if hi / lo < 8:
                ax.yaxis.set_minor_locator(mticker.LogLocator(subs=(2.0, 3.0, 5.0)))
                ax.yaxis.set_minor_formatter(plain)
            else:
                ax.yaxis.set_minor_formatter(mticker.NullFormatter())
            ax.grid(True, which="both", lw=0.3, alpha=0.4)
            if i == 0:
                ax.set_title(f"{backend} / {test}", fontsize=9, pad=30)
            if j == 0:
                ax.set_ylabel(f"{SHORT[model]}  tokens/s")
            ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            ax.tick_params(axis="x", labelsize=7, rotation=30)
    handles = [Patch(facecolor=CLASS_COLOR[c], alpha=max(CLASS_ALPHA[c], 0.3), label=CLASS_NAME_EN[c]) for c in "ABCD"]
    for m in MODELS:
        handles.append(plt.Line2D([], [], color=MODEL_COLOR[m], marker=MODEL_MARKER[m], lw=0.9, ms=3, label=m))
    fig.legend(handles=handles, loc="lower center", ncol=7, frameon=False, fontsize=8)
    fig.suptitle("llama-bench throughput over 81 llama.cpp tags (Apple M5; candidate intervals shaded by first class)",
                 fontsize=10)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    for suffix in (".pdf", ".svg"):
        fig.savefig(out_base.with_suffix(suffix))
    plt.close(fig)


def main() -> None:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--min-rel", type=float, default=Params.min_rel)
    ap.add_argument("--k-sd", type=float, default=Params.k_sd)
    ap.add_argument("--near", type=float, default=Params.near)
    ap.add_argument("--load-k", type=float, default=Params.load_k)
    ap.add_argument("--drift", type=float, default=Params.drift)
    ap.add_argument("--no-plot", action="store_true")
    ns = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    prm = Params(ns.min_rel, ns.k_sd, ns.near, ns.load_k, ns.drift)
    changes_path = ns.out_dir / "config_changes.csv"
    if not changes_path.is_file():
        raise SystemExit(f"{changes_path} missing: run step0_effective_config.py first")
    changes = pd.read_csv(changes_path, dtype=str).fillna("")
    for c in ("prev_build", "build"):
        changes[c] = changes[c].astype(int)
    rel = pd.read_csv(RELEASES)
    rel["commits_since_prev"] = pd.to_numeric(rel.commits_since_prev, errors="coerce")
    df = load_measurements()
    logger.info("loaded %d measurements, %d series", len(df), df.series.nunique())
    pairs = mark_spikes(pair_events(df, prm), changes)
    ev = pairs[pairs.is_event].copy()
    groups = merge_intervals(ev)
    events = classify(groups, ev, changes, rel)
    ns.out_dir.mkdir(parents=True, exist_ok=True)
    events.to_csv(ns.out_dir / "candidate_events.csv", index=False)
    lf_rows = []
    for path in sorted(RESULTS.glob("b*/records.csv"), key=lambda p: int(p.parent.name[1:])):
        r = pd.read_csv(path)
        if r.empty:
            continue
        bad = sorted(set(r[r.status == "load_failed"].model))
        if bad:
            lf_rows.append({"tag": path.parent.name, "models": ",".join(bad)})
    write_markdown(events, pairs, prm, ns.out_dir / "candidate_events.md", pd.DataFrame(lf_rows))
    if not ns.no_plot:
        plot_timeline(df, events, pairs, ns.out_dir / "timeline")
    logger.info("%d series events -> %d intervals %s", len(ev), len(events), events["class"].value_counts().to_dict())


if __name__ == "__main__":
    main()
