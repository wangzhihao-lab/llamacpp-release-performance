#!/usr/bin/env python3
"""Root-cause protocol, step 3: bisect a confirmed event down to adjacent releases (or commits).

Input is one confirmed series (tag_lo, tag_hi, model, backend, test, expected direction):
either on the command line (``--lo --hi --model --backend --test --direction``) or from step 2
(``--from-step2 E49`` reads ``results/analysis/interleaved/E49_*/summary.csv`` and takes every
series judged C, most significant first; ``--series`` restricts them; ``--step2-rule v11``
reads the v1.1 verdicts of ``interleaved/judge_v11_series.csv`` instead).  Each series is
bisected on its own; binaries are shared through ``bins/``.

1. Candidates: the release tags of ``data/releases.csv`` whose build number lies strictly
   between lo and hi.  Every step takes the median candidate as mid.  ``bins/<mid>/llama-bench``
   is reused when it exists, otherwise built with ``BUILD_ONLY=1
   RESULTS_ROOT=results/bisect_builds /usr/bin/arch -arm64 /bin/bash scripts/build_bench.sh
   <mid>``.  A failed build is recorded as a skip, counts as a build, and the candidate next
   to the median is tried instead (left and right alternating).
2. Three-way interleaved measurement: round 1 lo, mid, hi; round 2 hi, mid, lo; ...
   (``--rounds``, default 2).  Every run is its own process with step 2's fixed configuration
   (``binary_caps`` and ``fixed_args`` imported from step2_interleaved), only the test of
   interest (pp512: ``-p 512 -n 0``; tg128: ``-p 0 -n 128``), ``-r`` 5 for mistral-7b and 10
   for the two small models, ``GGML_METAL_PATH_RESOURCES=bins/<tag>``.  Before a run: 20 s
   cooldown after the previous run or build, then wait (at most 300 s) for top's CPU idle >= 80%,
   macOS thermal state <= ``--thermal-max`` (1; fanless MacBook Air) and no other
   llama-bench/llama-server/llama-cli (step 2's ``cpu_idle_pct``, ``thermal_state`` and
   ``busy_processes``).
3. Judgment: per run y = ln(median samples_ts); per side the means L_lo, L_mid, L_hi;
   f = (L_mid - L_lo) / (L_hi - L_lo).  f <= 0.35: mid looks old (lo = mid); f >= 0.65: mid
   looks new (hi = mid); in between ``intermediate`` (possibly two stacked changes), continued
   by f < 0.5 / >= 0.5 and flagged.  Every step first checks that L_hi - L_lo has the expected
   sign and at least half the reference magnitude (step 2's confirmed |ln ratio|; ``--ref-lr``
   overrides; step 1's value is the fallback), otherwise ``effect_lost`` ends the series.
4. End: lo and hi are adjacent release tags (``--commit-level`` then bisects the first-parent
   commits between them, built from ``archive/<sha>.tar.gz`` as ``c<sha12>``), or a build is
   needed after ``--max-builds`` (8) builds.  The commits lo..hi are read from the blob-less
   clone ``repo/`` without network (``GIT_NO_LAZY_FETCH=1``, ``-c protocol.allow=never``); PR
   numbers come from the ``(#12345)`` suffix of the subject.

Safety: real runs only inside the measurement window (``--window``, local time, default 07:00-17:30),
checked before every build and every run; refuses while step 2 (``interleaved/.step2.lock``)
or the campaign runs; holds ``results/analysis/bisect/.step3.lock``.  SIGTERM/SIGINT kill the
running llama-bench (a running build is left to finish) and stop; the state is kept.

Outputs per series ``results/analysis/bisect/<event>_<model>_<backend>_<test>/``: target.json,
steps.csv (one row per step or skipped candidate), builds.tsv, runs.tsv, one
``s<step>_r<round>_<role>_<tag>.json/.log`` per run, ``build_<tag>.log``, result.json and log.md
(the process and the conclusion for humans); over all series summary.csv, summary.md and
run.log.  Starting the same command again resumes from these files (finished runs are not
repeated).  ``--dry-run`` prints candidates, the first mid, the builds and every command of
the next step, starts no process and writes nothing, at any time; ``--summarize-only``
rebuilds summary.csv/summary.md.

Real run from the repository root (inside the window, detached):
  nohup uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step3_bisect.py --from-step2 E49 > results/analysis/bisect_nohup.out 2>&1 &

Run: uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step3_bisect.py --lo b8545 --hi b8740 --model mistral-7b --backend metal --test pp512 --direction up --dry-run
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import datetime as dt
import importlib.util
import json
import logging
import math
import os
import re
import shlex
import signal
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_step2() -> ModuleType:
    """Import ``step2_interleaved.py`` from this directory.

    ``python3 -I`` keeps the script directory off ``sys.path``, so the module is loaded from its
    file and registered in ``sys.modules`` (its dataclasses need that); it is loaded only once.

    Returns:
        The step-2 module.

    Raises:
        ImportError: If the file cannot be loaded.
    """
    name = "step2_interleaved"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


S2 = _load_step2()
# Reused from step 2 unchanged: help parsing, fixed configuration, quiet test, window, locks.
Caps = S2.Caps
binary_caps = S2.binary_caps
fixed_args = S2.fixed_args
cpu_idle_pct = S2.cpu_idle_pct
thermal_state = S2.thermal_state
busy_processes = S2.busy_processes
window_left = S2.window_left
parse_window = S2.parse_window
local_now = S2.local_now
pid_alive = S2.pid_alive

ROOT: Path = S2.ROOT
RESULTS: Path = S2.RESULTS
BINS: Path = S2.BINS
OUT_DIR = RESULTS / "analysis" / "bisect"
BUILD_RESULTS = RESULTS / "bisect_builds"
INTERLEAVED = RESULTS / "analysis" / "interleaved"
STEP2_LOCK = INTERLEAVED / ".step2.lock"
JUDGE_V11 = INTERLEAVED / "judge_v11_series.csv"
LOCK_NAME = ".step3.lock"
RELEASES_CSV = ROOT / "data" / "releases.csv"
BUILD_SCRIPT = ROOT / "scripts" / "build_bench.sh"
REPO = ROOT / "repo"
GITHUB = "https://github.com/ggml-org/llama.cpp"
ARM64 = ("/usr/bin/arch", "-arm64")
TEST_ARGS = {"pp512": ("-p", "512", "-n", "0"), "tg128": ("-p", "0", "-n", "128")}
TEST_TOKENS = {"pp512": 512, "tg128": 128}
ROLES = ("lo", "mid", "hi")
JUDGED = ("old", "new", "intermediate", "effect_lost", "run_failed")
PR_RE = re.compile(r"\(#(\d+)\)")
LABEL_RE = re.compile(r"[\w.-]+")
STEPS_FIELDS = ["step", "level", "lo", "mid", "hi", "n_candidates", "mid_pos", "mid_commit", "build", "n_lo", "n_mid",
                "n_hi", "ts_lo", "ts_mid", "ts_hi", "d", "d_over_ref", "f", "verdict", "decision", "note",
                "fixed_equivalent", "finished_at_utc"]
BUILDS_FIELDS = ["tag", "commit", "ok", "status", "seconds", "reason", "finished_at_utc"]
RUNS_FIELDS = ["step", "level", "round", "pos", "role", "tag", "model", "backend", "test", "exit_code", "wall_s",
               "load1_before", "idle_pct_before", "thermal_state_before", "waited_s", "settled", "started_at_utc",
               "finished_at_utc", "ok",
               "median_ts", "json_file", "log_file", "env", "cmd"]
SUMMARY_FIELDS = ["event_id", "series", "lo0", "hi0", "direction", "ref_lr", "ref_source", "status", "pause_reason",
                  "note", "lo", "hi", "level", "measured_steps", "builds", "intermediate", "outside", "n_commits",
                  "prs", "updated_at_utc"]
STATUS_TEXT = {"located": "search ended at adjacent points", "effect_lost": "the effect was lost",
               "stopped_max_builds": "build budget used up",
               "stopped_unbuildable": "all remaining candidates failed to build",
               "endpoint_unbuildable": "an endpoint cannot be built", "run_failed": "an endpoint failed to run",
               "incomplete": "incomplete, can be resumed"}

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- small helpers


def utc_now() -> str:
    """Current UTC time as ``YYYY-MM-DDTHH:MM:SSZ``."""
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pct(lr: float) -> str:
    """A log ratio as a signed percentage, e.g. 0.575 -> '+77.8%'."""
    return f"{math.expm1(lr):+.1%}" if math.isfinite(lr) else "n/a"


def to_float(text: Any) -> float:
    """Parse a CSV cell as float; NaN when empty or malformed."""
    try:
        return float(text) if text not in (None, "") else math.nan
    except (TypeError, ValueError):
        return math.nan


def read_rows(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    """Rows of a CSV/TSV file with a header (empty when the file is missing).

    Args:
        path: File.
        delimiter: Field separator.

    Returns:
        One dict per row.
    """
    if not path.is_file():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def append_row(path: Path, fields: list[str], row: dict[str, Any], delimiter: str) -> None:
    """Append one row to a CSV/TSV file, writing the header first when the file is new.

    Args:
        path: File.
        fields: Column order.
        row: Values (missing keys are written empty).
        delimiter: Field separator.
    """
    new = not path.is_file()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter=delimiter, extrasaction="ignore")
        if new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})


def read_json(path: Path) -> dict[str, Any]:
    """A JSON object from a file, {} when it is missing or unreadable."""
    try:
        obj = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return obj if isinstance(obj, dict) else {}


def lock_owner(path: Path) -> int:
    """pid stored in a lock file if that process is alive, else 0."""
    try:
        pid = int(path.read_text().strip() or 0)
    except (OSError, ValueError):
        return 0
    return pid if pid > 0 and pid_alive(pid) else 0


# --------------------------------------------------------------------------- releases and candidates


@dataclass(frozen=True)
class Point:
    """A buildable source state.

    Attributes:
        name: ``b<N>`` for a release tag, ``c<12 hex>`` for a first-parent commit; also the
            ``bins/`` directory name and the build_bench.sh argument.
        commit: Full commit id.
        key: Sort key: (build number of the release at or before it, commit position after it).
        date: Commit date (UTC) for releases.
        commits_since_prev: Commits since the previous release tag (releases.csv).
    """

    name: str
    commit: str
    key: tuple[int, int]
    date: str = ""
    commits_since_prev: int = 0

    @property
    def is_commit(self) -> bool:
        """True for a commit point, False for a release tag."""
        return self.name.startswith("c")


def load_releases(path: Path = RELEASES_CSV) -> list[Point]:
    """Release tags of data/releases.csv, ordered by build number.

    Args:
        path: releases.csv.

    Returns:
        One Point per tag.
    """
    points = [Point(r["tag"], r["commit"], (int(r["build_number"]), 0), r["commit_date_utc"],
                    int(r["commits_since_prev"] or 0)) for r in read_rows(path)]
    return sorted(points, key=lambda p: p.key)


def median_order(n: int) -> list[int]:
    """Indices 0..n-1 by distance from the median position; ties left first (left/right alternating).

    Args:
        n: Number of candidates.

    Returns:
        The order in which candidates are tried as mid.
    """
    center = (n - 1) / 2
    return sorted(range(n), key=lambda i: (abs(i - center), i))


# --------------------------------------------------------------------------- targets


@dataclass
class Target:
    """One confirmed series to bisect.

    Attributes:
        event_id: Event label (E49, or <lo>-<hi> for an ad-hoc pair).
        lo: Older release tag (effect absent).
        hi: Newer release tag (effect present).
        model: Model name.
        backend: metal or cpu.
        test: pp512 or tg128.
        sign: Expected sign of ln(hi / lo): +1 up, -1 down.
        ref_lr: Reference magnitude |ln(hi / lo)| (None if unknown).
        ref_source: Where ref_lr comes from.
        snr: Significance of the step-2 confirmation (ordering only).
    """

    event_id: str
    lo: str
    hi: str
    model: str
    backend: str
    test: str
    sign: int
    ref_lr: float | None
    ref_source: str
    snr: float = 0.0

    @property
    def series(self) -> str:
        """'model/backend/test'."""
        return f"{self.model}/{self.backend}/{self.test}"

    @property
    def label(self) -> str:
        """State directory name '<event>_<model>_<backend>_<test>'."""
        return f"{self.event_id}_{self.model}_{self.backend}_{self.test}"

    @property
    def direction(self) -> str:
        """'up' or 'down'."""
        return "up" if self.sign > 0 else "down"


def step2_rows(event_id: str | None, rule: str) -> list[dict[str, str]]:
    """Series rows of the step-2 judgment.

    Args:
        event_id: Event (None = all events).
        rule: 'v1' = ``interleaved/<event>_*/summary.csv`` written by step2_interleaved.py;
            'v11' = ``interleaved/judge_v11_series.csv`` written by step2b_judge.py.

    Returns:
        Rows with at least event_id, tag_a, tag_b, series, verdict, fixed_lr.
    """
    if rule == "v11":
        rows = read_rows(JUDGE_V11)
        return [r for r in rows if event_id is None or r.get("event_id") == event_id]
    rows: list[dict[str, str]] = []
    for path in sorted(INTERLEAVED.glob(f"{event_id}_*/summary.csv" if event_id else "*/summary.csv")):
        rows += read_rows(path)
    return rows


def step2_reference(lo: str, hi: str, series: str, rule: str) -> float | None:
    """Signed fixed-phase ln ratio of a step-2 C verdict for this tag pair and series.

    Args:
        lo: Older tag.
        hi: Newer tag.
        series: 'model/backend/test'.
        rule: 'v1' or 'v11' (see step2_rows).

    Returns:
        The ln ratio, or None when no such C verdict exists.
    """
    for r in step2_rows(None, rule):
        if (r.get("tag_a"), r.get("tag_b"), r.get("series"), r.get("verdict")) == (lo, hi, series, "C"):
            lr = to_float(r.get("fixed_lr"))
            if math.isfinite(lr):
                return lr
    return None


def step1_series(lo: str, hi: str, model: str, backend: str, test: str) -> tuple[str, float] | None:
    """Event id and campaign ln ratio of this series in candidate_events.csv (read only).

    Args:
        lo: Older tag of the series pair.
        hi: Newer tag of the series pair.
        model: Model name.
        backend: metal or cpu.
        test: pp512 or tg128.

    Returns:
        (event_id, log_ratio), or None when the series is not listed.
    """
    for row in read_rows(S2.EVENTS_CSV):
        try:
            series = json.loads(row.get("series_json") or "[]")
        except json.JSONDecodeError:
            continue
        for s in series:
            if (s.get("tag_old"), s.get("tag_new"), s.get("model"), s.get("backend"), s.get("test")) == \
                    (lo, hi, model, backend, test):
                return row["event_id"], float(s["log_ratio"])
    return None


def event_for_pair(lo: str, hi: str) -> str:
    """Event id of candidate_events.csv whose interval is exactly (lo, hi), '' if none."""
    for row in read_rows(S2.EVENTS_CSV):
        if row.get("tag_old") == lo and row.get("tag_new") == hi:
            return row["event_id"]
    return ""


def target_from_cli(ns: argparse.Namespace, by_name: dict[str, Point]) -> Target:
    """The target given by --lo/--hi/--model/--backend/--test/--direction.

    Args:
        ns: Parsed arguments.
        by_name: Release tags by name.

    Returns:
        The target; its reference magnitude comes from --ref-lr, else step 2, else step 1.

    Raises:
        ValueError: On missing or inconsistent arguments.
    """
    missing = [f"--{o}" for o in ("lo", "hi", "model", "backend", "test", "direction") if getattr(ns, o) is None]
    if missing:
        raise ValueError(f"give --from-step2 EVENT or all of --lo --hi --model --backend --test --direction "
                         f"(missing: {' '.join(missing)})")
    for tag in (ns.lo, ns.hi):
        if tag not in by_name:
            raise ValueError(f"{tag} is not a release tag of {RELEASES_CSV}")
    if by_name[ns.lo].key >= by_name[ns.hi].key:
        raise ValueError(f"--lo {ns.lo} must be older than --hi {ns.hi}")
    sign = 1 if ns.direction == "up" else -1
    series = f"{ns.model}/{ns.backend}/{ns.test}"
    s1 = step1_series(ns.lo, ns.hi, ns.model, ns.backend, ns.test)
    s2 = step2_reference(ns.lo, ns.hi, series, ns.step2_rule)
    event_id = ns.event_id or (s1[0] if s1 else "") or event_for_pair(ns.lo, ns.hi) or f"{ns.lo}-{ns.hi}"
    if ns.ref_lr is not None:
        ref, source = abs(ns.ref_lr), "--ref-lr"
    elif s2 is not None:
        ref, source = abs(s2), f"step 2 fixed phase ({ns.step2_rule})"
    elif s1 is not None:
        ref, source = abs(s1[1]), "step 1 campaign (no step-2 C verdict found)"
    else:
        ref, source = None, "none"
    for lr, what in ((s2, "step 2"), (s1[1] if s1 else None, "step 1")):
        if lr is not None and (lr > 0) != (sign > 0):
            logger.warning("%s %s->%s: %s measured %s but --direction is %s", series, ns.lo, ns.hi, what, pct(lr),
                           ns.direction)
    return Target(event_id, ns.lo, ns.hi, ns.model, ns.backend, ns.test, sign, ref, source)


def targets_from_step2(ns: argparse.Namespace, by_name: dict[str, Point]) -> list[Target]:
    """Every series of an event that step 2 judged C, most significant first.

    Args:
        ns: Parsed arguments (from_step2, step2_rule, series, ref_lr).
        by_name: Release tags by name.

    Returns:
        Targets.

    Raises:
        LookupError: When the step-2 result is missing, has no C series, or --series matches none.
    """
    rows = step2_rows(ns.from_step2, ns.step2_rule)
    if not rows:
        where = JUDGE_V11 if ns.step2_rule == "v11" else INTERLEAVED / f"{ns.from_step2}_*" / "summary.csv"
        raise LookupError(f"no step-2 result for {ns.from_step2} ({where} not found or without this event); "
                          "run step 2 first, or give --lo/--hi/--model/--backend/--test/--direction")
    chosen = [r for r in rows if r.get("verdict") == "C"]
    if not chosen:
        listed = ", ".join(f"{r.get('series')}:{r.get('verdict')}" for r in rows if r.get("listed") in ("1", "True"))
        raise LookupError(f"{ns.from_step2}: no series judged C by step 2 ({listed or 'no listed series'})")
    targets = []
    for r in chosen:
        model, backend, test = r["series"].split("/")
        lr = to_float(r.get("fixed_lr"))
        if not math.isfinite(lr) or lr == 0:
            raise LookupError(f"{ns.from_step2} {r['series']}: fixed_lr missing in the step-2 result")
        for tag in (r["tag_a"], r["tag_b"]):
            if tag not in by_name:
                raise LookupError(f"{tag} is not a release tag of {RELEASES_CSV}")
        z, tau = to_float(r.get("fixed_z")), to_float(r.get("fixed_tau"))
        snr = abs(z) if math.isfinite(z) else (abs(lr) / tau if tau > 0 else 0.0)
        ref, source = (abs(ns.ref_lr), "--ref-lr") if ns.ref_lr is not None else \
            (abs(lr), f"step 2 fixed phase ({ns.step2_rule})")
        targets.append(Target(ns.from_step2, r["tag_a"], r["tag_b"], model, backend, test, 1 if lr > 0 else -1,
                              ref, source, snr))
    if ns.series:
        targets = [t for t in targets if t.series in ns.series]
        if not targets:
            raise LookupError(f"--series {','.join(ns.series)} matches none of the C series of {ns.from_step2}")
    return sorted(targets, key=lambda t: -t.snr)


def select_targets(ns: argparse.Namespace, releases: list[Point]) -> list[Target]:
    """Targets from --from-step2 or from the command line.

    Args:
        ns: Parsed arguments.
        releases: Release tags.

    Returns:
        Targets in processing order.

    Raises:
        LookupError: See targets_from_step2.
        ValueError: See target_from_cli.
    """
    by_name = {p.name: p for p in releases}
    if ns.from_step2:
        return targets_from_step2(ns, by_name)
    return [target_from_cli(ns, by_name)]


# --------------------------------------------------------------------------- run planning


@dataclass
class RunSpec:
    """One llama-bench process of a bisection step.

    Attributes:
        step: Step number (1-based).
        level: 'release' or 'commit'.
        rnd: Round (1-based).
        pos: Position inside the round (1-3).
        role: 'lo', 'mid' or 'hi'; 'warmup' for the unused run before a step (v1.2).
        point: The binary's source state.
        model: Model name.
        backend: metal or cpu.
        test: pp512 or tg128.
        argv: Full command.
        env: Extra environment variables.
        json_path: stdout (llama-bench JSON).
        log_path: stderr.
        est_s: Estimated wall time in seconds.
    """

    step: int
    level: str
    rnd: int
    pos: int
    role: str
    point: Point
    model: str
    backend: str
    test: str
    argv: list[str]
    env: dict[str, str]
    json_path: Path
    log_path: Path
    est_s: float


def reps_for(model: str, ns: argparse.Namespace) -> int:
    """llama-bench -r: --reps for mistral-7b, --reps-small for the two small models."""
    return ns.reps_small if model in S2.SMALL_MODELS else ns.reps


def round_roles(rnd: int) -> tuple[str, ...]:
    """Run order of one round: lo, mid, hi in odd rounds, hi, mid, lo in even rounds."""
    return ROLES if rnd % 2 == 1 else ROLES[::-1]


def _release_alias(caps: Caps, point: Point) -> Caps:
    """Caps whose tag fixed_args can read as a build number (a commit uses its base release)."""
    return replace(caps, tag=f"b{point.key[0]}") if point.is_commit else caps


def aligned_args(caps: dict[str, Caps], points: dict[str, Point], backend: str,
                 ns: argparse.Namespace) -> tuple[dict[str, list[str]], list[str], bool]:
    """Step 2's fixed configuration for the three binaries of a step.

    fixed_args adds an option to one side only when that binary lists it, so the arguments of a
    binary do not depend on its partner; the pairs (lo, mid), (mid, hi), (lo, hi) give each
    binary's arguments and every omission note.

    Args:
        caps: Role -> Caps.
        points: Role -> Point.
        backend: metal or cpu.
        ns: Parsed arguments (threads, batch, ubatch).

    Returns:
        (role -> arguments, omission notes, equivalent).
    """
    threads = {"metal": ns.threads_metal, "cpu": ns.threads_cpu}
    alias = {role: _release_alias(caps[role], points[role]) for role in ROLES}
    args: dict[str, list[str]] = {}
    notes: list[str] = []
    equivalent = True
    for a, b in (("lo", "mid"), ("mid", "hi"), ("lo", "hi")):
        args_a, args_b, pair_notes, eq = fixed_args(alias[a], alias[b], backend, threads, ns.batch, ns.ubatch)
        args.setdefault(a, args_a)
        args.setdefault(b, args_b)
        equivalent = equivalent and eq
        for note in pair_notes:
            side, _, rest = note.partition("=")
            role = a if side == "A" else b
            text = f"{role} {points[role].name}: {rest.partition(': ')[2] or rest}"
            if text not in notes:
                notes.append(text)
    return args, notes, equivalent


def run_estimate(target: Target, ns: argparse.Namespace) -> float:
    """Estimated wall time of one run, from the campaign throughput at the original endpoints.

    Args:
        target: Target.
        ns: Parsed arguments.

    Returns:
        Seconds (load ~10 s + (reps + warm-up) x tokens / slower endpoint's rate); 120 if unknown.
    """
    rates = [S2.campaign_mean(tag, target.model, target.backend, target.test) for tag in (target.lo, target.hi)]
    rates = [r for r in rates if r > 0]
    if not rates:
        return 120.0
    reps = reps_for(target.model, ns)
    per_rep = TEST_TOKENS[target.test] / min(rates)
    return 10.0 + per_rep * (reps + 1 if target.test.startswith("pp") else reps)


def plan_runs(step: int, level: str, points: dict[str, Point], caps: dict[str, Caps], target: Target,
              ns: argparse.Namespace, out: Path, est: float) -> tuple[list[RunSpec], list[str], bool]:
    """All runs of one step in execution order.

    Args:
        step: Step number.
        level: 'release' or 'commit'.
        points: Role -> Point.
        caps: Role -> Caps.
        target: Target.
        ns: Parsed arguments.
        out: Series directory.
        est: Estimated seconds per run.

    Returns:
        (runs, omission notes, equivalent).
    """
    args, notes, equivalent = aligned_args(caps, points, target.backend, ns)
    model_file = S2.MODELS_DIR / S2.MODEL_FILES[target.model]
    base = ["-m", str(model_file), *TEST_ARGS[target.test], "-r", str(reps_for(target.model, ns)), "-o", "json"]
    specs = []
    for rnd in range(1, ns.rounds + 1):
        for pos, role in enumerate(round_roles(rnd), 1):
            point, c = points[role], caps[role]
            stem = f"s{step:02d}_r{rnd}_{role}_{point.name}"
            env = {"GGML_METAL_PATH_RESOURCES": c.metal_resources} if c.metal_resources else {}
            specs.append(RunSpec(step, level, rnd, pos, role, point, target.model, target.backend, target.test,
                                 [*ARM64, str(c.binary), *base, *args[role]], env, out / f"{stem}.json",
                                 out / f"{stem}.log", est))
    return specs, notes, equivalent


def run_row(spec: RunSpec) -> dict[str, Any]:
    """The runs.tsv fields that come from the plan."""
    return {"step": spec.step, "level": spec.level, "round": spec.rnd, "pos": spec.pos, "role": spec.role,
            "tag": spec.point.name, "model": spec.model, "backend": spec.backend, "test": spec.test,
            "cmd": shlex.join(spec.argv), "env": " ".join(f"{k}={v}" for k, v in spec.env.items()),
            "json_file": spec.json_path.name, "log_file": spec.log_path.name}


# --------------------------------------------------------------------------- judgment


def run_level(path: Path, test: str) -> float | None:
    """ln(median samples_ts) of one run.

    Args:
        path: llama-bench JSON file.
        test: pp512 or tg128.

    Returns:
        The value, or None when the file has no result for the test.
    """
    stats = S2.test_samples(S2.load_bench_json(path)).get(test)
    if stats is None:
        return None
    samples = [x for x in stats[1] if x > 0] or ([stats[0]] if stats[0] > 0 else [])
    return math.log(statistics.median(samples)) if samples else None


@dataclass
class Decision:
    """Judgment of one step.

    Attributes:
        verdict: old, new, intermediate or effect_lost.
        decision: 'lo=mid', 'hi=mid' or 'stop'.
        f: (L_mid - L_lo) / (L_hi - L_lo); NaN for effect_lost.
        d: L_hi - L_lo.
        note: Extra remark ('mid outside [lo, hi]', or why the effect is lost).
    """

    verdict: str
    decision: str
    f: float
    d: float
    note: str = ""


def decide(levels: dict[str, float], sign: int, ref: float, ns: argparse.Namespace) -> Decision:
    """Apply the step-3 rule to the side means of one step.

    Args:
        levels: Role -> mean ln throughput.
        sign: Expected sign of L_hi - L_lo.
        ref: Reference magnitude |ln ratio|.
        ns: Parsed arguments (f_old, f_new, lost_frac).

    Returns:
        The decision.
    """
    d = levels["hi"] - levels["lo"]
    need = ns.lost_frac * ref
    if sign * d <= 0 or abs(d) < need:
        return Decision("effect_lost", "stop", math.nan, d,
                        f"L_hi-L_lo = {d:+.4f} ({pct(d)}); needs sign {'+' if sign > 0 else '-'} and "
                        f"|.| >= {need:.4f} ({ns.lost_frac:g} x reference {ref:.4f})")
    f = (levels["mid"] - levels["lo"]) / d
    note = "mid outside [lo, hi]" if f < -ns.f_old or f > 2 - ns.f_new else ""
    if f <= ns.f_old:
        return Decision("old", "lo=mid", f, d, note)
    if f >= ns.f_new:
        return Decision("new", "hi=mid", f, d, note)
    return Decision("intermediate", "lo=mid" if f < 0.5 else "hi=mid", f, d, note)


# --------------------------------------------------------------------------- side effects


@dataclass
class BuildOutcome:
    """Result of one build attempt.

    Attributes:
        ok: Binary usable (built, commit verified, arm64).
        status: build_bench.sh status (built, build_failed, download_failed, ...).
        seconds: Wall time.
        reason: Failure reason.
    """

    ok: bool
    status: str
    seconds: float
    reason: str = ""


@dataclass
class Control:
    """Stop flag and running child process, shared with the signal handler.

    Attributes:
        stop: A stop was requested.
        building: A build is running (it is left to finish).
        child: The running llama-bench process.
        first_run: No run or build happened yet in this process (no cooldown before the first run).
    """

    stop: bool = False
    building: bool = False
    child: subprocess.Popen[Any] | None = None
    first_run: bool = True


class GitError(RuntimeError):
    """A git command on the local clone failed."""


class Hooks:
    """Side effects of a bisection; RealHooks talks to the machine, the unit tests use fakes."""

    def have_binary(self, point: Point) -> bool:
        """Whether ``bins/<point>/llama-bench`` exists."""
        raise NotImplementedError

    def known_build_failure(self, point: Point) -> str:
        """Status of an earlier failed build of this point ('' if none)."""
        raise NotImplementedError

    def build(self, point: Point, log_dir: Path) -> BuildOutcome:
        """Build llama-bench for a point.

        Args:
            point: Release tag or commit.
            log_dir: Directory for the build log.

        Returns:
            The outcome.
        """
        raise NotImplementedError

    def caps(self, point: Point) -> Caps:
        """Options accepted by the point's binary."""
        raise NotImplementedError

    def measure(self, spec: RunSpec) -> dict[str, Any]:
        """Run one llama-bench process.

        Args:
            spec: The run.

        Returns:
            runs.tsv fields: exit_code, wall_s, load1_before, idle_pct_before, waited_s, settled,
            started_at_utc, finished_at_utc, ok, median_ts.  exit_code 'skipped-window',
            'skipped-signal' or 'not-quiet' means the run did not start.
        """
        raise NotImplementedError

    def time_left(self) -> float:
        """Seconds left in the measurement window."""
        raise NotImplementedError

    def sleep(self, seconds: float) -> None:
        """Cooldown pause (interrupted by a stop request)."""
        raise NotImplementedError

    def first_parent_commits(self, base: str, hi: str) -> list[str]:
        """Full ids of the first-parent commits in (base, hi], oldest first.

        Args:
            base: Commit id.
            hi: Commit id.

        Returns:
            Commit ids.

        Raises:
            GitError: When git fails.
        """
        raise NotImplementedError

    def commit_log(self, lo: Point, hi: Point) -> list[dict[str, Any]]:
        """Commits lo..hi (newest first) with date, author, subject, PR, changed files.

        Args:
            lo: Older point.
            hi: Newer point.

        Returns:
            One dict per commit.

        Raises:
            GitError: When git fails.
        """
        raise NotImplementedError


def binary_path(point: Point) -> Path:
    """``bins/<point>/llama-bench``."""
    return BINS / point.name / "llama-bench"


def build_failure_status(point: Point) -> str:
    """'build_failed' when results/bisect_builds/<point>/status.json records a failed build, else ''."""
    status = read_json(BUILD_RESULTS / point.name / "status.json").get("status", "")
    return status if status == "build_failed" else ""


def build_command(point: Point, ns: argparse.Namespace) -> tuple[dict[str, str], list[str]]:
    """Environment overrides and argv of the build-only call of build_bench.sh.

    RESULTS_ROOT is results/bisect_builds: build_bench.sh starts with ``rm -rf
    $RESULTS_ROOT/<tag>`` and must never be pointed at results/ itself.  It runs as arm64 because
    the uv Python is x86_64 (Rosetta) and its children would otherwise compile for the wrong host.

    Args:
        point: Release tag or commit.
        ns: Parsed arguments (build_timeout).

    Returns:
        (environment overrides, argv).
    """
    env = {"BUILD_ONLY": "1", "RESULTS_ROOT": str(BUILD_RESULTS), "BUILD_TIMEOUT_S": str(int(ns.build_timeout))}
    return env, [*ARM64, "/bin/bash", str(BUILD_SCRIPT), point.name]


def is_arm64(binary: Path) -> bool:
    """Whether lipo lists arm64 for a binary (True when lipo cannot tell)."""
    try:
        res = subprocess.run(["/usr/bin/lipo", "-archs", str(binary)], capture_output=True, text=True, timeout=30,
                             check=False)
    except (OSError, subprocess.TimeoutExpired):
        return True
    return res.returncode != 0 or "arm64" in res.stdout.split()


def interruptible_sleep(seconds: float, ctl: Control) -> None:
    """Sleep in 1-second slices until done or a stop is requested."""
    end = time.monotonic() + seconds
    while not ctl.stop:
        left = end - time.monotonic()
        if left <= 0:
            return
        time.sleep(min(1.0, left))


def wait_quiet(ns: argparse.Namespace, ctl: Control) -> tuple[float, bool, float, int]:
    """Wait until top's CPU idle >= --idle-min, the thermal state <= --thermal-max and no other
    llama-bench/llama-server/llama-cli runs (step 2's criterion; the machine is a fanless MacBook Air).

    Args:
        ns: Parsed arguments (idle_min, thermal_max, quiet_wait_max).
        ctl: Control (a stop request ends the wait).

    Returns:
        (seconds waited, quiet reached, last idle percent, last thermal state; -1 if unknown).
    """
    t0 = time.monotonic()
    idle, therm = -1.0, -1
    while not ctl.stop:
        idle = cpu_idle_pct()
        therm = thermal_state()
        busy = busy_processes()
        waited = time.monotonic() - t0
        therm_ok = ns.thermal_max < 0 or therm < 0 or therm <= ns.thermal_max
        if idle >= ns.idle_min and therm_ok and not busy:
            return waited, True, idle, therm
        if waited >= ns.quiet_wait_max:
            logger.warning("not quiet after %.0f s (idle %.1f%%, thermal %d, busy: %s)", waited, idle, therm,
                           ", ".join(busy) or "none")
            return waited, False, idle, therm
        interruptible_sleep(10.0, ctl)
    return time.monotonic() - t0, False, idle, therm


def execute_run(spec: RunSpec, ns: argparse.Namespace, ctl: Control,
                time_left: Callable[[], float]) -> dict[str, Any]:
    """Wait for a quiet machine, then run one llama-bench process into its JSON/log files.

    Args:
        spec: The run.
        ns: Parsed arguments.
        ctl: Control (child process registration, stop flag).
        time_left: Callable returning the seconds left in the window.

    Returns:
        runs.tsv fields (see Hooks.measure).
    """
    waited, settled, idle, therm = wait_quiet(ns, ctl)
    load1 = os.getloadavg()[0]
    row: dict[str, Any] = {"load1_before": f"{load1:.2f}", "idle_pct_before": f"{idle:.1f}",
                           "thermal_state_before": therm, "waited_s": f"{waited:.0f}", "settled": int(settled),
                           "ok": 0}
    if ctl.stop:
        return {**row, "exit_code": "skipped-signal"}
    if not settled and ns.on_quiet_timeout == "stop":
        return {**row, "exit_code": "not-quiet"}
    if time_left() < spec.est_s + 30:
        return {**row, "exit_code": "skipped-window"}
    started = utc_now()
    t0 = time.monotonic()
    with spec.json_path.open("w") as jf, spec.log_path.open("w") as lf:
        proc = subprocess.Popen(spec.argv, stdout=jf, stderr=lf, env={**os.environ, **spec.env},
                                start_new_session=True)
        ctl.child = proc
        try:
            rc: Any = proc.wait(timeout=ns.timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            rc = 124
        finally:
            ctl.child = None
    level = run_level(spec.json_path, spec.test)
    return {**row, "exit_code": rc, "wall_s": f"{time.monotonic() - t0:.3f}", "started_at_utc": started,
            "finished_at_utc": utc_now(), "ok": int(level is not None),
            "median_ts": f"{math.exp(level):.4f}" if level is not None else ""}


def git(args: list[str]) -> str:
    """Run git on the local blob-less clone without any network access.

    Args:
        args: git arguments after ``git -C repo``.

    Returns:
        stdout.

    Raises:
        GitError: When git fails or cannot be started.
    """
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"}
    try:
        res = subprocess.run(["git", "-c", "protocol.allow=never", "-C", str(REPO), *args], capture_output=True,
                             text=True, env=env, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitError(f"git {' '.join(args[:2])}: {exc}") from exc
    if res.returncode != 0:
        raise GitError(f"git {' '.join(args[:2])}: {res.stderr.strip()[:300]}")
    return res.stdout


def read_commit_log(lo_commit: str, hi_commit: str) -> list[dict[str, Any]]:
    """Commits lo..hi from repo/ (newest first): id, date, author, subject, PR, changed files.

    Changed paths need only trees, which the blob-less clone has; if that fails the log is read
    without them.

    Args:
        lo_commit: Older commit id.
        hi_commit: Newer commit id.

    Returns:
        One dict per commit.

    Raises:
        GitError: When git log fails.
    """
    fmt = "%x1e%H%x1f%cI%x1f%an%x1f%s"
    try:
        out = git(["log", "--no-renames", "--name-only", f"--format={fmt}", f"{lo_commit}..{hi_commit}"])
    except GitError as exc:
        logger.warning("changed files unavailable (%s); reading the log without them", exc)
        out = git(["log", f"--format={fmt}", f"{lo_commit}..{hi_commit}"])
    commits = []
    for chunk in out.split("\x1e")[1:]:
        head, _, rest = chunk.partition("\n")
        sha, date, author, subject = ([*head.split("\x1f", 3), "", "", ""])[:4]
        files = [line.strip() for line in rest.splitlines() if line.strip()]
        found = PR_RE.findall(subject)
        pr = found[-1] if found else ""
        commits.append({"sha": sha, "date": date, "author": author, "subject": subject, "pr": pr,
                        "pr_url": f"{GITHUB}/pull/{pr}" if pr else "", "commit_url": f"{GITHUB}/commit/{sha}",
                        "n_files": len(files), "files": files[:40]})
    return commits


class RealHooks(Hooks):
    """Hooks that build, run llama-bench and read git on this machine."""

    def __init__(self, ns: argparse.Namespace, ctl: Control, win: tuple[dt.time, dt.time]) -> None:
        """Keep the arguments, the control block and the window.

        Args:
            ns: Parsed arguments.
            ctl: Control shared with the signal handler.
            win: Measurement window.
        """
        self.ns = ns
        self.ctl = ctl
        self.win = win
        self._caps: dict[str, Caps] = {}

    def have_binary(self, point: Point) -> bool:
        """See Hooks."""
        return binary_path(point).is_file()

    def known_build_failure(self, point: Point) -> str:
        """See Hooks."""
        return build_failure_status(point)

    def build(self, point: Point, log_dir: Path) -> BuildOutcome:
        """See Hooks; the build runs to completion even when a stop is requested meanwhile."""
        if BUILD_RESULTS.resolve() == RESULTS.resolve():
            raise RuntimeError("build results must not go to results/ itself")
        extra, argv = build_command(point, self.ns)
        t0 = time.monotonic()
        self.ctl.building = True
        try:
            with (log_dir / f"build_{point.name}.log").open("w") as fh:
                rc = subprocess.run(argv, stdout=fh, stderr=subprocess.STDOUT, env={**os.environ, **extra},
                                    check=False, start_new_session=True,
                                    timeout=2 * self.ns.build_timeout + 900).returncode
        except subprocess.TimeoutExpired:
            rc = 124
        finally:
            self.ctl.building = False
        seconds = time.monotonic() - t0
        status = read_json(BUILD_RESULTS / point.name / "status.json")
        st = str(status.get("status") or f"no status.json (rc {rc})")
        reason = str(status.get("failure_reason") or "")
        ok = st == "built" and self.have_binary(point)
        if ok and not status.get("commit_verified"):
            ok, reason = False, (f"tarball commit {status.get('tarball_commit')!r} does not match "
                                 f"{status.get('release_commit')!r}")
        if ok and not is_arm64(binary_path(point)):
            ok, reason = False, "binary is not arm64"
        return BuildOutcome(ok, st, seconds, reason)

    def caps(self, point: Point) -> Caps:
        """See Hooks; reads the saved --help of campaign tags, runs --help for bisection builds."""
        if point.name not in self._caps:
            caps = binary_caps(point.name, allow_exec=True)
            if not caps.flags:
                return caps
            self._caps[point.name] = caps
        return self._caps[point.name]

    def measure(self, spec: RunSpec) -> dict[str, Any]:
        """See Hooks."""
        return execute_run(spec, self.ns, self.ctl, self.time_left)

    def time_left(self) -> float:
        """See Hooks."""
        return window_left(local_now(), self.win)

    def sleep(self, seconds: float) -> None:
        """See Hooks."""
        interruptible_sleep(seconds, self.ctl)

    def first_parent_commits(self, base: str, hi: str) -> list[str]:
        """See Hooks."""
        return git(["rev-list", "--reverse", "--first-parent", f"{base}..{hi}"]).split()

    def commit_log(self, lo: Point, hi: Point) -> list[dict[str, Any]]:
        """See Hooks."""
        return read_commit_log(lo.commit, hi.commit)


class DryHooks(Hooks):
    """Read-only stand-ins for --dry-run: file checks only; no process is started."""

    def __init__(self) -> None:
        """Start with no git request recorded."""
        self.git_needed = False

    def have_binary(self, point: Point) -> bool:
        """See Hooks."""
        return binary_path(point).is_file()

    def known_build_failure(self, point: Point) -> str:
        """See Hooks."""
        return build_failure_status(point)

    def caps(self, point: Point) -> Caps:
        """Saved --help text only (results/<tag>/llama-bench_help.txt); --help is never executed."""
        return binary_caps(point.name, allow_exec=False)

    def first_parent_commits(self, base: str, hi: str) -> list[str]:
        """Not available without git: records the need and returns nothing."""
        self.git_needed = True
        return []

    def time_left(self) -> float:
        """Unlimited (nothing runs)."""
        return math.inf


# --------------------------------------------------------------------------- bisection


class _Pause(Exception):
    """Stop the series for now (window, signal, busy machine); the state is kept for resuming."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


class _Stop(Exception):
    """End the series with a final status."""

    def __init__(self, status: str, note: str = "") -> None:
        super().__init__(status)
        self.status = status
        self.note = note


@dataclass
class Progress:
    """Bisection state rebuilt from steps.csv and builds.tsv.

    Attributes:
        lo: Current older point.
        hi: Current newer point.
        skipped: Candidates that failed to build or to run.
        stopped: Final verdict recorded by a 'stop' row ('' while running).
        stop_note: Note of that row.
        measured: Steps measured so far (the next step number is measured + 1).
        intermediate: Steps judged intermediate.
        outside: Steps whose mid fell outside [lo, hi].
        builds: Build attempts of this series.
        built_ok: Points this series built successfully.
    """

    lo: Point
    hi: Point
    skipped: set[str] = field(default_factory=set)
    stopped: str = ""
    stop_note: str = ""
    measured: int = 0
    intermediate: int = 0
    outside: int = 0
    builds: int = 0
    built_ok: set[str] = field(default_factory=set)


class SeriesState:
    """Files of one series (``<out>/<event>_<model>_<backend>_<test>/``)."""

    def __init__(self, path: Path) -> None:
        """Name the files; nothing is created here.

        Args:
            path: Series directory.
        """
        self.path = path
        self.target_json = path / "target.json"
        self.steps_csv = path / "steps.csv"
        self.builds_tsv = path / "builds.tsv"
        self.runs_tsv = path / "runs.tsv"
        self.result_json = path / "result.json"
        self.log_md = path / "log.md"

    def steps(self) -> list[dict[str, str]]:
        """Rows of steps.csv."""
        return read_rows(self.steps_csv)

    def builds(self) -> list[dict[str, str]]:
        """Rows of builds.tsv."""
        return read_rows(self.builds_tsv, "\t")

    def append_step(self, row: dict[str, Any]) -> None:
        """Append a row to steps.csv."""
        append_row(self.steps_csv, STEPS_FIELDS, row, ",")

    def append_build(self, row: dict[str, Any]) -> None:
        """Append a row to builds.tsv."""
        append_row(self.builds_tsv, BUILDS_FIELDS, row, "\t")

    def append_run(self, row: dict[str, Any]) -> None:
        """Append a row to runs.tsv."""
        append_row(self.runs_tsv, RUNS_FIELDS, row, "\t")

    def log(self, *lines: str) -> None:
        """Append lines to log.md."""
        with self.log_md.open("a") as fh:
            fh.write("\n".join(lines) + "\n")


class Bisector:
    """Bisection of one series; all state lives in its directory, so a new start resumes it."""

    def __init__(self, target: Target, ns: argparse.Namespace, releases: list[Point], hooks: Hooks, ctl: Control,
                 out_root: Path) -> None:
        """Set up without touching the file system.

        Args:
            target: The series.
            ns: Parsed arguments.
            releases: Release tags (sorted).
            hooks: Side effects.
            ctl: Control block.
            out_root: Parent of the series directory.
        """
        self.target = target
        self.ns = ns
        self.releases = releases
        self.points: dict[str, Point] = {p.name: p for p in releases}
        self.hooks = hooks
        self.ctl = ctl
        self.state = SeriesState(out_root / target.label)
        self.est = run_estimate(target, ns)
        self.started = False
        self.logged_steps: set[int] = set()

    # ------------------------------------------------------------------ state

    def check_target(self) -> None:
        """Create the series directory and target.json, or check that a resumed one matches.

        Raises:
            ValueError: When the directory holds a different series or direction.
        """
        t, st = self.target, self.state
        st.path.mkdir(parents=True, exist_ok=True)
        ident = {"event_id": t.event_id, "lo": t.lo, "hi": t.hi, "model": t.model, "backend": t.backend,
                 "test": t.test, "sign": t.sign}
        saved = read_json(st.target_json)
        if saved:
            diff = {k: (saved.get(k), v) for k, v in ident.items() if saved.get(k) != v}
            if diff:
                raise ValueError(f"{st.path} holds another bisection (saved vs now: {diff}); use another --out "
                                 "or remove that directory")
            if t.ref_source != "--ref-lr" and saved.get("ref_lr") is not None:
                # keep the reference the bisection started with
                t.ref_lr, t.ref_source = float(saved["ref_lr"]), str(saved.get("ref_source", ""))
                return
        st.target_json.write_text(json.dumps({**ident, "series": t.series, "direction": t.direction,
                                              "ref_lr": t.ref_lr, "ref_source": t.ref_source,
                                              "written_at_utc": utc_now()}, indent=1) + "\n")

    def replay(self) -> Progress:
        """Rebuild the progress from steps.csv and builds.tsv (reads files only).

        Returns:
            Progress.

        Raises:
            ValueError: When steps.csv names an unknown point.
        """
        prog = Progress(self.points[self.target.lo], self.points[self.target.hi])
        for row in self.state.steps():
            name = row["mid"]
            if name not in self.points:
                self.commit_candidates(prog.lo, prog.hi)
            mid = self.points.get(name)
            if mid is None:
                raise ValueError(f"{self.state.steps_csv}: unknown point {name}")
            decision, verdict = row["decision"], row["verdict"]
            if decision == "skip":
                prog.skipped.add(name)
            elif decision == "lo=mid":
                prog.lo = mid
            elif decision == "hi=mid":
                prog.hi = mid
            elif decision == "stop":
                prog.stopped, prog.stop_note = verdict, row.get("note", "")
            prog.measured += verdict in JUDGED
            prog.intermediate += verdict == "intermediate"
            prog.outside += row.get("note", "").startswith("mid outside")
        builds = self.state.builds()
        prog.builds = len(builds)
        prog.built_ok = {b["tag"] for b in builds if b.get("ok") == "1"}
        return prog

    def candidates(self, prog: Progress) -> tuple[str, list[Point]]:
        """Points strictly between lo and hi: releases, else (with --commit-level) commits.

        Args:
            prog: Progress.

        Returns:
            (level, candidates in order).
        """
        rel = [p for p in self.releases if prog.lo.key < p.key < prog.hi.key]
        if rel or not self.ns.commit_level:
            return "release", rel
        return "commit", self.commit_candidates(prog.lo, prog.hi)

    def commit_candidates(self, lo: Point, hi: Point) -> list[Point]:
        """First-parent commits strictly between lo and hi as points ``c<sha12>``.

        Positions count from the release at or before lo, so every call numbers a commit alike.

        Args:
            lo: Older point.
            hi: Newer point.

        Returns:
            Commit points in order.
        """
        base = max((r for r in self.releases if r.key <= lo.key), key=lambda r: r.key)
        found = []
        for i, sha in enumerate(self.hooks.first_parent_commits(base.commit, hi.commit), 1):
            name = f"c{sha[:12]}"
            found.append(self.points.setdefault(name, Point(name, sha, (base.key[0], i))))
        return [p for p in found if lo.key < p.key < hi.key and p.commit != hi.commit]

    # ------------------------------------------------------------------ run

    def run(self) -> dict[str, Any]:
        """Run or resume the bisection of this series.

        Returns:
            The result (also written to result.json).

        Raises:
            ValueError: On a mismatching state directory or a missing reference magnitude.
        """
        if self.target.ref_lr is None:
            raise ValueError(f"{self.target.series}: no reference magnitude (pass --ref-lr)")
        self.check_target()
        prog = self.replay()
        try:
            if prog.stopped:
                raise _Stop(prog.stopped, prog.stop_note)
            while True:
                self.one_step(prog)
        except _Pause as pause:
            return self.pause(prog, pause.reason, pause.detail)
        except _Stop as stop:
            return self.finish(prog, stop.status, stop.note)

    def one_step(self, prog: Progress) -> None:
        """Pick a mid, make sure the three binaries exist, measure, judge and narrow.

        Args:
            prog: Progress (updated in place).

        Raises:
            _Pause: Window end, stop request or busy machine.
            _Stop: The series is finished.
        """
        if self.ctl.stop:
            raise _Pause("signal")
        level, cands = self.candidates(prog)
        if not cands:
            raise _Stop("located")
        self.ensure_endpoints(prog, level)
        mid, idx, how = self.pick_mid(prog, level, cands)
        step = prog.measured + 1
        info = {"n_candidates": len(cands), "mid_pos": idx + 1, "build": how}
        levels, counts, equivalent = self.measure_step(prog, level, mid, step, info)
        self.begin()
        prog.measured += 1
        row: dict[str, Any] = {"step": step, "level": level, "lo": prog.lo.name, "mid": mid.name, "hi": prog.hi.name,
                               "mid_commit": mid.commit, "fixed_equivalent": int(equivalent),
                               "finished_at_utc": utc_now(), **info, **{f"n_{r}": counts[r] for r in ROLES},
                               **{f"ts_{r}": f"{math.exp(levels[r]):.4f}" for r in ROLES if r in levels}}
        if "lo" not in levels or "hi" not in levels:
            note = "no valid run for " + ", ".join(r for r in ("lo", "hi") if r not in levels)
            self.state.append_step({**row, "verdict": "run_failed", "decision": "stop", "note": note})
            self.state.log(f"  - Result: no valid run at an endpoint ({note}); stopping")
            raise _Stop("run_failed", note)
        if "mid" not in levels:
            prog.skipped.add(mid.name)
            self.state.append_step({**row, "verdict": "run_failed", "decision": "skip", "note": "no valid run for mid"})
            self.state.log(f"  - Result: mid {mid.name} has no valid run (it failed to load or run); skipping this candidate")
            return
        ref = float(self.target.ref_lr or 0.0)
        dec = decide(levels, self.target.sign, ref, self.ns)
        row.update(d=f"{dec.d:.5f}", d_over_ref=f"{self.target.sign * dec.d / ref:.3f}",
                   f="" if math.isnan(dec.f) else f"{dec.f:.4f}", verdict=dec.verdict, decision=dec.decision,
                   note=dec.note)
        self.state.append_step(row)
        self.state.log(judgement_line(row, dec, counts))
        prog.intermediate += dec.verdict == "intermediate"
        prog.outside += dec.note.startswith("mid outside")
        if dec.decision == "stop":
            raise _Stop("effect_lost", dec.note)
        if dec.decision == "lo=mid":
            prog.lo = mid
        else:
            prog.hi = mid

    def ensure_endpoints(self, prog: Progress, level: str) -> None:
        """Build lo/hi when their binaries are missing (normally they exist).

        Args:
            prog: Progress.
            level: Current level (for the steps.csv row).

        Raises:
            _Stop: Budget used up or an endpoint cannot be built.
            _Pause: See try_build.
        """
        for point in (prog.lo, prog.hi):
            if self.hooks.have_binary(point):
                continue
            if prog.builds >= self.ns.max_builds:
                raise _Stop("stopped_max_builds", f"endpoint {point.name} has no binary")
            outcome = self.try_build(prog, point)
            if not outcome.ok:
                note = f"endpoint {point.name}: {outcome.status} {outcome.reason}".strip()
                self.state.append_step({"step": prog.measured + 1, "level": level, "lo": prog.lo.name,
                                        "mid": point.name, "hi": prog.hi.name, "mid_commit": point.commit,
                                        "build": outcome.status, "verdict": "endpoint_unbuildable",
                                        "decision": "stop", "note": note, "finished_at_utc": utc_now()})
                raise _Stop("endpoint_unbuildable", note)

    def pick_mid(self, prog: Progress, level: str, cands: list[Point]) -> tuple[Point, int, str]:
        """The median candidate with a binary, building it if needed; failures move outwards.

        Args:
            prog: Progress.
            level: Current level.
            cands: Candidates.

        Returns:
            (mid, index in cands, 'reused' | 'built').

        Raises:
            _Stop: Budget used up, or no candidate can be built.
            _Pause: See try_build.
        """
        for idx in median_order(len(cands)):
            point = cands[idx]
            if point.name in prog.skipped:
                continue
            if self.hooks.have_binary(point):
                return point, idx, "built" if point.name in prog.built_ok else "reused"
            base = {"step": prog.measured + 1, "level": level, "lo": prog.lo.name, "mid": point.name,
                    "hi": prog.hi.name, "n_candidates": len(cands), "mid_pos": idx + 1, "mid_commit": point.commit,
                    "verdict": "build_failed", "decision": "skip"}
            known = self.hooks.known_build_failure(point)
            if known:
                prog.skipped.add(point.name)
                self.state.append_step({**base, "build": f"known {known}", "finished_at_utc": utc_now(),
                                        "note": "failed in an earlier build (results/bisect_builds); not rebuilt"})
                self.begin()
                self.state.log(f"- Candidate {point.name} failed to build earlier (results/bisect_builds); not rebuilt, skipped")
                continue
            if prog.builds >= self.ns.max_builds:
                if level == "commit" and not (prog.lo.is_commit or prog.hi.is_commit):
                    raise _Stop("located", "release level done; commit level skipped: build budget used up")
                raise _Stop("stopped_max_builds", f"{prog.builds} builds used; next mid {point.name} needs a build")
            outcome = self.try_build(prog, point)
            if outcome.ok:
                return point, idx, "built"
            prog.skipped.add(point.name)
            self.state.append_step({**base, "build": outcome.status, "finished_at_utc": utc_now(),
                                    "note": outcome.reason[:300]})
        raise _Stop("stopped_unbuildable", f"no buildable candidate left between {prog.lo.name} and {prog.hi.name}")

    def try_build(self, prog: Progress, point: Point) -> BuildOutcome:
        """Build one point (counted) if the window still has --build-est seconds.

        Args:
            prog: Progress (builds incremented).
            point: Release tag or commit.

        Returns:
            The outcome (also appended to builds.tsv and log.md).

        Raises:
            _Pause: Stop requested or too little window left.
        """
        if self.ctl.stop:
            raise _Pause("signal")
        left = self.hooks.time_left()
        if left < self.ns.build_est:
            raise _Pause("window", f"{left:.0f} s left < --build-est {self.ns.build_est:.0f} s before building "
                                   f"{point.name}")
        self.begin()
        self.state.log(f"- Build {point.name} ({point.commit[:12]}) started at {local_now():%H:%M:%S}")
        outcome = self.hooks.build(point, self.state.path)
        prog.builds += 1
        if outcome.ok:
            prog.built_ok.add(point.name)
        self.ctl.first_run = False  # cool down before the next run
        self.state.append_build({"tag": point.name, "commit": point.commit, "ok": int(outcome.ok),
                                 "status": outcome.status, "seconds": f"{outcome.seconds:.1f}",
                                 "reason": outcome.reason[:300], "finished_at_utc": utc_now()})
        verdict = "Succeeded" if outcome.ok else f"Failed ({outcome.status}{': ' + outcome.reason if outcome.reason else ''})"
        self.state.log(f"  - {verdict} in {outcome.seconds:.0f} s; builds of this series: {prog.builds}/{self.ns.max_builds}"
                       + ("" if outcome.ok else "; skipping this candidate and trying the next one nearest the median"))
        return outcome

    def measure_step(self, prog: Progress, level: str, mid: Point, step: int,
                     info: dict[str, Any]) -> tuple[dict[str, float], dict[str, int], bool]:
        """Run (or resume) the interleaved runs of one step and average them per side.

        Args:
            prog: Progress.
            level: Current level.
            mid: Mid point.
            step: Step number.
            info: n_candidates, mid_pos, build (for log.md).

        Returns:
            (role -> mean ln throughput for roles with a valid run, role -> valid runs, equivalent).

        Raises:
            _Pause: Window end, stop request or busy machine.
        """
        points = {"lo": prog.lo, "mid": mid, "hi": prog.hi}
        caps = {role: self.hooks.caps(p) for role, p in points.items()}
        specs, notes, equivalent = plan_runs(step, level, points, caps, self.target, self.ns, self.state.path,
                                             self.est)
        todo = [s for s in specs if run_level(s.json_path, s.test) is None]
        if todo and step not in self.logged_steps:
            self.begin()
            self.logged_steps.add(step)
            self.state.log(*step_header(step, level, points, specs, notes, equivalent, info, len(specs) - len(todo)))
        if todo and self.ns.warmup:
            # v1.2: one run of the first pending command before the step's runs (again after a resume),
            # so that the first measured run does not carry the build or pause before it; it is written to
            # warmup_*.json and recorded in runs.tsv with role 'warmup', and no level uses it.
            first = todo[0]
            todo = [replace(first, rnd=0, pos=0, role="warmup",
                            json_path=first.json_path.with_name(f"warmup_{first.json_path.name}"),
                            log_path=first.log_path.with_name(f"warmup_{first.log_path.name}")), *todo]
        for spec in todo:
            if self.ctl.stop:
                raise _Pause("signal")
            need = spec.est_s + (0.0 if self.ctl.first_run else self.ns.cooldown) + 30.0
            left = self.hooks.time_left()
            if left < need:
                raise _Pause("window", f"{left:.0f} s left < {need:.0f} s needed for {spec.json_path.stem}")
            if not self.ctl.first_run:
                self.hooks.sleep(self.ns.cooldown)
                if self.ctl.stop:
                    raise _Pause("signal")
            self.ctl.first_run = False
            row = {**run_row(spec), **self.hooks.measure(spec)}
            self.state.append_run(row)
            logger.info("%s %s rc=%s wall=%ss idle=%s%% waited=%ss median=%s", self.target.label,
                        spec.json_path.stem, row.get("exit_code"), row.get("wall_s", ""), row.get("idle_pct_before"),
                        row.get("waited_s"), row.get("median_ts", ""))
            code = row.get("exit_code")
            if code == "skipped-signal":
                raise _Pause("signal")
            if code == "skipped-window":
                raise _Pause("window", f"after waiting for a quiet machine, too little window left for "
                                       f"{spec.json_path.stem}")
            if code == "not-quiet":
                raise _Pause("busy", "machine not quiet within --quiet-wait-max (--on-quiet-timeout stop)")
        levels: dict[str, float] = {}
        counts: dict[str, int] = {}
        for role in ROLES:
            values = [v for s in specs if s.role == role and (v := run_level(s.json_path, s.test)) is not None]
            counts[role] = len(values)
            if values:
                levels[role] = statistics.fmean(values)
        return levels, counts, equivalent

    def begin(self) -> None:
        """Write the log.md header of this invocation once, before its first build or run."""
        if self.started:
            return
        self.started = True
        t, ns = self.target, self.ns
        if not self.state.log_md.is_file():
            ref = float(t.ref_lr or 0.0)
            self.state.log(
                f"# Step 3 bisection: {t.event_id} {t.series} ({t.lo} → {t.hi}, "
                f"expected {'increase' if t.sign > 0 else 'decrease'})", "",
                f"Reference magnitude |ln ratio| = {ref:.4f} ({pct(t.sign * ref)}, source: {t.ref_source}); every step "
                f"requires L_hi − L_lo to have the expected sign and to reach at least {ns.lost_frac:g} times the "
                "reference magnitude, otherwise the series stops as effect_lost.",
                f"Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ {ns.f_old:g} looks old (lo = mid), f ≥ {ns.f_new:g} "
                "looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), "
                "continued by f < 0.5 / ≥ 0.5.", "")
        self.state.log(f"## Run {local_now():%Y-%m-%d %H:%M %Z} (pid {os.getpid()})", "",
                       f"Parameters: rounds {ns.rounds}, -r {reps_for(t.model, ns)}, cooldown {ns.cooldown:g} s, "
                       f"idle share ≥ {ns.idle_min:g}%, thermal state ≤ {ns.thermal_max} (wait at most "
                       f"{ns.quiet_wait_max:g} s), max-builds {ns.max_builds}, commit-level "
                       f"{'on' if ns.commit_level else 'off'}, window {ns.window}.", "")

    # ------------------------------------------------------------------ results

    def result(self, prog: Progress, status: str, note: str) -> dict[str, Any]:
        """Result dictionary without the commit list.

        Args:
            prog: Progress.
            status: Final or 'incomplete'.
            note: Remark.

        Returns:
            The result.
        """
        t = self.target
        between = [p for p in self.releases if prog.lo.key < p.key <= prog.hi.key]
        return {"event_id": t.event_id, "series": t.series, "label": t.label, "lo0": t.lo, "hi0": t.hi,
                "direction": t.direction, "ref_lr": t.ref_lr, "ref_source": t.ref_source, "status": status,
                "pause_reason": "", "note": note, "lo": prog.lo.name, "hi": prog.hi.name,
                "lo_commit": prog.lo.commit, "hi_commit": prog.hi.commit,
                "level": "commit" if prog.lo.is_commit or prog.hi.is_commit else "release",
                "measured_steps": prog.measured, "builds": prog.builds, "intermediate": prog.intermediate,
                "outside": prog.outside, "skipped": sorted(prog.skipped),
                "commits_est": sum(p.commits_since_prev for p in between) if not prog.lo.is_commit else None,
                "n_commits": None, "prs": [], "commits": [], "git_error": "", "updated_at_utc": utc_now()}

    def pause(self, prog: Progress, reason: str, detail: str) -> dict[str, Any]:
        """Record an interruption (resumable).

        Args:
            prog: Progress.
            reason: window, signal or busy.
            detail: Explanation.

        Returns:
            The result with status 'incomplete'.
        """
        res = self.result(prog, "incomplete", detail)
        res["pause_reason"] = reason
        self.state.result_json.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
        if self.started:
            text = {"window": "not enough time left in the window", "signal": "stop signal received",
                    "busy": "the machine stayed busy"}.get(reason, reason)
            self.state.log(f"- Paused ({text}{': ' + detail if detail else ''}): current interval {prog.lo.name} → "
                           f"{prog.hi.name}, steps measured: {prog.measured}, builds: {prog.builds}; run the same "
                           "command again to resume.", "")
        return res

    def finish(self, prog: Progress, status: str, note: str) -> dict[str, Any]:
        """Write the final result with the commits lo..hi; log.md gets the conclusion once.

        Args:
            prog: Progress.
            status: Final status.
            note: Remark.

        Returns:
            The result.
        """
        res = self.result(prog, status, note)
        try:
            commits = self.hooks.commit_log(prog.lo, prog.hi)
        except GitError as exc:
            commits = []
            res["git_error"] = str(exc)
        res.update(commits=commits, n_commits=len(commits) if not res["git_error"] else None,
                   prs=[c["pr"] for c in commits if c.get("pr")])
        previous = read_json(self.state.result_json)
        self.state.result_json.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
        if any(previous.get(k) != res[k] for k in ("status", "lo", "hi", "measured_steps", "builds")):
            self.begin()
            self.state.log(*conclusion_lines(res))
        return res


# --------------------------------------------------------------------------- log.md text


def step_header(step: int, level: str, points: dict[str, Point], specs: list[RunSpec], notes: list[str],
                equivalent: bool, info: dict[str, Any], done: int) -> list[str]:
    """log.md lines that open a step.

    Args:
        step: Step number.
        level: release or commit.
        points: Role -> Point.
        specs: Planned runs.
        notes: Omission notes of the fixed configuration.
        equivalent: Configuration fully aligned.
        info: n_candidates, mid_pos, build.
        done: Runs already complete (resumed step).

    Returns:
        Lines.
    """
    args = {s.role: shlex.join(s.argv[s.argv.index("json") + 1:]) for s in specs}
    how = {"reused": "existing binary reused", "built": "built in this run"}.get(info["build"], info["build"])
    lines = [(f"- Step {step} ({level} level, {info['n_candidates']} candidates, mid is number {info['mid_pos']}, {how}): "
              f"lo {points['lo'].name} / mid {points['mid'].name} / hi {points['hi'].name}"),
             f"  - Fixed configuration ({'fully aligned' if equivalent else 'not fully aligned'}): " +
             "; ".join(f"{r} `{args[r]}`" for r in ROLES if r in args)]
    lines += [f"  - Omission: {n}" for n in notes]
    lines.append(f"  - Runs planned: {len(specs)}" + (f" (resumed: {done} already done)" if done else ""))
    return lines


def judgement_line(row: dict[str, Any], dec: Decision, counts: dict[str, int]) -> str:
    """log.md line with the judgment of a step.

    Args:
        row: steps.csv row.
        dec: Decision.
        counts: Valid runs per role.

    Returns:
        One line.
    """
    ts = " / ".join(f"{r} {float(row[f'ts_{r}']):.1f}" for r in ROLES)
    head = (f"  - Result: {ts} t/s (valid runs {counts['lo']}/{counts['mid']}/{counts['hi']}); "
            f"L_hi − L_lo = {pct(dec.d)} ({float(row['d_over_ref']):.2f} times the reference)")
    if dec.verdict == "effect_lost":
        return f"{head} → **effect_lost**: wrong sign or below half the reference magnitude, stopping ({dec.note})"
    mid = row["mid"]
    if dec.verdict == "old":
        text = f"looks old, lo = {mid}"
    elif dec.verdict == "new":
        text = f"looks new, hi = {mid}"
    else:
        side = "lo" if dec.decision == "lo=mid" else "hi"
        text = (f"**intermediate** (possibly two stacked changes), treated as f {'<' if side == 'lo' else '≥'} 0.5, "
                f"{side} = {mid}")
    extra = "; mid lies outside the range from lo to hi (not monotonic?)" if dec.note.startswith("mid outside") else ""
    return f"{head}; f = {dec.f:.2f} → {text}{extra}"


def conclusion_lines(res: dict[str, Any], max_rows: int = 60) -> list[str]:
    """log.md conclusion block.

    Args:
        res: Final result.
        max_rows: Commits listed (all of them are in result.json).

    Returns:
        Lines.
    """
    status = STATUS_TEXT.get(res["status"], res["status"])
    n_commits = res["n_commits"] if res["n_commits"] is not None else "?"
    lines = ["", f"## Conclusion ({local_now():%Y-%m-%d %H:%M %Z})", "",
             f"Status: **{res['status']}** ({status}){'; ' + res['note'] if res['note'] else ''}.",
             (f"Boundary: {res['lo']} → {res['hi']} ({res['level']} level, commits between: {n_commits}); "
              f"steps measured: {res['measured_steps']}, builds: {res['builds']}, intermediate steps: "
              f"{res['intermediate']}, skipped candidates: {', '.join(res['skipped']) or 'none'}.")]
    if res["git_error"]:
        lines.append(f"Reading the commits failed: {res['git_error']}")
    if res["commits"]:
        lines += ["", "| Commit | Date | Subject | PR | Files changed |", "|---|---|---|---|---|"]
        for c in res["commits"][:max_rows]:
            pr = f"[#{c['pr']}]({c['pr_url']})" if c["pr"] else ""
            subject = c["subject"].replace("|", "\\|")
            lines.append(f"| [{c['sha'][:10]}]({c['commit_url']}) | {c['date'][:10]} | {subject} | {pr} | "
                         f"{c['n_files']} |")
        if len(res["commits"]) > max_rows:
            lines.append(f"(another {len(res['commits']) - max_rows} commits are in result.json)")
    lines.append("")
    return lines


# --------------------------------------------------------------------------- summary


def write_global_summary(out: Path) -> list[dict[str, Any]]:
    """summary.csv and summary.md over every series directory with a result.json.

    Args:
        out: Bisection root (results/analysis/bisect).

    Returns:
        Summary rows.
    """
    rows = []
    for path in sorted(out.glob("*/result.json")):
        res = read_json(path)
        if not res:
            continue
        row = {k: res.get(k, "") for k in SUMMARY_FIELDS}
        row["prs"] = " ".join(f"#{p}" for p in res.get("prs", []))
        row["n_commits"] = "" if res.get("n_commits") is None else res["n_commits"]
        rows.append(row)
    if not rows:
        logger.info("no bisection results under %s yet", out)
        return rows
    with (out / "summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Step 3: summary of the bisections", "",
             ("Generated by `scripts/analysis/step3_bisect.py`. The process of each series is in log.md of its "
              "subdirectory."), "",
             ("| Event | Series | Original interval | Direction (reference magnitude) | Status | Boundary | Level | "
              "Steps/builds | intermediate | Commits | PR |"),
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ref = to_float(r["ref_lr"])
        sign = 1 if r["direction"] == "up" else -1
        status = r["status"] + (f" ({r['pause_reason']})" if r["pause_reason"] else "")
        lines.append(f"| {r['event_id']} | {r['series']} | {r['lo0']}→{r['hi0']} | {r['direction']} ({pct(sign * ref)}) | "
                     f"{status} | {r['lo']}→{r['hi']} | {r['level']} | {r['measured_steps']}/{r['builds']} | "
                     f"{r['intermediate']} | {r['n_commits']} | {r['prs']} |")
    lines += ["", ("Decision: every step interleaves lo, mid and hi; f = (L_mid − L_lo)/(L_hi − L_lo), f ≤ 0.35 looks "
                   "old, ≥ 0.65 looks new, and values in between are intermediate; when L_hi − L_lo has the wrong sign or "
                   "is below half the reference magnitude, the series stops as effect_lost. located = lo and hi are "
                   "adjacent releases (or commits); stopped_max_builds = the interval when the build budget ran out."), ""]
    (out / "summary.md").write_text("\n".join(lines))
    logger.info("summary: %d series -> %s", len(rows), out / "summary.md")
    return rows


# --------------------------------------------------------------------------- dry run


def provisional_caps(point: Point, known: list[tuple[Point, Caps]]) -> tuple[Caps, str]:
    """Caps for a binary whose --help is not available without running it.

    Args:
        point: The point without saved help text.
        known: (point, caps) with saved help text.

    Returns:
        (caps copied from the nearest known binary, name of that binary or '').
    """
    usable = [(p, c) for p, c in known if c.flags]
    if not usable:
        return Caps(point.name, binary_path(point), metal_resources=str(BINS / point.name)), ""
    near, caps = min(usable, key=lambda pc: abs(pc[0].key[0] - point.key[0]))
    return replace(caps, tag=point.name, binary=binary_path(point), metal_resources=str(BINS / point.name),
                   help_source=f"provisional: {near.name}"), near.name


def print_dry_run(targets: list[Target], ns: argparse.Namespace, releases: list[Point],
                  win: tuple[dt.time, dt.time]) -> None:
    """Print the plan of the next step of every target; nothing is executed or written.

    Args:
        targets: Targets.
        ns: Parsed arguments.
        releases: Release tags.
        win: Measurement window.
    """
    now = local_now()
    left = window_left(now, win)
    inside = f"inside, {left / 60:.0f} min left" if left > 0 else "OUTSIDE -> a real run would refuse to start (exit 3)"
    print(f"# step 3 dry run at {now:%Y-%m-%d %H:%M:%S %Z}; window {ns.window}: {inside}")
    running = [f"{name} pid {pid}" for name, path in (("campaign", S2.CAMPAIGN_LOCK), ("step 2", STEP2_LOCK),
                                                      ("step 3", ns.out / LOCK_NAME)) if (pid := lock_owner(path))]
    print(f"# lock holders: {', '.join(running) or 'none'} (a real run refuses while the campaign or step 2 runs)")
    gate = f"idle >= {ns.idle_min:g}%" + (f", thermal state <= {ns.thermal_max}" if ns.thermal_max >= 0 else "")
    print(f"# runs wait for {gate} and no other llama-bench/llama-server/llama-cli, at most {ns.quiet_wait_max:g} s")
    print("# nothing below is executed and no file is written")
    for target in targets:
        print_target_plan(target, ns, releases)


def print_target_plan(t: Target, ns: argparse.Namespace, releases: list[Point]) -> None:
    """Dry-run plan of one series (see print_dry_run).

    Args:
        t: Target.
        ns: Parsed arguments.
        releases: Release tags.
    """
    hooks = DryHooks()
    bis = Bisector(t, ns, releases, hooks, Control(), ns.out)
    ref = f"{t.ref_lr:.4f} ({pct(t.sign * t.ref_lr)})" if t.ref_lr is not None else "UNKNOWN (pass --ref-lr)"
    print(f"\n== {t.label}: {t.series} {t.lo} -> {t.hi}, expected {t.direction}; reference |ln ratio| {ref} "
          f"from {t.ref_source}")
    resumed = bis.state.steps_csv.is_file()
    prog = bis.replay()
    state = (f"resume: {prog.measured} steps measured, {prog.builds} builds, interval {prog.lo.name} -> "
             f"{prog.hi.name}") if resumed else "new"
    print(f"   state: {bis.state.path} ({state})")
    if prog.stopped:
        print(f"   finished earlier with {prog.stopped}; nothing to do")
        return
    level, cands = bis.candidates(prog)
    if hooks.git_needed:
        print("   commit level: the commit list needs git (not run in a dry run)")
    commits = sum(p.commits_since_prev for p in releases if prog.lo.key < p.key <= prog.hi.key)
    span = f" ({cands[0].name} .. {cands[-1].name})" if cands else ""
    print(f"   candidates: {len(cands)} {'release tags' if level == 'release' else 'commits'} strictly between "
          f"{prog.lo.name} and {prog.hi.name}{span}; "
          f"{commits} commits in {prog.lo.name}..{prog.hi.name} (releases.csv)")
    if not cands:
        print("   no candidate left: a real run writes the result (located) and the commit list")
        return
    print(f"   at most {math.ceil(math.log2(len(cands) + 1))} more steps to an adjacent pair; builds used "
          f"{prog.builds}/{ns.max_builds}")
    order = [i for i in median_order(len(cands)) if cands[i].name not in prog.skipped]
    mid = cands[order[0]]
    have = hooks.have_binary(mid)
    print(f"   next mid: {mid.name} (candidate {order[0] + 1} of {len(cands)}, commit {mid.commit[:12]}); "
          f"bins/{mid.name}/llama-bench {'present -> reused' if have else 'missing -> build'}")
    for p in (prog.lo, prog.hi):
        if not hooks.have_binary(p):
            print(f"   endpoint {p.name} has no binary -> it is built first (counts as a build)")
    if not have:
        extra, argv = build_command(mid, ns)
        env = " ".join(f"{k}={v}" for k, v in extra.items())
        print(f"     build: cd {ROOT} && {env} {shlex.join(argv)} > {bis.state.path / f'build_{mid.name}.log'} 2>&1")
        print(f"     if that build fails, next tried: {', '.join(cands[i].name for i in order[1:5])}")
    for what, lo, hi in (("looks old (lo = mid)", mid, prog.hi), ("looks new (hi = mid)", prog.lo, mid)):
        sub = [p for p in cands if lo.key < p.key < hi.key and p.name not in prog.skipped]
        nxt = sub[median_order(len(sub))[0]] if sub else None
        state = "" if nxt is None else (" (binary present)" if hooks.have_binary(nxt) else " (needs a build)")
        print(f"   following mid if {mid.name} {what}: {nxt.name if nxt else 'none: adjacent pair reached'}{state}")
    reusable = [p.name for p in cands if hooks.have_binary(p)]
    print(f"   binaries already in bins/ among the candidates: {', '.join(reusable) or 'none'}")
    points = {"lo": prog.lo, "mid": mid, "hi": prog.hi}
    known = [(p, hooks.caps(p)) for p in points.values()]
    caps: dict[str, Caps] = {}
    for role, (p, c) in zip(ROLES, known, strict=True):
        caps[role] = c
        if not c.flags:
            caps[role], source = provisional_caps(p, known)
            print(f"   {role} {p.name}: no saved --help; options below are provisional"
                  + (f" (copied from {source}'s help); the real run reads its own --help after the build"
                     if source else " (none known)"))
    specs, notes, equivalent = plan_runs(prog.measured + 1, level, points, caps, t, ns, bis.state.path, bis.est)
    print(f"   fixed configuration (step 2's binary_caps + fixed_args): {'aligned' if equivalent else 'NOT aligned'}")
    for s in specs[:3]:
        print(f"     {s.role:3s} {s.point.name}: {shlex.join(s.argv[s.argv.index('json') + 1:])}")
    for n in notes:
        print(f"     note: {n}")
    print(f"   runs of step {prog.measured + 1} ({ns.rounds} rounds, -r {reps_for(t.model, ns)}, {t.test} only):")
    for s in specs:
        env = " ".join(f"{k}={v}" for k, v in s.env.items())
        print(f"     [r{s.rnd} {s.pos} {s.role:3s}] {env + ' ' if env else ''}{shlex.join(s.argv)} "
              f"> {bis.state.path.name}/{s.json_path.name} 2> {bis.state.path.name}/{s.log_path.name}")
    step_s = len(specs) * bis.est + (len(specs) - 1) * ns.cooldown
    steps = math.ceil(math.log2(len(cands) + 1))
    print(f"   estimate: ~{bis.est:.0f} s per run; one step = {len(specs)} runs + {len(specs) - 1} x {ns.cooldown:g} s "
          f"cooldown ~ {step_s / 60:.1f} min (+ build ~2 min + quiet waits); {steps} steps ~ "
          f"{steps * (step_s + 120) / 3600:.1f} h")


# --------------------------------------------------------------------------- main


def csv_list(text: str) -> list[str]:
    """Comma-separated values."""
    return [x.strip() for x in text.split(",") if x.strip()]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command-line interface.

    Args:
        argv: Arguments (default sys.argv).

    Returns:
        Parsed arguments.
    """
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n", 1)[0])
    ap.add_argument("--from-step2", metavar="EVENT", help="bisect the series step 2 judged C for this event")
    ap.add_argument("--step2-rule", choices=("v1", "v11"), default="v1",
                    help="v1: interleaved/<event>_*/summary.csv (step2_interleaved.py); v11: "
                         "interleaved/judge_v11_series.csv (step2b_judge.py)")
    ap.add_argument("--series", type=csv_list, default=None,
                    help="with --from-step2: only these model/backend/test series (default: every C series)")
    ap.add_argument("--lo", help="older release tag (effect absent)")
    ap.add_argument("--hi", help="newer release tag (effect present)")
    ap.add_argument("--model", choices=sorted(S2.MODEL_FILES))
    ap.add_argument("--backend", choices=("metal", "cpu"))
    ap.add_argument("--test", choices=sorted(TEST_ARGS))
    ap.add_argument("--direction", choices=("up", "down"), help="expected change from lo to hi")
    ap.add_argument("--event-id", help="state directory label (default: the step-1 event of the pair, else <lo>-<hi>)")
    ap.add_argument("--ref-lr", type=float, default=None,
                    help="reference |ln(hi/lo)| (default: step 2's fixed-phase value, else step 1's)")
    ap.add_argument("--rounds", type=int, default=2, help="interleaved rounds per step (lo-mid-hi, hi-mid-lo, ...)")
    ap.add_argument("--max-builds", type=int, default=8, help="build attempts per series (failures count)")
    ap.add_argument("--commit-level", action="store_true",
                    help="after adjacent releases, bisect the first-parent commits between them")
    ap.add_argument("--f-old", type=float, default=0.35, help="f <= this: mid looks old")
    ap.add_argument("--f-new", type=float, default=0.65, help="f >= this: mid looks new")
    ap.add_argument("--lost-frac", type=float, default=0.5,
                    help="effect_lost when |L_hi - L_lo| < this x the reference (or the sign flips)")
    ap.add_argument("--reps", type=int, default=5, help="llama-bench -r for mistral-7b")
    ap.add_argument("--reps-small", type=int, default=10, help="llama-bench -r for tinyllama-1.1b and qwen2.5-1.5b")
    ap.add_argument("--threads-metal", type=int, default=4)
    ap.add_argument("--threads-cpu", type=int, default=8)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--ubatch", type=int, default=512)
    ap.add_argument("--cooldown", type=float, default=20.0, help="seconds between runs (and after a build)")
    ap.add_argument("--idle-min", type=float, default=80.0, help="start a run only at this CPU idle %% or more")
    ap.add_argument("--thermal-max", type=int, default=1,
                    help="start a run only at this macOS thermal state or lower (0 nominal, 1 fair, 2 serious; "
                         "-1 = off), as step 2")
    ap.add_argument("--quiet-wait-max", type=float, default=300.0, help="max seconds to wait for a quiet machine")
    ap.add_argument("--on-quiet-timeout", choices=("proceed", "stop"), default="proceed",
                    help="when the machine stays busy: run anyway (runs.tsv settled=0) or pause")
    ap.add_argument("--window", default="07:00-17:30", help="local-time window for real runs (HH:MM-HH:MM; 00:00-24:00 = no limit)")
    ap.add_argument("--no-warmup", dest="warmup", action="store_false",
                    help="no warm-up run before each step (v1.2 adds one; no statistic uses it)")
    ap.add_argument("--timeout", type=float, default=1800.0, help="per-run limit in seconds")
    ap.add_argument("--build-timeout", type=float, default=1800.0,
                    help="BUILD_TIMEOUT_S for build_bench.sh (configure and build each)")
    ap.add_argument("--build-est", type=float, default=600.0, help="window seconds a build needs before it starts")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--dry-run", action="store_true", help="print the plan and commands only")
    ap.add_argument("--summarize-only", action="store_true", help="rebuild summary.csv/summary.md")
    ns = ap.parse_args(argv)
    if ns.from_step2 and any(getattr(ns, o) is not None for o in ("lo", "hi", "model", "backend", "test", "direction")):
        ap.error("give either --from-step2 or --lo/--hi/--model/--backend/--test/--direction")
    for label in (ns.from_step2, ns.event_id):
        if label is not None and not LABEL_RE.fullmatch(label):
            ap.error(f"bad event label {label!r} (letters, digits, '_', '-', '.')")
    if ns.rounds < 2:
        ap.error("--rounds must be >= 2 (lo-mid-hi and hi-mid-lo)")
    if not 0 < ns.f_old < 0.5 < ns.f_new < 1:
        ap.error("need 0 < --f-old < 0.5 < --f-new < 1")
    if ns.max_builds < 0 or not 0 < ns.lost_frac <= 1:
        ap.error("need --max-builds >= 0 and 0 < --lost-frac <= 1")
    return ns


CTL = Control()


def handle_signal(signum: int, _frame: Any) -> None:
    """Request a stop; kill the running llama-bench process group (a running build may finish)."""
    CTL.stop = True
    child = CTL.child
    if child is not None and child.poll() is None:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(child.pid, signal.SIGTERM)
    logger.warning("signal %s: stopping%s", signum, " after the running build" if CTL.building else "")


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Arguments (default sys.argv).

    Returns:
        Exit code: 0 ok, 2 bad input or missing step-2 result, 3 outside the window, 4 locked.
    """
    ns = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    try:
        win = parse_window(ns.window)
    except ValueError as exc:
        logger.error("%s", exc)
        return 2
    if ns.summarize_only:
        write_global_summary(ns.out)
        return 0
    releases = load_releases()
    try:
        targets = select_targets(ns, releases)
    except (LookupError, ValueError) as exc:
        logger.error("%s", exc)
        return 2
    if ns.dry_run:
        print_dry_run(targets, ns, releases, win)
        return 0
    if window_left(local_now(), win) <= 0:
        logger.error("outside the measurement window %s (local %s): refusing to run. Use --dry-run to inspect the plan.",
                     ns.window, local_now().strftime("%H:%M %Z"))
        return 3
    unknown = [t.series for t in targets if t.ref_lr is None]
    if unknown:
        logger.error("no reference magnitude for %s: pass --ref-lr", ", ".join(unknown))
        return 2
    for name, path in (("campaign", S2.CAMPAIGN_LOCK), ("step 2", STEP2_LOCK)):
        pid = lock_owner(path)
        if pid:
            logger.error("%s is running (pid %d, %s): refusing", name, pid, path)
            return 4
    ns.out.mkdir(parents=True, exist_ok=True)
    lock = ns.out / LOCK_NAME
    other = lock_owner(lock)
    if other and other != os.getpid():
        logger.error("another step3 instance is running (pid %d): refusing", other)
        return 4
    lock.write_text(str(os.getpid()))
    handler = logging.FileHandler(ns.out / "run.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    rc = 0
    try:
        hooks = RealHooks(ns, CTL, win)
        logger.info("start: %d series, window %s", len(targets), ns.window)
        for target in targets:
            if CTL.stop:
                break
            try:
                res = Bisector(target, ns, releases, hooks, CTL, ns.out).run()
            except ValueError as exc:
                logger.error("%s: %s", target.label, exc)
                rc = 2
                continue
            logger.info("%s: %s %s -> %s (%d steps, %d builds)%s", target.label, res["status"], res["lo"], res["hi"],
                        res["measured_steps"], res["builds"], f" [{res['pause_reason']}]" if res["pause_reason"] else "")
            if res["status"] == "incomplete":
                break
        write_global_summary(ns.out)
    finally:
        lock.unlink(missing_ok=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
