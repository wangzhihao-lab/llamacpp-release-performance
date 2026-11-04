#!/usr/bin/env python3
"""Root-cause protocol, step 2: interleaved re-measurement of candidate events.

For every selected event of ``results/analysis/candidate_events.csv`` (step 1) and every
(model, back end) it involves, the already-built binaries ``bins/<tag>/llama-bench`` of
the two sampled tags (A = older, B = newer; taken per series from ``series_json``) are
re-run on this machine in two phases:

* ``fixed``: the same explicit configuration on both sides: threads (metal 4 /
  cpu 8), ``-b 512``, ``-ub 512``, flash attention off, KV cache f16/f16, mmap loading,
  ``--poll 50``, ``-nopo 1`` (cpu), ``--repack 1``, ``-pg 0,0`` (v1.2), each flag only where the binary's
  ``--help`` lists it.  A dropped flag is recorded as an equivalent omission (the old
  binary's only behavior equals the fixed value) or a non-equivalent one (it cannot
  be aligned, e.g. ``--poll`` against a pre-threadpool binary).  Order ABBA-alternating
  (AB, BA, AB; ``--order abab`` for plain ABAB), ``--rounds`` rounds (>= 3), preceded since v1.2
  (2026-10-14) by one warm-up run of side A that no statistic uses (``--no-warmup`` to drop it);
  ``-r --reps`` (5) for mistral-7b, ``-r --reps-small`` (10) for the two small models.
* ``default``: each side exactly as the campaign ran it (its own defaults plus the
  ``extra_args`` recorded in ``results/<tag>/runs.tsv``, ``-r 5``), ``--default-rounds`` rounds.

Every run is its own process (``/usr/bin/arch -arm64 bins/<tag>/llama-bench -p 512
-n 128 -r <reps> -o json ...``).  Before each run the script sleeps ``--cooldown`` seconds
(not before the first), then waits until top's CPU idle is >= ``--idle-min`` (80, the
campaign's criterion), the macOS thermal state is at most ``--thermal-max`` (1 = fair; the
machine is a fanless MacBook Air; probe ``bin/thermal_state`` built from thermal_state.swift)
and no other llama-bench/llama-server/llama-cli process is running, at most
``--load-wait-max`` (300) seconds; load1 is recorded and gates only when
``--load-max`` > 0 (on this Mac load1 exceeded 2 in 98% of the campaign's calls even when
the CPU was 82-97% idle).  It refuses to start outside the
measurement window (local time, ``--window``, default 07:00-17:30) and stops before any run that
would not finish inside it; completed runs are kept and skipped on the next start.

Judgment per series on the log scale, as in step 1 (expected sign = step-1 sign):
fixed: lr = ln(mean_B / mean_A) of the per-run means, tau = max(ln 1.1, 3 x pooled sd of
ln(samples)) over all runs of each side; confirmed if |lr| >= tau, the sign matches and
every round has that sign.  default: the same test on the default runs.
Verdict: C (persists with identical configuration -> implementation or build change),
A (only with the default configurations), noise (neither), reversed (fixed confirms the
opposite sign), incomplete.  Event verdict: C > A > reversed > noise > incomplete.
B (build-option) candidates stay inside the binaries and therefore show up as C;
separating B from C needs a rebuild with equal options (step 3).

Outputs (``results/analysis/interleaved/``): ``<event>_<old>_<new>/`` with plan.json,
runs.tsv, one ``<phase>_r<k>_<A|B>_<tag>_<model>_<backend>.json/.log`` per run,
summary.csv and summary.md; ``summary.csv``/``summary.md`` over all events; run.log.
``--dry-run`` only prints the plan and every command (no process is started, nothing
is written) and works at any time; ``--summarize-only`` rebuilds the summaries.

Real run from the repository root (inside the window, detached):
  nohup uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step2_interleaved.py --classes C,A,B > results/analysis/interleaved_nohup.out 2>&1 &

Run: uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step2_interleaved.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import math
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
BINS = ROOT / "bins"
EVENTS_CSV = RESULTS / "analysis" / "candidate_events.csv"
OUT_DIR = RESULTS / "analysis" / "interleaved"
CAMPAIGN_LOCK = ROOT / "logs" / "campaign.lock" / "pid"
MODELS_DIR = Path(os.environ.get("MODELS_DIR", ROOT / "models"))
MODEL_FILES = {
    "tinyllama-1.1b": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
    "mistral-7b": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "qwen2.5-1.5b": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
}
CLASS_PRIORITY = {"C": 0, "A": 1, "B": 2, "D": 3}
BUSY_PROCS = ("llama-bench", "llama-server", "llama-cli")
TESTS = {"pp512": (512, 0), "tg128": (0, 128)}
RUNS_FIELDS = ["event_id", "phase", "round", "side", "tag", "model", "backend", "cmd", "env", "exit_code",
               "wall_s", "load1_before", "idle_pct_before", "thermal_state_before", "waited_s", "load_settled",
               "started_at_utc", "finished_at_utc", "tests_ok", "json_file", "log_file"]
THERMAL_PROBE = Path(__file__).resolve().parent / "bin" / "thermal_state"  # built from thermal_state.swift
SMALL_MODELS = ("tinyllama-1.1b", "qwen2.5-1.5b")
CAMPAIGN_REPS = 5

logger = logging.getLogger(__name__)
STOP = {"flag": False, "child": None}


# --------------------------------------------------------------------------- small helpers


def parse_window(text: str) -> tuple[dt.time, dt.time]:
    """Parse 'HH:MM-HH:MM' into two times.

    The end may be written 24:00 (midnight); '00:00-24:00' is the whole day, i.e. no limit.

    Args:
        text: Window spec.

    Returns:
        (start, end); start == end means the whole day.

    Raises:
        ValueError: On a malformed spec.
    """
    m = re.fullmatch(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", text.strip())
    if not m:
        raise ValueError(f"bad window {text!r}, expected HH:MM-HH:MM")
    h1, m1, h2, m2 = (int(x) for x in m.groups())
    if (h2, m2) == (24, 0):
        h2 = 0
    return dt.time(h1, m1), dt.time(h2, m2)


def local_now() -> dt.datetime:
    """Current local time, timezone-aware (the window is defined in local time)."""
    return dt.datetime.now().astimezone()


def window_left(now: dt.datetime, win: tuple[dt.time, dt.time]) -> float:
    """Seconds left in the window at ``now``; 0 means outside.

    Args:
        now: Local time (aware or naive).
        win: (start, end); start > end means the window wraps past midnight, start == end
            means the whole day.

    Returns:
        Seconds until the window ends (infinite for the whole day), or 0 when ``now`` is
        outside it.
    """
    start, end = win
    if start == end:
        return math.inf
    t = now.time()
    if start <= end:
        inside = start <= t < end
        end_dt = dt.datetime.combine(now.date(), end, tzinfo=now.tzinfo)
    else:
        inside = t >= start or t < end
        day = now.date() + (dt.timedelta(days=1) if t >= start else dt.timedelta())
        end_dt = dt.datetime.combine(day, end, tzinfo=now.tzinfo)
    return (end_dt - now).total_seconds() if inside else 0.0


def pid_alive(pid: int) -> bool:
    """Whether a process exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def cpu_idle_pct() -> float:
    """CPU idle percentage over a 1-second sample (second sample of ``top``), as build_bench.sh.

    Returns:
        Idle percent, or -1.0 when ``top`` cannot be read.
    """
    try:
        res = subprocess.run(["top", "-l", "2", "-s", "1", "-n", "0"], capture_output=True, text=True, timeout=30,
                             check=False)
    except (OSError, subprocess.TimeoutExpired):
        return -1.0
    vals = re.findall(r"CPU usage:.*?([\d.]+)% idle", res.stdout)
    return float(vals[-1]) if vals else -1.0


def thermal_state() -> int:
    """macOS ProcessInfo.thermalState (0 nominal, 1 fair, 2 serious, 3 critical); -1 if unavailable.

    The machine is a fanless MacBook Air, so sustained load raises the thermal state and the
    system throttles; the value is recorded before every run and gates the start (``--thermal-max``).
    """
    if not THERMAL_PROBE.is_file():
        return -1
    try:
        res = subprocess.run([str(THERMAL_PROBE)], capture_output=True, text=True, timeout=10, check=False)
        return int(res.stdout.strip())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return -1


def busy_processes() -> list[str]:
    """Names of benchmark/engine processes currently running (other than our child)."""
    found = []
    child = STOP["child"]
    for name in BUSY_PROCS:
        try:
            res = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        pids = [int(p) for p in res.stdout.split() if p.isdigit()]
        if child is not None:
            pids = [p for p in pids if p != child.pid]
        if pids:
            found.append(f"{name}({','.join(map(str, pids))})")
    return found


def load_bench_json(path: Path) -> list[dict[str, Any]]:
    """Parse a llama-bench ``-o json`` file, tolerating junk around the array."""
    if not path.is_file():
        return []
    text = path.read_text(errors="replace")
    start = text.find("[")
    if start < 0:
        return []
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return []
    return [r for r in obj if isinstance(r, dict)] if isinstance(obj, list) else []


def test_samples(recs: list[dict[str, Any]]) -> dict[str, tuple[float, list[float]]]:
    """Map 'pp512'/'tg128' -> (avg_ts, samples_ts) from llama-bench JSON records."""
    out: dict[str, tuple[float, list[float]]] = {}
    for r in recs:
        key = next((k for k, (np_, ng) in TESTS.items() if r.get("n_prompt") == np_ and r.get("n_gen") == ng), None)
        if key is None or r.get("avg_ts") is None:
            continue
        samples = r.get("samples_ts")
        if not samples and r.get("samples_ns"):
            tokens = r.get("n_prompt") or r.get("n_gen")
            samples = [tokens * 1e9 / ns for ns in r["samples_ns"] if ns]
        out[key] = (float(r["avg_ts"]), [float(x) for x in samples or []])
    return out


# --------------------------------------------------------------------------- binaries


@dataclass
class Caps:
    """What one llama-bench binary accepts (from its --help).

    Attributes:
        tag: Release tag.
        binary: Path of llama-bench.
        flags: Option strings listed by --help (short and long).
        deprecated: Long options marked DEPRECATED.
        fa_values: Accepted values of --flash-attn ('<0|1>' or '<on|off|auto>'), '' if absent.
        metal_resources: Directory for GGML_METAL_PATH_RESOURCES (bins/<tag>, as the campaign).
        help_source: Where the help text came from.
    """

    tag: str
    binary: Path
    flags: set[str] = field(default_factory=set)
    deprecated: set[str] = field(default_factory=set)
    fa_values: str = ""
    metal_resources: str = ""
    help_source: str = ""

    def has(self, *opts: str) -> bool:
        """True if any of the option strings is supported and not deprecated."""
        return any(o in self.flags and o not in self.deprecated for o in opts)


HELP_OPT = re.compile(r"^\s*(-{1,2}[A-Za-z][\w-]*)(?:\s+(?:N|<[^>]*>))?(?:\s*,\s*(--[\w-]+))?\s*(<[^>]*>)?(.*)$")


def binary_caps(tag: str, allow_exec: bool) -> Caps:
    """Read the capabilities of ``bins/<tag>/llama-bench``.

    Args:
        tag: Release tag.
        allow_exec: Run ``llama-bench --help`` when the saved help text is missing.

    Returns:
        Caps (flags empty if neither source is available).
    """
    binary = BINS / tag / "llama-bench"
    caps = Caps(tag, binary)
    # build_bench.sh exported GGML_METAL_PATH_RESOURCES=<build>/bin for every tag; bins/<tag>
    # is the copy of that directory (old versions load ggml-metal.metal from it).
    caps.metal_resources = str(BINS / tag)
    saved = RESULTS / tag / "llama-bench_help.txt"
    text = ""
    if saved.is_file():
        text, caps.help_source = saved.read_text(errors="replace"), str(saved)
    elif allow_exec and binary.is_file():
        try:
            res = subprocess.run(["/usr/bin/arch", "-arm64", str(binary), "--help"], capture_output=True, text=True,
                                 timeout=60, check=False)
            text, caps.help_source = res.stdout + res.stderr, "llama-bench --help"
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("%s: --help failed: %s", tag, exc)
    for line in text.splitlines():
        m = HELP_OPT.match(line)
        if not m:
            continue
        short, long_, values, rest = m.group(1), m.group(2), m.group(3) or "", m.group(4)
        caps.flags.add(short)
        if long_:
            caps.flags.add(long_)
        if "DEPRECATED" in rest:
            caps.deprecated.update({short, long_} - {None})
        if long_ == "--flash-attn":
            caps.fa_values = values or (re.search(r"<[^>]*>", line).group(0) if re.search(r"<[^>]*>", line) else "")
    return caps


def campaign_args(tag: str, model: str, backend: str) -> tuple[list[str], float]:
    """Back-end arguments and wall time the campaign used for (tag, model, backend, main).

    Args:
        tag: Release tag.
        model: Model name.
        backend: metal or cpu.

    Returns:
        (extra args, wall seconds; 0 if unknown).
    """
    path = RESULTS / tag / "runs.tsv"
    if path.is_file():
        with path.open(newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                if row.get("model") == model and row.get("backend") == backend and row.get("param_set") == "main":
                    try:
                        wall = float(row.get("wall_s") or 0)
                    except ValueError:
                        wall = 0.0
                    return shlex.split(row.get("extra_args", "")), wall
    return (["-ngl", "99"] if backend == "metal" else ["-ngl", "0", "-t", "8"]), 0.0


def fixed_args(a: Caps, b: Caps, backend: str, threads: dict[str, int], batch: int,
               ubatch: int) -> tuple[list[str], list[str], list[str], bool]:
    """Explicit configuration shared by both binaries.

    Args:
        a: Older binary.
        b: Newer binary.
        backend: metal or cpu.
        threads: backend -> thread count.
        batch: n_batch.
        ubatch: n_ubatch.

    Returns:
        (args for A, args for B, notes, equivalent); ``equivalent`` is False when a
        setting could not be aligned between the two binaries.
    """
    notes: list[str] = []
    equivalent = True
    args = {"A": ["-ngl", "99" if backend == "metal" else "0", "-t", str(threads[backend]), "-b", str(batch)],
            "B": ["-ngl", "99" if backend == "metal" else "0", "-t", str(threads[backend]), "-b", str(batch)]}
    sides = {"A": a, "B": b}

    def per_side(name: str, opts: tuple[str, ...], build: Any, equal_when_missing: str) -> None:
        nonlocal equivalent
        support = {s: c.has(*opts) for s, c in sides.items()}
        for s, c in sides.items():
            if support[s]:
                args[s] += build(c)
            elif any(support.values()):
                if equal_when_missing:
                    notes.append(f"{s}={c.tag}: {name} not supported and omitted (equivalent: {equal_when_missing})")
                else:
                    notes.append(f"{s}={c.tag}: {name} not supported and omitted (not equivalent)")
                    equivalent = False

    per_side("-ub", ("-ub", "--ubatch-size"), lambda c: ["-ub", str(ubatch)],
             f"no ubatch; the whole batch of {batch} is processed at once")
    per_side("-fa", ("-fa", "--flash-attn"),
             lambda c: ["-fa", "off" if "off" in c.fa_values else "0"], "this release has no flash attention")
    per_side("-ctk/-ctv", ("-ctk", "--cache-type-k"), lambda c: ["-ctk", "f16", "-ctv", "f16"], "f16_kv defaults to true")

    def mmap_args(c: Caps) -> list[str]:
        if c.has("-lm", "--load-mode"):
            return ["-lm", "mmap"]
        out = ["-mmp", "1"]
        if c.has("-dio", "--direct-io"):
            out += ["-dio", "0"]
        return out

    per_side("mmap", ("-lm", "--load-mode", "-mmp", "--mmap"), mmap_args, "models load through mmap by default")
    per_side("--poll", ("--poll",), lambda c: ["--poll", "50"], "")
    if backend == "cpu":
        def nopo_note(c: Caps) -> str:
            return "Metal takes no op offload (< b6556)" if int(c.tag[1:]) < 6556 else ""
        support = {s: c.has("-nopo", "--no-op-offload") for s, c in sides.items()}
        for s, c in sides.items():
            if support[s]:
                args[s] += ["-nopo", "1"]
            elif any(support.values()):
                eq = nopo_note(c)
                notes.append(f"{s}={c.tag}: -nopo not supported and omitted "
                             f"({'equivalent: ' + eq if eq else 'not equivalent'})")
                equivalent = equivalent and bool(eq)
    per_side("--repack", ("--repack",), lambda c: ["--repack", "1"],
             "repacking is on by default (or this release has no repacking)")
    # v1.2: around b2874 llama-bench ran an extra pp512+tg128 test by default (-pg 512,128); it comes
    # after pp512 and tg128, so it does not change them, but it doubles the run and heats the chip.
    per_side("-pg", ("-pg",), lambda c: ["-pg", "0,0"], "this release has no combined -pg test")
    return args["A"], args["B"], notes, equivalent


# --------------------------------------------------------------------------- planning


@dataclass
class Run:
    """One llama-bench invocation of the plan.

    Attributes:
        event_id: Event id.
        phase: 'fixed', 'default' or 'warmup' (v1.2; excluded from every statistic).
        rnd: Round number (1-based).
        side: 'A' (older) or 'B' (newer).
        tag: Release tag of the binary.
        model: Model name.
        backend: metal or cpu.
        argv: Full command.
        env: Extra environment variables.
        est_s: Estimated wall time.
        stem: Output file stem.
    """

    event_id: str
    phase: str
    rnd: int
    side: str
    tag: str
    model: str
    backend: str
    argv: list[str]
    env: dict[str, str]
    est_s: float
    stem: str


@dataclass
class Group:
    """Runs comparing one tag pair for one (model, back end) inside an event."""

    tag_a: str
    tag_b: str
    model: str
    backend: str
    series: list[dict[str, Any]]
    fixed_a: list[str]
    fixed_b: list[str]
    notes: list[str]
    equivalent: bool
    runs: list[Run] = field(default_factory=list)


@dataclass
class EventPlan:
    """All runs of one event."""

    event_id: str
    tag_old: str
    tag_new: str
    cls: str
    max_lr: float
    out: Path
    groups: list[Group] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def runs(self) -> list[Run]:
        """Runs in execution order."""
        return [r for g in self.groups for r in g.runs]


def order_sides(rounds: int, order: str) -> list[tuple[int, str]]:
    """(round, side) sequence: ABAB... or ABBA-alternating."""
    seq = []
    for r in range(1, rounds + 1):
        pair = ("A", "B") if order == "abab" or r % 2 == 1 else ("B", "A")
        seq += [(r, s) for s in pair]
    return seq


def build_plan(ev: pd.Series, ns: argparse.Namespace, caps_cache: dict[str, Caps]) -> EventPlan:
    """Turn one candidate event into an execution plan.

    Args:
        ev: Row of candidate_events.csv.
        ns: Parsed arguments.
        caps_cache: tag -> Caps cache.

    Returns:
        EventPlan (``problems`` non-empty when something needed is missing).
    """
    plan = EventPlan(ev["event_id"], ev["tag_old"], ev["tag_new"], ev["class"], float(ev["max_abs_log_ratio"]),
                     ns.out / f"{ev['event_id']}_{ev['tag_old']}_{ev['tag_new']}")
    series = json.loads(ev["series_json"])
    keyed: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for s in series:
        if ns.models and s["model"] not in ns.models:
            continue
        if ns.backends and s["backend"] not in ns.backends:
            continue
        keyed.setdefault((s["tag_old"], s["tag_new"], s["model"], s["backend"]), []).append(s)
    threads = {"metal": ns.threads_metal, "cpu": ns.threads_cpu}
    for (ta, tb, model, backend), ser in sorted(keyed.items()):
        for t in (ta, tb):
            if t not in caps_cache:
                caps_cache[t] = binary_caps(t, allow_exec=not ns.dry_run)
        ca, cb = caps_cache[ta], caps_cache[tb]
        mfile = MODELS_DIR / MODEL_FILES[model]
        for c in (ca, cb):
            if not c.binary.is_file():
                plan.problems.append(f"missing binary {c.binary}")
            if not c.flags:
                plan.problems.append(f"no help text for {c.tag}")
        if not mfile.is_file():
            plan.problems.append(f"missing model {mfile}")
        fa, fb, notes, equivalent = fixed_args(ca, cb, backend, threads, ns.batch, ns.ubatch)
        da, wall_a = campaign_args(ta, model, backend)
        db, wall_b = campaign_args(tb, model, backend)
        grp = Group(ta, tb, model, backend, ser, fa, fb, notes, equivalent)
        # fixed: more repetitions for the small models, whose pp512 lasts only 0.1-0.3 s per repetition
        # on Metal; default: exactly the campaign's -r 5, so the re-run is comparable with the campaign.
        fixed_reps = ns.reps_small if model in SMALL_MODELS else ns.reps
        if ns.warmup:
            # v1.2: one run of side A's fixed command before the group, excluded from every statistic,
            # so that the first measured run does not carry the switch from the previous group (in the
            # early data the first run of a group could deviate from the later runs by tens of percent:
            # GPU ramp-up, a cooler chip on this fanless machine).
            env = {"GGML_METAL_PATH_RESOURCES": ca.metal_resources} if ca.metal_resources else {}
            argv = ["/usr/bin/arch", "-arm64", str(ca.binary), "-m", str(mfile), "-p", "512", "-n", "128",
                    "-r", str(fixed_reps), "-o", "json", *fa]
            est = (wall_a or 60.0) * fixed_reps / CAMPAIGN_REPS
            grp.runs.append(Run(plan.event_id, "warmup", 0, "A", ca.tag, model, backend, argv, env, est,
                                f"warmup_r0_A_{ca.tag}_{model}_{backend}"))
        for phase, rounds, a_args, b_args, reps in (("fixed", ns.rounds, fa, fb, fixed_reps),
                                                    ("default", ns.default_rounds, da, db, CAMPAIGN_REPS)):
            base = ["-m", str(mfile), "-p", "512", "-n", "128", "-r", str(reps), "-o", "json"]
            for rnd, side in order_sides(rounds, ns.order):
                caps = ca if side == "A" else cb
                extra = a_args if side == "A" else b_args
                env = {"GGML_METAL_PATH_RESOURCES": caps.metal_resources} if caps.metal_resources else {}
                stem = f"{phase}_r{rnd}_{side}_{caps.tag}_{model}_{backend}"
                est = (wall_a if side == "A" else wall_b) or 60.0
                est *= reps / CAMPAIGN_REPS
                argv = ["/usr/bin/arch", "-arm64", str(caps.binary), *base, *extra]
                grp.runs.append(Run(plan.event_id, phase, rnd, side, caps.tag, model, backend, argv, env, est, stem))
        plan.groups.append(grp)
    return plan


def select_events(ns: argparse.Namespace) -> pd.DataFrame:
    """Candidate events chosen by --event-ids/--classes, in execution order."""
    ev = pd.read_csv(ns.events)
    if ns.event_ids:
        ev = ev[ev.event_id.isin(ns.event_ids)]
    else:
        ev = ev[ev["class"].isin(ns.classes)]
    ev = ev.assign(_prio=ev["class"].map(CLASS_PRIORITY).fillna(9))
    if ns.order_by == "priority":
        ev = ev.sort_values(["_prio", "max_abs_log_ratio"], ascending=[True, False])
    else:
        ev = ev.sort_values("b_old")
    if ns.max_events:
        ev = ev.head(ns.max_events)
    return ev.drop(columns="_prio")


# --------------------------------------------------------------------------- execution


def output_complete(path: Path) -> bool:
    """True if a run's JSON holds both pp512 and tg128 results."""
    return set(test_samples(load_bench_json(path))) >= set(TESTS)


def wait_quiet(ns: argparse.Namespace) -> tuple[float, bool, float, int]:
    """Wait until CPU idle >= idle_min, thermal state <= thermal_max, no busy process runs and
    (if set) load1 < load_max.

    The idle criterion is the campaign's (build_bench.sh, QUIET_IDLE_PCT=80). load1 is only a
    gate when ``--load-max`` > 0: on this Mac it sat above 2 in 98% of the campaign's calls
    even at 82-97% idle, so a load1 gate would make nearly every run wait the full limit.

    Args:
        ns: Parsed arguments.

    Returns:
        (seconds waited, settled, last idle percent, last thermal state).
    """
    t0 = time.monotonic()
    idle, therm = -1.0, -1
    while not STOP["flag"]:
        idle = cpu_idle_pct()
        therm = thermal_state()
        load1 = os.getloadavg()[0]
        busy = busy_processes()
        load_ok = ns.load_max <= 0 or load1 < ns.load_max
        therm_ok = ns.thermal_max < 0 or therm < 0 or therm <= ns.thermal_max
        if idle >= ns.idle_min and therm_ok and load_ok and not busy:
            return time.monotonic() - t0, True, idle, therm
        if time.monotonic() - t0 >= ns.load_wait_max:
            logger.warning("not quiet after %.0f s (idle=%.1f%% thermal=%d load1=%.2f busy=%s)",
                           time.monotonic() - t0, idle, therm, load1, busy)
            return time.monotonic() - t0, False, idle, therm
        time.sleep(10)
    return time.monotonic() - t0, False, idle, therm


def execute_run(run: Run, out: Path, ns: argparse.Namespace) -> dict[str, Any]:
    """Run one llama-bench process and return its runs.tsv row.

    Args:
        run: The run.
        out: Event output directory.
        ns: Parsed arguments.

    Returns:
        Row dict (exit_code 'skipped-load' when --on-load-timeout skip applies).
    """
    jpath, lpath = out / f"{run.stem}.json", out / f"{run.stem}.log"
    waited, settled, idle, therm = wait_quiet(ns)
    load1 = os.getloadavg()[0]
    row = {"event_id": run.event_id, "phase": run.phase, "round": run.rnd, "side": run.side, "tag": run.tag,
           "model": run.model, "backend": run.backend, "cmd": shlex.join(run.argv),
           "env": " ".join(f"{k}={v}" for k, v in run.env.items()), "load1_before": f"{load1:.2f}",
           "idle_pct_before": f"{idle:.1f}", "thermal_state_before": therm, "waited_s": f"{waited:.0f}",
           "load_settled": int(settled),
           "json_file": jpath.name, "log_file": lpath.name}
    if not settled and ns.on_load_timeout == "skip":
        row.update(exit_code="skipped-load", wall_s="0", started_at_utc="", finished_at_utc="", tests_ok=0)
        return row
    env = dict(os.environ, **run.env)
    started = dt.datetime.now(dt.UTC)
    t0 = time.monotonic()
    rc: Any = None
    with jpath.open("w") as jf, lpath.open("w") as lf:
        proc = subprocess.Popen(run.argv, stdout=jf, stderr=lf, env=env, start_new_session=True)
        STOP["child"] = proc
        try:
            rc = proc.wait(timeout=ns.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            rc = 124
        finally:
            STOP["child"] = None
    row.update(exit_code=rc, wall_s=f"{time.monotonic() - t0:.3f}",
               started_at_utc=started.strftime("%Y-%m-%dT%H:%M:%SZ"),
               finished_at_utc=dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
               tests_ok=int(output_complete(jpath)))
    return row


def append_row(path: Path, row: dict[str, Any]) -> None:
    """Append one row to runs.tsv (header on first write)."""
    new = not path.is_file()
    with path.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=RUNS_FIELDS, delimiter="\t", extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def run_plans(plans: list[EventPlan], ns: argparse.Namespace, win: tuple[dt.time, dt.time]) -> str:
    """Execute all plans in order; stop at the window end or on a signal.

    Args:
        plans: Event plans.
        ns: Parsed arguments.
        win: Measurement window.

    Returns:
        Reason the loop ended ('done', 'window', 'signal', 'busy').
    """
    first = True
    for plan in plans:
        if plan.problems:
            logger.error("%s skipped: %s", plan.event_id, "; ".join(plan.problems))
            continue
        plan.out.mkdir(parents=True, exist_ok=True)
        (plan.out / "plan.json").write_text(json.dumps(plan_to_json(plan), indent=1, ensure_ascii=False))
        for grp in plan.groups:
            # a warm-up run only precedes measured runs that are still to do (again after a resume)
            pending = any(r.phase != "warmup" and (ns.force or not output_complete(plan.out / f"{r.stem}.json"))
                          for r in grp.runs)
            for run in grp.runs:
                if STOP["flag"]:
                    return "signal"
                if run.phase == "warmup":
                    if not pending:
                        continue
                elif output_complete(plan.out / f"{run.stem}.json") and not ns.force:
                    continue
                need = run.est_s + (0 if first else ns.cooldown) + 30
                left = window_left(local_now(), win)
                if left < need:
                    logger.info("window: %.0f s left < %.0f s needed for %s; stopping", left, need, run.stem)
                    return "window"
                if not first:
                    time.sleep(ns.cooldown)
                first = False
                row = execute_run(run, plan.out, ns)
                append_row(plan.out / "runs.tsv", row)
                logger.info("%s %s rc=%s wall=%ss load1=%s waited=%ss", plan.event_id, run.stem, row["exit_code"],
                            row["wall_s"], row["load1_before"], row["waited_s"])
                if row["exit_code"] == "skipped-load" and ns.on_load_timeout == "stop":
                    return "busy"
        write_event_summary(plan, ns)
    return "done"


# --------------------------------------------------------------------------- judgment


def side_stats(paths: list[Path], test: str) -> tuple[list[float], list[float]]:
    """Per-run means and pooled ln(samples) of one side for one test."""
    means, logs = [], []
    for p in paths:
        st = test_samples(load_bench_json(p)).get(test)
        if st is None:
            continue
        means.append(st[0])
        logs += [math.log(x) for x in st[1] if x > 0]
    return means, logs


def judge(a_paths: list[Path], b_paths: list[Path], test: str, sign: float, ns: argparse.Namespace,
          pairs: list[tuple[Path, Path]]) -> dict[str, Any]:
    """Log-scale test of B vs A for one phase.

    Args:
        a_paths: JSON files of side A.
        b_paths: JSON files of side B.
        test: 'pp512' or 'tg128'.
        sign: Expected sign (+1/-1) from step 1.
        ns: Parsed arguments.
        pairs: (A, B) file pairs of the same round.

    Returns:
        Dict with lr, tau, pass, reversed, n runs, round signs.
    """
    ma, la = side_stats(a_paths, test)
    mb, lb = side_stats(b_paths, test)
    if not ma or not mb:
        return {"n_a": len(ma), "n_b": len(mb), "lr": float("nan"), "tau": float("nan"), "pass": False,
                "reversed": False, "complete": False, "round_signs": ""}
    complete = len(ma) == len(a_paths) and len(mb) == len(b_paths)  # every planned round present
    lr = math.log(float(np.mean(mb)) / float(np.mean(ma)))
    sa = float(np.std(la, ddof=1)) if len(la) > 1 else 0.0
    sb = float(np.std(lb, ddof=1)) if len(lb) > 1 else 0.0
    na, nb = max(len(la), 2), max(len(lb), 2)
    pooled = math.sqrt(((na - 1) * sa ** 2 + (nb - 1) * sb ** 2) / (na + nb - 2))
    tau = max(math.log1p(ns.min_rel), ns.k_sd * pooled)
    signs = []
    for pa, pb in pairs:
        xa, xb = side_stats([pa], test)[0], side_stats([pb], test)[0]
        if xa and xb:
            signs.append(int(np.sign(math.log(xb[0] / xa[0]))))
    consistent = all(s == sign for s in signs) if signs else False
    big = abs(lr) >= tau
    return {"n_a": len(ma), "n_b": len(mb), "lr": lr, "tau": tau, "mean_a": float(np.mean(ma)),
            "mean_b": float(np.mean(mb)), "pass": bool(big and np.sign(lr) == sign and consistent),
            "reversed": bool(big and np.sign(lr) == -sign), "complete": complete,
            "round_signs": "".join("+" if s > 0 else "-" for s in signs)}


def series_verdict(fixed: dict[str, Any], default: dict[str, Any]) -> str:
    """Combine the two phases into C / A / reversed / noise / incomplete."""
    if not fixed["complete"]:
        return "incomplete"
    if fixed["pass"]:
        return "C"
    if fixed["reversed"]:
        return "reversed"
    if not default["complete"]:
        return "incomplete"
    return "A" if default["pass"] else "noise"


def event_verdict(verdicts: list[str]) -> str:
    """Event verdict from its listed series."""
    for v in ("C", "A", "reversed"):
        if v in verdicts:
            return v
    if verdicts and all(v == "noise" for v in verdicts):
        return "noise"
    return "incomplete"


def summarize_event(plan: EventPlan, ns: argparse.Namespace) -> list[dict[str, Any]]:
    """Judge every series of an event from the files in its directory.

    Args:
        plan: Event plan.
        ns: Parsed arguments.

    Returns:
        One row per series (listed series and the other test of the same runs).
    """
    rows = []
    unsettled: dict[tuple[str, str, str], int] = {}
    runs_tsv = plan.out / "runs.tsv"
    if runs_tsv.is_file():
        with runs_tsv.open(newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                if r.get("load_settled") == "0":
                    key = (r["tag"], r["model"], r["backend"])
                    unsettled[key] = unsettled.get(key, 0) + 1
    for grp in plan.groups:
        listed = {s["test"]: s for s in grp.series}
        for test in TESTS:
            s = listed.get(test)
            out: dict[str, Any] = {"event_id": plan.event_id, "step1_class": plan.cls, "tag_a": grp.tag_a,
                                   "tag_b": grp.tag_b, "series": f"{grp.model}/{grp.backend}/{test}",
                                   "listed": int(s is not None), "fixed_equivalent": int(grp.equivalent),
                                   "fixed_notes": " | ".join(grp.notes),
                                   "runs_unsettled": unsettled.get((grp.tag_a, grp.model, grp.backend), 0)
                                   + unsettled.get((grp.tag_b, grp.model, grp.backend), 0)}
            camp_a, camp_b = campaign_mean(grp.tag_a, grp.model, grp.backend, test), \
                campaign_mean(grp.tag_b, grp.model, grp.backend, test)
            step1_lr = s["log_ratio"] if s else (math.log(camp_b / camp_a) if camp_a and camp_b else 0.0)
            sign = 1.0 if step1_lr >= 0 else -1.0
            out.update(step1_lr=step1_lr, step1_delta=math.expm1(step1_lr), campaign_a=camp_a, campaign_b=camp_b)
            res = {}
            for phase in ("fixed", "default"):
                runs = [r for r in grp.runs if r.phase == phase]
                a = [plan.out / f"{r.stem}.json" for r in runs if r.side == "A"]
                b = [plan.out / f"{r.stem}.json" for r in runs if r.side == "B"]
                rounds = sorted({r.rnd for r in runs})
                pairs = [(plan.out / f"{ra.stem}.json", plan.out / f"{rb.stem}.json") for k in rounds
                         for ra in runs if ra.rnd == k and ra.side == "A" for rb in runs if rb.rnd == k and rb.side == "B"]
                res[phase] = judge(a, b, test, sign, ns, pairs)
                for k, v in res[phase].items():
                    out[f"{phase}_{k}"] = v
            d = res["default"]
            out["repro_a"] = (d.get("mean_a", float("nan")) / camp_a - 1.0) if camp_a else float("nan")
            out["repro_b"] = (d.get("mean_b", float("nan")) / camp_b - 1.0) if camp_b else float("nan")
            out["verdict"] = series_verdict(res["fixed"], res["default"]) if s else "info"
            rows.append(out)
    return rows


def count_unsettled(plan: EventPlan) -> int:
    """Runs of an event that started although load1 had not settled (runs.tsv)."""
    path = plan.out / "runs.tsv"
    if not path.is_file():
        return 0
    with path.open(newline="") as fh:
        return sum(1 for r in csv.DictReader(fh, delimiter="\t") if r.get("load_settled") == "0")


def short_series(series: str) -> str:
    """'mistral-7b/metal/pp512' -> 'mistral/metal/pp512'."""
    model, rest = series.split("/", 1)
    return {"tinyllama-1.1b": "tiny", "mistral-7b": "mistral", "qwen2.5-1.5b": "qwen"}.get(model, model) + "/" + rest


def campaign_mean(tag: str, model: str, backend: str, test: str) -> float:
    """avg_ts of the campaign measurement (0 if missing)."""
    path = RESULTS / tag / "records.csv"
    if not path.is_file():
        return 0.0
    with path.open(newline="") as fh:
        for r in csv.DictReader(fh):
            if r["model"] == model and r["backend"] == backend and r["test"] == test and r["status"] == "ok":
                return float(r["avg_ts"])
    return 0.0


def write_event_summary(plan: EventPlan, ns: argparse.Namespace) -> list[dict[str, Any]]:
    """Write summary.csv / summary.md of one event directory."""
    rows = summarize_event(plan, ns)
    if not rows or not plan.out.is_dir():
        return rows
    pd.DataFrame(rows).to_csv(plan.out / "summary.csv", index=False)
    listed = [r for r in rows if r["listed"]]
    verdict = event_verdict([r["verdict"] for r in listed])
    lines = [f"# {plan.event_id}: {plan.tag_old} → {plan.tag_new} (step-1 class {plan.cls})", "",
             f"Event verdict: **{verdict}**", "",
             ("| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | "
              "Reproduction deviation A/B | Verdict |"),
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        f = "n/a" if not r["fixed_complete"] else \
            f"{math.expm1(r['fixed_lr']):+.1%} ({math.expm1(r['fixed_tau']):.1%}, {r['fixed_round_signs']})"
        d = "n/a" if not r["default_complete"] else f"{math.expm1(r['default_lr']):+.1%} ({math.expm1(r['default_tau']):.1%})"
        rep = f"{r['repro_a']:+.1%}/{r['repro_b']:+.1%}" if r["default_complete"] else "n/a"
        lines.append(f"| {r['series']}{'' if r['listed'] else ' (not listed)'} | {r['tag_a']}→{r['tag_b']} | "
                     f"{r['step1_delta']:+.1%} | {f} | {d} | {rep} | {r['verdict']} |")
    notes = sorted({n for g in plan.groups for n in g.notes})
    if notes:
        lines += ["", "Omissions in the fixed configuration:", ""] + [f"- {n}" for n in notes]
    n_uns = count_unsettled(plan)
    lines += ["", ("Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 "
                   "(a large deviation means that the time of the original measurement affected it). "
                   "Runs started without a quiet machine after the full wait (CPU idle share below the threshold "
                   f"or another llama process running): {n_uns} (load_settled=0 in runs.tsv)."), ""]
    (plan.out / "summary.md").write_text("\n".join(lines))
    return rows


def write_global_summary(plans: list[EventPlan], ns: argparse.Namespace) -> None:
    """Aggregate per-event summaries into interleaved/summary.csv and summary.md."""
    rows = []
    for plan in plans:
        if plan.out.is_dir():
            rows += write_event_summary(plan, ns)
    if not rows:
        logger.info("no measurements yet; no global summary written")
        return
    df = pd.DataFrame(rows)
    ns.out.mkdir(parents=True, exist_ok=True)
    df.to_csv(ns.out / "summary.csv", index=False)
    ev_rows = []
    for plan in plans:
        sub = df[(df.event_id == plan.event_id) & (df.listed == 1)]
        if sub.empty:
            continue
        ev_rows.append({"event": plan.event_id, "pair": f"{plan.tag_old}→{plan.tag_new}", "step1": plan.cls,
                        "verdict": event_verdict(list(sub.verdict)),
                        "series": ", ".join(f"{short_series(s)}:{v}" for s, v in zip(sub.series, sub.verdict)),
                        "unsettled": count_unsettled(plan)})
    lines = ["# Step 2: summary of the interleaved re-measurements", "",
             ("Generated by `scripts/analysis/step2_interleaved.py`. The details of each event are in summary.md "
              "of its subdirectory."), "",
             "| Event | Interval | Step-1 class | Re-measurement verdict | Series | Runs without a quiet machine |",
             "|---|---|---|---|---|---|"]
    lines += [f"| {e['event']} | {e['pair']} | {e['step1']} | {e['verdict']} | {e['series']} | {e['unsettled']} |"
              for e in ev_rows]
    lines += ["", ("Verdicts: C = still ≥ the threshold in the fixed phase, in the same direction (a change of the "
                   "implementation or the build; class B candidates also appear as C here); A = only with the release "
                   "defaults; noise = in neither phase; reversed = the opposite direction in the fixed phase; "
                   "incomplete = runs are missing."), ""]
    (ns.out / "summary.md").write_text("\n".join(lines))
    logger.info("global summary: %d events -> %s", len(ev_rows), ns.out / "summary.md")


# --------------------------------------------------------------------------- dry run


def plan_to_json(plan: EventPlan) -> dict[str, Any]:
    """Serializable view of a plan."""
    return {"event_id": plan.event_id, "tag_old": plan.tag_old, "tag_new": plan.tag_new, "class": plan.cls,
            "problems": plan.problems,
            "groups": [{"tag_a": g.tag_a, "tag_b": g.tag_b, "model": g.model, "backend": g.backend,
                        "series": [s["series"] for s in g.series], "fixed_a": g.fixed_a, "fixed_b": g.fixed_b,
                        "notes": g.notes, "equivalent": g.equivalent,
                        "runs": [{"phase": r.phase, "round": r.rnd, "side": r.side, "tag": r.tag, "stem": r.stem,
                                  "env": r.env, "argv": r.argv, "est_s": r.est_s} for r in g.runs]}
                       for g in plan.groups]}


def print_dry_run(plans: list[EventPlan], ns: argparse.Namespace, win: tuple[dt.time, dt.time]) -> None:
    """Print the plan and every command; nothing is executed or written."""
    now = local_now()
    left = window_left(now, win)
    print(f"# dry run at {now:%Y-%m-%d %H:%M:%S} local; window {ns.window}: "
          f"{'inside, %.0f min left' % (left / 60) if left > 0 else 'OUTSIDE -> a real run would refuse to start'}")
    gate = f"idle >= {ns.idle_min}%" + (f", thermal <= {ns.thermal_max}" if ns.thermal_max >= 0 else "") + \
        (f" and load1 < {ns.load_max}" if ns.load_max > 0 else "")
    print(f"# now: idle {cpu_idle_pct():.1f}%, thermal state {thermal_state()}, load1 {os.getloadavg()[0]:.2f} "
          f"(runs wait for {gate}, "
          f"at most {ns.load_wait_max:.0f} s); busy processes: {', '.join(busy_processes()) or 'none'}")
    total_runs, total_est = 0, 0.0
    for plan in plans:
        runs = plan.runs
        est = sum(r.est_s for r in runs) + ns.cooldown * len(runs)
        total_runs += len(runs)
        total_est += est
        print(f"\n== {plan.event_id} {plan.tag_old} -> {plan.tag_new} (step-1 class {plan.cls}, "
              f"max |ln ratio| {plan.max_lr:.2f}) -> {plan.out}")
        for p in plan.problems:
            print(f"   PROBLEM: {p}")
        for g in plan.groups:
            print(f"   group {g.model}/{g.backend} {g.tag_a} vs {g.tag_b}; series: "
                  f"{', '.join(s['series'].split('/', 2)[2] for s in g.series)}; fixed config "
                  f"{'aligned' if g.equivalent else 'NOT fully aligned'}")
            print(f"     fixed A: {shlex.join(g.fixed_a)}")
            print(f"     fixed B: {shlex.join(g.fixed_b)}")
            for n in g.notes:
                print(f"     note: {n}")
            for r in g.runs:
                env = " ".join(f"{k}={v}" for k, v in r.env.items())
                print(f"     [{r.phase:7s} r{r.rnd} {r.side}] {env + ' ' if env else ''}{shlex.join(r.argv)} "
                      f"> {plan.out.name}/{r.stem}.json 2> {plan.out.name}/{r.stem}.log")
        print(f"   runs: {len(runs)}; estimate {est / 60:.1f} min (benchmark + {ns.cooldown} s cooldown each; "
              "load waits not included)")
    print(f"\n# total: {len(plans)} events, {total_runs} runs, about {total_est / 3600:.1f} h plus load waits "
          f"(window length {window_hours(win):.1f} h)")


def window_hours(win: tuple[dt.time, dt.time]) -> float:
    """Length of the window in hours."""
    a = win[0].hour * 60 + win[0].minute
    b = win[1].hour * 60 + win[1].minute
    return ((b - a) % (24 * 60)) / 60 or 24.0


# --------------------------------------------------------------------------- main


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command-line interface."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--events", type=Path, default=EVENTS_CSV)
    ap.add_argument("--event-ids", type=lambda s: [x.strip() for x in s.split(",") if x.strip()], default=None)
    ap.add_argument("--classes", type=lambda s: [x.strip() for x in s.split(",") if x.strip()],
                    default=["A", "B", "C", "D"], help="step-1 classes to re-test (default all)")
    ap.add_argument("--max-events", type=int, default=0)
    ap.add_argument("--order-by", choices=("priority", "chronological"), default="priority",
                    help="priority = C, A, B, D, each by decreasing |ln ratio|")
    ap.add_argument("--models", type=lambda s: [x.strip() for x in s.split(",")], default=None)
    ap.add_argument("--backends", type=lambda s: [x.strip() for x in s.split(",")], default=None)
    ap.add_argument("--rounds", type=int, default=3, help="ABAB rounds with the fixed configuration (>= 3)")
    ap.add_argument("--default-rounds", type=int, default=1, help="rounds with each side's own defaults")
    ap.add_argument("--order", choices=("abab", "abba"), default="abba",
                    help="abba = AB, BA, AB, ... (position and linear drift balanced between sides)")
    ap.add_argument("--reps", type=int, default=5, help="llama-bench -r in the fixed phase for mistral-7b")
    ap.add_argument("--reps-small", type=int, default=10,
                    help="llama-bench -r in the fixed phase for tinyllama-1.1b and qwen2.5-1.5b "
                         "(the default phase always uses the campaign's -r 5)")
    ap.add_argument("--threads-metal", type=int, default=4)
    ap.add_argument("--threads-cpu", type=int, default=8)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--ubatch", type=int, default=512)
    ap.add_argument("--cooldown", type=float, default=20.0, help="seconds between runs")
    ap.add_argument("--idle-min", type=float, default=80.0,
                    help="start a run only when top's CPU idle %% is at least this (campaign: 80)")
    ap.add_argument("--thermal-max", type=int, default=1,
                    help="start a run only when the macOS thermal state is at most this (0 nominal, 1 fair, "
                         "2 serious); -1 = off")
    ap.add_argument("--load-max", type=float, default=0.0,
                    help="also require load1 below this; 0 = off (load1 is recorded either way)")
    ap.add_argument("--load-wait-max", type=float, default=300.0, help="max seconds to wait for a quiet machine")
    ap.add_argument("--on-load-timeout", choices=("proceed", "skip", "stop"), default="proceed",
                    help="what to do when the machine does not get quiet (the row is flagged load_settled=0)")
    ap.add_argument("--window", default="07:00-17:30", help="local-time window for real runs (HH:MM-HH:MM; 00:00-24:00 = no limit)")
    ap.add_argument("--timeout", type=float, default=1800.0, help="per-run limit in seconds")
    ap.add_argument("--min-rel", type=float, default=0.10)
    ap.add_argument("--k-sd", type=float, default=3.0)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--force", action="store_true", help="re-run runs whose output already exists")
    ap.add_argument("--no-warmup", dest="warmup", action="store_false",
                    help="no warm-up run before each group (v1.2 adds one; the first events of 2026-10-14 had none)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and commands only")
    ap.add_argument("--summarize-only", action="store_true", help="rebuild summaries from existing outputs")
    ns = ap.parse_args(argv)
    if ns.rounds < 3:
        ap.error("--rounds must be >= 3 (protocol: ABAB at least 3 times each)")
    return ns


def handle_signal(signum: int, _frame: Any) -> None:
    """Stop after killing the current llama-bench process group."""
    STOP["flag"] = True
    child = STOP["child"]
    if child is not None and child.poll() is None:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    logger.warning("signal %s: stopping", signum)


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    ns = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    win = parse_window(ns.window)
    real = not (ns.dry_run or ns.summarize_only)
    if real and window_left(local_now(), win) <= 0:
        logger.error("outside the measurement window %s (local %s): refusing to run. Use --dry-run to inspect the plan.",
                     ns.window, local_now().strftime("%H:%M %Z"))
        return 3
    if not ns.events.is_file():
        logger.error("%s missing: run step1_candidate_events.py first", ns.events)
        return 2
    events = select_events(ns)
    caps_cache: dict[str, Caps] = {}
    plans = [build_plan(ev, ns, caps_cache) for _, ev in events.iterrows()]
    if ns.dry_run:
        print_dry_run(plans, ns, win)
        return 0
    if ns.summarize_only:
        write_global_summary(plans, ns)
        return 0
    if CAMPAIGN_LOCK.is_file():
        try:
            pid = int(CAMPAIGN_LOCK.read_text().strip() or 0)
        except ValueError:
            pid = 0
        if pid and pid_alive(pid):
            logger.error("campaign is running (pid %d): refusing", pid)
            return 4
    ns.out.mkdir(parents=True, exist_ok=True)
    lock = ns.out / ".step2.lock"
    if lock.is_file():
        try:
            other = int(lock.read_text().strip() or 0)
        except ValueError:
            other = 0
        if other and pid_alive(other):
            logger.error("another step2 instance is running (pid %d): refusing", other)
            return 4
    lock.write_text(str(os.getpid()))
    handler = logging.FileHandler(ns.out / "run.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(handler)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    try:
        logger.info("start: %d events, %d runs, window %s", len(plans), sum(len(p.runs) for p in plans), ns.window)
        reason = run_plans(plans, ns, win)
        logger.info("stopped: %s", reason)
        write_global_summary(plans, ns)
    finally:
        lock.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
