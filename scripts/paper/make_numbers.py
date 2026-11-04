#!/usr/bin/env python3
"""Generate ``paper/numbers.tex``: every number quoted in the paper, as LaTeX macros.

Each macro is computed from a result file under ``results/`` (nothing is typed in by hand);
the generated file has one ``\\newcommand`` per line, preceded by a comment that names the
source file and the computation.  ``results/`` is only read, never written.

Sources (all relative to the project root):

* campaign scale: ``results/progress.csv``, ``results/<tag>/records.csv``;
* step 1 candidates: ``results/analysis/candidate_events.csv``;
* step 1b change points: ``results/analysis/changepoints.csv``, ``changepoint_events.csv``;
* re-measures and A/A control: ``remeasure_events.csv``, ``control_events.csv``;
* judge v1.1 and its drop-round-1 sensitivity run: ``results/analysis/interleaved/judge_v11_{events,series}[_norm1].csv``;
* visibility (step 4) and set cover (step 5, recomputed here): ``results/analysis/step4_visibility.csv``;
* bisection (step 3): ``results/analysis/bisect/*/result.json`` and, for events made of two changes, ``steps.csv``;
* first-run deviation of the groups measured without warm-up: ``results/analysis/interleaved/*/runs.tsv`` and the
  llama-bench JSON files next to it (same computation as Figure 4b);
* release dates: ``data/releases.csv``; tensor-API probe result per sampled release: ``results/<tag>/llama-bench_help.txt``;
* root-cause categories: ``results/analysis/root_cause_categories.csv``;
* power and sensitivity: ``interleaved/noise_model_v11.csv`` (MDE), the judge series file re-judged with
  ``scripts/analysis/step2b_judge.confirms`` (threshold sensitivity), campaign ``results/<tag>/runs.tsv`` with
  the default-phase re-runs (drift), ``bisect/E01cpu_*`` and ``harness_check_E01/`` (E01 CPU re-checks);
* protocol constants (thresholds, rounds, repetitions, waits): the argparse and ``Params`` defaults of
  ``scripts/analysis/step1*.py``, ``step2*.py``, ``step3_bisect.py``, the shell defaults of
  ``scripts/build_bench.sh`` and two literals of the protocol (``PROTOCOL_LITERALS``).

Macro names are camel case and contain letters only; event ids are spelled out
(E01 -> ``EOne``, E46 -> ``EFortySix``), so ``\\eFortyNineTagOld`` is the older end of E49.
Macros whose name ends in ``Raw`` are computed before the excluded-cell list is applied.

Run: taskpolicy -b nice -n 19 uv run --no-project --with pandas --with numpy python3 -I scripts/paper/make_numbers.py
"""

from __future__ import annotations

import argparse
import ast
import csv
import itertools
import json
import logging
import math
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]

MODELS = ("tinyllama-1.1b", "qwen2.5-1.5b", "mistral-7b")
BACKENDS = ("metal", "cpu")
TESTS = ("pp512", "tg128")
SERIES = tuple(f"{m}/{b}/{t}" for b in BACKENDS for m in MODELS for t in TESTS)
VISIBLE_STATES = ("up", "down")

# Cells (event, series) of the step-4 visibility matrix that the paper does not count as visible.
# E01 x mistral-7b/cpu/pp512: measured at -22% in step 2 (10-14) and in the v1.2 re-measure E01R
# (10-15), but on 2026-10-26 the bisection E01cpu was effect_lost (-5.3%) and the interleaved
# harness check (results/analysis/harness_check_E01/) gave about -4%, so only the Metal part of
# E01 is kept (Section 6 of the paper).  This is a judgement, not a result number.
DEFAULT_EXCLUDED_CELLS: tuple[tuple[str, str], ...] = (("E01", "mistral-7b/cpu/pp512"),)

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")
_ONES = ("Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
         "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen",
         "Nineteen")
_TENS = ("", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety")
_ORIGINAL_EVENT = re.compile(r"^E\d+$")


@dataclass(frozen=True)
class Macro:
    """One LaTeX macro with its provenance."""

    name: str
    value: str
    source: str
    method: str


def number_word(n: int) -> str:
    """Camel-case English word for 0 <= n < 100 (46 -> 'FortySix').

    Args:
        n: Integer in [0, 99].

    Returns:
        The spelled-out number with capitalised parts.

    Raises:
        ValueError: If n is outside [0, 99].
    """
    if not 0 <= n < 100:
        raise ValueError(f"number_word supports 0..99, got {n}")
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (_ONES[ones] if ones else "")


def event_word(event_id: str) -> str:
    """'E01' -> 'EOne', 'E46' -> 'EFortySix' (letters only, for macro names).

    Raises:
        ValueError: If the id is not E followed by digits.
    """
    if not _ORIGINAL_EVENT.match(event_id):
        raise ValueError(f"not an original event id: {event_id}")
    return "E" + number_word(int(event_id[1:]))


def macro_prefix(event_id: str) -> str:
    """'E01' -> 'eOne' (lower-case first letter, so macros read \\eOneTagOld)."""
    w = event_word(event_id)
    return w[0].lower() + w[1:]


def signed_pct(pct: float) -> str:
    """Rounded signed percentage for text mode: +159 or $-$65 (no percent sign)."""
    r = round(pct)
    return f"+{r}" if r > 0 else (f"$-${abs(r)}" if r < 0 else "0")


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _event_key(event_id: str) -> int:
    return int(event_id[1:])


# --------------------------------------------------------------------------------------------
# campaign scale
# --------------------------------------------------------------------------------------------


def campaign_macros(root: Path) -> list[Macro]:
    """Campaign scale from results/progress.csv and every results/<tag>/records.csv.

    Args:
        root: Project root.

    Returns:
        Macros for sampled/built/failed tags, records, models, backends, tests, reps and time span.
    """
    pp = root / "results" / "progress.csv"
    prog = pd.read_csv(pp)
    src_p = _rel(pp, root)
    n_ok = int((prog.status == "ok").sum())
    frames = []
    for tag in prog.tag:
        f = root / "results" / str(tag) / "records.csv"
        if f.is_file() and f.stat().st_size > 0:
            frames.append(pd.read_csv(f))
    rec = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["status", "model", "backend", "test", "n_samples"])
    ok = rec[rec.status == "ok"]
    src_r = "results/<tag>/records.csv"
    dates = pd.to_datetime(prog.commit_date_utc, utc=True)
    start, end = dates.min(), dates.max()
    reps = ok.n_samples.mode()
    out = [
        Macro("nTagsSampled", str(len(prog)), src_p, "rows (one per sampled release tag)"),
        Macro("nTagsBuilt", str(n_ok), src_p, "rows with status == ok"),
        Macro("nTagsFailed", str(len(prog) - n_ok), src_p, "rows with status != ok (build failures)"),
        Macro("nRecords", str(len(ok)), src_r, "rows with status == ok, summed over the tags of progress.csv"),
        Macro("nRecordsFailed", str(len(rec) - len(ok)), src_r, "rows with status != ok (model load failures)"),
        Macro("nModels", str(ok.model.nunique()), src_r, "distinct model among ok rows"),
        Macro("nBackends", str(ok.backend.nunique()), src_r, "distinct backend among ok rows"),
        Macro("nTests", str(ok.test.nunique()), src_r, "distinct test among ok rows"),
        Macro("nSeries", str(ok.groupby(["model", "backend", "test"]).ngroups), src_r,
              "distinct (model, backend, test) among ok rows"),
        Macro("nRepsCampaign", str(int(reps.iloc[0])) if len(reps) else "0", src_r, "mode of n_samples among ok rows"),
        Macro("campaignStartMonth", MONTHS[start.month - 1], src_p, "month of the earliest commit_date_utc"),
        Macro("campaignStartYear", str(start.year), src_p, "year of the earliest commit_date_utc"),
        Macro("campaignEndMonth", MONTHS[end.month - 1], src_p, "month of the latest commit_date_utc"),
        Macro("campaignEndYear", str(end.year), src_p, "year of the latest commit_date_utc"),
        Macro("campaignSpanMonths", str((end.year - start.year) * 12 + end.month - start.month), src_p,
              "calendar months from the earliest to the latest commit_date_utc"),
    ]
    out += campaign_session_macros(root, list(prog.tag))
    return out


def campaign_session_macros(root: Path, tags: list[str]) -> list[Macro]:
    """Number of llama-bench calls of the campaign and the wall-clock length of the session.

    Reads ``results/<tag>/runs.tsv`` (one row per llama-bench process).  The session runs from the
    earliest ``started_at_utc`` to the latest ``started_at_utc + wall_s``.  Returns no macros when no
    tag has a runs.tsv (e.g. a synthetic tree without one).

    Args:
        root: Project root.
        tags: Tags of progress.csv.

    Returns:
        Macros campaignCalls, campaignSessionHours, campaignSessionDays.
    """
    frames = []
    for tag in tags:
        f = root / "results" / str(tag) / "runs.tsv"
        if f.is_file() and f.stat().st_size > 0:
            frames.append(pd.read_csv(f, sep="\t", usecols=["started_at_utc", "wall_s"]))
    if not frames:
        logger.warning("no results/<tag>/runs.tsv found; campaign session macros skipped")
        return []
    runs = pd.concat(frames, ignore_index=True)
    t0 = pd.to_datetime(runs.started_at_utc, utc=True)
    t1 = t0 + pd.to_timedelta(pd.to_numeric(runs.wall_s, errors="coerce").fillna(0), unit="s")
    hours = (t1.max() - t0.min()).total_seconds() / 3600
    days = t0.dt.strftime("%Y-%m-%d").nunique()
    src = "results/<tag>/runs.tsv"
    return [
        Macro("campaignCalls", str(len(runs)), src, "rows (one llama-bench process per version x model x backend)"),
        Macro("campaignSessionHours", f"{hours:.1f}", src,
              "hours from the earliest started_at_utc to the latest started_at_utc + wall_s"),
        Macro("campaignSessionDays", str(days), src, "distinct UTC dates of started_at_utc"),
    ]


# --------------------------------------------------------------------------------------------
# protocol constants (read from the analysis scripts, not from results/)
# --------------------------------------------------------------------------------------------

SCRIPTS = Path(__file__).resolve().parents[1]

# Constants that no script states as a default.  Each comes from the study protocol (Section 3.4 of the paper).
PROTOCOL_LITERALS: tuple[tuple[str, str, str], ...] = (
    ("protNoWarmupEvents", "18",
     ("protocol v1.2: the first 18 events (2026-10-14 queue) were measured "
      "before the warm-up run was introduced")),
    ("protWarmupRuns", "1",
     "protocol v1.2: one warm-up run per group and per bisection step"),
    ("protWarmupRunsWord", "one", "protWarmupRuns as a word"),
)


def _literal(node: ast.expr) -> object:
    """Value of a constant expression node (numbers, strings, unary minus)."""
    return ast.literal_eval(node)


def argparse_default(path: Path, option: str) -> object:
    """Default of ``ap.add_argument(option, ..., default=<literal>)`` in a script.

    A default of the form ``Params.<field>`` is resolved through :func:`params_default`.

    Args:
        path: Python script.
        option: Option string, e.g. ``"--cooldown"``.

    Returns:
        The default value.

    Raises:
        KeyError: If the option or its default is not found.
    """
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            continue
        opts = [a.value for a in node.args if isinstance(a, ast.Constant)]
        if option not in opts:
            continue
        for kw in node.keywords:
            if kw.arg != "default":
                continue
            v = kw.value
            if isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == "Params":
                return params_default(path, v.attr)
            return _literal(v)
    raise KeyError(f"{option} default not found in {path}")


def params_default(path: Path, field: str) -> object:
    """Default of field ``field`` of the dataclass ``Params`` in a script.

    Raises:
        KeyError: If there is no such field with a literal default.
    """
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Params":
            for st in node.body:
                if (isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name)
                        and st.target.id == field and st.value is not None):
                    return _literal(st.value)
    raise KeyError(f"Params.{field} not found in {path}")


def shell_default(path: Path, var: str) -> str:
    """Default of ``VAR="${VAR:-<value>}"`` in a shell script.

    Raises:
        KeyError: If the assignment is not found.
    """
    m = re.search(rf'^{var}="\$\{{{var}:-([^}}]*)\}}"', path.read_text(), re.MULTILINE)
    if not m:
        raise KeyError(f"{var} default not found in {path}")
    return m.group(1)


def _num(v: object) -> str:
    """20.0 -> '20', 0.35 -> '0.35', 999 -> '999'."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"not a number: {v!r}")
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _pct(v: object) -> str:
    """0.05 -> '5' (a fraction written as a percentage without the sign)."""
    if not isinstance(v, (int, float)):
        raise TypeError(f"not a number: {v!r}")
    return _num(round(float(v) * 100, 6))


def protocol_macros(scripts: Path = SCRIPTS) -> list[Macro]:
    """Protocol constants of steps 1 to 3, parsed from the defaults of the analysis scripts.

    Args:
        scripts: The ``scripts/`` directory (holds ``analysis/`` and ``build_bench.sh``).

    Returns:
        Macros prot* (re-measurement, judge, bisection, detectors) and camp* (campaign driver).

    Raises:
        KeyError: If a default cannot be found in its script.
        TypeError: If a default is not numeric.
    """
    an = scripts / "analysis"
    s1, s1b = an / "step1_candidate_events.py", an / "step1b_changepoints.py"
    s2, s2b, s3 = an / "step2_interleaved.py", an / "step2b_judge.py", an / "step3_bisect.py"
    bb = scripts / "build_bench.sh"
    queue = an / "queues" / "continuous.tsv"

    def arg(path: Path, opt: str, name: str, fmt: Callable[[object], str] = _num) -> Macro:
        return Macro(name, fmt(argparse_default(path, opt)), _rel(path, scripts.parent), f"argparse default of {opt}")

    def par(path: Path, field: str, name: str, fmt: Callable[[object], str] = _num) -> Macro:
        return Macro(name, fmt(params_default(path, field)), _rel(path, scripts.parent), f"Params.{field} default")

    def sh(var: str, name: str) -> Macro:
        return Macro(name, shell_default(bb, var), _rel(bb, scripts.parent), f"default of ${var}")

    out = [
        # step 1: adjacent-pair threshold detector
        par(s1, "min_rel", "protCandMinRel", _pct),
        par(s1, "k_sd", "protCandKSd"),
        # step 1b: E-Divisive means
        par(s1b, "alpha", "protCpAlpha"),
        par(s1b, "min_size", "protCpMinSize"),
        par(s1b, "n_perm", "protCpPerm"),
        par(s1b, "p_max", "protCpPMax"),
        # step 2: interleaved re-measurement
        arg(s2, "--rounds", "protRoundsFixed"),
        arg(s2, "--default-rounds", "protRoundsDefault"),
        arg(s2, "--reps", "protRepsLarge"),
        arg(s2, "--reps-small", "protRepsSmall"),
        arg(s2, "--threads-metal", "protThreadsMetal"),
        arg(s2, "--threads-cpu", "protThreadsCpu"),
        arg(s2, "--batch", "protBatch"),
        arg(s2, "--ubatch", "protUbatch"),
        arg(s2, "--cooldown", "protCooldown"),
        arg(s2, "--idle-min", "protIdleMin"),
        arg(s2, "--thermal-max", "protThermalMax"),
        arg(s2, "--load-wait-max", "protWaitMax"),
        # step 2b: judge v1.1
        arg(s2b, "--min-rel", "protJudgeMinRel", _pct),
        arg(s2b, "--z-min", "protJudgeZ"),
        # step 3: bisection
        arg(s3, "--rounds", "protBisectRounds"),
        arg(s3, "--max-builds", "protMaxBuilds"),
        arg(s3, "--f-old", "protFOld"),
        arg(s3, "--f-new", "protFNew"),
        arg(s3, "--lost-frac", "protLostFrac"),
        # campaign driver
        sh("REPS", "campReps"),
        sh("CPU_THREADS", "campThreadsCpu"),
        sh("COOLDOWN_S", "campCooldown"),
        sh("QUIET_IDLE_PCT", "campIdleMin"),
        sh("QUIET_MAX_WAIT_S", "campWaitMax"),
        sh("QUIET_TAG_BUDGET_S", "campTagWaitBudget"),
    ]
    m = re.search(r'"--poll",\s*"(\d+)"', s2.read_text())
    if not m:
        raise KeyError(f"--poll value not found in {s2}")
    out.append(Macro("protPoll", m.group(1), _rel(s2, scripts.parent), "value passed with --poll in fixed_args"))
    m = re.search(r"^bisect_E16R\tstep3\t.*--rounds (\d+)", queue.read_text(), re.MULTILINE)
    if not m:
        raise KeyError(f"bisect_E16R --rounds not found in {queue}")
    out.append(Macro("protBisectRoundsNoisy", m.group(1), _rel(queue, scripts.parent),
                     "--rounds of the queue item bisect_E16R (noisy CPU series)"))
    out += [Macro(n, v, "scripts/paper/make_numbers.py PROTOCOL_LITERALS", why) for n, v, why in PROTOCOL_LITERALS]
    return out


def release_macros(root: Path) -> list[Macro]:
    """Release cadence in the sampled window and the spacing of the sampling grid.

    Reads ``data/releases.csv`` (every release tag) and ``data/selected_tags.csv`` (grid points of
    select_tags.py; the last row, the newest tag, has grid_point_utc 'newest').  Returns no macros
    when either file is missing.

    Args:
        root: Project root.

    Returns:
        Macros nReleasesWindow, releaseOneCommitPct, tagGridPoints, tagGridDays.
    """
    rel_p, sel_p = root / "data" / "releases.csv", root / "data" / "selected_tags.csv"
    if not (rel_p.is_file() and sel_p.is_file()):
        logger.warning("data/releases.csv or data/selected_tags.csv missing; release macros skipped")
        return []
    rel, sel = pd.read_csv(rel_p), pd.read_csv(sel_p)
    lo, hi = int(sel.build_number.min()), int(sel.build_number.max())
    win = rel[(rel.build_number >= lo) & (rel.build_number <= hi)]
    steps = pd.to_numeric(win.commits_since_prev, errors="coerce").dropna()
    grid = pd.to_datetime(sel.loc[sel.grid_point_utc != "newest", "grid_point_utc"], utc=True).sort_values()
    days = grid.diff().dropna().dt.total_seconds().mean() / 86400
    s_rel, s_sel = _rel(rel_p, root), _rel(sel_p, root)
    # commits after the oldest sampled tag up to the newest; the oldest tag's own count lies before the window
    commits = int(pd.to_numeric(win.sort_values("build_number").commits_since_prev.iloc[1:], errors="coerce").sum())
    return [
        Macro("nCommitsWindow", f"{commits:,}", s_rel,
              "sum of commits_since_prev of the tags after the oldest sampled tag up to the newest"),
        Macro("releasePerCommitPct", str(round(100 * (len(win) - 1) / commits)), s_rel,
              "tags after the oldest sampled tag per commit in that range, percent, rounded"),
        Macro("nReleasesWindow", f"{len(win):,}", s_rel,
              "release tags with build number between the oldest and newest sampled tag (inclusive)"),
        Macro("releaseOneCommitPct", str(round(100 * float((steps == 1).mean()))), s_rel,
              "percent of those tags whose commits_since_prev == 1, rounded"),
        Macro("tagGridPoints", str(len(grid)), s_sel, "grid points of select_tags.py (newest tag appended separately)"),
        Macro("tagGridDays", f"{days:.1f}", s_sel, "mean spacing of grid_point_utc in days"),
    ]


# --------------------------------------------------------------------------------------------
# step 1 candidates and step 1b change points
# --------------------------------------------------------------------------------------------


def candidate_macros(cand: pd.DataFrame, src: str) -> list[Macro]:
    """Step-1 candidate counts, overall and by class (A/B/C/D)."""
    out = [Macro("nCandidates", str(len(cand)), src, "rows (step-1 candidate event intervals)")]
    for cls in ("A", "B", "C", "D"):
        out.append(Macro(f"nCandidatesClass{cls}", str(int((cand["class"] == cls).sum())), src,
                         f"rows with class == {cls}"))
    return out


def changepoint_macros(cps: pd.DataFrame, cp_events: pd.DataFrame, src_cp: str, src_ev: str) -> list[Macro]:
    """Change-point counts: all persistent changes, those step 1 missed, the CP events and the overlap with step 1."""
    missed = cps.cp_event_id.notna() & (cps.cp_event_id.astype(str).str.len() > 0)
    overl = set()
    for v in cps.step1_same_group.dropna().astype(str):
        overl.update(re.findall(r"E\d+", v))
    return [
        Macro("nChangepoints", str(len(cps)), src_cp, "rows (persistent changes found by E-Divisive)"),
        Macro("nChangepointsMissed", str(int(missed.sum())), src_cp,
              "rows with a cp_event_id (change not covered by a step-1 candidate)"),
        Macro("nChangepointEvents", str(len(cp_events)), src_ev, "rows (CP events re-measured in step 2)"),
        Macro("nCandidatesOnChangepoint", str(len(overl)), src_cp,
              "distinct step-1 event ids in step1_same_group (a step-1 interval of the same model x backend "
              "group covers the change)"),
    ]


# --------------------------------------------------------------------------------------------
# judge v1.1
# --------------------------------------------------------------------------------------------


def judge_macros(events: pd.DataFrame, series: pd.DataFrame, cand: pd.DataFrame, cp_events: pd.DataFrame,
                 remeasure: pd.DataFrame, control: pd.DataFrame, src_ev: str, src_se: str) -> list[Macro]:
    """Confirmed and noise counts by candidate source, re-measure agreement and the A/A control.

    Args:
        events: judge_v11_events.csv.
        series: judge_v11_series.csv.
        cand: candidate_events.csv (step-1 ids and classes).
        cp_events: changepoint_events.csv.
        remeasure: remeasure_events.csv (ids ending in R).
        control: control_events.csv (A/A ids).
        src_ev: Display path of the events file.
        src_se: Display path of the series file.

    Returns:
        Macros (see the method strings).
    """
    v = events.set_index("event_id").verdict_v11.astype(str)
    out: list[Macro] = []

    def count(ids: list[str], verdict: str) -> int:
        return int(sum(v.get(i, "") == verdict for i in ids))

    step1 = list(cand.event_id)
    confirmed = sorted([i for i in step1 if v.get(i, "") == "C"], key=_event_key)
    out += [
        Macro("nCandidatesJudged", str(sum(i in v.index for i in step1)), src_ev, "step-1 ids present in the judge"),
        Macro("nConfirmed", str(len(confirmed)), src_ev, "step-1 ids with verdict_v11 == C"),
        Macro("nConfirmedConfigOnly", str(count(step1, "A")), src_ev,
              "step-1 ids with verdict_v11 == A (only the default configuration changes)"),
        Macro("nNoise", str(count(step1, "noise")), src_ev, "step-1 ids with verdict_v11 == noise"),
        Macro("confirmedEventList", ", ".join(confirmed), src_ev, "step-1 ids with verdict_v11 == C"),
    ]
    cls = cand.set_index("event_id")["class"]
    for c in ("A", "B", "C", "D"):
        ids = [i for i in step1 if cls.get(i) == c]
        out.append(Macro(f"nConfirmedClass{c}", str(count(ids, "C")), src_ev,
                         f"step-1 ids of step-1 class {c} with verdict_v11 == C"))
    cp_ids = list(cp_events.event_id)
    out += [
        Macro("nChangepointConfirmed", str(count(cp_ids, "C")), src_ev, "CP ids with verdict_v11 == C"),
        Macro("nChangepointNoise", str(count(cp_ids, "noise")), src_ev, "CP ids with verdict_v11 == noise"),
    ]
    rm_ids = [i for i in remeasure.event_id if i in v.index]
    agree = sum(v[i] == v.get(i[:-1], "") for i in rm_ids)
    out += [
        Macro("nRemeasured", str(len(rm_ids)), src_ev, "re-measure ids (E..R) present in the judge"),
        Macro("nRemeasuredAgree", str(int(agree)), src_ev,
              "re-measure ids whose verdict_v11 equals that of the original id"),
    ]
    aa = series[series.event_id.isin(list(control.event_id))]
    out += [
        Macro("nAASeries", str(len(aa)), src_se, "series rows of the A/A control ids"),
        Macro("nAAFalsePositives", str(int((aa.verdict == "aa_false_positive").sum())), src_se,
              "A/A series rows with verdict == aa_false_positive"),
    ]
    return out


def sensitivity_macros(ev: pd.DataFrame, ev1: pd.DataFrame, se: pd.DataFrame, se1: pd.DataFrame,
                       src: str) -> list[Macro]:
    """Agreement between the main judge and the drop-round-1 (``_norm1``) judge.

    Event level compares verdict_v11 per event id; series level compares verdict per
    (event, series, tag pair), on all rows and on the rows listed by step 1 (``listed == 1``).
    """
    m = ev.merge(ev1, on="event_id", how="outer", suffixes=("", "_n"))
    e_dis = int((m.verdict_v11.astype(str) != m.verdict_v11_n.astype(str)).sum())
    keys = ["event_id", "series", "tag_a", "tag_b"]
    s = se.merge(se1, on=keys, how="outer", suffixes=("", "_n"))
    dis = s.verdict.astype(str) != s.verdict_n.astype(str)
    s_dis = int(dis.sum())
    conf_flip = int((dis & ((s.verdict == "C") | (s.verdict_n == "C"))).sum())
    flipped_events = sorted({e for e in s.loc[dis, "event_id"]})
    return [
        Macro("nSensitivityEvents", str(len(m)), src, "event ids in the union of the two judge event files"),
        Macro("nSensitivityEventDisagree", str(e_dis), src, "event ids whose verdict_v11 differs between main and _norm1"),
        Macro("nSensitivitySeries", str(len(s)), src, "series rows in the union of the two judge series files"),
        Macro("nSensitivitySeriesDisagree", str(s_dis), src, "series rows whose verdict differs between main and _norm1"),
        Macro("nSensitivitySeriesFlipC", str(conf_flip), src,
              "of those, rows where either judge says C (series-level confirmations that flip)"),
        Macro("sensitivitySeriesDisagreeEvents", ", ".join(flipped_events) if flipped_events else "none", src,
              "event ids of the disagreeing series rows"),
    ]


# --------------------------------------------------------------------------------------------
# visibility (step 4) and set cover (step 5)
# --------------------------------------------------------------------------------------------


def read_visibility(path: Path) -> pd.DataFrame:
    """Read step4_visibility.csv keeping 'n/a' and empty states as strings."""
    vis = pd.read_csv(path, keep_default_na=False, dtype={"state": str, "source": str})
    for c in ("lr_pct", "z"):
        vis[c] = pd.to_numeric(vis[c].replace("", np.nan), errors="coerce")
    return vis


def apply_exclusions(vis: pd.DataFrame, excluded: tuple[tuple[str, str], ...]) -> pd.DataFrame:
    """Copy of the visibility frame with excluded (event, series) cells set to state 'excluded'."""
    out = vis.copy()
    for ev, s in excluded:
        mask = (out.event_id == ev) & (out.series == s)
        if not mask.any():
            logger.warning("excluded cell %s x %s is not in the visibility table", ev, s)
        out.loc[mask, "state"] = "excluded"
    return out


def cover(vis: pd.DataFrame) -> dict[str, object]:
    """Exhaustive set cover of the confirmed events by the 12 series.

    Args:
        vis: Visibility frame (event_id, series, state).

    Returns:
        Dict with sees (series -> events), best (list of minimal series tuples), k, single_max,
        single_series, events, undetectable.
    """
    events = set(vis.event_id)
    sees = {s: set(vis[(vis.series == s) & vis.state.isin(VISIBLE_STATES)].event_id) for s in SERIES}
    detectable = set().union(*sees.values())
    best: list[tuple[str, ...]] = []
    for k in range(1, len(SERIES) + 1):
        best = [c for c in itertools.combinations(SERIES, k) if set().union(*(sees[x] for x in c)) >= detectable]
        if best:
            break
    single = max(SERIES, key=lambda x: (len(sees[x]), -SERIES.index(x)))
    return {"sees": sees, "best": best, "k": len(best[0]) if best else 0, "single_max": len(sees[single]),
            "single_series": single, "events": events, "undetectable": events - detectable}


def visibility_macros(vis_raw: pd.DataFrame, excluded: tuple[tuple[str, str], ...], src: str) -> list[Macro]:
    """Visible-cell counts and set-cover numbers, after and (suffix Raw) before the exclusions."""
    vis = apply_exclusions(vis_raw, excluded)
    excl_txt = "; ".join(f"{e} x {s}" for e, s in excluded) or "none"
    out: list[Macro] = [Macro("nExcludedCells", str(len(excluded)), "make_numbers.py DEFAULT_EXCLUDED_CELLS / --exclude",
                              f"cells excluded from visibility: {excl_txt}")]
    for suffix, frame, note in (("", vis, f"after excluding {excl_txt}"), ("Raw", vis_raw, "before exclusions")):
        visible = frame.state.isin(VISIBLE_STATES)
        tg = frame.series.str.endswith("/tg128")
        out += [
            Macro(f"nVisibleCells{suffix}", str(int(visible.sum())), src, f"cells with state up/down, {note}"),
            Macro(f"nVisibleCellsTg{suffix}", str(int((visible & tg).sum())), src,
                  f"cells with state up/down on a tg128 series, {note}"),
            Macro(f"nVisibleCellsPp{suffix}", str(int((visible & ~tg).sum())), src,
                  f"cells with state up/down on a pp512 series, {note}"),
        ]
        cv = cover(frame)
        n_ev = len(cv["events"])
        out += [
            Macro(f"coverMinSeries{suffix}", str(cv["k"]), src,
                  f"smallest number of series whose visible events cover all detectable events (exhaustive), {note}"),
            Macro(f"coverMinSeriesWord{suffix}", number_word(int(cv["k"])).lower(), src, "the same count as a word"),
            Macro(f"coverNOptimal{suffix}", str(len(cv["best"])), src, f"number of series sets of that size, {note}"),
            Macro(f"coverSingleMax{suffix}", str(cv["single_max"]), src,
                  f"most events seen by one series ({cv['single_series']}), {note}"),
            Macro(f"coverSingleMiss{suffix}", str(n_ev - cv["single_max"]), src,
                  f"confirmed events minus coverSingleMax{suffix}, {note}"),
            Macro(f"nUndetectable{suffix}", str(len(cv["undetectable"])), src,
                  f"confirmed events no series sees, {note}"),
        ]
        best_sets = {frozenset(c) for c in cv["best"]}
        for model, word in (("tinyllama-1.1b", "Tiny"), ("qwen2.5-1.5b", "Qwen"), ("mistral-7b", "Mistral")):
            pair = frozenset({f"{model}/metal/pp512", "mistral-7b/cpu/pp512"})
            out.append(Macro(f"coverPair{word}Metal{suffix}", "yes" if pair in best_sets else "no", src,
                             f"whether {model} Metal pp512 with Mistral-7B CPU pp512 is a smallest covering set, {note}"))
    out += [
        Macro("nVisibilityCellsMeasured", str(int(vis_raw.state.isin(VISIBLE_STATES + ("none",)).sum())), src,
              "cells with state up/down/none (measured on both sides)"),
        Macro("nVisibilityCellsNA", str(int((vis_raw.state == "n/a").sum())), src,
              "cells with state n/a (model not supported by that version)"),
        Macro("nVisibilityEvents", str(vis_raw.event_id.nunique()), src, "distinct event_id"),
    ]
    return out


# --------------------------------------------------------------------------------------------
# bisection (step 3)
# --------------------------------------------------------------------------------------------


def read_bisect(bisect_dir: Path) -> pd.DataFrame:
    """One row per ``bisect/*/result.json`` with the base event id (E16R, E01c, E01cpu -> E16, E01)."""
    rows = []
    for f in sorted(bisect_dir.glob("*/result.json")):
        r = json.loads(f.read_text())
        m = re.match(r"^(E\d+)", str(r.get("event_id", "")))
        if not m:
            logger.warning("skip %s: event id %r", f, r.get("event_id"))
            continue
        rows.append({"dir": f.parent.name, "run_id": r["event_id"], "event_id": m.group(1),
                     "series": r.get("series", ""), "status": r.get("status", ""), "level": r.get("level", ""),
                     "lo": r.get("lo", ""), "hi": r.get("hi", ""), "lo_commit": r.get("lo_commit", ""),
                     "hi_commit": r.get("hi_commit", ""), "steps": int(r.get("measured_steps", 0)),
                     "builds": int(r.get("builds", 0)), "n_commits": int(r.get("n_commits", 0)),
                     "ref_lr": float(r.get("ref_lr", 0.0) or 0.0), "lo0": str(r.get("lo0", "") or ""),
                     "hi0": str(r.get("hi0", "") or ""), "intermediate": int(r.get("intermediate", 0) or 0)})
    return pd.DataFrame(rows, columns=["dir", "run_id", "event_id", "series", "status", "level", "lo", "hi",
                                       "lo_commit", "hi_commit", "steps", "builds", "n_commits", "ref_lr",
                                       "lo0", "hi0", "intermediate"])


def primary_bisect(runs: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None]:
    """Primary located release-level run (most builds, then largest |ref_lr|) and the located commit-level run.

    The commit-level run is the one that continues the primary run, i.e. whose starting interval
    (lo0, hi0) is the release boundary (lo, hi) of the primary run.  A commit-level run that starts
    elsewhere (E01a bisects the first part of E01) is a segment run, see ``segment_runs``.  Runs
    without lo0/hi0 are accepted as continuations when no run matches.
    """
    loc = runs[runs.status == "located"]
    rel = loc[loc.level == "release"]
    com = loc[loc.level == "commit"]
    pick = None
    if len(rel):
        pick = rel.assign(a=rel.ref_lr.abs()).sort_values(["builds", "a"], ascending=False).iloc[0]
    if pick is not None and len(com):
        match = com[(com.lo0 == str(pick.lo)) & (com.hi0 == str(pick.hi))]
        com = match if len(match) else com[(com.lo0 == "") & (com.hi0 == "")]
    cpick = com.sort_values("builds", ascending=False).iloc[0] if len(com) else None
    return pick, cpick


def segment_runs(runs: pd.DataFrame) -> pd.DataFrame:
    """Located runs of one event that bisect a part of its interval (E01a on the first part of E01).

    A segment run is neither the primary run nor its continuation, and its starting interval
    (lo0, hi0) differs from that of the primary run; further series bisected over the same
    interval (E49 on Qwen2.5 and Mistral-7B) are not segments.
    """
    rel, com = primary_bisect(runs)
    if rel is None:
        return runs.iloc[0:0]
    used = {r.dir for r in (rel, com) if r is not None}
    loc = runs[(runs.status == "located") & ~runs.dir.isin(used)]
    return loc[(loc.lo0 != str(rel.lo0)) | (loc.hi0 != str(rel.hi0))]


def bisect_total_macros(runs: pd.DataFrame, src: str) -> list[Macro]:
    """Totals over all bisection runs."""
    located_events = runs[runs.status == "located"].event_id.nunique()
    return [
        Macro("bisectRuns", str(len(runs)), src, "number of bisection runs (result.json files)"),
        Macro("bisectRunsLocated", str(int((runs.status == "located").sum())), src, "runs with status == located"),
        Macro("bisectRunsEffectLost", str(int((runs.status == "effect_lost").sum())), src,
              "runs with status == effect_lost"),
        Macro("bisectBuildsTotal", str(int(runs.builds.sum())), src, "sum of builds over all runs"),
        Macro("bisectStepsTotal", str(int(runs.steps.sum())), src, "sum of measured_steps over all runs"),
        Macro("nEventsLocated", str(int(located_events)), src, "distinct base event ids with a located run"),
        Macro("bisectIntermediateSteps", str(int(runs.intermediate.sum())), src,
              "sum of the intermediate counts (steps with an intermediate midpoint) over all runs"),
        Macro("bisectRunsIntermediate", str(int((runs.intermediate > 0).sum())), src,
              "runs with at least one intermediate step"),
    ]


# --------------------------------------------------------------------------------------------
# per confirmed event
# --------------------------------------------------------------------------------------------


def event_macros(confirmed: list[str], cand: pd.DataFrame, vis_raw: pd.DataFrame,
                 excluded: tuple[tuple[str, str], ...], runs: pd.DataFrame,
                 src_cand: str, src_vis: str, src_bis: str) -> list[Macro]:
    """Per confirmed event: interval, effect size of the primary visible series, bisection result, visibility.

    The primary visible series is the visible cell (after exclusions) with the largest |z| in
    step4_visibility.csv; PctMin/PctMax are the smallest and largest |change| over the visible cells.
    """
    vis = apply_exclusions(vis_raw, excluded)
    c = cand.set_index("event_id")
    out: list[Macro] = []
    for ev in confirmed:
        p = macro_prefix(ev)
        if ev in c.index:
            out += [Macro(f"{p}TagOld", str(c.at[ev, "tag_old"]), src_cand, f"tag_old of {ev}"),
                    Macro(f"{p}TagNew", str(c.at[ev, "tag_new"]), src_cand, f"tag_new of {ev}"),
                    Macro(f"{p}CommitsBetween", str(int(c.at[ev, "commits_between"])), src_cand,
                          f"commits_between of {ev}")]
        g = vis[(vis.event_id == ev) & vis.state.isin(VISIBLE_STATES)]
        graw = vis_raw[(vis_raw.event_id == ev) & vis_raw.state.isin(VISIBLE_STATES)]
        out += [Macro(f"{p}NVisible", str(len(g)), src_vis, f"visible cells of {ev} after exclusions"),
                Macro(f"{p}NVisibleRaw", str(len(graw)), src_vis, f"visible cells of {ev} before exclusions")]
        if len(g):
            top = g.loc[g.z.abs().idxmax()]
            a = g.lr_pct.abs()
            out += [
                Macro(f"{p}Pct", str(round(abs(top.lr_pct))), src_vis,
                      f"|lr_pct| of the visible cell with largest |z| ({top.series}, source {top.source}), rounded"),
                Macro(f"{p}PctSigned", signed_pct(top.lr_pct), src_vis, "same cell, signed, rounded"),
                Macro(f"{p}PctMin", str(round(a.min())), src_vis, f"smallest |lr_pct| over visible cells of {ev}"),
                Macro(f"{p}PctMax", str(round(a.max())), src_vis, f"largest |lr_pct| over visible cells of {ev}"),
            ]
        er = runs[runs.event_id == ev]
        rel, com = primary_bisect(er)
        if rel is None:
            logger.warning("%s has no located release-level bisection", ev)
            continue
        chain = [rel] + ([com] if com is not None else [])
        last = chain[-1]
        out += [
            Macro(f"{p}BisectLo", str(rel.lo), src_bis, f"lo of the primary located release-level run {rel.dir}"),
            Macro(f"{p}BisectHi", str(rel.hi), src_bis, f"hi of {rel.dir}"),
            Macro(f"{p}BisectSteps", str(int(sum(r.steps for r in chain))), src_bis,
                  "measured_steps of " + " + ".join(r.dir for r in chain)),
            Macro(f"{p}BisectBuilds", str(int(sum(r.builds for r in chain))), src_bis,
                  "builds of " + " + ".join(r.dir for r in chain)),
            Macro(f"{p}BisectBuildsAll", str(int(er.builds.sum())), src_bis,
                  f"builds over all bisection runs of {ev} ({', '.join(er.dir)})"),
            Macro(f"{p}BisectCommits", str(int(last.n_commits)), src_bis, f"n_commits in the final boundary of {last.dir}"),
        ]
        # The culprit commit is a file fact only when the final boundary holds exactly one commit;
        # with two or more, choosing the culprit is a reading of the diffs and stays out of the macros.
        if int(last.n_commits) == 1:
            out.append(Macro(f"{p}BisectCommit", str(last.hi_commit)[:9], src_bis,
                             f"hi_commit of {last.dir} (boundary holds one commit), first 9 characters"))
        if com is not None:
            out.append(Macro(f"{p}ReleaseBoundaryCommits", str(int(rel.n_commits)), src_bis,
                             f"n_commits in the release-level boundary of {rel.dir} (before the commit-level run)"))
            out.append(Macro(f"{p}BisectLoCommit", str(com.lo_commit)[:9], src_bis,
                             f"lo_commit of the commit-level run {com.dir}, first 9 characters"))
    return out


def boundary_macros(confirmed: list[str], runs: pd.DataFrame, src: str) -> list[Macro]:
    """How many confirmed events end at a one-commit boundary, and the largest final boundary.

    The final boundary of an event is that of its located commit-level run when there is one,
    otherwise that of its primary located release-level run (as in event_macros).
    """
    sizes = []
    for ev in confirmed:
        rel, com = primary_bisect(runs[runs.event_id == ev])
        last = com if com is not None else rel
        if last is not None:
            sizes.append(int(last.n_commits))
    if not sizes:
        return []
    return [
        Macro("nBoundarySingleCommit", str(sum(n == 1 for n in sizes)), src,
              "confirmed events whose final bisection boundary holds one commit"),
        Macro("bisectMaxBoundaryCommits", str(max(sizes)), src,
              "largest number of commits in the final boundary of a confirmed event"),
    ]


def boundary_throughput(steps: pd.DataFrame) -> tuple[float, float]:
    """Throughput (ts, geometric mean) of the two boundary binaries, as measured together in the last step.

    After the last step the boundary is (lo, mid) when the decision was hi=mid and (mid, hi) when
    it was lo=mid; both ends were measured interleaved in that step (columns ts_lo, ts_mid, ts_hi).

    Raises:
        ValueError: If the last decision is neither hi=mid nor lo=mid.
    """
    last = steps.sort_values("step").iloc[-1]
    if last.decision == "hi=mid":
        return float(last.ts_lo), float(last.ts_mid)
    if last.decision == "lo=mid":
        return float(last.ts_mid), float(last.ts_hi)
    raise ValueError(f"last step decision {last.decision!r} is neither hi=mid nor lo=mid")


def _pct_change(old: float, new: float) -> float:
    return (new / old - 1.0) * 100.0


def segment_macros(confirmed: list[str], runs: pd.DataFrame, bisect_dir: Path, src: str) -> list[Macro]:
    """Events made of two changes: the main chain (primary run + continuation) and one segment run.

    For an event with exactly one segment run (a further located run on a part of the interval,
    started because a step of the primary run was intermediate), the changes of the two parts are
    the throughput of the two boundary binaries in the last step of each part (boundary_throughput,
    steps.csv columns ts_* = exp of the mean log throughput of the runs, i.e. the geometric mean in tok/s).  The part whose interval ends first is
    called First, the other Second.  Interval: ts_lo -> ts_hi of step 1 of the primary run, i.e. the
    two ends of the event measured together; Product: the product of the two parts' ratios; Residual:
    Interval / Product - 1.  Prefix e<Event>: e.g. eOneFirstCommit.
    """
    out: list[Macro] = []
    for ev in confirmed:
        er = runs[runs.event_id == ev]
        seg = segment_runs(er)
        if len(seg) == 0:
            continue
        if len(seg) > 1:
            logger.warning("%s has %d segment runs; segment macros skipped", ev, len(seg))
            continue
        rel, com = primary_bisect(er)
        if rel is None:
            continue
        s = seg.iloc[0]
        main_last = com if com is not None else rel
        st_rel = pd.read_csv(bisect_dir / str(rel.dir) / "steps.csv")
        st_main = pd.read_csv(bisect_dir / str(main_last.dir) / "steps.csv")
        st_seg = pd.read_csv(bisect_dir / str(s.dir) / "steps.csv")
        seg_first = int(str(s.hi0).lstrip("b") or 0) <= int(str(rel.lo).lstrip("b") or 0)
        parts = {"First": ("seg", st_seg), "Second": ("main", st_main)} if seg_first else \
            {"First": ("main", st_main), "Second": ("seg", st_seg)}
        p = macro_prefix(ev)
        ratios = []
        for name, (kind, st) in parts.items():
            old, new = boundary_throughput(st)
            ratios.append(new / old)
            run = s if kind == "seg" else main_last
            out += [Macro(f"{p}{name}TsOld", str(round(old)), f"{src} ({run.dir})",
                          "older boundary end, ts (geometric mean tok/s) in the last step, rounded"),
                    Macro(f"{p}{name}TsNew", str(round(new)), f"{src} ({run.dir})",
                          "newer boundary end, ts (geometric mean tok/s) in the last step, rounded"),
                    Macro(f"{p}{name}Pct", str(round(_pct_change(old, new))), f"{src} ({run.dir})",
                          "change between the two boundary ends in the last step (%), rounded")]
        s1 = st_rel.sort_values("step").iloc[0]
        whole = float(s1.ts_hi) / float(s1.ts_lo)
        prod = ratios[0] * ratios[1]
        out += [
            Macro(f"{p}IntervalPct", str(round((whole - 1) * 100)), f"{src} ({rel.dir})",
                  f"step 1 of {rel.dir}: ts_hi / ts_lo - 1 (%), the two ends of {ev} measured together, rounded"),
            Macro(f"{p}ProductPct", str(round((prod - 1) * 100)), src,
                  "product of the First and Second boundary ratios, minus 1 (%), rounded"),
            Macro(f"{p}ResidualPct", str(round((whole / prod - 1) * 100)), src,
                  "Interval ratio / Product ratio - 1 (%): change not carried by the two boundaries, rounded"),
            Macro(f"{p}SegLo", str(s.lo0), f"{src} ({s.dir})", f"lo0 of the segment run {s.dir}"),
            Macro(f"{p}SegHi", str(s.hi0), f"{src} ({s.dir})", f"hi0 of the segment run {s.dir}"),
            Macro(f"{p}SegSteps", str(int(s.steps)), f"{src} ({s.dir})", f"measured_steps of {s.dir}"),
            Macro(f"{p}SegBuilds", str(int(s.builds)), f"{src} ({s.dir})", f"builds of {s.dir}"),
            Macro(f"{p}SegCommits", str(int(s.n_commits)), f"{src} ({s.dir})", f"n_commits in the boundary of {s.dir}"),
            Macro(f"{p}SegLoCommit", str(s.lo_commit)[:9], f"{src} ({s.dir})",
                  f"lo_commit of {s.dir}, first 9 characters"),
        ]
        if int(s.n_commits) == 1:
            out.append(Macro(f"{p}SegCommit", str(s.hi_commit)[:9], f"{src} ({s.dir})",
                             f"hi_commit of {s.dir} (boundary holds one commit), first 9 characters"))
        inter = st_rel[st_rel.verdict == "intermediate"]
        if len(inter):
            i0 = inter.sort_values("step").iloc[0]
            out += [Macro(f"{p}IntermediateMid", str(i0.mid), f"{src} ({rel.dir})",
                          f"midpoint of the first intermediate step (step {int(i0.step)}) of {rel.dir}"),
                    Macro(f"{p}IntermediateF", f"{float(i0.f):.2f}", f"{src} ({rel.dir})",
                          "relative position f of that midpoint, two decimals"),
                    Macro(f"{p}IntermediateStep", str(int(i0.step)), f"{src} ({rel.dir})",
                          "step number of that step")]
    return out


# --------------------------------------------------------------------------------------------
# Results-section details: series words, single cells, rejected examples, noise scales
# --------------------------------------------------------------------------------------------

MODEL_WORD = {"tinyllama-1.1b": "Tiny", "qwen2.5-1.5b": "Qwen", "mistral-7b": "Mistral"}
BACKEND_WORD = {"metal": "Metal", "cpu": "Cpu"}
TEST_WORD = {"pp512": "Pp", "tg128": "Tg"}

# Step-1 candidates quoted with their campaign and re-measured change (event, series): E14 and E25,
# rejected, as examples in RQ1; E25 and the confirmed E49, on the same series, in the motivation
# figure and the introduction.  The numbers come from the result files.
CHANGE_EXAMPLES: tuple[tuple[str, str], ...] = (("E14", "qwen2.5-1.5b/metal/pp512"),
                                                 ("E25", "tinyllama-1.1b/metal/pp512"),
                                                 ("E49", "tinyllama-1.1b/metal/pp512"))
# Series whose judge noise scale s is quoted in RQ3 (E50 on Mistral-7B Metal is large but not significant).
NOISE_EXAMPLES: tuple[tuple[str, str], ...] = (("E50", "mistral-7b/metal/pp512"),
                                               ("E50", "tinyllama-1.1b/metal/pp512"))


def series_word(series: str) -> str:
    """'mistral-7b/cpu/pp512' -> 'MistralCpuPp' (letters only, for macro names).

    Raises:
        KeyError: If a part of the series is unknown.
    """
    m, b, t = series.split("/")
    return MODEL_WORD[m] + BACKEND_WORD[b] + TEST_WORD[t]


def signed_num(v: float, digits: int = 1) -> str:
    """Signed number for text mode with a math minus: 1.57 -> '1.6', -1.08 -> '$-$1.1'."""
    r = round(float(v), digits)
    s = f"{abs(r):.{digits}f}"
    return f"$-${s}" if r < 0 else s


def visibility_cell_macros(vis_raw: pd.DataFrame, src: str) -> list[Macro]:
    """Signed change and z of every measured cell of step4_visibility.csv (before exclusions).

    Names are vis<Event><Series> and vis<Event><Series>Z, e.g. \\visEFiftyMistralMetalPp.
    """
    out: list[Macro] = []
    rows = [r for _, r in vis_raw.iterrows()
            if _ORIGINAL_EVENT.match(str(r.event_id)) and str(r.series) in SERIES and not pd.isna(r.lr_pct)]
    for r in sorted(rows, key=lambda x: (_event_key(str(x.event_id)), SERIES.index(str(x.series)))):
        name = "vis" + event_word(str(r.event_id)) + series_word(str(r.series))
        out.append(Macro(name, signed_pct(float(r.lr_pct)), src,
                         f"lr_pct of {r.event_id} x {r.series} (state {r.state}, source {r.source}), rounded"))
        if not pd.isna(r.z):
            out.append(Macro(name + "Z", signed_num(float(r.z)), src, f"z of {r.event_id} x {r.series}, one decimal"))
    return out


def cover_series_macros(vis_raw: pd.DataFrame, excluded: tuple[tuple[str, str], ...], src: str) -> list[Macro]:
    """Number of confirmed events each series sees after the exclusions (the bars of Figure 7)."""
    cv = cover(apply_exclusions(vis_raw, excluded))
    return [Macro("coverSees" + series_word(s), str(len(cv["sees"][s])), src,
                  f"events visible in {s} after exclusions: {', '.join(sorted(cv['sees'][s], key=_event_key)) or 'none'}")
            for s in SERIES]


def _judge_row(series_df: pd.DataFrame, event_id: str, series: str, tag_a: str | None = None,
               tag_b: str | None = None) -> pd.Series | None:
    g = series_df[(series_df.event_id == event_id) & (series_df.series == series)]
    if tag_a is not None:
        g = g[(g.tag_a == tag_a) & (g.tag_b == tag_b)]
    return g.iloc[0] if len(g) else None


def change_example_macros(cand: pd.DataFrame, series_df: pd.DataFrame, src_cand: str, src_se: str,
                          examples: tuple[tuple[str, str], ...] = CHANGE_EXAMPLES) -> list[Macro]:
    """Campaign change and re-measured change of selected candidates (``CHANGE_EXAMPLES``).

    The campaign change is the ``delta`` (relative change of the mean) of the series in
    ``series_json`` with the largest |delta|; the re-measured change is exp(fixed_lr) - 1 of the judge
    row with the same series and tag pair.
    """
    out: list[Macro] = []
    c = cand.set_index("event_id")
    for ev, s in examples:
        if ev not in c.index or "series_json" not in c.columns:
            logger.warning("example %s not in candidate_events.csv", ev)
            continue
        entries = [d for d in json.loads(str(c.at[ev, "series_json"])) if d.get("series") == s]
        if not entries:
            logger.warning("example %s has no step-1 entry for %s", ev, s)
            continue
        d = max(entries, key=lambda x: abs(float(x["delta"])))
        row = _judge_row(series_df, ev, s, str(d["tag_old"]), str(d["tag_new"]))
        if row is None or "fixed_lr" not in row.index:
            logger.warning("example %s x %s has no judge row", ev, s)
            continue
        p = macro_prefix(ev)
        out += [
            Macro(f"{p}CampPct", signed_pct(100 * float(d["delta"])), src_cand,
                  f"series_json delta of {ev} x {s} ({d['tag_old']} -> {d['tag_new']}), percent, rounded"),
            Macro(f"{p}RemPct", signed_pct(100 * (math.exp(float(row.fixed_lr)) - 1)), src_se,
                  f"exp(fixed_lr) - 1 of {ev} x {s}, same tag pair, percent, rounded (verdict {row.verdict})"),
            Macro(f"{p}RemZ", signed_num(float(row.fixed_z)), src_se, f"fixed_z of {ev} x {s}, one decimal"),
        ]
    return out


def noise_example_macros(cand: pd.DataFrame, series_df: pd.DataFrame, src: str,
                         examples: tuple[tuple[str, str], ...] = NOISE_EXAMPLES) -> list[Macro]:
    """Noise scale s of the fixed phase (log scale, two decimals) for selected (event, series) rows."""
    out: list[Macro] = []
    c = cand.set_index("event_id")
    for ev, s in examples:
        ta, tb = (str(c.at[ev, "tag_old"]), str(c.at[ev, "tag_new"])) if ev in c.index else (None, None)
        row = _judge_row(series_df, ev, s, ta, tb)
        if row is None or "fixed_s" not in row.index:
            logger.warning("noise example %s x %s has no judge row", ev, s)
            continue
        out.append(Macro(f"{macro_prefix(ev)}{series_word(s)}Noise", f"{float(row.fixed_s):.2f}", src,
                         f"fixed_s of {ev} x {s} (noise scale of the log statistic), two decimals"))
    return out


# --------------------------------------------------------------------------------------------
# first-run deviation of the groups measured without warm-up (Figure 4b)
# --------------------------------------------------------------------------------------------

BIAS_BAND = 0.10  # band (fraction) used in the text to call a first-run deviation small


def run_value(run_dir: Path, json_name: str, test: str) -> float:
    """Median of samples_ts of one test in one llama-bench JSON output (NaN if missing)."""
    try:
        data = json.loads((run_dir / json_name).read_text())
    except (OSError, ValueError):
        return math.nan
    for r in data:
        is_pp = r.get("n_prompt", 0) > 0 and r.get("n_gen", 0) == 0
        is_tg = r.get("n_gen", 0) > 0 and r.get("n_prompt", 0) == 0
        if (test == "pp512" and is_pp) or (test == "tg128" and is_tg):
            s = r.get("samples_ts") or []
            return float(np.median(s)) if s else float(r.get("avg_ts", math.nan))
    return math.nan


def first_run_bias(root: Path) -> pd.DataFrame:
    """First fixed-phase run of every unwarmed group versus the other runs of the same tag.

    A group is (event directory, model, backend); it is unwarmed when its runs.tsv has no
    ``warmup`` row (protocol v1.2 added the warm-up, so these are the groups measured before).
    For the first run (by start time) and, as a reference, for the first run of the other side,
    the deviation is value / mean(other fixed runs of the same tag) - 1.

    Args:
        root: Project root.

    Returns:
        Frame with event, model, backend, test, role ('first' or 'reference'), dev.
    """
    rows = []
    for f in sorted((root / "results" / "analysis" / "interleaved").glob("*/runs.tsv")):
        runs = pd.read_csv(f, sep="\t")
        runs = runs[runs.exit_code == 0]
        for (model, backend), g in runs.groupby(["model", "backend"]):
            if (g.phase == "warmup").any():
                continue
            fx = g[g.phase == "fixed"].sort_values("started_at_utc")
            if fx.tag.nunique() < 2 and fx.side.nunique() < 2:
                continue
            first = fx.iloc[0]
            other_side = fx[fx.side != first.side]
            picks = [("first", first)]
            if len(other_side):
                picks.append(("reference", other_side.iloc[0]))
            for role, run in picks:
                same = fx[(fx.side == run.side) & (fx.json_file != run.json_file)]
                for test in TESTS:
                    v = run_value(f.parent, run.json_file, test)
                    rest = [run_value(f.parent, j, test) for j in same.json_file]
                    rest = [x for x in rest if not math.isnan(x)]
                    if math.isnan(v) or not rest:
                        continue
                    rows.append({"event": f.parent.name.split("_")[0], "model": model, "backend": backend,
                                 "test": test, "role": role, "dev": v / float(np.mean(rest)) - 1.0})
    df = pd.DataFrame(rows, columns=["event", "model", "backend", "test", "role", "dev"])
    logger.info("first-run bias: %d unwarmed groups in %d events",
                len(df[(df.role == "first") & (df.test == "pp512")]), df.event.nunique() if len(df) else 0)
    return df


def bias_macros(bias: pd.DataFrame, src: str, band: float = BIAS_BAND) -> list[Macro]:
    """Summary of the first-run deviation (role 'first' only), as plotted in Figure 4b.

    Args:
        bias: Output of first_run_bias.
        src: Display path of the source.
        band: Deviations with |dev| <= band count as small.

    Returns:
        Macros bias* (groups, events, band, shares, medians by back end and test, largest by model and back end).
    """
    first = bias[bias.role == "first"]
    if first.empty:
        logger.warning("no unwarmed groups; first-run bias macros skipped")
        return []
    pct = first.dev * 100
    large = first[first.dev.abs() > band]
    meds = first.groupby(["backend", "test"]).dev.median() * 100
    out = [
        Macro("biasGroups", str(first.groupby(["event", "model", "backend"]).ngroups), src,
              "distinct (event, model, backend) groups without a warm-up run"),
        Macro("biasEvents", str(first.event.nunique()), src, "distinct events of those groups"),
        Macro("biasBand", _num(round(band * 100, 6)), "scripts/paper/make_numbers.py BIAS_BAND",
              "band (percent) within which a first-run deviation counts as small"),
        Macro("biasFasterPct", str(round(100 * float((first.dev > 0).mean()))), src,
              "percent of first-run deviations (all groups and tests) that are positive (faster)"),
        Macro("biasLargeN", str(len(large)), src, "first-run deviations with |dev| > biasBand"),
        Macro("biasLargeFasterPct", str(round(100 * float((large.dev > 0).mean()))) if len(large) else "0", src,
              "percent of those that are positive (faster)"),
        Macro("biasMedianMin", signed_pct(float(meds.min())), src, "smallest median deviation over back end x test"),
        Macro("biasMedianMax", signed_pct(float(meds.max())), src, "largest median deviation over back end x test"),
    ]
    for m in MODELS:
        dm = first[first.model == m]
        if len(dm):
            out.append(Macro(f"bias{MODEL_WORD[m]}WithinBandPct",
                             str(round(100 * float((dm.dev.abs() <= band).mean()))), src,
                             f"percent of {m} first-run deviations with |dev| <= biasBand"))
        for b in BACKENDS:
            d = pct[(first.model == m) & (first.backend == b)]
            if len(d):
                mx = round(float(d.max()))
                out.append(Macro(f"bias{MODEL_WORD[m]}{BACKEND_WORD[b]}Max", f"$-${-mx}" if mx < 0 else str(mx), src,
                                 f"largest first-run deviation of {m} on {b} (percent, rounded)"))
                top = first.loc[d.idxmax()]
                out.append(Macro(f"bias{MODEL_WORD[m]}{BACKEND_WORD[b]}MaxEvent", str(top.event), src,
                                 f"event of that deviation ({top.test})"))
    return out


# --------------------------------------------------------------------------------------------
# lifetimes: E03 -> E04 and the silent tensor-API probe failure before E49
# --------------------------------------------------------------------------------------------

_TENSOR = re.compile(r"has tensor\s*=\s*(true|false)")


def lifetime_macros(root: Path, runs: pd.DataFrame) -> list[Macro]:
    """Days between bisection boundaries, and the releases whose tensor-API probe failed.

    eThreeLifetimeDays: commit date of the E04 boundary release minus that of the E03 boundary release
    (the regression of E03 is undone by E04).  The tensor-API probe result of each sampled release is
    read from the Metal initialisation log at the head of results/<tag>/llama-bench_help.txt.

    Args:
        root: Project root.
        runs: read_bisect output.

    Returns:
        Macros, or an empty list when data/releases.csv is missing.
    """
    rel_p = root / "data" / "releases.csv"
    if not rel_p.is_file():
        logger.warning("data/releases.csv missing; lifetime macros skipped")
        return []
    rel = pd.read_csv(rel_p)
    date = dict(zip(rel.tag.astype(str), pd.to_datetime(rel.commit_date_utc, utc=True)))
    src_rel = _rel(rel_p, root)
    out: list[Macro] = []
    hi = {}
    for ev in ("E03", "E04", "E49"):
        pick, _ = primary_bisect(runs[runs.event_id == ev])
        if pick is not None:
            hi[ev] = str(pick.hi)
    if "E03" in hi and "E04" in hi and hi["E03"] in date and hi["E04"] in date:
        days = (date[hi["E04"]] - date[hi["E03"]]).total_seconds() / 86400
        out.append(Macro("eThreeLifetimeDays", str(round(days)), src_rel,
                         f"days from {hi['E03']} (E03 boundary) to {hi['E04']} (E04 boundary), commit dates, rounded"))
    prog_p = root / "results" / "progress.csv"
    if not prog_p.is_file():
        return out
    flags: dict[str, str] = {}
    for tag in pd.read_csv(prog_p).tag.astype(str):
        f = root / "results" / tag / "llama-bench_help.txt"
        if f.is_file():
            m = _TENSOR.search(f.read_text(errors="replace"))
            if m:
                flags[tag] = m.group(1)
    off = sorted((t for t, v in flags.items() if v == "false"), key=lambda t: int(t.lstrip("b")))
    on = sorted((t for t, v in flags.items() if v == "true"), key=lambda t: int(t.lstrip("b")))
    if not off:
        return out
    src_h = "results/<tag>/llama-bench_help.txt"
    out += [
        Macro("nTagsTensorOff", str(len(off)), src_h, "sampled releases whose log says has tensor = false"),
        Macro("nTagsTensorOn", str(len(on)), src_h, "sampled releases whose log says has tensor = true"),
        Macro("tensorOffFirst", off[0], src_h, "oldest release with has tensor = false"),
        Macro("tensorOffLast", off[-1], src_h, "newest release with has tensor = false"),
    ]
    if on:
        out.append(Macro("tensorOnFirst", on[0], src_h, "oldest release with has tensor = true"))
    if "E49" in hi and hi["E49"] in date and off[0] in date:
        days = (date[hi["E49"]] - date[off[0]]).total_seconds() / 86400
        out.append(Macro("tensorOffDays", str(round(days)), src_rel,
                         f"days from {off[0]} (oldest release with the probe failing) to {hi['E49']} (E49 boundary)"))
    return out


# --------------------------------------------------------------------------------------------
# root-cause categories (results/analysis/root_cause_categories.csv, Table 4 of the paper)
# --------------------------------------------------------------------------------------------

CATEGORY_KEYS: tuple[str, ...] = ("Metal", "Blas", "Thread", "Repack")


def category_macros(path: Path, confirmed: list[str], root: Path) -> list[Macro]:
    """Number of confirmed events per root-cause category.

    Reads ``root_cause_categories.csv``, one row per category with the columns category, name and
    events (event ids separated by semicolons).

    Raises:
        ValueError: If the categories are not those of ``CATEGORY_KEYS``, or the events of the table
            differ from the confirmed events.
    """
    if not path.is_file():
        logger.warning("%s missing; category macros skipped", path)
        return []
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    keys = tuple(r["category"] for r in rows)
    if keys != CATEGORY_KEYS:
        raise ValueError(f"expected categories {CATEGORY_KEYS} in {path}, found {keys}")
    src = _rel(path, root)
    out: list[Macro] = [Macro("nRootCauseCategories", str(len(rows)), src, "rows (one per root-cause category)"),
                        Macro("nRootCauseCategoriesWord", number_word(len(rows)).lower(), src, "the same count as a word")]
    seen: list[str] = []
    for r in rows:
        evs = r["events"].split(";")
        seen += evs
        out.append(Macro(f"cat{r['category']}N", str(len(evs)), src, f"events of category {r['name']}: {', '.join(evs)}"))
    if sorted(seen, key=_event_key) != sorted(confirmed, key=_event_key):
        raise ValueError(f"category events {sorted(seen)} differ from confirmed events {sorted(confirmed)}")
    return out


# --------------------------------------------------------------------------------------------
# power, refuted/inconclusive noise verdicts, threshold sensitivity, drift,
# recovery in later samples, the E01 CPU re-checks and the borderline visibility cells
# --------------------------------------------------------------------------------------------

Z_WORD = {2.5: "TwoHalf", 3.0: "Three", 3.5: "ThreeHalf"}
FLOOR_WORD = {0.03: "Three", 0.05: "Five", 0.10: "Ten"}
SENS_Z: tuple[float, ...] = (2.5, 3.0, 3.5)
SENS_FLOOR: tuple[float, ...] = (0.03, 0.05, 0.10)
Z_POWER80 = 0.8416212335729143  # standard normal quantile of 0.8 (one-sided power 80%)
BORDER_Z = (2.5, 3.0)  # |z| range of a visibility cell called borderline (below the judge's z)
LARGE_CELL_PCT = 10.0  # a not-visible cell with |change| >= this percentage is reported as large
MODEL_TEXT = {"tinyllama-1.1b": "TinyLlama", "qwen2.5-1.5b": "Qwen2.5", "mistral-7b": "Mistral-7B"}
BACKEND_TEXT = {"metal": "Metal", "cpu": "CPU"}


def load_judge(scripts: Path = SCRIPTS) -> object:
    """Import ``scripts/analysis/step2b_judge.py`` (the decision rule of the paper) as a module."""
    an = str(scripts / "analysis")
    if an not in sys.path:
        sys.path.insert(0, an)
    import importlib
    return importlib.import_module("step2b_judge")


def series_text(series: str) -> str:
    """'mistral-7b/cpu/tg128' -> 'Mistral-7B CPU tg128'."""
    m, b, t = series.split("/")
    return f"{MODEL_TEXT[m]} {BACKEND_TEXT[b]} {t}"


def campaign_pair_lr(frames: list[pd.DataFrame]) -> dict[tuple[str, str, str, str], float]:
    """(event, series, tag_old, tag_new) -> campaign log ratio, from the series_json of the event files."""
    out: dict[tuple[str, str, str, str], float] = {}
    for df in frames:
        if "series_json" not in df.columns:
            continue
        for _, e in df.iterrows():
            for s in json.loads(str(e.series_json)):
                out[(str(e.event_id), str(s["series"]), str(s["tag_old"]), str(s["tag_new"]))] = float(s["log_ratio"])
    return out


def power_macros(noise: pd.DataFrame, series_df: pd.DataFrame, noise_ids: dict[str, list[str]],
                 pair_lr: dict[tuple[str, str, str, str], float], aa_ids: list[str], z: float, n_side: int,
                 src_noise: str, src_se: str) -> list[Macro]:
    """Minimum detectable effect, the A/A interval and the split of noise verdicts.

    MDE of a series: exp(z * s * sqrt(2 / n)) - 1 with s = sigma_fixed of the noise model (a lower
    bound, since the judge uses max(sigma_fixed, own SD)); this is the smallest change whose
    estimate reaches |z| = z (50% power), and with z + 0.84 the change detected with 80% power.
    A noise event is refuted when every listed series has its campaign log ratio (same tag pair)
    outside fixed_lr +- z * fixed_se, and inconclusive otherwise (or without a usable row).

    Args:
        noise: noise_model_v11.csv.
        series_df: judge_v11_series.csv.
        noise_ids: {"" : step-1 noise ids, "Cp": CP noise ids}.
        pair_lr: Output of campaign_pair_lr.
        aa_ids: A/A control event ids.
        z: Judge z threshold.
        n_side: Fixed-phase runs per side.
        src_noise: Display path of the noise model.
        src_se: Display path of the series file.

    Returns:
        Macros mde*, aa*, nNoiseRefuted*, nNoiseInconclusive*.
    """
    k = math.sqrt(2.0 / n_side)
    mde = np.expm1(z * noise.sigma_fixed.astype(float) * k) * 100
    mde80 = np.expm1((z + Z_POWER80) * noise.sigma_fixed.astype(float) * k) * 100
    tg = noise.test.astype(str) == "tg128"
    lab = noise.model + "/" + noise.backend + "/" + noise.test
    out = [
        Macro("mdeMin", str(round(float(mde.min()))), src_noise,
              f"min over series of exp({_num(z)} sigma_fixed sqrt(2/{n_side})) - 1 (%), {lab[mde.idxmin()]}"),
        Macro("mdeMax", str(round(float(mde.max()))), src_noise, f"same, max ({lab[mde.idxmax()]})"),
        Macro("mdePpMin", str(round(float(mde[~tg].min()))), src_noise, "same, min over pp512 series"),
        Macro("mdePpMax", str(round(float(mde[~tg].max()))), src_noise, "same, max over pp512 series"),
        Macro("mdeTgMin", str(round(float(mde[tg].min()))), src_noise, "same, min over tg128 series"),
        Macro("mdeTgMax", str(round(float(mde[tg].max()))), src_noise, "same, max over tg128 series"),
        Macro("mdePowerMin", str(round(float(mde80.min()))), src_noise,
              f"min over series of exp(({_num(z)} + 0.84) sigma_fixed sqrt(2/{n_side})) - 1 (%), 80% power"),
        Macro("mdePowerMax", str(round(float(mde80.max()))), src_noise, "same, max"),
        Macro("powerRunsPerSide", str(n_side), src_noise, "fixed-phase runs per side used for the MDE"),
    ]
    need = {"fixed_lr", "fixed_se", "listed", "tag_a", "tag_b"}
    if not need <= set(series_df.columns):
        logger.warning("judge series file lacks %s; noise split and A/A width skipped", need - set(series_df.columns))
        return out
    aa = series_df[series_df.event_id.isin(aa_ids)]
    if len(aa):
        hw = np.expm1(z * aa.fixed_se.astype(float)) * 100
        n = len(aa)
        out += [Macro("aaHalfWidthMin", str(round(float(hw.min()))), src_se,
                      f"min over A/A series of exp({_num(z)} fixed_se) - 1 (%): half-width of the +-z SE interval"),
                Macro("aaHalfWidthMax", str(round(float(hw.max()))), src_se, "same, max"),
                Macro("aaFpUpperPct", str(round(100 * (1 - 0.05 ** (1 / n)))), src_se,
                      f"exact one-sided 95% upper bound on the per-series false-positive rate after 0 of {n}: "
                      f"1 - 0.05^(1/{n}) (%)")]
    mde_lr = dict(zip(lab, z * noise.sigma_fixed.astype(float) * k))  # MDE of each series in log space
    total_ref = total_inc = rows_out = rows_all = 0
    below_mde = 0  # inconclusive step-1 events whose listed campaign changes are all below the series MDE
    for suffix, ids in noise_ids.items():
        ref = 0
        for e in ids:
            rows = series_df[(series_df.event_id == e) & (series_df.listed == 1)]
            ok, small = [], []
            for r in rows.itertuples():
                c = pair_lr.get((e, str(r.series), str(r.tag_a), str(r.tag_b)))
                if c is None or pd.isna(r.fixed_lr) or pd.isna(r.fixed_se):
                    continue
                ok.append(abs(c - float(r.fixed_lr)) > z * float(r.fixed_se))
                small.append(abs(c) < mde_lr.get(str(r.series), float("inf")))
            refuted = bool(ok) and all(ok)
            ref += int(refuted)
            if not suffix and not refuted and small and all(small):
                below_mde += 1
            rows_out += sum(ok)
            rows_all += len(ok)
        total_ref += ref
        total_inc += len(ids) - ref
        what = "CP" if suffix else "step-1"
        out += [Macro(f"nNoiseRefuted{suffix}", str(ref), src_se,
                      f"{what} noise events whose listed series all have the campaign lr outside fixed_lr +- "
                      f"{_num(z)} fixed_se"),
                Macro(f"nNoiseInconclusive{suffix}", str(len(ids) - ref), src_se, f"other {what} noise events")]
    out += [Macro("nInconclusiveBelowMde", str(below_mde), f"{src_se}, {src_noise}",
                  "inconclusive step-1 noise events whose campaign change is below the MDE in every listed series"),
            Macro("nNoiseRefutedAll", str(total_ref), src_se, "refuted step-1 and CP noise events"),
            Macro("nNoiseInconclusiveAll", str(total_inc), src_se, "inconclusive step-1 and CP noise events"),
            Macro("nNoiseRowsRefuted", str(rows_out), src_se,
                  "listed series rows of those events with the campaign lr outside fixed_lr +- z fixed_se"),
            Macro("nNoiseRows", str(rows_all), src_se, "listed series rows of those events with a usable judgement")]
    return out


def _judge_confirmed(series_df: pd.DataFrame, ids: list[str], judge: object, z: float, floor: float) -> set[str]:
    """Event ids (of ``ids``) with a listed series that the judge's ``confirms`` accepts at (z, floor)."""
    ns = argparse.Namespace(z_min=z, min_rel=floor)
    out: set[str] = set()
    rows = series_df[series_df.event_id.isin(ids) & (series_df.listed == 1)]
    for r in rows.itertuples():
        if pd.isna(r.step1_lr) or pd.isna(r.fixed_z) or r.fixed_n_a < 2 or r.fixed_n_b < 2:
            continue
        sign = 1.0 if r.step1_lr >= 0 else -1.0
        ok, _ = judge.confirms({"lr": float(r.fixed_lr), "z": float(r.fixed_z)}, sign, ns)  # type: ignore[attr-defined]
        if ok:
            out.add(str(r.event_id))
    return out


def threshold_sensitivity_macros(series_df: pd.DataFrame, step1_ids: list[str], cp_ids: list[str],
                                 aa_ids: list[str], vis: pd.DataFrame, judge: object, src: str,
                                 zs: tuple[float, ...] = SENS_Z, floors: tuple[float, ...] = SENS_FLOOR,
                                 default: tuple[float, float] | None = None) -> list[Macro]:
    """Confirmed events, visible cells and covering-set size when the judge's z and floor vary.

    Confirmation re-applies ``step2b_judge.confirms`` to the fixed-phase lr and z of every listed
    series (lr, s and z do not depend on the thresholds, so this equals re-running the judge with
    ``--z-min`` and ``--min-rel``); visibility re-applies the two-sided rule to the lr and z of
    step4_visibility.csv (excluded cells stay excluded).

    Args:
        series_df: judge_v11_series.csv.
        step1_ids: Step-1 candidate ids.
        cp_ids: CP event ids.
        aa_ids: A/A ids.
        vis: Visibility frame after exclusions.
        judge: The step2b_judge module.
        src: Display path.
        zs: z thresholds.
        floors: Floors (fractions).
        default: (z, floor) of the paper, checked against the main judge when given.

    Returns:
        Macros sens<Kind>Z<z>Floor<floor> and the ranges sens<Kind>Min/Max.
    """
    need = {"fixed_lr", "fixed_z", "step1_lr", "fixed_n_a", "fixed_n_b", "listed"}
    if not need <= set(series_df.columns):
        logger.warning("judge series file lacks %s; threshold sensitivity skipped", need - set(series_df.columns))
        return []
    out: list[Macro] = []
    acc: dict[str, list[int]] = {k: [] for k in ("Conf", "Cp", "AA", "VisPp", "VisTg", "Cover")}
    for z in zs:
        for fl in floors:
            conf = _judge_confirmed(series_df, step1_ids, judge, z, fl)
            cpc = _judge_confirmed(series_df, cp_ids, judge, z, fl)
            aa = series_df[series_df.event_id.isin(aa_ids)]
            afp = int(((aa.fixed_z.abs() >= z) & (aa.fixed_lr.abs() >= math.log1p(fl))).sum())
            v = vis.copy()
            meas = v.state.isin(VISIBLE_STATES + ("none",))
            hit = meas & (v.z.abs() >= z) & (np.log1p(v.lr_pct / 100).abs() >= math.log1p(fl))
            v.loc[meas, "state"] = np.where(hit[meas], np.where(v.lr_pct[meas] > 0, "up", "down"), "none")
            tg = v.series.str.endswith("/tg128")
            vis_ok = v.state.isin(VISIBLE_STATES)
            k = cover(v)["k"]
            tag = f"Z{Z_WORD[z]}Floor{FLOOR_WORD[fl]}"
            vals = {"Conf": len(conf), "Cp": len(cpc), "AA": afp, "VisPp": int((vis_ok & ~tg).sum()),
                    "VisTg": int((vis_ok & tg).sum()), "Cover": int(k)}
            for kind, val in vals.items():
                acc[kind].append(val)
                out.append(Macro(f"sens{kind}{tag}", str(val), src, f"{kind} at z = {_num(z)}, floor = {_pct(fl)}%"))
            if default is not None and (z, fl) == default:
                main = series_df[series_df.event_id.isin(step1_ids) & (series_df.verdict == "C")].event_id.nunique()
                if main != len(conf):
                    raise ValueError(f"re-applied judge confirms {len(conf)} events, the judge file {main}")
    for kind, vals in acc.items():
        out += [Macro(f"sens{kind}Min", str(min(vals)), src, f"min of {kind} over the z x floor grid"),
                Macro(f"sens{kind}Max", str(max(vals)), src, f"max of {kind} over the z x floor grid")]
    # A floor decides a judgment only where |z| passes but |lr| is below the floor.  With this noise
    # floor none does, so in effect only z varies; compute_all checks it.
    fx = series_df.dropna(subset=["fixed_se", "fixed_z", "fixed_lr"])
    vm = vis[vis.state.isin(VISIBLE_STATES + ("none",))]
    binding = 0
    for z in zs:
        for fl in floors:
            binding += int(((fx.fixed_z.abs() >= z) & (fx.fixed_lr.abs() < math.log1p(fl))).sum())
            binding += int(((vm.z.abs() >= z) & (np.log1p(vm.lr_pct / 100).abs() < math.log1p(fl))).sum())
    out.append(Macro("sensFloorBindings", str(binding), src,
                     "judgments (series rows and visibility cells, summed over the grid) that a floor decides"))
    if len(fx):
        min_pass = float(np.expm1(min(zs) * fx.fixed_se.astype(float).min()) * 100)
        out.append(Macro("sensMinPassPct", str(round(min_pass)), src,
                         f"smallest change that can reach |z| = {_num(min(zs))} over all {len(fx)} judged fixed-phase "
                         f"rows (%): exp(z * min fixed_se) - 1"))
    grid = "scripts/paper/make_numbers.py SENS_Z, SENS_FLOOR"
    out += [Macro("sensZList", and_list([_num(z) for z in zs]), grid, "z thresholds of the grid"),
            Macro("sensFloorList", and_list([_pct(fl) for fl in floors]), grid, "floors of the grid (%)"),
            Macro("sensZLow", _num(min(zs)), grid, "lowest z of the grid"),
            Macro("sensZHigh", _num(max(zs)), grid, "highest z of the grid"),
            Macro("nSensSettings", number_word(len(zs) * len(floors)).lower(), grid,
                  "number of (z, floor) settings, as a word"),
            Macro("nSensZ", number_word(len(zs)).lower(), grid, "number of z thresholds of the grid, as a word")]
    return out


def _spearman(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    """Spearman rho and its two-sided p-value (normal approximation, rho * sqrt(n - 1))."""
    rho = float(x.rank().corr(y.rank()))
    n = len(x)
    p = math.erfc(abs(rho) * math.sqrt(max(n - 1, 0)) / math.sqrt(2)) if n > 2 and not math.isnan(rho) else math.nan
    return rho, p


def drift_macros(root: Path, judge: object, cp_events: pd.DataFrame) -> list[Macro]:
    """Campaign deviation from the re-measured level against measurement time and idle share.

    Residual of a (release, series): campaign statistic y (ln median, as in the judge) minus the mean
    y of the default-phase re-runs of the same binary (same configuration, measured in later
    sessions and out of release order), so the version effect is removed.  For each series, Spearman
    rho of the residual with the hours since the start of the campaign and with the idle share
    recorded before the campaign run.  Also: minutes between the campaign runs of the two releases
    of every CP event (the model and back end of its series).

    Args:
        root: Project root.
        judge: The step2b_judge module (collect, campaign_value).
        cp_events: changepoint_events.csv.

    Returns:
        Macros drift*, or an empty list without re-runs or runs.tsv files.
    """
    res_dir, il = root / "results", root / "results" / "analysis" / "interleaved"
    values, _ = judge.collect(il)  # type: ignore[attr-defined]
    vdf = pd.DataFrame([v.__dict__ for v in values])
    if vdf.empty or not (vdf.phase == "default").any():
        logger.warning("no default-phase re-runs; drift macros skipped")
        return []
    rerun = vdf[vdf.phase == "default"].groupby(["tag", "model", "backend", "test"]).y.mean()
    prog = pd.read_csv(res_dir / "progress.csv")
    rows = []
    for tag in prog.tag.astype(str):
        f = res_dir / tag / "runs.tsv"
        if not f.is_file():
            continue
        for r in pd.read_csv(f, sep="\t").itertuples():
            if int(r.exit_code) != 0:
                continue
            for test in TESTS:
                y = judge.campaign_value(res_dir, tag, r.model, r.backend, test)  # type: ignore[attr-defined]
                if y is None:
                    continue
                rows.append({"tag": tag, "model": r.model, "backend": r.backend, "test": test, "y": y,
                             "t": pd.Timestamp(r.started_at_utc), "idle": float(r.idle_pct_before)})
    camp = pd.DataFrame(rows)
    if camp.empty:
        logger.warning("no campaign runs.tsv; drift macros skipped")
        return []
    t0 = camp.t.min()
    camp["h"] = (camp.t - t0).dt.total_seconds() / 3600
    key = list(zip(camp.tag, camp.model, camp.backend, camp.test))
    camp["res"] = [y - rerun[k] if k in rerun.index else math.nan for y, k in zip(camp.y, key)]
    m = camp.dropna(subset=["res"])
    rt, ri, ns = [], [], []
    for _, g in m.groupby(["model", "backend", "test"]):
        if len(g) < 5:
            continue
        rt.append(_spearman(g.h, g.res))
        ri.append(_spearman(g.idle, g.res))
        ns.append(len(g))
    src = "results/<tag>/runs.tsv + campaign JSON + default re-runs in results/analysis/interleaved/"
    if not rt:
        return []
    out = [
        Macro("driftSeries", str(len(rt)), src, "series with at least 5 releases that have a default re-run"),
        Macro("driftReleasesMin", str(min(ns)), src, "fewest releases with a re-run in one series"),
        Macro("driftReleasesMax", str(max(ns)), src, "most releases with a re-run in one series"),
        Macro("driftRhoTimeMin", signed_num(min(r for r, _ in rt), 2), src,
              "smallest Spearman rho of residual (campaign y - re-run y) vs hours since campaign start"),
        Macro("driftRhoTimeMax", signed_num(max(r for r, _ in rt), 2), src, "largest such rho"),
        Macro("driftRhoTimeMedian", signed_num(float(np.median([r for r, _ in rt])), 2), src,
              "median such rho over the series"),
        Macro("driftTimeSig", str(sum(p < 0.05 for _, p in rt)), src,
              "series with p < 0.05 for rho(time) (normal approximation rho sqrt(n-1))"),
        Macro("driftRhoIdleMin", signed_num(min(r for r, _ in ri), 2), src,
              "smallest Spearman rho of the residual vs idle share before the campaign run"),
        Macro("driftRhoIdleMax", signed_num(max(r for r, _ in ri), 2), src, "largest such rho"),
        Macro("driftRhoIdleMedian", signed_num(float(np.median([r for r, _ in ri])), 2), src,
              "median such rho over the series"),
        Macro("driftIdleSig", str(sum(p < 0.05 for _, p in ri)), src, "series with p < 0.05 for rho(idle)"),
        Macro("driftIdlePos", str(sum(r > 0 for r, _ in ri)), src,
              "series with rho(idle) > 0 (campaign slower than the re-run when the machine was busier)"),
    ]
    gaps = []
    for e in cp_events.itertuples():
        for s in json.loads(str(e.series_json)):
            mo, b, _ = str(s["series"]).split("/")
            g = camp[(camp.model == mo) & (camp.backend == b)]
            to, tn = g[g.tag == str(e.tag_old)].t, g[g.tag == str(e.tag_new)].t
            if len(to) and len(tn):
                gaps.append((tn.min() - to.min()).total_seconds() / 60)
    if gaps:
        out += [Macro("cpGapMinutesMin", str(round(min(gaps))), src,
                      "fewest minutes between the campaign runs of the two releases of a CP event (same model, back end)"),
                Macro("cpGapMinutesMax", str(round(max(gaps))), src, "most such minutes")]
    return out


def recovery_macros(root: Path, confirmed: list[str], cand: pd.DataFrame, vis: pd.DataFrame, judge: object,
                    floor: float, src: str) -> list[Macro]:
    """Whether each confirmed change persists in the later sampled releases of the campaign.

    For every visible series (after exclusions) the reference is the campaign statistic of the older
    release of the event.  A regression is back at the first later sampled release in which every
    visible series is within ln(1 + floor) of (or above) its reference; an improvement is kept when
    every visible series is still above its reference by more than ln(1 + floor) in the newest sampled
    release.  Campaign data: one pass, each release with its own defaults.

    Returns:
        Macros campNewestTag, e<Ev>CampFate (text), e<Ev>CampFateDays and, for regressions not back,
        e<Ev>CampOpenDays (days from the newer end of the event to the newest sampled release).
    """
    rel_p, prog_p = root / "data" / "releases.csv", root / "results" / "progress.csv"
    if not (rel_p.is_file() and prog_p.is_file()):
        return []
    rel = pd.read_csv(rel_p)
    date = dict(zip(rel.tag.astype(str), pd.to_datetime(rel.commit_date_utc, utc=True)))
    prog = pd.read_csv(prog_p)
    tags = sorted((str(t) for t, s in zip(prog.tag, prog.status) if s == "ok"), key=lambda t: int(t.lstrip("b")))
    if not tags:
        return []
    newest = tags[-1]
    out = [Macro("campNewestTag", newest, _rel(prog_p, root), "newest sampled release that built")]
    c = cand.set_index("event_id")
    thr = math.log1p(floor)
    for ev in confirmed:
        if ev not in c.index:
            continue
        g = vis[(vis.event_id == ev) & vis.state.isin(VISIBLE_STATES)]
        if g.empty:
            continue
        to, tn = str(c.at[ev, "tag_old"]), str(c.at[ev, "tag_new"])
        later = [t for t in tags if int(t.lstrip("b")) > int(tn.lstrip("b"))]
        sign = 1 if (g.lr_pct > 0).sum() >= len(g) / 2 else -1
        dev: dict[str, list[float]] = {t: [] for t in later}
        for s in g.series:
            mo, b, te = str(s).split("/")
            ref = judge.campaign_value(root / "results", to, mo, b, te)  # type: ignore[attr-defined]
            for t in later:
                y = judge.campaign_value(root / "results", t, mo, b, te)  # type: ignore[attr-defined]
                if ref is not None and y is not None:
                    dev[t].append(y - ref)
        p = macro_prefix(ev)
        if sign < 0:
            back = next((t for t in later if dev[t] and len(dev[t]) == len(g) and all(d >= -thr for d in dev[t])),
                        None)
            if back:
                days = round((date[back] - date[tn]).total_seconds() / 86400) if back in date and tn in date else 0
                out += [Macro(f"{p}CampFate", f"back at {back}", src, f"first later sample with every visible series "
                              f"within {_pct(floor)}% of {to} or above"),
                        Macro(f"{p}CampFateDays", str(days), src, f"days from {tn} to {back} (commit dates)")]
            else:
                days = round((date[newest] - date[tn]).total_seconds() / 86400) if tn in date else 0
                out += [Macro(f"{p}CampFate", "not back", src,
                              f"no later sample up to {newest} has every visible series within {_pct(floor)}% of {to}"),
                        Macro(f"{p}CampOpenDays", str(days), src, f"days from {tn} to {newest} (commit dates)")]
        else:
            last = dev.get(newest, [])
            kept = bool(last) and all(d > thr for d in last)
            out.append(Macro(f"{p}CampFate", "kept" if kept else "not kept", src,
                             f"every visible series above its {to} level by more than {_pct(floor)}% in {newest}"))
    return out


def eone_recheck_macros(root: Path, runs: pd.DataFrame) -> list[Macro]:
    """The 2026-10-26 re-checks of E01 on Mistral-7B CPU pp512 (bisection E01cpu and harness_check_E01).

    Days from the measurement dates of E01 and E01R (last fixed run in interleaved/<dir>/runs.tsv) to
    the first run of the E01cpu bisection; its measured change (step 1, ts_hi / ts_lo - 1) and the
    reference effect (ref_lr); the change of the harness check (mean of the pp512 medians of the newer
    release over that of the older, all its non-warm-up runs) and its number of rounds.
    """
    an = root / "results" / "analysis"
    cpu = runs[(runs.run_id == "E01cpu")]
    if cpu.empty:
        return []
    d = an / "bisect" / str(cpu.iloc[0].dir)
    out: list[Macro] = []
    try:
        bis = pd.read_csv(d / "runs.tsv", sep="\t")
        steps = pd.read_csv(d / "steps.csv")
    except (OSError, ValueError) as exc:
        logger.warning("E01cpu bisection files unreadable: %s", exc)
        return []
    t_bis = pd.to_datetime(bis.started_at_utc, utc=True).min()
    days = []
    for name in ("E01", "E01R"):
        hit = sorted(an.glob(f"interleaved/{name}_*/runs.tsv"))
        if hit:
            t = pd.to_datetime(pd.read_csv(hit[0], sep="\t").started_at_utc, utc=True).max()
            days.append((t_bis.normalize() - t.normalize()).days)
    src = "results/analysis/bisect/E01cpu_*/ + interleaved/E01*_*/runs.tsv"
    if days:
        out += [Macro("eOneRecheckDaysMin", str(min(days)), src, "days from E01R (last run) to the E01cpu bisection"),
                Macro("eOneRecheckDaysMax", str(max(days)), src, "days from E01 (last run) to the E01cpu bisection")]
    s1 = steps.sort_values("step").iloc[0]
    out += [Macro("eOneCpuBisectPct", signed_num(_pct_change(float(s1.ts_lo), float(s1.ts_hi)), 1), src,
                  "step 1 of E01cpu: ts_hi / ts_lo - 1 (%), one decimal"),
            Macro("eOneCpuRefPct", signed_pct(100 * math.expm1(-abs(float(cpu.iloc[0].ref_lr)))), src,
                  "reference effect of E01cpu: exp(-|ref_lr|) - 1 (%)")]
    hc = an / "harness_check_E01"
    if hc.is_dir():
        vals: dict[str, list[float]] = {}
        for f in sorted(hc.glob("r*_b*_n*.json")):
            tag = f.name.split("_")[1]
            v = run_value(hc, f.name, "pp512")
            if not math.isnan(v):
                vals.setdefault(tag, []).append(v)
        if len(vals) == 2:
            old, new = sorted(vals, key=lambda t: int(t.lstrip("b")))
            out.append(Macro("eOneHarnessPct", signed_pct(_pct_change(float(np.mean(vals[old])),
                                                                      float(np.mean(vals[new])))),
                             _rel(hc, root), f"mean pp512 median of {new} over {old} - 1 (%), all non-warm-up runs"))
            sh = hc / "run.sh"
            m = re.search(r"for r in ([\d ]+);", sh.read_text()) if sh.is_file() else None
            if m:
                out.append(Macro("eOneHarnessRounds", str(len(m.group(1).split())), _rel(sh, root),
                                 "rounds of the loop in run.sh"))
    return out


def borderline_macros(vis: pd.DataFrame, src: str, z: float) -> list[Macro]:
    """Not-visible cells close to the rule: |z| in BORDER_Z, and those with |change| >= LARGE_CELL_PCT."""
    meas = vis[vis.state == "none"]
    bl = meas[(meas.z.abs() >= BORDER_Z[0]) & (meas.z.abs() < BORDER_Z[1])]
    big = meas[meas.lr_pct.abs() >= LARGE_CELL_PCT]

    def fmt(df: pd.DataFrame) -> str:
        items = [f"{r.event_id} on {series_text(str(r.series))} ({signed_pct(float(r.lr_pct))}\\%, "
                 f"$z = {float(r.z):.2f}$)" for r in df.itertuples()]
        return "; ".join(items) if items else "none"

    big_tg = big[big.series.str.endswith("/tg128")]
    tg_meas = vis[vis.series.str.endswith("/tg128") & vis.state.isin(VISIBLE_STATES + ("none", "excluded"))]
    return [
        Macro("nTgCellsMeasured", str(len(tg_meas)), src, "tg128 cells measured on both sides (state up/down/none)"),
        Macro("nBorderlineCells", str(len(bl)), src, f"not-visible cells with {BORDER_Z[0]} <= |z| < {BORDER_Z[1]}"),
        Macro("borderlineCellList", fmt(bl), src, "those cells: event, series, change, z (two decimals)"),
        Macro("nLargeNotVisibleCells", str(len(big)), src,
              f"not-visible cells with |change| >= {_num(LARGE_CELL_PCT)}% (|z| < {_num(z)})"),
        Macro("nLargeNotVisibleCellsCap", number_word(len(big)), src, "that count as a capitalised word (sentence start)"),
        Macro("nLargeNotVisibleCellsTg", str(len(big_tg)), src, "of those, on tg128"),
        Macro("largeNotVisibleCellList", fmt(big), src, "those cells"),
        Macro("largeCellPct", _num(LARGE_CELL_PCT), "scripts/paper/make_numbers.py LARGE_CELL_PCT",
              "change (%) above which a not-visible cell is listed"),
    ]


def review_macros(root: Path, scripts: Path, cand: pd.DataFrame, cpev: pd.DataFrame, ev: pd.DataFrame,
                  se: pd.DataFrame, control: pd.DataFrame, vis_raw: pd.DataFrame,
                  excluded: tuple[tuple[str, str], ...], confirmed: list[str], runs: pd.DataFrame) -> list[Macro]:
    """Power, noise split, threshold sensitivity, drift, recovery, E01 re-check and borderline macros."""
    an = root / "results" / "analysis"
    s2, s2b = scripts / "analysis" / "step2_interleaved.py", scripts / "analysis" / "step2b_judge.py"
    z = float(argparse_default(s2b, "--z-min"))  # type: ignore[arg-type]
    floor = float(argparse_default(s2b, "--min-rel"))  # type: ignore[arg-type]
    n_side = int(argparse_default(s2, "--rounds"))  # type: ignore[call-overload]
    judge = load_judge(scripts)
    v = ev.set_index("event_id").verdict_v11.astype(str)
    step1, cps, aa = list(cand.event_id), list(cpev.event_id), list(control.event_id)
    noise_ids = {"": [e for e in step1 if v.get(e) == "noise"], "Cp": [e for e in cps if v.get(e) == "noise"]}
    vis = apply_exclusions(vis_raw, excluded)
    src_se = _rel(an / "interleaved" / "judge_v11_series.csv", root)
    out: list[Macro] = []
    nm = an / "interleaved" / "noise_model_v11.csv"
    if nm.is_file():
        out += power_macros(pd.read_csv(nm), se, noise_ids, campaign_pair_lr([cand, cpev]), aa, z, n_side,
                            _rel(nm, root), src_se)
    else:
        logger.warning("%s missing; power macros skipped", nm)
    if {"listed", "fixed_n_a", "fixed_n_b"} <= set(se.columns):
        judged = se[se.event_id.isin(step1 + cps + list(pd.read_csv(an / "remeasure_events.csv").event_id))
                    & (se.listed == 1) & (se.fixed_n_a >= 2) & (se.fixed_n_b >= 2)]
        out.append(Macro("nJudgedListedRows", str(len(judged)), src_se,
                         "listed series rows of step-1, CP and re-measure events with >= 2 fixed runs per side"))
    out += threshold_sensitivity_macros(se, step1, cps, aa, vis, judge,
                                        f"{src_se} + step4_visibility.csv, step2b_judge.confirms",
                                        default=(z, floor))
    out += drift_macros(root, judge, cpev)
    out += recovery_macros(root, confirmed, cand, vis, judge, floor,
                           "results/<tag>/<model>_<backend>.json (campaign) + step4_visibility.csv")
    out += eone_recheck_macros(root, runs)
    row = _judge_row(se, "E01", "mistral-7b/cpu/pp512") if "fixed_lr" in se.columns else None
    if row is not None:
        out += [Macro("eOneMistralCpuFirstPct", signed_pct(100 * math.expm1(float(row.fixed_lr))), src_se,
                      f"E01 (first re-measurement) x mistral-7b/cpu/pp512: exp(fixed_lr) - 1 (%), verdict {row.verdict}"),
                Macro("eOneMistralCpuFirstZ", signed_num(float(row.fixed_z)), src_se, "its fixed_z, one decimal")]
    out += borderline_macros(vis, _rel(an / "step4_visibility.csv", root), z)
    return out


def _t04_context_macros(root: Path, sw: Path) -> list[Macro]:
    """Why T04 measured tg128 alone: pp512 duration of b1561 over b1621 in E04's first re-measurement,
    and b1561's tg128 there (after pp512) and in T04 (alone), as geometric means of the run medians.

    Args:
        root: Repository root.
        sw: results/analysis/switch.

    Returns:
        swFourPpTimeRatio, swFourTgAfterPp, swFourTgAlone (none when a file is missing).
    """
    first = root / "results" / "analysis" / "interleaved" / "E04_b1561_b1621"
    alone = sw / "T04_mistral-7b_cpu_tg128"
    if not (first / "runs.tsv").is_file() or not (alone / "runs.tsv").is_file():
        return []

    def geo(d: Path, tag: str, test: str) -> float:
        with (d / "runs.tsv").open(newline="") as fh:
            rows = [r for r in csv.DictReader(fh, delimiter="\t")
                    if r["phase"] == "fixed" and r["tag"] == tag and r["model"] == "mistral-7b" and r["backend"] == "cpu"]
        ys = [y for r in rows if (y := _run_log_median(d / r["json_file"], test)) is not None]
        return math.exp(sum(ys) / len(ys)) if ys else float("nan")

    pp_old, pp_new = geo(first, "b1561", "pp512"), geo(first, "b1621", "pp512")
    src, src_t = _rel(first / "runs.tsv", root), _rel(alone / "runs.tsv", root)
    return [Macro("swFourPpTimeRatio", f"{pp_new / pp_old:.1f}", src,
                  "pp512 test duration of b1561 over b1621 (inverse throughput ratio), E04 mistral-7b/cpu fixed phase"),
            Macro("swFourTgAfterPp", f"{geo(first, 'b1561', 'tg128'):.1f}", src,
                  "b1561 tg128 (tokens/s) in E04's first re-measurement, where it followed pp512 in the same run"),
            Macro("swFourTgAfterPpB", f"{geo(first, 'b1621', 'tg128'):.1f}", src, "the same for b1621"),
            Macro("swFourTgAlone", f"{geo(alone, 'b1561', 'tg128'):.1f}", src_t, "b1561 tg128 (tokens/s) in T04, alone"),
            Macro("swFourTgAloneB", f"{geo(alone, 'b1621', 'tg128'):.1f}", src_t, "the same for b1621")]


def _run_log_median(path: Path, test: str) -> float | None:
    """ln(median samples_ts) of one llama-bench JSON for pp512 or tg128 (None if absent)."""
    try:
        text = path.read_text(errors="replace")
        recs = json.loads(text[text.find("["):])
    except (OSError, json.JSONDecodeError):
        return None
    want = (512, 0) if test == "pp512" else (0, 128)
    for r in recs if isinstance(recs, list) else []:
        if (r.get("n_prompt"), r.get("n_gen")) == want and r.get("samples_ts"):
            s = sorted(float(x) for x in r["samples_ts"] if x > 0)
            if s:
                return math.log(float(np.median(s)))
    return None


SWITCH_EXP_WORD = {"S19": "Nineteen", "S46": "FortySix", "T04": "Four", "T50": "Fifty"}
SWITCH_MODEL_WORD = {"tinyllama-1.1b": "Tiny", "qwen2.5-1.5b": "Qwen", "mistral-7b": "Mistral"}
SWITCH_FIRST = {"T04": ("E04", "mistral-7b/cpu/tg128"), "T50": ("E50", "mistral-7b/metal/pp512")}


def switch_macros(root: Path, se: pd.DataFrame) -> list[Macro]:
    """Switch controls (S19, S46) and cell re-tests (T04, T50) of step 3b, and the path check.

    Comparisons X -> Y of ``results/analysis/switch/comparisons.csv``: sw<Exp><Model><Y><X> is the
    change (%) of arm Y over arm X and ...Z its z (one decimal); for S19/S46 the series is CPU pp512,
    for T04/T50 the single re-tested cell (no model word).  sw<Exp><Model>Recovered is the share of
    the A -> B change that arm C recovers (%).  The path check gives the back end of the matrix
    multiplications of the measured Mistral-7B batch.  The first measurement of the two re-tested
    cells (judge_v11_series.csv) gets ...FirstPct and ...FirstZ.

    Args:
        root: Repository root.
        se: judge_v11_series.csv.

    Returns:
        The macros (none when step 3b has not run).
    """
    sw = root / "results" / "analysis" / "switch"
    cmp_path, path_csv = sw / "comparisons.csv", sw / "path_summary.csv"
    if not cmp_path.is_file():
        return []
    src, src_p = _rel(cmp_path, root), _rel(path_csv, root)
    cmp_ = pd.read_csv(cmp_path)
    out: list[Macro] = []
    for r in cmp_.itertuples():
        exp, series = str(r.exp), str(r.series)
        model = series.split("/")[0]
        name = "sw" + SWITCH_EXP_WORD[exp] + ("" if exp.startswith("T") else SWITCH_MODEL_WORD[model])
        if r.x == "R":
            out.append(Macro(name + "Recovered", str(round(100 * float(r.lr))), src,
                             f"{series}: (mean y_C - mean y_B) / (mean y_A - mean y_B), %"))
            continue
        pair = f"{r.y}{r.x}"
        out += [Macro(name + pair, signed_pct(100 * math.expm1(float(r.lr))), src,
                      f"{series}: change of arm {r.y} over arm {r.x} (%), n = {int(r.n_y)}/{int(r.n_x)} runs"),
                Macro(name + pair + "Z", signed_num(float(r.z), 1), src, f"{series}: z of that change")]
    nowin_path = root / "results" / "analysis" / "interleaved" / "judge_v11_series_nowin.csv"
    nowin = pd.read_csv(nowin_path) if nowin_path.is_file() else None
    for exp, (ev, series) in SWITCH_FIRST.items():
        hit = se[(se.event_id == ev) & (se.series == series)]
        if len(hit) == 1:
            out += [Macro(f"sw{SWITCH_EXP_WORD[exp]}FirstPct", signed_pct(100 * math.expm1(float(hit.fixed_lr.iloc[0]))),
                          "results/analysis/interleaved/judge_v11_series.csv", f"{ev} x {series}: first re-measurement (%)"),
                    Macro(f"sw{SWITCH_EXP_WORD[exp]}FirstZ", f"{float(hit.fixed_z.iloc[0]):.2f}",
                          "results/analysis/interleaved/judge_v11_series.csv", f"{ev} x {series}: its z")]
        nw = nowin[(nowin.event_id == ev) & (nowin.series == series)] if nowin is not None else pd.DataFrame()
        if len(nw) == 1:
            out.append(Macro(f"sw{SWITCH_EXP_WORD[exp]}FirstNoWinZ", f"{float(nw.fixed_z.iloc[0]):.2f}",
                             _rel(nowin_path, root), f"{ev} x {series}: z of the first re-measurement without the runs "
                                                     "that overlapped outside load"))
    helps = sorted((p for p in (root / "results").glob("b*") if p.name[1:].isdigit() and
                    (p / "llama-bench_help.txt").is_file()), key=lambda p: int(p.name[1:]))
    m = re.search(r"--poll <0\.\.\.100>\s+\(default: (\d+)\)", (helps[-1] / "llama-bench_help.txt").read_text()) \
        if helps else None
    if m:
        out.append(Macro("pollDefaultNewest", m.group(1), _rel(helps[-1] / "llama-bench_help.txt", root),
                         f"default --poll level of the newest built release, {helps[-1].name}"))
    m2 = re.search(r"--repack <0\|1>\s+\(default: (\d)\)", (helps[-1] / "llama-bench_help.txt").read_text()) \
        if helps else None
    if m2:
        out.append(Macro("repackDefaultNewest", m2.group(1), _rel(helps[-1] / "llama-bench_help.txt", root),
                         f"default --repack of the newest built release, {helps[-1].name} (1 = on)"))
    plans = sorted((root / "results" / "analysis" / "interleaved").glob("*/plan.json"))
    groups = [(json.loads(pl.read_text())["event_id"], g.get("equivalent"))
              for pl in plans for g in json.loads(pl.read_text()).get("groups", [])]
    if groups:
        neq = [e for e, ok in groups if ok is False]
        out += [Macro("nGroupsAll", str(len(groups)), "results/analysis/interleaved/*/plan.json",
                      "re-measured (event, model, back end) groups"),
                Macro("nGroupsNotEquiv", str(len(neq)), "results/analysis/interleaved/*/plan.json",
                      f"groups whose fixed configurations could not be aligned (events: {sorted(set(neq))})"),
                Macro("nGroupsNotEquivWord", number_word(len(neq)).lower(), "results/analysis/interleaved/*/plan.json",
                      "the same count as a word")]
    out += _t04_context_macros(root, sw)
    arms = pd.read_csv(sw / "arms.csv")
    rounds = arms.groupby(["exp", "series"]).n.max()
    out += [Macro("swRoundsLong", str(int(rounds.max())), _rel(sw / "arms.csv", root), "rounds of the long groups"),
            Macro("swRoundsShort", str(int(rounds.min())), _rel(sw / "arms.csv", root), "rounds of the short groups")]
    if path_csv.is_file():
        ps = pd.read_csv(path_csv)
        counts = {str(r.log): ast.literal_eval(str(r.mul_mat_by_backend)) for r in ps.itertuples()}

        def blas(log: str) -> int:
            return int(counts[log].get("BLAS", 0))

        mm = {log: sum(c.values()) for log, c in counts.items()}
        old, new = "path_S46_mistral-7b_A_b7141.log", "path_S46_mistral-7b_B_b7142.log"
        off = "path_S46_mistral-7b_C_b7142-norepack.log"
        e19 = ("path_S19_mistral-7b_A_b3643.log", "path_S19_mistral-7b_B_b3644.log")
        if len({mm[old], mm[new], mm[off], mm[e19[0]], mm[e19[1]]}) != 1:
            raise ValueError("path check: the Mistral-7B batches differ in their number of matrix multiplications")
        if blas(e19[0]) != blas(e19[1]):
            raise ValueError("path check: b3643 and b3644 assign BLAS differently; revise the E19 text")
        out += [Macro("pathMulMats", str(mm[old]), src_p, "matrix multiplications of the measured Mistral-7B pp512 batch"),
                Macro("pathBlasOld", str(blas(old)), src_p, "of those on BLAS at b7141"),
                Macro("pathBlasNew", str(blas(new)), src_p, "of those on BLAS at b7142"),
                Macro("pathBlasNoRepack", str(blas(off)), src_p, "of those on BLAS at b7142 built without repacking"),
                Macro("pathBlasNineteen", str(blas(e19[0])), src_p, "of those on BLAS at b3643 and at b3644")]
    return out


def cost_macros(root: Path, cooldown_s: float) -> list[Macro]:
    """Machine time of the re-measurement and the bisection, from their run and build logs.

    Args:
        root: Project root.
        cooldown_s: Pause between two re-measurement runs (``step2_interleaved.py`` default).

    Returns:
        Macros; none (with a warning) when the logs are missing.
    """
    an = root / "results" / "analysis"
    inter = [pd.read_csv(f, sep="\t").assign(dir=f.parent.name) for f in sorted((an / "interleaved").glob("*/runs.tsv"))]
    bis = [pd.read_csv(f, sep="\t") for f in sorted((an / "bisect").glob("*/runs.tsv"))]
    builds = [pd.read_csv(f, sep="\t") for f in sorted((an / "bisect").glob("*/builds.tsv"))]
    if not inter or not bis or not builds:
        logger.warning("run or build logs missing; cost macros skipped")
        return []
    r, b, bu = pd.concat(inter), pd.concat(bis), pd.concat(builds)
    ok = r[r.exit_code == 0]
    per_event = ok.groupby("dir").wall_s.sum() / 60
    built = bu[bu.status == "built"]
    src_r = "results/analysis/interleaved/*/runs.tsv"
    src_b = "results/analysis/bisect/*/runs.tsv, builds.tsv"
    return [
        Macro("nRemeasureEvents", str(r.dir.nunique()), src_r, "event directories (step-1, CP, A/A, R and V events)"),
        Macro("nRemeasureRunsAll", f"{len(r):,}", src_r, "rows: every run, warm-up and default phase included"),
        Macro("remeasureRunHours", f"{r.wall_s.sum() / 3600:.1f}", src_r, "sum of wall_s, hours, one decimal"),
        Macro("remeasureCooldownHours", f"{len(r) * cooldown_s / 3600:.1f}", src_r,
              "runs x the pause between runs, hours, one decimal"),
        Macro("remeasureEventMinutes", str(round(float(per_event.median()))), src_r,
              "median over events of the summed wall_s of successful runs, minutes"),
        Macro("nBisectRunsAll", str(len(b)), src_b, "rows of the bisection run logs, warm-ups included"),
        Macro("bisectRunHours", f"{b.wall_s.sum() / 3600:.1f}", src_b, "sum of wall_s, hours, one decimal"),
        Macro("bisectBuildSeconds", str(round(float(built.seconds.median()))), src_b,
              "median build time of the successful builds, seconds"),
    ]


def and_list(items: list[str]) -> str:
    """['E01', 'E14', 'E44'] -> 'E01, E14 and E44'."""
    if len(items) <= 1:
        return "".join(items) or "none"
    return ", ".join(items[:-1]) + " and " + items[-1]


def load_window_macros(root: Path, cand: pd.DataFrame, ev: pd.DataFrame, vis: pd.DataFrame) -> list[Macro]:
    """Re-judgement without the runs that overlap a recorded window of outside load.

    Reads ``load_windows.tsv``, ``load_window_runs.tsv`` and ``load_window_bisect_steps.csv``
    (``scripts/analysis/load_window_check.py``) and ``judge_v11_*_nowin.csv``
    (``step2b_judge.py --exclude-windows results/analysis/load_windows.tsv --suffix _nowin``).
    An event counts as confirmed when its verdict or that of its re-measurement (E..R) is C.

    Args:
        root: Project root.
        cand: candidate_events.csv.
        ev: judge_v11_events.csv (main judgement).
        vis: step4_visibility.csv after exclusions (for the borderline cells).

    Returns:
        Macros; none (with a warning) when an input file is missing.
    """
    an = root / "results" / "analysis"
    il = an / "interleaved"
    files = [an / "load_windows.tsv", an / "load_window_runs.tsv", an / "load_window_bisect_steps.csv",
             il / "judge_v11_events_nowin.csv", il / "judge_v11_series_nowin.csv"]
    missing = [f for f in files if not f.is_file()]
    if missing:
        logger.warning("load-window files missing (%s); macros skipped", ", ".join(str(f) for f in missing))
        return []
    windows = pd.read_csv(files[0], sep="\t")
    runs = pd.read_csv(files[1], sep="\t")
    steps = pd.read_csv(files[2])
    evn, sen = pd.read_csv(files[3]), pd.read_csv(files[4])
    v = ev.set_index("event_id").verdict_v11.astype(str)
    vn = evn.set_index("event_id").verdict_v11.astype(str)
    step1 = list(cand.event_id)

    def confirmed(verd: pd.Series) -> list[str]:
        return sorted([e for e in step1 if verd.get(e) == "C" or verd.get(f"{e}R") == "C"], key=_event_key)

    main_c, nowin_c = confirmed(v), confirmed(vn)
    if main_c != nowin_c:
        logger.warning("confirmed events differ without the overlapping runs: %s vs %s", main_c, nowin_c)
    changed = [e for e in v.index if v[e] != vn.get(e, "")]
    to_incomplete = sorted([e for e in changed if vn.get(e) == "incomplete"], key=_event_key)
    other = [e for e in changed if vn.get(e) != "incomplete"]
    inter = runs[(runs.kind == "interleaved") & (runs.phase != "warmup")]
    src_w = "results/analysis/load_windows.tsv"
    src_r = "results/analysis/load_window_runs.tsv"
    src_n = "results/analysis/interleaved/judge_v11_*_nowin.csv"
    src_b = "results/analysis/load_window_bisect_steps.csv"
    meas = vis[vis.state == "none"]
    bl = meas[(meas.z.abs() >= BORDER_Z[0]) & (meas.z.abs() < BORDER_Z[1])]
    bl_z = []
    for r in bl.itertuples():
        hit = sen[(sen.event_id == r.event_id) & (sen.series == r.series)]
        if len(hit) == 1:
            bl_z.append(f"{float(hit.fixed_z.iloc[0]):.2f}")
    with_f = steps[steps.f.notna()]
    dev = float((with_f.f - with_f.f.round()).abs().max()) if len(with_f) else float("nan")
    return [
        Macro("nLoadWindows", str(len(windows)), src_w, "recorded windows of outside load"),
        Macro("nLoadWindowsOwn", str(int((windows.source == "this study").sum())), src_w,
              "of those, analysis jobs of this study on the measurement machine"),
        Macro("nLoadWindowRuns", str(len(inter)), src_r,
              "re-measurement runs (warm-ups excluded) that overlap a window"),
        Macro("nLoadWindowEvents", str(inter.dir.nunique()), src_r, "event directories with such runs"),
        Macro("nConfirmedNoWin", str(len(nowin_c)), src_n,
              "step-1 events confirmed (or re-measured and confirmed) without the overlapping runs"),
        Macro("loadWindowConfirmedSame", "yes" if main_c == nowin_c else "no", src_n,
              "whether that set equals the main set"),
        Macro("loadWindowIncompleteEvents", and_list(to_incomplete), src_n,
              "events whose verdict becomes incomplete (too few runs) without the overlapping runs"),
        Macro("nLoadWindowOtherChanges", str(len(other)), src_n,
              "events whose verdict changes to something other than incomplete"),
        Macro("loadWindowBorderlineZ", ", ".join(bl_z) if bl_z else "none", src_n,
              "fixed_z of the borderline visibility cells without the overlapping runs (two decimals)"),
        Macro("nLoadWindowBisectSteps", str(len(steps)), src_b,
              "bisection steps with an overlapping run that enters the step statistic"),
        Macro("nLoadWindowBisectLost", str(int((steps.verdict == "effect_lost").sum())), src_b,
              "of those, steps that lost the effect"),
        Macro("loadWindowBisectFDev", f"{math.ceil(dev * 100) / 100:.2f}", src_b,
              "largest distance of f from 0 or 1 among the other steps, rounded up to 0.01"),
    ]


# --------------------------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------------------------


def compute_all(root: Path, excluded: tuple[tuple[str, str], ...], scripts: Path = SCRIPTS) -> list[Macro]:
    """Compute every macro from the result files under ``root``.

    Args:
        root: Project root (contains results/).
        excluded: (event, series) cells not counted as visible.
        scripts: scripts/ directory whose defaults give the protocol constants.

    Returns:
        All macros in output order.

    Raises:
        FileNotFoundError: If a required result file is missing.
        ValueError: If two macros share a name or a name is not letters only.
    """
    an = root / "results" / "analysis"
    il = an / "interleaved"
    paths = {k: an / v for k, v in {
        "cand": "candidate_events.csv", "cps": "changepoints.csv", "cpev": "changepoint_events.csv",
        "rm": "remeasure_events.csv", "ctl": "control_events.csv", "vis": "step4_visibility.csv"}.items()}
    paths |= {"ev": il / "judge_v11_events.csv", "se": il / "judge_v11_series.csv",
              "ev1": il / "judge_v11_events_norm1.csv", "se1": il / "judge_v11_series_norm1.csv"}
    for p in paths.values():
        if not p.is_file():
            raise FileNotFoundError(p)
    r = {k: _rel(v, root) for k, v in paths.items()}
    cand = pd.read_csv(paths["cand"])
    cpev = pd.read_csv(paths["cpev"])
    ev, se = pd.read_csv(paths["ev"]), pd.read_csv(paths["se"])
    vis = read_visibility(paths["vis"])
    runs = read_bisect(an / "bisect")
    src_bis = _rel(an / "bisect", root) + "/*/result.json"
    confirmed = sorted([e for e in ev.loc[ev.verdict_v11 == "C", "event_id"]
                        if e in set(cand.event_id)], key=_event_key)
    macros = campaign_macros(root)
    macros += release_macros(root)
    macros += protocol_macros(scripts)
    macros += candidate_macros(cand, r["cand"])
    macros += changepoint_macros(pd.read_csv(paths["cps"]), cpev, r["cps"], r["cpev"])
    macros += judge_macros(ev, se, cand, cpev, pd.read_csv(paths["rm"]), pd.read_csv(paths["ctl"]), r["ev"], r["se"])
    macros += sensitivity_macros(ev, pd.read_csv(paths["ev1"]), se, pd.read_csv(paths["se1"]),
                                 f"{r['ev']} / {r['se']} vs *_norm1.csv")
    macros += visibility_macros(vis, excluded, r["vis"])
    macros += bisect_total_macros(runs, src_bis)
    macros += event_macros(confirmed, cand, vis, excluded, runs, r["cand"], r["vis"], src_bis)
    macros += boundary_macros(confirmed, runs, src_bis)
    macros += segment_macros(confirmed, runs, an / "bisect", _rel(an / "bisect", root) + "/<run>/steps.csv")
    macros += visibility_cell_macros(vis, r["vis"])
    macros += cover_series_macros(vis, excluded, r["vis"])
    macros += change_example_macros(cand, se, r["cand"], r["se"])
    macros += noise_example_macros(cand, se, r["se"])
    macros += bias_macros(first_run_bias(root), "results/analysis/interleaved/*/runs.tsv + llama-bench JSON")
    macros += lifetime_macros(root, runs)
    macros += category_macros(an / "root_cause_categories.csv", confirmed, root)
    macros += review_macros(root, scripts, cand, cpev, ev, se, pd.read_csv(paths["ctl"]), vis, excluded, confirmed,
                            runs)
    macros += load_window_macros(root, cand, ev, apply_exclusions(vis, excluded))
    macros += cost_macros(root, float(argparse_default(scripts / "analysis" / "step2_interleaved.py", "--cooldown")))
    macros += switch_macros(root, se)
    vals = {m.name: m.value for m in macros}
    if vals.get("sensFloorBindings", "0") != "0":  # the text says the floors changed nothing
        raise ValueError(f"a floor decides {vals['sensFloorBindings']} judgments; revise the threshold text")
    names = [m.name for m in macros]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise ValueError(f"duplicate macro names: {sorted(dup)}")
    bad = [n for n in names if not re.fullmatch(r"[A-Za-z]+", n)]
    if bad:
        raise ValueError(f"macro names must be letters only: {bad}")
    return macros


def render(macros: list[Macro]) -> str:
    """numbers.tex text: a header comment, then for each macro a comment line and one \\newcommand line."""
    lines = ["% Generated by scripts/paper/make_numbers.py; do not edit by hand.",
             ("% Rerun: taskpolicy -b nice -n 19 uv run --no-project --with pandas --with numpy python3 -I "
              "scripts/paper/make_numbers.py"), ""]
    for m in macros:
        lines.append(f"% {m.source}: {m.method}".replace("\n", " "))
        lines.append(f"\\newcommand{{\\{m.name}}}{{{m.value}}}")
    return "\n".join(lines) + "\n"


def parse_exclusion(text: str) -> tuple[str, str]:
    """'E01:mistral-7b/cpu/pp512' -> ('E01', 'mistral-7b/cpu/pp512').

    Raises:
        argparse.ArgumentTypeError: If the text is not EVENT:SERIES.
    """
    ev, sep, s = text.partition(":")
    if not sep or not ev or s.count("/") != 2:
        raise argparse.ArgumentTypeError(f"expected EVENT:model/backend/test, got {text!r}")
    return ev, s


def main(argv: list[str] | None = None) -> int:
    """Write numbers.tex; return 0 on success, 1 when a result file is missing."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=None, help="default: <root>/paper/numbers.tex")
    ap.add_argument("--exclude", type=parse_exclusion, action="append", default=None,
                    help="EVENT:model/backend/test cell to exclude (repeatable; replaces the default list)")
    ap.add_argument("--scripts", type=Path, default=SCRIPTS,
                    help="scripts/ directory read for the protocol constants (default: this repository's)")
    ap.add_argument("--no-default-exclusions", action="store_true", help="exclude nothing unless --exclude is given")
    ns = ap.parse_args(argv)
    excluded = tuple(ns.exclude) if ns.exclude else (() if ns.no_default_exclusions else DEFAULT_EXCLUDED_CELLS)
    try:
        macros = compute_all(ns.root, excluded, ns.scripts)
    except FileNotFoundError as exc:
        logger.error("missing result file: %s", exc)
        return 1
    out = ns.out or ns.root / "paper" / "numbers.tex"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(macros))
    logger.info("wrote %d macros to %s", len(macros), out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
