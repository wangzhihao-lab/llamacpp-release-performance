#!/usr/bin/env python3
"""Root-cause protocol, step 1b: change points of the 12 series (E-Divisive means).

Step 1 compares adjacent sampled tags only: a one-tag spike yields two adjacent
candidates, and a sustained change spread over two or three intervals of less than
10 % each is missed.  This step looks at every series as a whole.

1. Statistic per (tag, series): median of the run's ``samples_ts`` (``avg_ts`` when the
   samples are missing), log scale, ordered by build number.  Rows with
   ``param_set == main`` and ``status == ok`` only (qwen2.5-1.5b cannot be loaded by the
   oldest builds and by b2761; those points are absent).
2. Robust noise of a series: sigma = 1.4826 * MAD(first differences) / sqrt(2).
   Isolated spike: a point farther than 4 sigma from the median of its two left and two
   right neighbours (one neighbour on the short side next to an end; the two end points
   are never flagged) while the two sides agree, |median(left) - median(right)| < 2 sigma.
   Spikes are listed and left out of the change-point search.
3. E-Divisive (Matteson & James 2014, JASA 109:334-345) with alpha = 1 on the spike-free
   series.  For a cluster Z_1..Z_T and X_tau = {Z_1..Z_tau} (n = tau),
   Y_tau(kappa) = {Z_tau+1..Z_kappa} (m = kappa - tau):

     E^(X, Y; a) = 2/(mn) sum_i sum_j |X_i - Y_j|^a
                   - C(n,2)^-1 sum_{i<k} |X_i - X_k|^a - C(m,2)^-1 sum_{j<k} |Y_j - Y_k|^a
     Q^(X, Y; a) = mn/(m+n) E^(X, Y; a)
     (tau^, kappa^) = argmax over 3 <= n, 3 <= m of Q^(X_tau, Y_tau(kappa); a)

   (``scan_splits``: block sums of the distance matrix from a 2-D prefix sum; ``cross``,
   ``within_x``, ``within_y`` are the three double sums.)  Hierarchical bisection: with
   k-1 accepted change points the best split of every cluster is computed and the cluster
   with the largest Q^ proposes the k-th change point tau^ (kappa^ only bounds the right
   sample; ``e_divisive``).  Significance: the observations are permuted within every
   cluster, the maximal Q^ over all clusters is recomputed for R = 999 permutations and
   p = (1 + #{Q^(r) >= Q^}) / (R + 1); the point is accepted when p < 0.01, otherwise the
   procedure stops (``permutation_test``).  Generator: numpy default_rng seeded with
   zlib.crc32(series name).  ``--kappa end`` fixes kappa at the end of the cluster, as
   MongoDB's signal_processing_algorithms does; it is run as a robustness comparison
   (with early-stopped rejections, see Params.exact_p, which leaves the change points
   unchanged).
4. Per change point: levels (medians) of the two adjacent segments, delta = exp(right -
   left) - 1, p, sigma, |ln ratio| / sigma; |delta| < 5 % is flagged small (kept, not
   re-measured).  Gradual change: the point next to the boundary on each side is a
   transition point when it lies strictly between the two levels and farther than
   2 sigma from the level of its own segment; the transition interval (span_old,
   span_new) is then widened past it by one point on that side.  transition_may_extend
   flags a widened end that would itself qualify (the transition may be longer).
5. Change points of different series whose transition intervals (b_span_old, b_span_new]
   overlap are merged into change intervals R01, R02, ...
6. Comparison with step 1 (candidate_events.csv): (i) the change interval overlaps a
   step-1 event and the same (model, back end) is listed there with a tag pair that
   overlaps the transition (step 2 re-measures it); (ii) it overlaps a step-1 event but
   this (model, back end) is not listed with an overlapping pair; (iii) no step-1 event
   overlaps.  Conversely every step-1 series candidate is matched to change points (same
   series, overlapping pair) and to spikes (its pair touches a spike of the series).

Outputs (results/analysis/): changepoints.csv, spikes.csv, changepoint_events.csv (types
(ii)/(iii) with |delta| >= 5 %, columns of candidate_events.csv, class CP; step 2 selects
them only with ``--classes CP``), changepoints.md, changepoints.pdf, changepoints.svg.
Inputs are only read: results/<tag>/records.csv and JSON, data/releases.csv,
results/analysis/candidate_events.csv and config_changes.csv.  ``--self-test-only`` runs
the synthetic checks without writing anything.

Run it as one single-threaded process at background priority (the four *_NUM_THREADS
variables and ``taskpolicy -b nice -n 19``) so that it does not disturb timing
measurements on the same machine.

Run from the repository root: OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1 taskpolicy -b nice -n 19 uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step1b_changepoints.py
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import math
import zlib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT_DIR = RESULTS / "analysis"
EVENTS_CSV = OUT_DIR / "candidate_events.csv"
CHANGES_CSV = OUT_DIR / "config_changes.csv"
RELEASES = ROOT / "data" / "releases.csv"

MODELS = ("tinyllama-1.1b", "mistral-7b", "qwen2.5-1.5b")
SHORT = {"tinyllama-1.1b": "tiny", "mistral-7b": "mistral", "qwen2.5-1.5b": "qwen"}
BACKENDS = ("metal", "cpu")
TESTS = ("pp512", "tg128")
TEST_SHAPE = {"pp512": (512, 0), "tg128": (0, 128)}
PALETTE = ("#332288", "#117733", "#44AA99", "#88CCEE", "#DDCC77", "#CC6677", "#AA4499", "#882255")
MODEL_COLOR = {m: PALETTE[i] for i, m in enumerate(MODELS)}
MODEL_MARKER = {"tinyllama-1.1b": "o", "mistral-7b": "s", "qwen2.5-1.5b": "^"}
SPAN_COLOR, SMALL_COLOR, CP_COLOR = PALETTE[3], PALETTE[4], PALETTE[5]
CAMPAIGN_REPS = 5  # llama-bench -r of every campaign run (all ok main rows have n_samples = 5)
COVERAGE_TEXT = {"i": "(i) covered by step 1 and group will be re-measured", "ii": "(ii) interval covered but group not listed",
                 "iii": "(iii) not covered by step 1 at all"}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Params:
    """Parameters of the change-point analysis.

    Attributes:
        alpha: Exponent of the energy distance (0 < alpha < 2).
        min_size: Minimum segment length on both sides of a split.
        n_perm: Number of permutations R of the significance test.
        p_max: A change point is accepted when p < p_max.
        kappa: 'full' searches (tau, kappa) as in Matteson & James (2014); 'end' fixes kappa at the
            end of the cluster.
        spike_k: Spike threshold in sigma (distance to the neighbours' median).
        spike_agree: Left and right neighbours must agree within this many sigma.
        spike_halfwin: Neighbours on each side used by the spike rule.
        small: |delta| below this (relative) marks a change point as small.
        gradual_k: A transition point lies farther than this many sigma from its level.
        recover_lo: A later rise recovers a fall when its |ln ratio| is at least
            recover_lo times the fall's ...
        recover_hi: ... and at most recover_hi times it.
        chunk: Permutations evaluated per vectorised batch.
        exact_p: Evaluate all permutations of a split that is rejected.  When False the
            test stops once acceptance is impossible, (1 + #exceedances) / (R + 1) >=
            p_max; accepted splits and therefore all change points are unchanged (an
            accepted split never reaches the stopping count, and a rejection ends the
            procedure), only the reported p of the final rejected split becomes a lower
            bound.  Used for the self-test and the kappa variant.
    """

    alpha: float = 1.0
    min_size: int = 3
    n_perm: int = 999
    p_max: float = 0.01
    kappa: str = "full"
    spike_k: float = 4.0
    spike_agree: float = 2.0
    spike_halfwin: int = 2
    small: float = 0.05
    gradual_k: float = 2.0
    recover_lo: float = 0.5
    recover_hi: float = 2.0
    chunk: int = 128
    exact_p: bool = True


@dataclass(frozen=True)
class ChangePoint:
    """One tested split of the hierarchical procedure.

    Attributes:
        index: First index of the right segment (in the analysed array).
        q: Q^ of the split.
        p: Permutation p-value.
        step: 1-based step of the hierarchical procedure.
        kappa_end: Exclusive end of the right sample Y_tau(kappa) at that step.
        n_perm_done: Permutations evaluated (fewer than R only for an early-stopped
            rejection, see Params.exact_p).
    """

    index: int
    q: float
    p: float
    step: int
    kappa_end: int
    n_perm_done: int


@dataclass
class SeriesResult:
    """Change-point analysis of one series.

    Attributes:
        series: Series id, e.g. ``mistral-7b/cpu/pp512``.
        tags: Tags of all measured points (build order).
        builds: Build numbers.
        dates: Commit dates (matplotlib date numbers).
        y: ln(statistic) of all points.
        avg_ts: Campaign avg_ts of all points.
        sd_log: SD of ln(samples) of every run.
        sigma: Robust noise of the series (log units).
        spikes: Spike records (dicts).
        spike_mask: True at spike points.
        keep: Indices of the non-spike points (into the full arrays).
        cps: Accepted change points (indices into the spike-free array), sorted.
        stop_test: The first rejected split (None if no cluster could be split).
    """

    series: str
    tags: list[str]
    builds: np.ndarray
    dates: np.ndarray
    y: np.ndarray
    avg_ts: np.ndarray
    sd_log: np.ndarray
    sigma: float
    spikes: list[dict[str, Any]] = field(default_factory=list)
    spike_mask: np.ndarray = field(default_factory=lambda: np.zeros(0, bool))
    keep: np.ndarray = field(default_factory=lambda: np.zeros(0, int))
    cps: list[ChangePoint] = field(default_factory=list)
    stop_test: ChangePoint | None = None

    def segments(self) -> list[tuple[int, int]]:
        """Segments [start, end) of the spike-free array."""
        bounds = [0] + [c.index for c in self.cps] + [len(self.keep)]
        return list(itertools.pairwise(bounds))

    def levels(self) -> list[float]:
        """Median ln(statistic) of every segment."""
        yk = self.y[self.keep]
        return [float(np.median(yk[a:b])) for a, b in self.segments()]


# --------------------------------------------------------------------------- data


def series_name(model: str, backend: str, test: str) -> str:
    """Canonical series id, e.g. ``mistral-7b/metal/pp512``."""
    return f"{model}/{backend}/{test}"


def short_name(series: str) -> str:
    """Short label, e.g. ``mistral/metal/pp512``."""
    model, rest = series.split("/", 1)
    return f"{SHORT.get(model, model)}/{rest}"


def load_json_samples(path: Path) -> dict[str, list[float]]:
    """Read samples_ts of pp512/tg128 from a llama-bench JSON file.

    Args:
        path: ``results/<tag>/<model>_<backend>.json``.

    Returns:
        Test name -> positive samples (missing tests are absent).
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
        key = next((t for t, (n_p, n_g) in TEST_SHAPE.items()
                    if r.get("n_prompt") == n_p and r.get("n_gen") == n_g), None)
        if key is None:
            continue
        samples = r.get("samples_ts")
        if not samples and r.get("samples_ns"):
            tokens = r.get("n_prompt") or r.get("n_gen")
            samples = [tokens * 1e9 / ns for ns in r["samples_ns"] if ns]
        vals = [float(x) for x in samples or [] if x and float(x) > 0]
        if vals:
            out[key] = vals
    return out


def load_measurements() -> pd.DataFrame:
    """All ok main-set pp512/tg128 records with the per-run statistic.

    Returns:
        One row per tag x model x back end x test with columns tag, build_number, date,
        model, backend, test, series, avg_ts, stat (median of samples_ts or avg_ts),
        stat_source, y = ln(stat), sd_log (SD of ln samples; cv when samples are absent).
    """
    frames = [pd.read_csv(p) for p in sorted(RESULTS.glob("b*/records.csv"))]
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    df = df[(df.status == "ok") & (df.param_set == "main") & (df.test.isin(TESTS))].copy()
    for c in ("avg_ts", "stddev_ts", "build_number"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["build_number"] = df.build_number.astype(int)
    df["series"] = [series_name(m, b, t) for m, b, t in zip(df.model, df.backend, df.test)]
    df["date"] = pd.to_datetime(df.commit_date_utc, utc=True).dt.tz_convert(None)
    cache: dict[Path, dict[str, list[float]]] = {}
    stat, source, sd_log = [], [], []
    for r in df.itertuples():
        path = RESULTS / r.tag / f"{r.model}_{r.backend}.json"
        if path not in cache:
            cache[path] = load_json_samples(path)
        s = cache[path].get(r.test, [])
        if s:
            stat.append(float(np.median(s)))
            source.append("samples")
        else:
            stat.append(float(r.avg_ts))
            source.append("avg_ts")
        sd_log.append(float(np.std(np.log(s), ddof=1)) if len(s) >= 2 else float(r.stddev_ts / r.avg_ts))
    df["stat"], df["stat_source"], df["sd_log"] = stat, source, sd_log
    df["y"] = np.log(df.stat)
    return df.sort_values(["series", "build_number"]).reset_index(drop=True)


# --------------------------------------------------------------------------- noise and spikes


def robust_sigma(y: np.ndarray) -> float:
    """Robust noise SD of one point: 1.4826 * MAD(first differences) / sqrt(2).

    Args:
        y: Ordered values (log scale).

    Returns:
        Sigma (a tiny floor keeps later ratios finite).
    """
    d = np.diff(y)
    if d.size == 0:
        return 1e-9
    mad = float(np.median(np.abs(d - np.median(d))))
    return max(1.4826 * mad / math.sqrt(2.0), 1e-9)


def find_spikes(y: np.ndarray, sigma: float, prm: Params) -> list[dict[str, Any]]:
    """Isolated one-point spikes.

    Args:
        y: Ordered values (log scale).
        sigma: Robust noise of the series.
        prm: Parameters (spike_k, spike_agree, spike_halfwin).

    Returns:
        One dict per spike: pos, dev (log), left/right/neighbour medians (log).
    """
    out = []
    h = prm.spike_halfwin
    for i in range(len(y)):
        left, right = y[max(0, i - h):i], y[i + 1:i + 1 + h]
        if left.size == 0 or right.size == 0:
            continue
        nb = float(np.median(np.concatenate([left, right])))
        dev = float(y[i] - nb)
        gap = abs(float(np.median(left)) - float(np.median(right)))
        if abs(dev) > prm.spike_k * sigma and gap < prm.spike_agree * sigma:
            out.append({"pos": i, "dev": dev, "neighbour_median": nb, "left_median": float(np.median(left)),
                        "right_median": float(np.median(right)), "lr_gap": gap})
    return out


# --------------------------------------------------------------------------- E-Divisive


def scan_splits(z: np.ndarray, alpha: float, min_size: int, kappa: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Best split (tau, kappa) of every row of ``z`` by the E-Divisive statistic.

    Q^(X_tau, Y_tau(kappa); alpha) = n m / (n + m) * E^ with n = tau, m = kappa - tau and
    E^ = 2/(nm) cross - within_x / C(n,2) - within_y / C(m,2), where cross, within_x and
    within_y are the sums of |Z_i - Z_j|^alpha over i in X, j in Y; i < k in X; j < k in Y.

    Args:
        z: (B, L) array (or 1-D for a single path) of one cluster.
        alpha: Distance exponent.
        min_size: Minimum n and m.
        kappa: 'full' (kappa from tau + min_size to L) or 'end' (kappa = L).

    Returns:
        (q, tau, kappa) per row: the maximal Q^ (-inf when L < 2 min_size) and the left
        sample size tau (= index of the first point of Y) and kappa where it is attained;
        ties go to the smallest tau, then the smallest kappa.
    """
    z = np.asarray(z, dtype=float)
    if z.ndim == 1:
        z = z[None, :]
    b, n = z.shape
    if n < 2 * min_size:
        return np.full(b, -np.inf), np.full(b, -1), np.full(b, -1)
    dist = np.abs(z[:, :, None] - z[:, None, :]) ** alpha
    cum = np.zeros((b, n + 1, n + 1))
    cum[:, 1:, 1:] = dist.cumsum(axis=1).cumsum(axis=2)
    taus = np.arange(min_size, n - min_size + 1)
    kaps = np.array([n]) if kappa == "end" else np.arange(2 * min_size, n + 1)
    t, k = np.meshgrid(taus, kaps, indexing="ij")
    valid = (k - t) >= min_size
    t0 = np.zeros_like(t)

    def block(r0: np.ndarray, r1: np.ndarray, c0: np.ndarray, c1: np.ndarray) -> np.ndarray:
        """Sum of dist[r0:r1, c0:c1] for every grid cell."""
        return cum[:, r1, c1] - cum[:, r0, c1] - cum[:, r1, c0] + cum[:, r0, c0]

    within_x = block(t0, t, t0, t) / 2.0
    within_y = block(t, k, t, k) / 2.0
    cross = block(t0, t, t, k)
    nx = t.astype(float)
    ny = np.where(valid, k - t, min_size).astype(float)
    e_hat = 2.0 * cross / (nx * ny) - within_x / (nx * (nx - 1.0) / 2.0) - within_y / (ny * (ny - 1.0) / 2.0)
    q_hat = np.where(valid, nx * ny / (nx + ny) * e_hat, -np.inf)
    flat = q_hat.reshape(b, -1)
    idx = flat.argmax(axis=1)
    ti, ki = np.unravel_index(idx, t.shape)
    return flat[np.arange(b), idx], taus[ti], kaps[ki]


def permutation_test(z: np.ndarray, bounds: list[int], q0: float, prm: Params,
                     rng: np.random.Generator) -> tuple[float, int]:
    """Permutation p-value of the proposed split given the current clusters.

    For every permutation r the observations of each cluster are shuffled independently
    and Q^(r) = max over clusters of the best split; p = (1 + #{Q^(r) >= Q^}) / (R + 1).
    Permutations are drawn in chunks: for each chunk, cluster by cluster.

    Args:
        z: Analysed array.
        bounds: Cluster boundaries [0, c_1, ..., len(z)].
        q0: Q^ of the proposed split.
        prm: Parameters (n_perm, chunk, alpha, min_size, kappa, p_max, exact_p).
        rng: Generator.

    Returns:
        (p, permutations evaluated).  With exact_p False the loop stops once
        (1 + #exceedances) / (R + 1) >= p_max; p is then that lower bound.
    """
    stop_at = math.ceil(prm.p_max * (prm.n_perm + 1) - 1 - 1e-9)
    clusters = [(s, e) for s, e in itertools.pairwise(bounds) if e - s >= 2 * prm.min_size]
    over, done = 0, 0
    for start in range(0, prm.n_perm, prm.chunk):
        m = min(prm.chunk, prm.n_perm - start)
        best = np.full(m, -np.inf)
        for s, e in clusters:
            order = np.argsort(rng.random((m, e - s)), axis=1)
            q, _, _ = scan_splits(z[s:e][order], prm.alpha, prm.min_size, prm.kappa)
            best = np.maximum(best, q)
        over += int(np.count_nonzero(best >= q0))
        done += m
        if not prm.exact_p and over >= stop_at:
            break
    return (1 + over) / (prm.n_perm + 1), done


def e_divisive(z: np.ndarray, prm: Params, rng: np.random.Generator) -> tuple[list[ChangePoint], ChangePoint | None]:
    """Hierarchical E-Divisive with a permutation test at every step.

    Args:
        z: Analysed array (one series, spikes removed).
        prm: Parameters.
        rng: Generator for the permutations.

    Returns:
        (accepted change points sorted by index, the first rejected split or None when no
        cluster can be split any more).
    """
    bounds = [0, len(z)]
    accepted: list[ChangePoint] = []
    memo: dict[tuple[int, int], tuple[float, int, int]] = {}
    step = 0
    while True:
        best: tuple[float, int, int] | None = None
        for s, e in itertools.pairwise(bounds):
            if (s, e) not in memo:
                q, tau, kap = scan_splits(z[s:e], prm.alpha, prm.min_size, prm.kappa)
                memo[(s, e)] = (float(q[0]), s + int(tau[0]), s + int(kap[0]))
            cand = memo[(s, e)]
            if np.isfinite(cand[0]) and (best is None or cand[0] > best[0]):
                best = cand
        if best is None:
            return sorted(accepted, key=lambda c: c.index), None
        q0, cp, kap = best
        p, done = permutation_test(z, bounds, q0, prm, rng)
        step += 1
        rec = ChangePoint(cp, q0, p, step, kap, done)
        if p >= prm.p_max:
            return sorted(accepted, key=lambda c: c.index), rec
        accepted.append(rec)
        bounds = sorted(bounds + [cp])


def analyse_series(name: str, g: pd.DataFrame, prm: Params) -> SeriesResult:
    """Spikes and change points of one series.

    Args:
        name: Series id (also the seed source).
        g: Measurements of the series.
        prm: Parameters.

    Returns:
        SeriesResult.
    """
    g = g.sort_values("build_number")
    y = g.y.to_numpy(float)
    res = SeriesResult(series=name, tags=list(g.tag), builds=g.build_number.to_numpy(int),
                       dates=mdates.date2num(g.date.dt.to_pydatetime()), y=y, avg_ts=g.avg_ts.to_numpy(float),
                       sd_log=g.sd_log.to_numpy(float), sigma=robust_sigma(y))
    res.spikes = find_spikes(y, res.sigma, prm)
    res.spike_mask = np.zeros(len(y), bool)
    res.spike_mask[[s["pos"] for s in res.spikes]] = True
    res.keep = np.flatnonzero(~res.spike_mask)
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    res.cps, res.stop_test = e_divisive(y[res.keep], prm, rng)
    return res


def transition_span(yk: np.ndarray, c: int, lev_old: float, lev_new: float, sigma: float,
                    k: float) -> tuple[int, int, bool]:
    """Widen the boundary (c - 1 | c) by one point per side when that point is in transition.

    The point next to the boundary on each side is a transition point when it lies
    strictly between the two levels and farther than k sigma from the level of its own
    segment; the interval end then moves one point further out.  Segments have at least
    three points, so the moved end stays inside its segment.

    Args:
        yk: Spike-free array.
        c: First index of the right segment.
        lev_old: Level of the left segment.
        lev_new: Level of the right segment.
        sigma: Robust noise.
        k: Distance from the own level, in sigma, that marks a transition point.

    Returns:
        (i_old, i_new, may_extend): last index taken as the old level, first index taken
        as the new level, and whether a moved end is itself a transition point (the
        transition may be longer than reported).
    """
    lo, hi = min(lev_old, lev_new), max(lev_old, lev_new)

    def between(v: float, own: float) -> bool:
        return lo < v < hi and abs(v - own) > k * sigma

    i_old, i_new, more = c - 1, c, False
    if between(float(yk[c - 1]), lev_old):
        i_old = c - 2
        more = more or between(float(yk[i_old]), lev_old)
    if between(float(yk[c]), lev_new):
        i_new = c + 1
        more = more or between(float(yk[i_new]), lev_new)
    return i_old, i_new, more


# --------------------------------------------------------------------------- tables


def changepoint_rows(res: SeriesResult, prm: Params) -> list[dict[str, Any]]:
    """One row per accepted change point of a series.

    Args:
        res: Series result.
        prm: Parameters.

    Returns:
        Row dicts (dates as pandas Timestamps).
    """
    rows = []
    model, backend, test = res.series.split("/")
    keep, yk = res.keep, res.y[res.keep]
    segs, levels = res.segments(), res.levels()
    spike_pos = {s["pos"] for s in res.spikes}
    for j, cp in enumerate(res.cps):
        c = cp.index
        (a, _), (_, b) = segs[j], segs[j + 1]
        lev_l, lev_r = levels[j], levels[j + 1]
        i_old, i_new, may_extend = transition_span(yk, c, lev_l, lev_r, res.sigma, prm.gradual_k)
        o_le, o_rs, o_so, o_sn = keep[c - 1], keep[c], keep[i_old], keep[i_new]
        d_log = lev_r - lev_l
        camp_lr = math.log(res.avg_ts[o_sn] / res.avg_ts[o_so])
        n0 = n1 = CAMPAIGN_REPS  # step-1 tau of this pair: max(ln 1.1, 3 x pooled SD of ln samples)
        pooled = math.sqrt(((n0 - 1) * res.sd_log[o_so] ** 2 + (n1 - 1) * res.sd_log[o_sn] ** 2) / (n0 + n1 - 2))
        rows.append({
            "series": res.series, "model": model, "backend": backend, "test": test,
            "cp_key": f"{short_name(res.series)}#{j + 1}", "accept_step": cp.step,
            "tag_left_end": res.tags[o_le], "tag_right_start": res.tags[o_rs],
            "b_left_end": int(res.builds[o_le]), "b_right_start": int(res.builds[o_rs]),
            "date_left_end": mdates.num2date(res.dates[o_le]).replace(tzinfo=None),
            "date_right_start": mdates.num2date(res.dates[o_rs]).replace(tzinfo=None),
            "seg_left_first": res.tags[keep[a]], "seg_left_n": c - a,
            "seg_right_last": res.tags[keep[b - 1]], "seg_right_n": b - c,
            "level_left": math.exp(lev_l), "level_right": math.exp(lev_r),
            "delta_log": d_log, "delta_pct": math.expm1(d_log), "direction": "+" if d_log > 0 else "-",
            "q_hat": cp.q, "p_value": cp.p, "n_perm": cp.n_perm_done, "sigma": res.sigma, "abs_delta_over_sigma": abs(d_log) / res.sigma,
            "small": abs(math.expm1(d_log)) < prm.small,
            "span_old": res.tags[o_so], "span_new": res.tags[o_sn],
            "b_span_old": int(res.builds[o_so]), "b_span_new": int(res.builds[o_sn]),
            "date_span_old": mdates.num2date(res.dates[o_so]).replace(tzinfo=None),
            "date_span_new": mdates.num2date(res.dates[o_sn]).replace(tzinfo=None),
            "n_transition_points": (c - 1 - i_old) + (i_new - c), "gradual": (i_old < c - 1) or (i_new > c),
            "transition_may_extend": may_extend,
            "spikes_inside_span": ";".join(res.tags[p] for p in sorted(spike_pos) if o_so < p < o_sn),
            "campaign_old": float(res.avg_ts[o_so]), "campaign_new": float(res.avg_ts[o_sn]),
            "campaign_log_ratio": camp_lr, "campaign_delta": math.expm1(camp_lr),
            "campaign_tau": max(math.log1p(0.10), 3.0 * pooled),
            "campaign_sign_agrees": (camp_lr > 0) == (d_log > 0),
        })
    return rows


def spike_rows(res: SeriesResult) -> list[dict[str, Any]]:
    """One row per isolated spike of a series."""
    model, backend, test = res.series.split("/")
    out = []
    for s in res.spikes:
        i = s["pos"]
        out.append({"series": res.series, "model": model, "backend": backend, "test": test, "tag": res.tags[i],
                    "build_number": int(res.builds[i]),
                    "date": mdates.num2date(res.dates[i]).strftime("%Y-%m-%d"),
                    "prev_tag": res.tags[i - 1], "next_tag": res.tags[i + 1],
                    "value": math.exp(res.y[i]), "neighbour_median": math.exp(s["neighbour_median"]),
                    "dev_log": s["dev"], "dev_pct": math.expm1(s["dev"]), "dev_over_sigma": abs(s["dev"]) / res.sigma,
                    "lr_gap_over_sigma": s["lr_gap"] / res.sigma, "sigma": res.sigma,
                    "direction": "+" if s["dev"] > 0 else "-", "campaign_avg_ts": float(res.avg_ts[i])})
    return out


def merge_intervals(cps: pd.DataFrame) -> list[list[int]]:
    """Group change points whose (b_span_old, b_span_new] intervals overlap.

    Args:
        cps: Change-point table.

    Returns:
        Lists of row labels, one per change interval, in chronological order.
    """
    groups: list[list[int]] = []
    cur: list[int] = []
    cur_end = -1
    for i in cps.sort_values(["b_span_old", "b_span_new"]).index:
        r = cps.loc[i]
        if cur and r.b_span_old < cur_end:
            cur.append(i)
            cur_end = max(cur_end, int(r.b_span_new))
        else:
            if cur:
                groups.append(cur)
            cur, cur_end = [i], int(r.b_span_new)
    if cur:
        groups.append(cur)
    return groups


def load_step1(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Step-1 events and their series candidates.

    Args:
        path: candidate_events.csv.

    Returns:
        (events, items): items has one row per series of every event with its own pair.
    """
    ev = pd.read_csv(path)
    items = []
    for r in ev.to_dict("records"):
        for s in json.loads(r["series_json"]):
            items.append({"event_id": r["event_id"], "step1_class": r["class"],
                          "series": s["series"], "model": s["model"], "backend": s["backend"], "test": s["test"],
                          "tag_old": s["tag_old"], "tag_new": s["tag_new"], "b_old": int(s["tag_old"][1:]),
                          "b_new": int(s["tag_new"][1:]), "log_ratio": float(s["log_ratio"]),
                          "noise": bool(s.get("noise", False))})
    return ev, pd.DataFrame(items)


def overlaps(a0: int, a1: int, b0: int, b1: int) -> bool:
    """Whether the half-open build intervals (a0, a1] and (b0, b1] overlap."""
    return a0 < b1 and b0 < a1


def assign_coverage(cps: pd.DataFrame, groups: list[list[int]], ev: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """Change-interval ids and the (i)/(ii)/(iii) coverage by step 1.

    Args:
        cps: Change-point table.
        groups: Output of merge_intervals().
        ev: Step-1 events.
        items: Step-1 series candidates.

    Returns:
        ``cps`` with interval_id, interval_b_old/new, coverage, step1_events_overlapping,
        step1_same_group, step1_pair_covers_span, step1_same_series_listed.
    """
    cps = cps.copy()
    for col in ("interval_id", "coverage", "step1_events_overlapping", "step1_same_group"):
        cps[col] = ""
    cps["interval_b_old"], cps["interval_b_new"] = 0, 0
    cps["step1_pair_covers_span"], cps["step1_same_series_listed"] = False, False
    for k, idx in enumerate(groups, 1):
        b0, b1 = int(cps.loc[idx, "b_span_old"].min()), int(cps.loc[idx, "b_span_new"].max())
        over_ev = ev[[overlaps(b0, b1, int(o), int(n)) for o, n in zip(ev.b_old, ev.b_new)]]
        over_txt = ";".join(f"{e}({c})" for e, c in zip(over_ev.event_id, over_ev["class"]))
        for i in idx:
            r = cps.loc[i]
            same = items[(items.model == r.model) & (items.backend == r.backend)]
            same = same[[overlaps(int(r.b_span_old), int(r.b_span_new), o, n) for o, n in zip(same.b_old, same.b_new)]]
            cov = "i" if not same.empty else ("ii" if not over_ev.empty else "iii")
            cps.loc[i, "interval_id"] = f"R{k:02d}"
            cps.loc[i, "interval_b_old"], cps.loc[i, "interval_b_new"] = b0, b1
            cps.loc[i, "coverage"] = cov
            cps.loc[i, "step1_events_overlapping"] = over_txt
            cps.loc[i, "step1_same_group"] = ";".join(sorted({f"{s.event_id}:{s.tag_old}-{s.tag_new}"
                                                             for s in same.itertuples()}))
            cps.loc[i, "step1_pair_covers_span"] = bool(((same.b_old <= r.b_span_old) &
                                                         (same.b_new >= r.b_span_new)).any())
            cps.loc[i, "step1_same_series_listed"] = bool((same.series == r.series).any())
    return cps


def event_classes(ev: pd.DataFrame) -> dict[str, str]:
    """event_id -> step-1 class."""
    return dict(zip(ev.event_id, ev["class"]))


def reverse_match(items: pd.DataFrame, cps: pd.DataFrame, spikes: pd.DataFrame,
                  ev: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match step-1 series candidates and events to change points and spikes.

    Args:
        items: Step-1 series candidates.
        cps: Change-point table.
        spikes: Spike table.
        ev: Step-1 events.

    Returns:
        (items with on_cp / on_cp_big / cp_keys / spike columns, one row per step-1 event
        with its category).
    """
    items = items.copy()
    spike_tags = {(s.series, s.tag) for s in spikes.itertuples()}
    on_cp, on_big, keys, spk = [], [], [], []
    for it in items.itertuples():
        sub = cps[(cps.series == it.series)]
        sub = sub[[overlaps(it.b_old, it.b_new, int(o), int(n)) for o, n in zip(sub.b_span_old, sub.b_span_new)]]
        on_cp.append(not sub.empty)
        on_big.append(bool((~sub.small).any()) if not sub.empty else False)
        keys.append(";".join(sub.cp_key))
        hit = [t for t in (it.tag_old, it.tag_new) if (it.series, t) in spike_tags]
        spk.append(";".join(hit))
    items["on_cp"], items["on_cp_big"], items["cp_keys"], items["spike_tags"] = on_cp, on_big, keys, spk
    cls = event_classes(ev)
    tags = ev.set_index("event_id")[["tag_old", "tag_new"]].to_dict("index")
    rows = []
    for eid, g in items.groupby("event_id", sort=False):
        if g.on_cp_big.any():
            cat = "change point (≥5%)"
        elif g.on_cp.any():
            cat = "small change point only (<5%)"
        elif (g.spike_tags != "").all():
            cat = "spike"
        else:
            cat = "other"
        detail = []
        for it in g.itertuples():
            tag = f"CP {it.cp_keys}" if it.on_cp else (f"spike@{it.spike_tags}" if it.spike_tags else "none")
            detail.append(f"{short_name(it.series)} {math.expm1(it.log_ratio):+.1%}: {tag}")
        rows.append({"event_id": eid, "step1_class": cls.get(eid, ""), "tag_old": tags[eid]["tag_old"],
                     "tag_new": tags[eid]["tag_new"], "n_series": len(g),
                     "category": cat, "partial_spike": bool((g.spike_tags != "").any() and cat == "other"),
                     "detail": "; ".join(detail)})
    return items, pd.DataFrame(rows)


def unrecovered(cps: pd.DataFrame, results: dict[str, SeriesResult], prm: Params) -> pd.DataFrame:
    """Falls (non-small) without a later rise of similar size in the same series.

    A later rise "recovers" a fall when recover_lo <= ln-rise / |ln-fall| <= recover_hi.

    Args:
        cps: Change-point table.
        results: Series results (for the later segment levels).
        prm: Parameters.

    Returns:
        One row per non-small fall with recovered_by (empty if none) and later levels.
    """
    rows = []
    for name, g in cps.groupby("series", sort=False):
        g = g.sort_values("b_left_end").reset_index(drop=True)
        levels = results[name].levels()
        for j, r in g.iterrows():
            if r.small or r.delta_log >= 0:
                continue
            later = g.iloc[j + 1:]
            ratio = later.delta_log / abs(r.delta_log)
            match = later[(later.delta_log > 0) & (ratio >= prm.recover_lo) & (ratio <= prm.recover_hi)]
            pre = math.log(r.level_left)
            after = levels[j + 1:]
            rows.append({"series": name, "cp_key": r.cp_key, "tag_left_end": r.tag_left_end,
                         "tag_right_start": r.tag_right_start, "span_old": r.span_old, "span_new": r.span_new,
                         "delta_pct": r.delta_pct, "p_value": r.p_value, "coverage": r.coverage,
                         "recovered_by": "" if match.empty else
                         f"{match.iloc[0].cp_key}({match.iloc[0].tag_left_end}→{match.iloc[0].tag_right_start},"
                         f"{match.iloc[0].delta_pct:+.1%})",
                         "later_rises": ";".join(f"{x.cp_key}{x.delta_pct:+.1%}" for x in later.itertuples()
                                                 if x.delta_log > 0),
                         "final_vs_pre": math.expm1(after[-1] - pre), "max_later_vs_pre": math.expm1(max(after) - pre)})
    return pd.DataFrame(rows)


def releases_between(rel: pd.DataFrame, b_old: int, b_new: int) -> tuple[int, int]:
    """Number of release tags and commits in (b_old, b_new]."""
    sub = rel[(rel.build_number > b_old) & (rel.build_number <= b_new)]
    return len(sub), int(sub.commits_since_prev.fillna(0).sum())


def build_cp_events(cps: pd.DataFrame, columns: list[str], rel: pd.DataFrame, changes: pd.DataFrame,
                    dates: dict[str, pd.Timestamp]) -> tuple[pd.DataFrame, dict[Any, str]]:
    """changepoint_events.csv: change intervals with (ii)/(iii) change points of |delta| >= 5 %.

    Args:
        cps: Change-point table with coverage.
        columns: Column names of candidate_events.csv (same order).
        rel: releases.csv.
        changes: config_changes.csv (step 0), informational.
        dates: tag -> commit date.

    Returns:
        (event table with exactly ``columns`` and event ids CP01, ...; row label of every
        listed change point -> its event id).
    """
    q = cps[(~cps.small) & (cps.coverage.isin(["ii", "iii"]))]
    rows = []
    assigned: dict[Any, str] = {}
    for k, (iid, g) in enumerate(sorted(q.groupby("interval_id"), key=lambda kv: kv[1].b_span_old.min()), 1):
        g = g.assign(_abs=g.campaign_log_ratio.abs()).sort_values("_abs", ascending=False)
        b_old, b_new = int(g.b_span_old.min()), int(g.b_span_new.max())
        n_rel, n_commits = releases_between(rel, b_old, b_new)
        inside = changes[(changes.prev_build < b_new) & (changes.build > b_old)] if not changes.empty else changes
        sj = [{"series": r.series, "model": r.model, "backend": r.backend, "test": r.test, "tag_old": r.span_old,
               "tag_new": r.span_new, "mean_old": round(float(r.campaign_old), 4),
               "mean_new": round(float(r.campaign_new), 4), "log_ratio": round(float(r.campaign_log_ratio), 5),
               "delta": round(float(r.campaign_delta), 5), "tau": round(float(r.campaign_tau), 5), "noise": False,
               "explained_by": []} for r in g.itertuples()]
        detail = [f"{short_name(r.series)}:{r.campaign_delta:+.1%}(cp={r.tag_left_end}|{r.tag_right_start},"
                  f"span={r.span_old}->{r.span_new},level={r.level_left:.4g}->{r.level_right:.4g}"
                  f"({r.delta_pct:+.1%}),p={r.p_value:.3f},abs/sigma={r.abs_delta_over_sigma:.1f},cov={r.coverage}"
                  f"{',sign-mismatch' if not r.campaign_sign_agrees else ''})" for r in g.itertuples()]
        why = "; ".join(f"{short_name(r.series)} segment level {r.delta_pct:+.1%} ({COVERAGE_TEXT[r.coverage]}"
                        f"{', overlaps step-1 events ' + r.step1_events_overlapping if r.step1_events_overlapping else ''})"
                        for r in g.itertuples())
        rows.append({
            "event_id": f"CP{k:02d}", "tag_old": f"b{b_old}", "tag_new": f"b{b_new}", "b_old": b_old, "b_new": b_new,
            "date_old": dates[f"b{b_old}"].strftime("%Y-%m-%d"), "date_new": dates[f"b{b_new}"].strftime("%Y-%m-%d"),
            "releases_between": n_rel, "commits_between": n_commits, "n_series": len(g),
            "series": ";".join(g.series), "n_noise_series": 0,
            "directions": ";".join("+" if x > 0 else "-" for x in g.campaign_log_ratio),
            "max_delta_signed": float(g.campaign_delta.iloc[0]), "max_abs_log_ratio": float(g._abs.max()),
            "min_tau_pct": float(np.expm1(g.campaign_tau.min())), "class": "CP", "class_candidates": "",
            "unexplained_series": "", "config_changes": "",
            "other_changes_in_interval": ";".join(f"{c.change_id}:{c.kind}:{c.label}({c.expected})"
                                                  for c in inside.itertuples()) if not inside.empty else "",
            "series_detail": " ; ".join(detail), "series_json": json.dumps(sj, ensure_ascii=False),
            "reason": f"Step 1b E-Divisive change point ({iid}, no configuration attribution): {why}",
        })
        assigned.update({i: f"CP{k:02d}" for i in g.index})
    return pd.DataFrame(rows, columns=columns), assigned


# --------------------------------------------------------------------------- variant and self-test


def compare_variant(results: dict[str, SeriesResult], variant: dict[str, SeriesResult]) -> pd.DataFrame:
    """Compare change points of the full (tau, kappa) search with kappa fixed at the end.

    A change point matches when the right-start positions in the spike-free array differ
    by at most one point.

    Args:
        results: Main results.
        variant: Results with ``kappa='end'``.

    Returns:
        One row per series with counts and the unmatched change points.
    """
    rows = []
    for name, res in results.items():
        a = [c.index for c in res.cps]
        b = [c.index for c in variant[name].cps]
        tags = [res.tags[i] for i in res.keep]
        only_a = [x for x in a if all(abs(x - v) > 1 for v in b)]
        only_b = [x for x in b if all(abs(x - v) > 1 for v in a)]
        rows.append({"series": name, "n_full": len(a), "n_end": len(b), "matched": len(a) - len(only_a),
                     "only_full": ";".join(f"{tags[x - 1]}|{tags[x]}" for x in only_a),
                     "only_end": ";".join(f"{tags[x - 1]}|{tags[x]}" for x in only_b)})
    return pd.DataFrame(rows)


def pipeline_on_array(y: np.ndarray, name: str, prm: Params) -> tuple[list[int], list[int], list[float]]:
    """Spike removal + E-Divisive on a synthetic series.

    Args:
        y: Values (log scale).
        name: Name (seed source).
        prm: Parameters.

    Returns:
        (spike positions, change-point positions in the original index, delta_log of each
        change point from segment medians).
    """
    sigma = robust_sigma(y)
    spikes = [s["pos"] for s in find_spikes(y, sigma, prm)]
    mask = np.ones(len(y), bool)
    mask[spikes] = False
    keep = np.flatnonzero(mask)
    cps, _ = e_divisive(y[keep], prm, np.random.default_rng(zlib.crc32(name.encode())))
    yk = y[keep]
    bounds = [0] + [c.index for c in cps] + [len(yk)]
    lev = [float(np.median(yk[a:b])) for a, b in itertools.pairwise(bounds)]
    return spikes, [int(keep[c.index]) for c in cps], [lev[j + 1] - lev[j] for j in range(len(cps))]


def brute_force_best(z: np.ndarray, alpha: float, min_size: int) -> tuple[float, int, int]:
    """Direct double loop over (tau, kappa) of Q^, for checking scan_splits."""
    best = (-math.inf, -1, -1)
    n = len(z)
    for tau in range(min_size, n - min_size + 1):
        for kap in range(tau + min_size, n + 1):
            x, y = z[:tau], z[tau:kap]
            nx, ny = len(x), len(y)
            cross = sum(abs(a - b) ** alpha for a in x for b in y)
            wx = sum(abs(x[i] - x[j]) ** alpha for i in range(nx) for j in range(i + 1, nx))
            wy = sum(abs(y[i] - y[j]) ** alpha for i in range(ny) for j in range(i + 1, ny))
            e = 2 * cross / (nx * ny) - wx / (nx * (nx - 1) / 2) - wy / (ny * (ny - 1) / 2)
            q = nx * ny / (nx + ny) * e
            if q > best[0] + 1e-12:
                best = (q, tau, kap)
    return best


def self_test(prm: Params, step_reps: int = 10, n_noise: int = 100) -> dict[str, Any]:
    """Synthetic checks of the implementation and of the false-alarm rate.

    (0) scan_splits against a direct double loop; (a1) length 78, Gaussian noise with
    SD 0.03 on the log scale (about 3 %), one step of +15 % or -15 % at position 10, 39 or
    68, ``step_reps`` replicates each: the change point closest to the step must lie
    within one point; (a2) ``n_noise`` pure-noise series with three isolated 5-sigma
    spikes each: share of series with any change point.  Rejections stop early
    (Params.exact_p = False), which leaves every accepted change point unchanged.

    Args:
        prm: Parameters (kappa as in the main run).
        step_reps: Replicates per step position.
        n_noise: Number of pure-noise series.

    Returns:
        Summary dict.
    """
    prm = replace(prm, exact_p=False)
    out: dict[str, Any] = {"n_perm": prm.n_perm, "p_max": prm.p_max}
    gen = np.random.default_rng(zlib.crc32(b"selftest|bruteforce"))
    worst = 0.0
    same_arg = True
    for _ in range(5):
        z = gen.normal(size=13)
        q, tau, kap = scan_splits(z, prm.alpha, prm.min_size, "full")
        bq, btau, bkap = brute_force_best(z, prm.alpha, prm.min_size)
        worst = max(worst, abs(q[0] - bq))
        same_arg = same_arg and (int(tau[0]), int(kap[0])) == (btau, bkap)
    out["bruteforce_max_abs_diff"], out["bruteforce_same_argmax"] = worst, same_arg
    n, sd = 78, 0.03
    errs, n_found, extra, extra_big, misses = [], 0, 0, 0, 0
    for c in (10, 39, 68):
        for k in range(step_reps):
            g = np.random.default_rng(zlib.crc32(f"selftest|step|{c}|{k}".encode()))
            y = g.normal(0.0, sd, n)
            y[c:] += math.log(1.15) if k % 2 == 0 else math.log(0.85)
            _, cps, dl = pipeline_on_array(y, f"selftest-step-{c}-{k}", prm)
            if not cps:
                misses += 1
                errs.append(math.inf)
                continue
            d = [abs(x - c) for x in cps]
            j = int(np.argmin(d))
            errs.append(d[j])
            n_found += 1
            others = [i for i in range(len(cps)) if i != j]
            extra += len(others)
            extra_big += sum(1 for i in others if abs(math.expm1(dl[i])) >= prm.small)
    out.update(step_series=3 * step_reps, step_detected=n_found, step_missed=misses,
               step_max_err=max(errs), step_mean_err=float(np.mean([e for e in errs if np.isfinite(e)] or [math.nan])),
               step_within1=sum(1 for e in errs if e <= 1), step_extra_cps=extra, step_extra_cps_big=extra_big)
    any_cp, big_cp, spike_hit, spike_false, total_spikes = 0, 0, 0, 0, 0
    for k in range(n_noise):
        g = np.random.default_rng(zlib.crc32(f"selftest|noise|{k}".encode()))
        y = g.normal(0.0, sd, n)
        pos: list[int] = []
        while len(pos) < 3:
            p = int(g.integers(2, n - 2))
            if all(abs(p - q) >= 5 for q in pos):
                pos.append(p)
        for p in pos:
            y[p] += 5 * sd * (1 if g.random() < 0.5 else -1)
        spikes, cps, dl = pipeline_on_array(y, f"selftest-noise-{k}", prm)
        total_spikes += 3
        spike_hit += len(set(spikes) & set(pos))
        spike_false += len(set(spikes) - set(pos))
        any_cp += bool(cps)
        big_cp += any(abs(math.expm1(x)) >= prm.small for x in dl)
    out.update(noise_series=n_noise, noise_any_cp=any_cp, noise_big_cp=big_cp, noise_spikes_found=spike_hit,
               noise_spikes_total=total_spikes, noise_false_spikes=spike_false)
    out["passed"] = bool(out["bruteforce_same_argmax"] and out["bruteforce_max_abs_diff"] < 1e-9
                         and out["step_within1"] == out["step_series"])
    return out


# --------------------------------------------------------------------------- report


def fmt_pct(x: float) -> str:
    """Signed percentage with one decimal."""
    return f"{x:+.1%}"


def write_markdown(path: Path, prm: Params, results: dict[str, SeriesResult], cps: pd.DataFrame,
                   spikes: pd.DataFrame, cp_events: pd.DataFrame, ev_cat: pd.DataFrame, items: pd.DataFrame,
                   unrec: pd.DataFrame, variant: pd.DataFrame | None, st: dict[str, Any] | None) -> None:
    """Write changepoints.md.

    Args:
        path: Output path.
        prm: Parameters.
        results: Series results.
        cps: Change-point table (with coverage).
        spikes: Spike table.
        cp_events: changepoint_events table.
        ev_cat: Step-1 events with their category.
        items: Step-1 series candidates with matches.
        unrec: Unrecovered falls.
        variant: kappa-end comparison (None if skipped).
        st: Self-test summary (None if skipped).
    """
    big = cps[~cps.small]
    cov_counts = ", ".join(f"{COVERAGE_TEXT[c]}: {int((big.coverage == c).sum())}" for c in ("i", "ii", "iii"))
    L = [
        "# Step 1b: change-point detection (E-Divisive means)",
        "",
        ("Generated by `scripts/analysis/step1b_changepoints.py`. Reads `results/<tag>/`, `candidate_events.csv`, "
         "`config_changes.csv` and `data/releases.csv` only; it builds nothing and runs no benchmark."),
        "",
        "## Method and parameters",
        "",
        ("- **Statistic**: for each (tag, series), the median of the 5 `samples_ts` of the campaign run (avg_ts when "
         "samples are missing), natural log, ordered by build number. Only rows with `param_set == main` and "
         "`status == ok` are used. qwen fails to load at b1778 and earlier and at b2761, so those points are absent."),
        "- **Robust noise** σ = 1.4826 · MAD(first differences) / √2 (log units, one value per series, from all points).",
        (f"- **Isolated spike**: a point that differs from the median of its {prm.spike_halfwin} neighbors on each side "
         "(only 1 on the short side next to an end; the two end points are not judged) by "
         f"> {prm.spike_k:g}σ, while the medians of the left and right neighbors differ by < {prm.spike_agree:g}σ. "
         "Spikes are listed in `spikes.csv` and left out of the change-point detection (a single pass, no iteration)."),
        (f"- **E-Divisive** (Matteson & James 2014, JASA 109:334-345), α = {prm.alpha:g}, minimum segment length "
         f"{prm.min_size}, R = {prm.n_perm} permutations, accepted when p < {prm.p_max:g}, κ search mode `{prm.kappa}`. "
         "How the implementation maps to the formulas of the original paper:"),
        "  - For a cluster Z_1..Z_T and 1 ≤ τ < κ ≤ T, X_τ = {Z_1..Z_τ} (n = τ) and Y_τ(κ) = {Z_τ+1..Z_κ} (m = κ − τ);",
        ("    Ê(X, Y; α) = 2/(mn)·Σ_i Σ_j |X_i − Y_j|^α − C(n,2)⁻¹·Σ_{i<k} |X_i − X_k|^α − C(m,2)⁻¹·Σ_{j<k} |Y_j − Y_k|^α; "
         "Q̂ = mn/(m+n)·Ê; (τ̂, κ̂) = argmax Q̂ with n, m ≥ 3. In the code, `scan_splits` takes the three double sums "
         "by blocks from a two-dimensional prefix sum of the distance matrix (`cross`, `within_x`, `within_y`) and "
         "computes all (τ, κ) in one vectorized step. Ties go to the smallest τ, then the smallest κ. The self-test "
         "checks this against a direct double loop."),
        ("  - Hierarchical bisection (`e_divisive`): with k−1 accepted change points, the best split of every cluster is "
         "computed and the cluster with the largest Q̂ proposes the k-th change point τ̂ (κ̂ only bounds the right "
         "sample and does not become a change point)."),
        ("  - Significance (`permutation_test`): the observations are permuted independently within every cluster and "
         "the maximal Q̂ over all clusters is recomputed, R times in all; "
         "p = (1 + #{Q̂^(r) ≥ Q̂}) / (R + 1). With p < 0.01 the point is accepted and the procedure continues, "
         "otherwise it stops. The generator is `numpy.random.default_rng(zlib.crc32(series name))`, so results are "
         "reproducible. All change points in this report use the full R permutations. In the synthetic self-test and "
         "the κ variant, a split stops early once its rejection is certain ((1 + exceedances)/(R + 1) ≥ 0.01). This "
         "changes no accepted change point (an accepted split never reaches the stopping count, and a rejection ends "
         "the procedure) and only makes the p of the final rejected split a lower bound."),
        ("  - Relation to existing implementations: the double (τ, κ) search, U-statistic normalization and "
         "within-cluster permutation are the same as in e.divisive of the R package ecp. MongoDB's "
         "signal_processing_algorithms (PyPI 2.1.6, checked by reading its source) fixes κ at the end of the window, "
         "normalizes within-cluster sums by n² (V statistic), uses p = #/(R+1), accepts when p ≤ the threshold and has "
         "no minimum segment length. Hunter (Fleming et al. 2023), according to its abstract, replaces the permutation "
         "test with a t-test to remove the randomness of the results. This script keeps the permutation test (fixed "
         "seed) and also runs the variant with κ fixed at the end of the cluster as a comparison (see the robustness "
         "section)."),
        (f"- **Change-point output**: the level of each adjacent segment is the median of the log statistic in it; "
         f"Δ = exp(right − left) − 1; |Δ| < {prm.small:.0%} is marked small (kept, but not put on the re-measurement "
         "list); |Δ|/σ uses the log difference."),
        (f"- **Gradual change**: the point next to the boundary (c−1 | c) on each side is a transition point if it lies "
         f"strictly between the two levels and farther than {prm.gradual_k:g}σ from the level of its own segment, and "
         "the transition interval is then widened past it by one point on that side. span_old and span_new are the "
         "tags where the transition starts and ends (without a gradual change, the last tag of the left segment and "
         "the first of the right). The interval is widened by one step only. If a widened end meets the same condition "
         "it is flagged `transition may be wider` (csv column transition_may_extend). Multi-step widening is not used "
         "because slow drift inside a long segment biases its median, and multi-step widening would run through "
         "undetected plateaus or dips (in a trial run the transition of qwen/cpu/tg128 extended into the two-point dip "
         "at b4464)."),
        ("- **Merging across series**: change points whose transition intervals (b_span_old, b_span_new] overlap (sharing "
         "only an end point does not count) are merged into change intervals R01, R02, ... (the same merging rule as "
         "step 1)."),
        ("- **Comparison with step 1** (per change point): (i) the change interval overlaps a step-1 event and the same "
         "(model, back end) is listed in step 1 with a tag pair that overlaps this transition interval (step 2 runs "
         "these binaries, and the other test is measured along with it); (ii) the change interval overlaps a step-1 "
         "event but this group is not listed with an overlapping tag pair; (iii) no step-1 event overlaps the change "
         "interval."),
        (f"- **Regression not recovered**: a falling change point with |Δ| ≥ {prm.small:.0%} that no rising change point "
         f"of similar size follows in the same series (similar size: ln rise / |ln fall| within "
         f"[{prm.recover_lo:g}, {prm.recover_hi:g}])."),
        "",
        "## Overview of results",
        "",
        f"- 12 series; points per series: {', '.join(f'{short_name(n)} {len(r.tags)}' for n, r in results.items())}.",
        (f"- Isolated spikes: {len(spikes)}; change points: {len(cps)}, with |Δ| ≥ {prm.small:.0%}: {len(big)}, "
         f"small: {int(cps.small.sum())}; gradual (transition interval spans ≥ 2 sampling intervals): {int(cps.gradual.sum())}."),
        f"- Change intervals after merging: {cps.interval_id.nunique()}.",
        (f"- Coverage classes (change points with |Δ| ≥ {prm.small:.0%}): {cov_counts}; change-point events written to "
         f"`changepoint_events.csv`: {len(cp_events)} ({', '.join(cp_events.event_id) or 'none'}), "
         f"with {int(cp_events.n_series.sum()) if len(cp_events) else 0} series in all."),
        ("- The class in `changepoint_events.csv` is CP. The default `--classes A,B,C,D` of `step2_interleaved.py` does "
         "not select these events, so a re-measurement needs `--classes CP` (or `--event-ids CP01,...`)."),
        "",
    ]
    L += ["## Change points per series", "",
          ("Columns: left end | right start = the adjacent sampled tags of the two segments; transition = span_old → "
           "span_new; level = segment median (t/s); p = permutation-test p; step = order of acceptance in the "
           "hierarchical bisection; campaign Δ = ratio of the campaign avg_ts at the two ends of the span − 1."), ""]
    for name, res in results.items():
        sub = cps[cps.series == name].sort_values("b_left_end")
        sp = spikes[spikes.series == name]
        stop = res.stop_test
        stop_txt = f"rejected split at stop p = {stop.p:.3f}" if stop is not None else "no cluster left to split"
        sp_txt = ", ".join(f"{s.tag} ({s.dev_pct:+.0%})" for s in sp.itertuples()) or "none"
        L.append(f"### {short_name(name)} (n = {len(res.tags)}, σ = {res.sigma:.4f} (≈{math.expm1(res.sigma):.1%}), "
                 f"spikes: {sp_txt}; {stop_txt})")
        L.append("")
        if sub.empty:
            L += ["No change points.", ""]
            continue
        L += ["| Change point | Left end \\| right start | Transition | Level left → right | Δ | p | Step | \\|Δ\\|/σ | Flags | campaign Δ | Interval | Coverage |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in sub.itertuples():
            flags = [f for f, on in (("small", r.small), (f"gradual({r.n_transition_points})", r.gradual),
                                     ("transition may be wider", r.transition_may_extend),
                                     ("sign mismatch", not r.campaign_sign_agrees)) if on]
            if r.spikes_inside_span:
                flags.append(f"spans spike {r.spikes_inside_span}")
            L.append(f"| {r.cp_key} | {r.tag_left_end} \\| {r.tag_right_start} | {r.span_old} → {r.span_new} | "
                     f"{r.level_left:.4g} → {r.level_right:.4g} | {fmt_pct(r.delta_pct)} | {r.p_value:.3f} | "
                     f"{r.accept_step} | {r.abs_delta_over_sigma:.1f} | {', '.join(flags) or '-'} | "
                     f"{fmt_pct(r.campaign_delta)} | {r.interval_id} | {r.coverage} |")
        L.append("")
    L += ["## Isolated spikes", "",
          "| Series | tag | Date | Value (t/s) | Neighbor median | Deviation | Deviation/σ | Left-right gap/σ |", "|---|---|---|---|---|---|---|---|"]
    for s in spikes.sort_values(["build_number", "series"]).itertuples():
        L.append(f"| {short_name(s.series)} | {s.tag} | {s.date} | {s.value:.4g} | {s.neighbour_median:.4g} | "
                 f"{fmt_pct(s.dev_pct)} | {s.dev_over_sigma:.1f} | {s.lr_gap_over_sigma:.1f} |")
    if spikes.empty:
        L.append("| - | - | - | - | - | - | - | - |")
    L += ["", "## Change intervals after merging", "",
          "| Interval | Transition start and end | Dates | Series (segment-level Δ; small in parentheses) | Overlapping step-1 events | Coverage | Change-point event |",
          "|---|---|---|---|---|---|---|"]
    for iid, g in sorted(cps.groupby("interval_id"), key=lambda kv: kv[1].b_span_old.min()):
        b0, b1 = int(g.interval_b_old.iloc[0]), int(g.interval_b_new.iloc[0])
        d0 = g.loc[g.b_span_old.idxmin(), "date_span_old"].strftime("%Y-%m-%d")
        d1 = g.loc[g.b_span_new.idxmax(), "date_span_new"].strftime("%Y-%m-%d")
        ser = ", ".join((f"({short_name(r.series)} {fmt_pct(r.delta_pct)})" if r.small
                        else f"{short_name(r.series)} {fmt_pct(r.delta_pct)}") for r in g.itertuples())
        covs = "/".join(sorted(set(g.coverage)))
        cpe = ",".join(sorted({x for x in g.cp_event_id if x})) or "-"
        L.append(f"| {iid} | b{b0} → b{b1} | {d0} → {d1} | {ser} | {g.step1_events_overlapping.iloc[0] or '-'} | "
                 f"{covs} | {cpe} |")
    L += ["", "## Comparison with step 1", "", f"### Change points missed by step 1: types (ii) and (iii), |Δ| ≥ {prm.small:.0%}", "",
          ("| Change-point event | Change point | Transition (re-measured tag pair) | Segment-level Δ | campaign Δ | p | "
           "\\|Δ\\|/σ | Coverage | Overlapping step-1 events | Tag pairs of this group in step 1 |"),
          "|---|---|---|---|---|---|---|---|---|---|"]
    miss = big[big.coverage.isin(["ii", "iii"])].sort_values(["b_span_old", "series"])
    for r in miss.itertuples():
        L.append(f"| {r.cp_event_id} | {r.cp_key} | {r.span_old} → {r.span_new} | {fmt_pct(r.delta_pct)} | "
                 f"{fmt_pct(r.campaign_delta)} | {r.p_value:.3f} | {r.abs_delta_over_sigma:.1f} | {r.coverage} | "
                 f"{r.step1_events_overlapping or '-'} | {r.step1_same_group or '-'} |")
    if miss.empty:
        L.append("| - | - | - | - | - | - | - | - | - | - |")
    part = big[(big.coverage == "i") & (~big.step1_pair_covers_span)]
    L += ["", f"### Type (i) change points whose step-1 tag pair covers only part of the transition ({len(part)})", "",
          ("Step 2 runs these binaries, but the step-1 tag pair does not span the whole transition interval, so the "
           "re-measured change may be smaller than the difference of the segment levels."), ""]
    for r in part.sort_values("b_span_old").itertuples():
        L.append(f"- {r.cp_key}: transition {r.span_old} → {r.span_new}, segment level {fmt_pct(r.delta_pct)}; "
                 f"this group in step 1: {r.step1_same_group}.")
    if part.empty:
        L.append("- None.")
    only_other = big[(big.coverage == "i") & (~big.step1_same_series_listed)]
    L += ["", f"### Type (i) change points measured only along with the other test of the group ({len(only_other)})", ""]
    for r in only_other.sort_values("b_span_old").itertuples():
        L.append(f"- {r.cp_key}: step 1 lists the other test of the same (model, back end) ({r.step1_same_group}); "
                 "the step-2 summary marks this series as info, and it does not enter the judgment of the event.")
    if only_other.empty:
        L.append("- None.")
    cnt = ev_cat.groupby(["category", "step1_class"]).size().unstack(fill_value=0)
    L += ["", f"### In reverse: where the step-1 events ({len(ev_cat)}) fall", "",
          ("Series-level match: the tag pair of a series in a step-1 event overlaps the transition interval of a change "
           "point of the same series → on a change point. Otherwise, if one end of the tag pair is an isolated spike of "
           "the same series → spike. Event level: an event with any series on a change point of at least 5% is "
           "`change point (≥5%)`; otherwise one with any series on a small change point is `small change point only`; "
           "otherwise, if all series touch a spike, `spike`; the rest are `other`."), "",
          "| Category | " + " | ".join(f"Step 1 {c}" for c in cnt.columns) + " | Total |",
          "|---|" + "---|" * (len(cnt.columns) + 1)]
    for cat in ("change point (≥5%)", "small change point only (<5%)", "spike", "other"):
        if cat not in cnt.index:
            L.append(f"| {cat} | " + " | ".join("0" for _ in cnt.columns) + " | 0 |")
            continue
        row = cnt.loc[cat]
        L.append(f"| {cat} | " + " | ".join(str(int(row[c])) for c in cnt.columns) + f" | {int(row.sum())} |")
    L.append("| Total | " + " | ".join(str(int(cnt[c].sum())) for c in cnt.columns) + f" | {int(cnt.values.sum())} |")
    n_spike_only = int(((~items.on_cp) & (items.spike_tags != "")).sum())
    n_neither = int(((~items.on_cp) & (items.spike_tags == "")).sum())
    L += ["", (f"Series level: step 1 has {len(items)} series candidates; on a change point: {int(items.on_cp.sum())} "
               f"(on one of ≥5%: {int(items.on_cp_big.sum())}); not on a change point but touching a spike: "
               f"{n_spike_only}; neither: {n_neither}. `other` events with a series touching a spike: "
               f"{int(ev_cat.partial_spike.sum())}."), "",
          "| Event | Step-1 class | Interval | Category | Series (step-1 Δ: match) |", "|---|---|---|---|---|"]
    for r in ev_cat.itertuples():
        L.append(f"| {r.event_id} | {r.step1_class} | {r.tag_old} → {r.tag_new} | {r.category} | {r.detail} |")
    L += ["", "## Regressions not recovered", "",
          (f"Falling change points with |Δ| ≥ {prm.small:.0%}, by series. Recovered means that a rising change point of "
           "similar size follows. Final and highest levels are the later segment levels relative to the level before "
           "the fall (later rises may come from unrelated improvements, so these are for reference only)."), "",
          ("| Series | Change point | Left end \\| right start | Segment-level Δ | p | Coverage | Later rise of similar size "
           "| All later rising change points | Final level vs before the fall | Highest later level vs before the fall |"),
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in unrec[unrec.recovered_by == ""].itertuples() if not unrec.empty else []:
        L.append(f"| {short_name(r.series)} | {r.cp_key} | {r.tag_left_end} \\| {r.tag_right_start} | "
                 f"{fmt_pct(r.delta_pct)} | {r.p_value:.3f} | {r.coverage} | none | {r.later_rises or '-'} | "
                 f"{fmt_pct(r.final_vs_pre)} | {fmt_pct(r.max_later_vs_pre)} |")
    rec = unrec[unrec.recovered_by != ""] if not unrec.empty else unrec
    rec_txt = "; ".join(f"{r.cp_key} {fmt_pct(r.delta_pct)} ← {r.recovered_by}" for r in rec.itertuples()) or "none"
    L += ["", f"Falling change points with a rise of similar size ({len(rec)}): {rec_txt}.", ""]
    if variant is not None:
        L += ["## Robustness: variant with κ fixed at the end of the cluster", "",
              ("Same data, same spike handling and same seed, with κ fixed at the end of the cluster (as the MongoDB "
               "implementation does). Two change points count as the same when their right-start positions differ by at "
               "most 1 point."), "",
              "| Series | Original (τ, κ) | κ = end | Matched | Only in original | Only in κ = end |", "|---|---|---|---|---|---|"]
        for r in variant.itertuples():
            L.append(f"| {short_name(r.series)} | {r.n_full} | {r.n_end} | {r.matched} | {r.only_full or '-'} | "
                     f"{r.only_end or '-'} |")
        L.append("")
    if st is not None:
        L += ["## Self-test on synthetic data", "",
              (f"- Vectorized statistic against a direct double loop (length 13, 5 sets): largest difference "
               f"{st['bruteforce_max_abs_diff']:.2e}, same argmax: {'yes' if st['bruteforce_same_argmax'] else 'no'}."),
              (f"- R = {st['n_perm']} permutations, accepted when p < {st['p_max']:g} (as in the main analysis; rejected "
               "splits stop early)."),
              (f"- Steps: length 78, Gaussian noise with SD 0.03 on the log scale (≈3%), a step of +15% or −15% at point "
               f"10, 39 or 68, {st['step_series'] // 3} series each: "
               f"detected {st['step_detected']}/{st['step_series']}, position error ≤ 1 in {st['step_within1']} series, "
               f"largest error {st['step_max_err']}, mean error {st['step_mean_err']:.2f}; extra change points: "
               f"{st['step_extra_cps']} (with |Δ| ≥ {prm.small:.0%}: {st['step_extra_cps_big']})."),
              (f"- Pure noise + 3 one-point spikes of 5σ (random sign, at least 5 apart), {st['noise_series']} series: "
               f"any change point in {st['noise_any_cp']} series "
               f"({st['noise_any_cp'] / st['noise_series']:.0%}), a change point with |Δ| ≥ {prm.small:.0%} in "
               f"{st['noise_big_cp']} series; the spike rule recovered {st['noise_spikes_found']}/{st['noise_spikes_total']} "
               f"true spikes and falsely flagged {st['noise_false_spikes']}."),
              ""]
    L += ["## Limitations", "",
          "- Only changes between sampled releases can be seen. A transition interval lies between sampled tags and does not locate a commit.",
          ("- σ is estimated from the MAD of adjacent differences and is too large when a series has many steps (especially "
           "tinyllama/metal), which makes the spike and gradual-change criteria conservative."),
          ("- The permutation test assumes that observations within a cluster are exchangeable; slow drift or "
           "autocorrelation across releases makes p too small. The hierarchical bisection tests step by step without a "
           "correction for multiple comparisons."),
          ("- Each point is a single campaign run, so segment levels and Δ come from the medians of single runs. Whether a "
           "change is real depends on the interleaved re-measurement of step 2."),
          ""]
    path.write_text("\n".join(L))


def plot_changepoints(results: dict[str, SeriesResult], cps: pd.DataFrame, out_base: Path, prm: Params) -> None:
    """3 x 4 panels: per-tag medians, segment levels, change points, spikes.

    Args:
        results: Series results.
        cps: Change-point table.
        out_base: Output path without suffix.
        prm: Parameters (for the title).
    """
    plt.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 8,
                         "axes.prop_cycle": matplotlib.cycler(color=list(PALETTE))})
    cols = [(b, t) for b in BACKENDS for t in TESTS]
    fig, axes = plt.subplots(len(MODELS), len(cols), figsize=(15, 10.2), sharex=True)
    plain = mticker.FuncFormatter(lambda v, _: f"{v:g}")
    for i, model in enumerate(MODELS):
        for j, (backend, test) in enumerate(cols):
            ax = axes[i][j]
            name = series_name(model, backend, test)
            res = results.get(name)
            if res is None:
                ax.set_axis_off()
                continue
            color, marker = MODEL_COLOR[model], MODEL_MARKER[model]
            vals = np.exp(res.y)
            sub = cps[cps.series == name].sort_values("b_left_end")
            for r in sub.itertuples():
                ax.axvspan(mdates.date2num(r.date_span_old), mdates.date2num(r.date_span_new), color=SPAN_COLOR,
                           alpha=0.35, lw=0, zorder=0)
            for k, r in enumerate(sub.itertuples()):
                x = (mdates.date2num(r.date_left_end) + mdates.date2num(r.date_right_start)) / 2
                if r.small:
                    ax.axvline(x, color=SMALL_COLOR, lw=0.9, ls="--", zorder=1)
                    continue
                ax.axvline(x, color=CP_COLOR, lw=0.9, zorder=1)
                ax.text(x, 1.01 + 0.055 * (k % 3), f"{r.delta_pct:+.0%}", transform=ax.get_xaxis_transform(),
                        ha="center", va="bottom", fontsize=5.5, color=CP_COLOR)
            ax.plot(res.dates[res.keep], vals[res.keep], ls="none", marker=marker, ms=2.8, color=color, zorder=3)
            sp = np.flatnonzero(res.spike_mask)
            if sp.size:
                ax.plot(res.dates[sp], vals[sp], ls="none", marker=marker, ms=4.5, mfc="none", mec=color, mew=0.9,
                        zorder=3)
            for (a, b), lev in zip(res.segments(), res.levels()):
                ax.hlines(math.exp(lev), res.dates[res.keep[a]], res.dates[res.keep[b - 1]], colors=color, lw=1.6,
                          zorder=4)
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(plain)
            if vals.max() / vals.min() < 8:
                ax.yaxis.set_minor_locator(mticker.LogLocator(subs=(2.0, 3.0, 5.0)))
                ax.yaxis.set_minor_formatter(plain)
            else:
                ax.yaxis.set_minor_formatter(mticker.NullFormatter())
            ax.grid(True, which="both", lw=0.3, alpha=0.4)
            if i == 0:
                ax.set_title(f"{backend} / {test}", fontsize=9, pad=40)
            if j == 0:
                ax.set_ylabel(f"{SHORT[model]}  tokens/s")
            if i == len(MODELS) - 1:
                ax.set_xlabel("commit date")
            ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            ax.tick_params(axis="x", labelsize=7, rotation=30)
    handles: list[Any] = [Line2D([], [], color=MODEL_COLOR[m], marker=MODEL_MARKER[m], ls="none", ms=3.5, label=m)
                          for m in MODELS]
    handles += [Line2D([], [], color=PALETTE[0], marker="o", ls="none", ms=4.5, mfc="none", label="isolated spike (excluded)"),
                Line2D([], [], color=PALETTE[0], lw=1.6, label="segment level (median)"),
                Line2D([], [], color=CP_COLOR, lw=0.9, label=f"change point, |Δ| ≥ {prm.small:.0%}"),
                Line2D([], [], color=SMALL_COLOR, lw=0.9, ls="--", label=f"change point, |Δ| < {prm.small:.0%}"),
                Patch(facecolor=SPAN_COLOR, alpha=0.35, label="transition span_old → span_new")]
    fig.legend(handles=handles, loc="lower center", ncol=8, frameon=False, fontsize=7.5)
    fig.suptitle(f"E-Divisive change points (α = {prm.alpha:g}, min. segment {prm.min_size}, {prm.n_perm} permutations, "
                 f"p < {prm.p_max:g}) of the per-tag median throughput, Apple M5", fontsize=10)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    for suffix in (".pdf", ".svg"):
        fig.savefig(out_base.with_suffix(suffix))
    plt.close(fig)


# --------------------------------------------------------------------------- main


def run_all(df: pd.DataFrame, prm: Params) -> dict[str, SeriesResult]:
    """Analyse all 12 series in the canonical order.

    Args:
        df: Measurements.
        prm: Parameters.

    Returns:
        Series id -> result.
    """
    out = {}
    for model in MODELS:
        for backend in BACKENDS:
            for test in TESTS:
                name = series_name(model, backend, test)
                g = df[df.series == name]
                if g.empty:
                    continue
                out[name] = analyse_series(name, g, prm)
                r = out[name]
                logger.info("%s: n=%d sigma=%.4f spikes=%d change points=%d", short_name(name), len(r.tags), r.sigma,
                            len(r.spikes), len(r.cps))
    return out


def main() -> int:
    """Entry point; returns the exit code."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--events", type=Path, default=EVENTS_CSV, help="step-1 candidate_events.csv")
    ap.add_argument("--alpha", type=float, default=Params.alpha)
    ap.add_argument("--min-size", type=int, default=Params.min_size)
    ap.add_argument("--n-perm", type=int, default=Params.n_perm)
    ap.add_argument("--p-max", type=float, default=Params.p_max)
    ap.add_argument("--kappa", choices=("full", "end"), default=Params.kappa)
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--no-variant", action="store_true", help="skip the kappa-end robustness comparison")
    ap.add_argument("--skip-self-test", action="store_true")
    ap.add_argument("--self-test-only", action="store_true", help="run the synthetic checks only; write nothing")
    ap.add_argument("--self-test-reps", type=int, default=10, help="synthetic step series per position (3 positions)")
    ap.add_argument("--self-test-noise", type=int, default=100, help="synthetic pure-noise series")
    ns = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    prm = Params(alpha=ns.alpha, min_size=ns.min_size, n_perm=ns.n_perm, p_max=ns.p_max, kappa=ns.kappa)
    st = None
    if not ns.skip_self_test or ns.self_test_only:
        st = self_test(prm, ns.self_test_reps, ns.self_test_noise)
        logger.info("self-test: %s", json.dumps(st, default=float))
        if ns.self_test_only:
            return 0 if st["passed"] else 1
    df = load_measurements()
    logger.info("loaded %d measurements (%d from samples_ts), %d series", len(df),
                int((df.stat_source == "samples").sum()), df.series.nunique())
    results = run_all(df, prm)
    cps = pd.DataFrame([row for r in results.values() for row in changepoint_rows(r, prm)])
    spikes = pd.DataFrame([row for r in results.values() for row in spike_rows(r)])
    if spikes.empty:
        spikes = pd.DataFrame(columns=["series", "tag", "build_number", "date", "dev_pct", "value", "neighbour_median",
                                       "dev_over_sigma", "lr_gap_over_sigma"])
    ev, items = load_step1(ns.events)
    cps = assign_coverage(cps, merge_intervals(cps), ev, items)
    cps["cp_event_id"] = ""
    rel = pd.read_csv(RELEASES)
    rel["commits_since_prev"] = pd.to_numeric(rel.commits_since_prev, errors="coerce")
    changes = pd.read_csv(CHANGES_CSV, dtype=str).fillna("") if CHANGES_CSV.is_file() else pd.DataFrame()
    if not changes.empty:
        for c in ("prev_build", "build"):
            changes[c] = changes[c].astype(int)
    dates = df.drop_duplicates("tag").set_index("tag").date.to_dict()
    columns = list(pd.read_csv(ns.events, nrows=0).columns)
    cp_events, assigned = build_cp_events(cps, columns, rel, changes, dates)
    cps.loc[list(assigned), "cp_event_id"] = list(assigned.values())
    items, ev_cat = reverse_match(items, cps, spikes, ev)
    unrec = unrecovered(cps, results, prm)
    variant = None
    if not ns.no_variant:
        alt = replace(prm, kappa="end" if prm.kappa == "full" else "full", exact_p=False)
        alt_res = {n: analyse_series(n, df[df.series == n], alt) for n in results}
        variant = compare_variant(results, alt_res)
        if prm.kappa == "end":
            variant = variant.rename(columns={"n_full": "n_end", "n_end": "n_full", "only_full": "only_end",
                                              "only_end": "only_full"})
    out = ns.out_dir
    out.mkdir(parents=True, exist_ok=True)
    cps_out = cps.copy()
    for c in ("date_left_end", "date_right_start", "date_span_old", "date_span_new"):
        cps_out[c] = pd.to_datetime(cps_out[c]).dt.strftime("%Y-%m-%d")
    cps_out.sort_values(["series", "b_left_end"]).to_csv(out / "changepoints.csv", index=False)
    spikes.to_csv(out / "spikes.csv", index=False)
    cp_events.to_csv(out / "changepoint_events.csv", index=False)
    write_markdown(out / "changepoints.md", prm, results, cps, spikes, cp_events, ev_cat, items, unrec, variant, st)
    if not ns.no_plot:
        plot_changepoints(results, cps, out / "changepoints", prm)
    logger.info("%d change points (%d with |delta| >= %.0f%%), %d spikes, %d intervals, %d CP events",
                len(cps), int((~cps.small).sum()), prm.small * 100, len(spikes), cps.interval_id.nunique(),
                len(cp_events))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
