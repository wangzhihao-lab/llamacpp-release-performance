"""Unit tests for step3_bisect.py and the build-only mode of build_bench.sh.

Nothing here builds llama.cpp, runs llama-bench or uses the network: the bisection runs on fake
release lists with fake builds and a fake measurement function that writes llama-bench-like
JSON from a known step function, and build_bench.sh runs in a temporary root with stub curl and
cmake.  Covered: (a) a single step at every candidate position is located to the right adjacent
pair; (b) a failing build is skipped, counted, and its neighbor tried; (c) two stacked changes
give an intermediate step; (d) effect_lost stops the series; (e) an interrupted bisection resumes
without repeating runs or builds; plus commit-level bisection, step-2 input, the E49 dry run and
the build-only mode.

Run: uv run --no-project --with pytest --with pandas --with numpy python3 -I -m pytest -p no:cacheprovider scripts/analysis/test_step3_bisect.py -q
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import random
import shutil
import subprocess
import sys
import zlib
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
BASE = math.log(100.0)


def _load(name: str) -> ModuleType:
    """Import a sibling script by path (``python3 -I`` keeps this directory off sys.path)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


s3 = _load("step3_bisect")


# --------------------------------------------------------------------------- fakes


def make_releases(n: int, first: int = 1000) -> list[Any]:
    """n release points with gaps in the build numbers, like the real tag list."""
    out = []
    for i in range(n):
        number = first + i + i // 3
        out.append(s3.Point(f"b{number}", f"{i + 1:012x}" + "a" * 28, (number, 0)))
    return out


class FakeHooks(s3.Hooks):
    """Fake machine: binaries are a shared set, builds succeed unless listed, runs follow level_of."""

    def __init__(self, level_of: Callable[[Any], float], binaries: set[str], fail: set[str] | None = None,
                 stop_after_runs: int | None = None, stop_after_builds: int | None = None,
                 history: list[str] | None = None) -> None:
        self.level_of = level_of
        self.binaries = binaries
        self.fail = fail or set()
        self.stop_after_runs = stop_after_runs
        self.stop_after_builds = stop_after_builds
        self.history = history or []
        self.ctl: Any = None
        self.runs: list[tuple[int, int, str, str]] = []
        self.built: list[str] = []

    def have_binary(self, point: Any) -> bool:
        return point.name in self.binaries

    def known_build_failure(self, point: Any) -> str:
        return ""

    def build(self, point: Any, log_dir: Path) -> Any:
        self.built.append(point.name)
        if self.stop_after_builds is not None and len(self.built) >= self.stop_after_builds:
            self.ctl.stop = True
        if point.name in self.fail:
            return s3.BuildOutcome(False, "build_failed", 1.0, "fake compiler error")
        self.binaries.add(point.name)
        return s3.BuildOutcome(True, "built", 1.0)

    def caps(self, point: Any) -> Any:
        return s3.Caps(point.name, Path("/fake/bins") / point.name / "llama-bench",
                       metal_resources=f"/fake/bins/{point.name}")

    def measure(self, spec: Any) -> dict[str, Any]:
        self.runs.append((spec.step, spec.rnd, spec.role, spec.point.name))
        rng = random.Random(zlib.crc32(f"{spec.step}|{spec.rnd}|{spec.role}|{spec.point.name}".encode()))
        level = self.level_of(spec.point)
        samples = [math.exp(level + rng.gauss(0.0, 0.004)) for _ in range(5)]
        n_prompt, n_gen = (512, 0) if spec.test == "pp512" else (0, 128)
        spec.json_path.write_text(json.dumps([{"n_prompt": n_prompt, "n_gen": n_gen,
                                               "avg_ts": sum(samples) / len(samples), "samples_ts": samples}]))
        spec.log_path.write_text("")
        if self.stop_after_runs is not None and len(self.runs) >= self.stop_after_runs:
            self.ctl.stop = True
        return {"exit_code": 0, "settled": 1, "ok": 1}

    def time_left(self) -> float:
        return 1e9

    def sleep(self, seconds: float) -> None:
        return

    def first_parent_commits(self, base: str, hi: str) -> list[str]:
        return self.history[self.history.index(base) + 1:self.history.index(hi) + 1]

    def commit_log(self, lo: Any, hi: Any) -> list[dict[str, Any]]:
        return []


def step_at(rel: list[Any], changes: dict[int, float]) -> Callable[[Any], float]:
    """level_of for changes {release index: ln step} (a point carries every change at or before it)."""
    def level_of(point: Any) -> float:
        return BASE + sum(d for j, d in changes.items() if point.key >= rel[j].key)
    return level_of


def run_bisect(out: Path, rel: list[Any], hooks: FakeHooks, ref: float, *, sign: int = 1,
               extra: tuple[str, ...] = (), label: str = "T1", warmup: bool = False) -> dict[str, Any]:
    """Run (or resume) one fake bisection of rel[0] -> rel[-1] into out."""
    ns = s3.parse_args(["--lo", rel[0].name, "--hi", rel[-1].name, "--model", "mistral-7b", "--backend", "metal",
                        "--test", "pp512", "--direction", "up" if sign > 0 else "down", "--out", str(out),
                        *(() if warmup else ("--no-warmup",)), *extra])
    target = s3.Target(label, rel[0].name, rel[-1].name, "mistral-7b", "metal", "pp512", sign, ref, "test")
    ctl = s3.Control()
    hooks.ctl = ctl
    return s3.Bisector(target, ns, rel, hooks, ctl, out).run()


def steps_of(out: Path, label: str = "T1") -> list[dict[str, str]]:
    """Rows of steps.csv."""
    return s3.read_rows(out / f"{label}_mistral-7b_metal_pp512" / "steps.csv")


# --------------------------------------------------------------------------- pure functions


def test_median_order_alternates_left_then_right() -> None:
    assert s3.median_order(1) == [0]
    assert s3.median_order(4) == [1, 2, 0, 3]
    assert s3.median_order(5) == [2, 1, 3, 0, 4]
    assert s3.median_order(133)[:3] == [66, 65, 67]


def test_decide_thresholds() -> None:
    ns = s3.parse_args(["--lo", "b1", "--hi", "b2", "--model", "mistral-7b", "--backend", "metal", "--test",
                        "pp512", "--direction", "up"])
    lv = {"lo": 0.0, "hi": 0.6}
    assert s3.decide({**lv, "mid": 0.2}, 1, 0.6, ns).decision == "lo=mid"  # f = 0.33
    assert s3.decide({**lv, "mid": 0.4}, 1, 0.6, ns).decision == "hi=mid"  # f = 0.67
    mid = s3.decide({**lv, "mid": 0.27}, 1, 0.6, ns)  # f = 0.45
    assert (mid.verdict, mid.decision) == ("intermediate", "lo=mid")
    mid = s3.decide({**lv, "mid": 0.33}, 1, 0.6, ns)  # f = 0.55
    assert (mid.verdict, mid.decision) == ("intermediate", "hi=mid")
    assert s3.decide({"lo": 0.0, "hi": 0.29, "mid": 0.1}, 1, 0.6, ns).verdict == "effect_lost"  # < half
    assert s3.decide({"lo": 0.0, "hi": 0.6, "mid": 0.1}, -1, 0.6, ns).verdict == "effect_lost"  # wrong sign
    assert s3.decide({**lv, "mid": -0.3}, 1, 0.6, ns).note.startswith("mid outside")


def test_wait_quiet_gates_on_idle_thermal_and_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    def scripted(states: list[tuple[float, int, list[str]]]) -> None:
        seq = iter(states)
        current: dict[str, Any] = {}

        def idle() -> float:
            current["s"] = next(seq)
            return current["s"][0]

        monkeypatch.setattr(s3, "cpu_idle_pct", idle)
        monkeypatch.setattr(s3, "thermal_state", lambda: current["s"][1])
        monkeypatch.setattr(s3, "busy_processes", lambda: current["s"][2])

    monkeypatch.setattr(s3, "interruptible_sleep", lambda *_a: None)
    base = ["--lo", "b1", "--hi", "b2", "--model", "mistral-7b", "--backend", "metal", "--test", "pp512",
            "--direction", "up"]
    scripted([(50.0, 0, []), (95.0, 2, []), (95.0, 1, ["llama-server(7)"]), (95.0, 1, [])])
    _, settled, idle, therm = s3.wait_quiet(s3.parse_args(base), s3.Control())
    assert (settled, idle, therm) == (True, 95.0, 1)
    scripted([(95.0, 2, [])])
    _, settled, _, therm = s3.wait_quiet(s3.parse_args([*base, "--quiet-wait-max", "0"]), s3.Control())
    assert (settled, therm) == (False, 2)
    scripted([(95.0, 3, [])])
    _, settled, _, _ = s3.wait_quiet(s3.parse_args([*base, "--thermal-max", "-1"]), s3.Control())
    assert settled


# --------------------------------------------------------------------------- (a) single step


@pytest.mark.parametrize("j", range(1, 22))
def test_single_step_located_at_every_position(tmp_path: Path, j: int) -> None:
    rel = make_releases(22)  # 20 candidates between rel[0] and rel[21]
    hooks = FakeHooks(step_at(rel, {j: 0.6}), {rel[0].name, rel[-1].name})
    res = run_bisect(tmp_path, rel, hooks, 0.6)
    assert res["status"] == "located"
    assert (res["lo"], res["hi"]) == (rel[j - 1].name, rel[j].name)
    assert res["builds"] == len(hooks.built) <= math.ceil(math.log2(21))
    rows = steps_of(tmp_path)
    assert {r["verdict"] for r in rows} <= {"old", "new"}
    assert len(hooks.runs) == len(set(hooks.runs)) == 6 * len(rows)
    for r in rows:  # interleaving: round 1 lo, mid, hi; round 2 hi, mid, lo
        order = [(rnd, role) for (step, rnd, role, _) in hooks.runs if step == int(r["step"])]
        assert order == [(1, "lo"), (1, "mid"), (1, "hi"), (2, "hi"), (2, "mid"), (2, "lo")]


# --------------------------------------------------------------------------- (b) build failures


def test_failed_build_is_skipped_counted_and_neighbour_tried(tmp_path: Path) -> None:
    rel = make_releases(22)
    cands = rel[1:-1]
    first, second = (cands[i] for i in s3.median_order(len(cands))[:2])
    hooks = FakeHooks(step_at(rel, {15: 0.6}), {rel[0].name, rel[-1].name}, fail={first.name})
    res = run_bisect(tmp_path, rel, hooks, 0.6)
    assert res["status"] == "located"
    assert (res["lo"], res["hi"]) == (rel[14].name, rel[15].name)
    assert hooks.built[:2] == [first.name, second.name]
    assert res["builds"] == len(hooks.built)
    assert first.name in res["skipped"]
    rows = steps_of(tmp_path)
    assert (rows[0]["mid"], rows[0]["verdict"], rows[0]["decision"]) == (first.name, "build_failed", "skip")
    assert rows[1]["mid"] == second.name
    assert rows[1]["verdict"] in ("old", "new")
    builds = s3.read_rows(tmp_path / "T1_mistral-7b_metal_pp512" / "builds.tsv", "\t")
    assert [(b["tag"], b["ok"]) for b in builds][:2] == [(first.name, "0"), (second.name, "1")]


def test_failed_build_at_the_boundary_leaves_it_between_lo_and_hi(tmp_path: Path) -> None:
    rel = make_releases(22)
    hooks = FakeHooks(step_at(rel, {15: 0.6}), {rel[0].name, rel[-1].name}, fail={rel[15].name})
    res = run_bisect(tmp_path, rel, hooks, 0.6)
    assert res["status"] == "stopped_unbuildable"
    assert (res["lo"], res["hi"]) == (rel[14].name, rel[16].name)
    assert res["skipped"] == [rel[15].name]


def test_build_budget_stops_the_series(tmp_path: Path) -> None:
    rel = make_releases(22)
    hooks = FakeHooks(step_at(rel, {7: 0.6}), {rel[0].name, rel[-1].name})
    res = run_bisect(tmp_path, rel, hooks, 0.6, extra=("--max-builds", "2"))
    assert res["status"] == "stopped_max_builds"
    assert res["builds"] == len(hooks.built) == 2
    assert res["measured_steps"] == 2
    lo, hi = (int(res[k][1:]) for k in ("lo", "hi"))
    assert lo < int(rel[7].name[1:]) <= hi


# --------------------------------------------------------------------------- (c) intermediate


def test_two_stacked_changes_give_intermediate(tmp_path: Path) -> None:
    rel = make_releases(22)
    first_mid = rel[1:-1][s3.median_order(20)[0]]
    assert first_mid == rel[10]
    hooks = FakeHooks(step_at(rel, {4: 0.35, 16: 0.25}), {rel[0].name, rel[-1].name})
    res = run_bisect(tmp_path, rel, hooks, 0.6)
    rows = steps_of(tmp_path)
    assert (rows[0]["mid"], rows[0]["verdict"], rows[0]["decision"]) == (rel[10].name, "intermediate", "hi=mid")
    assert 0.35 < float(rows[0]["f"]) < 0.65
    assert res["intermediate"] == 1
    assert res["status"] == "located"
    assert (res["lo"], res["hi"]) == (rel[3].name, rel[4].name)
    log = (tmp_path / "T1_mistral-7b_metal_pp512" / "log.md").read_text()
    assert "intermediate" in log


# --------------------------------------------------------------------------- (d) effect_lost


def test_effect_lost_when_the_step_is_too_small(tmp_path: Path) -> None:
    rel = make_releases(22)
    hooks = FakeHooks(step_at(rel, {9: 0.2}), {rel[0].name, rel[-1].name})
    res = run_bisect(tmp_path, rel, hooks, 0.6)
    assert res["status"] == "effect_lost"
    rows = steps_of(tmp_path)
    assert [r["verdict"] for r in rows] == ["effect_lost"]
    assert len(hooks.built) == 1
    assert len(hooks.runs) == 6
    assert (res["lo"], res["hi"]) == (rel[0].name, rel[-1].name)


def test_effect_lost_on_the_wrong_direction(tmp_path: Path) -> None:
    rel = make_releases(22)
    hooks = FakeHooks(step_at(rel, {9: 0.6}), {rel[0].name, rel[-1].name})
    res = run_bisect(tmp_path, rel, hooks, 0.6, sign=-1)
    assert res["status"] == "effect_lost"
    assert [r["verdict"] for r in steps_of(tmp_path)] == ["effect_lost"]


def test_effect_lost_midway_after_splitting_three_changes(tmp_path: Path) -> None:
    # mid b(rel[10]) carries 0.45 of 0.6 -> new (f 0.75); then rel[5] carries 0.2 of 0.45 -> intermediate
    # (f 0.44, lo = mid); the remaining lo..hi difference 0.25 is below half the reference 0.6 -> effect_lost
    rel = make_releases(22)
    hooks = FakeHooks(step_at(rel, {5: 0.2, 8: 0.25, 15: 0.15}), {rel[0].name, rel[-1].name})
    res = run_bisect(tmp_path, rel, hooks, 0.6)
    assert res["status"] == "effect_lost"
    assert [r["verdict"] for r in steps_of(tmp_path)] == ["new", "intermediate", "effect_lost"]
    assert (res["lo"], res["hi"]) == (rel[5].name, rel[10].name)


# --------------------------------------------------------------------------- (e) resume


def test_warmup_run_precedes_each_step_and_changes_nothing(tmp_path: Path) -> None:
    rel = make_releases(22)
    level_of = step_at(rel, {7: 0.6})
    plain = FakeHooks(level_of, {rel[0].name, rel[-1].name})
    ref = run_bisect(tmp_path / "plain", rel, plain, 0.6)
    warm = FakeHooks(level_of, {rel[0].name, rel[-1].name})
    res = run_bisect(tmp_path / "warm", rel, warm, 0.6, warmup=True)
    assert (res["status"], res["lo"], res["hi"], res["builds"]) == (ref["status"], ref["lo"], ref["hi"], ref["builds"])
    rows = steps_of(tmp_path / "warm")
    for r in rows:  # the warm-up runs the first pending command (round 1: lo)
        order = [(rnd, role) for (step, rnd, role, _) in warm.runs if step == int(r["step"])]
        assert order == [(0, "warmup"), (1, "lo"), (1, "mid"), (1, "hi"), (2, "hi"), (2, "mid"), (2, "lo")]
    assert [r for r in warm.runs if r[2] != "warmup"] == plain.runs
    run_rows = s3.read_rows(tmp_path / "warm" / "T1_mistral-7b_metal_pp512" / "runs.tsv", "\t")
    assert sum(r["role"] == "warmup" for r in run_rows) == len(rows)


def test_warmup_is_repeated_after_a_resume(tmp_path: Path) -> None:
    rel = make_releases(22)
    level_of = step_at(rel, {7: 0.6})
    binaries = {rel[0].name, rel[-1].name}
    h1 = FakeHooks(level_of, binaries, stop_after_runs=4)  # warm-up and round 1 of step 1
    assert run_bisect(tmp_path, rel, h1, 0.6, warmup=True)["status"] == "incomplete"
    h2 = FakeHooks(level_of, binaries)
    run_bisect(tmp_path, rel, h2, 0.6, warmup=True)
    assert [(rnd, role) for (step, rnd, role, _) in h2.runs if step == 1] == [(0, "warmup"), (2, "hi"), (2, "mid"),
                                                                              (2, "lo")]


def test_resume_repeats_no_run_and_no_build(tmp_path: Path) -> None:
    rel = make_releases(22)
    level_of = step_at(rel, {7: 0.6})
    ref_hooks = FakeHooks(level_of, {rel[0].name, rel[-1].name})
    ref = run_bisect(tmp_path / "ref", rel, ref_hooks, 0.6)

    out = tmp_path / "resumed"
    binaries = {rel[0].name, rel[-1].name}
    h1 = FakeHooks(level_of, binaries, stop_after_runs=4)  # interrupted inside step 1
    r1 = run_bisect(out, rel, h1, 0.6)
    assert (r1["status"], r1["pause_reason"]) == ("incomplete", "signal")
    h2 = FakeHooks(level_of, binaries, stop_after_builds=1)  # interrupted right after a build
    r2 = run_bisect(out, rel, h2, 0.6)
    assert r2["status"] == "incomplete"
    assert len(h2.built) == 1
    h3 = FakeHooks(level_of, binaries)
    r3 = run_bisect(out, rel, h3, 0.6)

    assert (r3["status"], r3["lo"], r3["hi"]) == (ref["status"], ref["lo"], ref["hi"])
    assert (r3["builds"], r3["measured_steps"]) == (ref["builds"], ref["measured_steps"])
    runs = h1.runs + h2.runs + h3.runs
    assert len(runs) == len(set(runs))
    assert sorted(runs) == sorted(ref_hooks.runs)
    assert h1.built + h2.built + h3.built == ref_hooks.built
    keep = ("step", "lo", "mid", "hi", "build", "verdict", "decision")
    assert [{k: r[k] for k in keep} for r in steps_of(out)] == [{k: r[k] for k in keep} for r in steps_of(tmp_path / "ref")]
    run_rows = s3.read_rows(out / "T1_mistral-7b_metal_pp512" / "runs.tsv", "\t")
    assert len(run_rows) == len(ref_hooks.runs)

    h4 = FakeHooks(level_of, binaries)  # a finished series does nothing on a new start
    r4 = run_bisect(out, rel, h4, 0.6)
    assert (h4.runs, h4.built) == ([], [])
    assert (r4["status"], r4["lo"], r4["hi"]) == (r3["status"], r3["lo"], r3["hi"])
    log = (out / "T1_mistral-7b_metal_pp512" / "log.md").read_text()
    assert log.count("## Conclusion") == 1
    assert log.count("Paused") == 2


def test_resume_refuses_a_different_series_in_the_same_directory(tmp_path: Path) -> None:
    rel = make_releases(10)
    hooks = FakeHooks(step_at(rel, {3: 0.6}), {rel[0].name, rel[-1].name})
    run_bisect(tmp_path, rel, hooks, 0.6)
    with pytest.raises(ValueError, match="holds another bisection"):
        run_bisect(tmp_path, rel, FakeHooks(step_at(rel, {3: 0.6}), set(hooks.binaries)), 0.6, sign=-1)


# --------------------------------------------------------------------------- commit level


def test_commit_level_bisects_commits_between_adjacent_releases(tmp_path: Path) -> None:
    sha = [f"{k:012x}" + "c" * 28 for k in range(1, 9)]
    # history: r0 r1 c1 c2 c3 c4 r2 r3 (first-parent, oldest first)
    history = [sha[0], sha[1], sha[2], sha[3], sha[4], sha[5], sha[6], sha[7]]
    rel = [s3.Point("b2000", sha[0], (2000, 0)), s3.Point("b2001", sha[1], (2001, 0), commits_since_prev=1),
           s3.Point("b2002", sha[6], (2002, 0), commits_since_prev=5), s3.Point("b2003", sha[7], (2003, 0))]

    def level_of(point: Any) -> float:
        return BASE + (0.6 if history.index(point.commit) >= history.index(sha[4]) else 0.0)

    hooks = FakeHooks(level_of, {"b2000", "b2003"}, history=history)
    res = run_bisect(tmp_path / "commit", rel, hooks, 0.6, extra=("--commit-level",))
    assert res["status"] == "located"
    assert res["level"] == "commit"
    assert (res["lo"], res["hi"]) == (f"c{sha[3][:12]}", f"c{sha[4][:12]}")
    assert any(name.startswith("c") for name in hooks.built)

    plain = FakeHooks(level_of, {"b2000", "b2003"}, history=history)
    res = run_bisect(tmp_path / "release", rel, plain, 0.6)
    assert (res["status"], res["level"], res["lo"], res["hi"]) == ("located", "release", "b2001", "b2002")


# --------------------------------------------------------------------------- step-2 input and dry run


def test_from_step2_reads_c_series(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3, "INTERLEAVED", tmp_path)
    releases = s3.load_releases()
    by_name = {p.name: p for p in releases}
    ns = s3.parse_args(["--from-step2", "E49"])
    with pytest.raises(LookupError, match="no step-2 result"):
        s3.targets_from_step2(ns, by_name)
    event_dir = tmp_path / "E49_b8545_b8740"
    event_dir.mkdir()
    rows = [{"event_id": "E49", "tag_a": "b8545", "tag_b": "b8740", "series": "mistral-7b/metal/pp512",
             "listed": 1, "fixed_lr": 0.57, "fixed_tau": 0.1, "verdict": "C"},
            {"event_id": "E49", "tag_a": "b8545", "tag_b": "b8740", "series": "qwen2.5-1.5b/metal/pp512",
             "listed": 1, "fixed_lr": 0.55, "fixed_tau": 0.3, "verdict": "C"},
            {"event_id": "E49", "tag_a": "b8545", "tag_b": "b8740", "series": "tinyllama-1.1b/metal/pp512",
             "listed": 1, "fixed_lr": 0.05, "fixed_tau": 0.5, "verdict": "noise"}]
    with (event_dir / "summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    targets = s3.targets_from_step2(ns, by_name)
    assert [t.series for t in targets] == ["mistral-7b/metal/pp512", "qwen2.5-1.5b/metal/pp512"]
    assert targets[0].label == "E49_mistral-7b_metal_pp512"
    assert (targets[0].sign, targets[0].ref_lr) == (1, 0.57)
    ns = s3.parse_args(["--from-step2", "E49", "--series", "qwen2.5-1.5b/metal/pp512"])
    assert [t.series for t in s3.targets_from_step2(ns, by_name)] == ["qwen2.5-1.5b/metal/pp512"]


def _snapshot(root: Path) -> dict[str, int] | None:
    """Paths and mtimes under root (None if it does not exist)."""
    if not root.exists():
        return None
    return {str(p): p.stat().st_mtime_ns for p in root.rglob("*")}


def test_dry_run_e49_starts_no_process_and_writes_nothing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                                                          capsys: pytest.CaptureFixture[str]) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("the dry run started a process")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    before = (_snapshot(s3.OUT_DIR), _snapshot(s3.BUILD_RESULTS), _snapshot(s3.BINS))
    # a fresh state directory: the real one holds the finished 2026-10-14 bisection of E49
    rc = s3.main(["--lo", "b8545", "--hi", "b8740", "--model", "mistral-7b", "--backend", "metal", "--test", "pp512",
                  "--direction", "up", "--dry-run", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert (_snapshot(s3.OUT_DIR), _snapshot(s3.BUILD_RESULTS), _snapshot(s3.BINS)) == before
    assert not any(tmp_path.iterdir())
    cands = [p for p in s3.load_releases() if 8545 < p.key[0] < 8740]
    mid = cands[s3.median_order(len(cands))[0]]
    assert f"candidates: {len(cands)} release tags strictly between b8545 and b8740" in out
    assert f"next mid: {mid.name}" in out
    if (s3.BINS / mid.name / "llama-bench").is_file():  # built by the real 2026-10-14 bisection
        assert f"bins/{mid.name}/llama-bench present -> reused" in out
    else:
        assert f"BUILD_ONLY=1 RESULTS_ROOT={s3.BUILD_RESULTS}" in out
    run_lines = [line for line in out.splitlines() if line.strip().startswith("[r")]
    assert len(run_lines) == 6
    assert all("/usr/bin/arch -arm64" in line and "-p 512 -n 0 -r 5 -o json" in line for line in run_lines)
    assert [line.split("]")[0].split()[-1] for line in run_lines] == ["lo", "mid", "hi", "hi", "mid", "lo"]


# --------------------------------------------------------------------------- build_bench.sh build-only mode


def _exe(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(0o755)


CURL_STUB = """#!/bin/sh
# stub curl: record the URL, copy the prepared tarball to the -o target
out=""; url=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    --retry|--retry-delay) shift 2 ;;
    -*) shift ;;
    *) url="$1"; shift ;;
  esac
done
echo "$url" >> "$STUB_LOG/curl_urls"
[ "${STUB_CURL_FAIL:-0}" = "1" ] && { echo "curl: (35) stub failure" >&2; exit 35; }
cp "$STUB_TARBALL" "$out"
"""

CMAKE_STUB = """#!/bin/sh
# stub cmake: record configure arguments; --build creates a fake llama-bench
case "$1" in
  --version) echo "cmake version 0.0-stub"; exit 0 ;;
  --build)
    [ "${STUB_FAIL_BUILD:-0}" = "1" ] && { echo "error: stub build failure"; exit 1; }
    mkdir -p "$2/bin"
    printf '#!/bin/sh\\necho "usage: llama-bench [options]"\\necho "  -nopo, --no-op-offload <0|1>  (default: 0)"\\n' > "$2/bin/llama-bench"
    chmod +x "$2/bin/llama-bench"
    echo "build $*" >> "$STUB_LOG/cmake_calls"; exit 0 ;;
  *)
    echo "configure $*" >> "$STUB_LOG/cmake_calls"
    while [ $# -gt 0 ]; do [ "$1" = "-B" ] && mkdir -p "$2"; shift; done
    exit 0 ;;
esac
"""


@pytest.fixture
def fake_root(tmp_path: Path) -> SimpleNamespace:
    """A temporary project root with build_bench.sh, parse_bench.py, a git 'llama.cpp' and stubs."""
    root = tmp_path / "root"
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPTS / "build_bench.sh", root / "scripts" / "build_bench.sh")
    shutil.copy2(SCRIPTS / "parse_bench.py", root / "scripts" / "parse_bench.py")
    upstream = tmp_path / "upstream"
    (upstream / "ggml").mkdir(parents=True)
    (upstream / "tools" / "llama-bench").mkdir(parents=True)
    (upstream / "CMakeLists.txt").write_text("project(fake)\n")
    (upstream / "ggml" / "CMakeLists.txt").write_text("\n")
    (upstream / "tools" / "llama-bench" / "llama-bench.cpp").write_text("int main() { return 0; }\n")
    git_env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
               "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@invalid", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@invalid", "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
               "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=upstream, env=git_env, capture_output=True, text=True,
                              check=True).stdout.strip()

    git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "-m", "fake llama.cpp")
    sha = git("rev-parse", "HEAD")
    tarball = tmp_path / "upstream.tar.gz"
    git("archive", "--format=tar.gz", "--prefix=llama.cpp-fake/", "-o", str(tarball), "HEAD")
    subprocess.run(["git", "clone", "-q", "--no-checkout", str(upstream), str(root / "repo")], env=git_env,
                   check=True, capture_output=True)
    (root / "data").mkdir()
    (root / "data" / "releases.csv").write_text(
        "tag,build_number,commit,commit_date_utc,prev_tag,commits_since_prev\n"
        f"b100,100,{sha},2026-01-01T00:00:00Z,,\nb101,101,{sha},2026-01-01T00:00:00Z,b100,1\n")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    _exe(stubs / "curl", CURL_STUB)
    _exe(stubs / "cmake", CMAKE_STUB)
    log = tmp_path / "stub_log"
    log.mkdir()
    return SimpleNamespace(root=root, sha=sha, tarball=tarball, stubs=stubs, log=log)


def run_build(fx: SimpleNamespace, tag: str, **extra: str) -> subprocess.CompletedProcess[str]:
    """Run the copied build_bench.sh in build-only mode with the stubs first on PATH."""
    env = {**os.environ, "PATH": f"{fx.stubs}:{os.environ['PATH']}", "STUB_LOG": str(fx.log),
           "STUB_TARBALL": str(fx.tarball), "BUILD_ONLY": "1",
           "RESULTS_ROOT": str(fx.root / "results" / "bisect_builds"), **extra}
    return subprocess.run(["/bin/bash", str(fx.root / "scripts" / "build_bench.sh"), tag], env=env,
                          capture_output=True, text=True, timeout=300, check=False)


def _lines(path: Path) -> list[str]:
    return path.read_text().splitlines() if path.is_file() else []


def test_build_bench_syntax() -> None:
    assert subprocess.run(["/bin/bash", "-n", str(SCRIPTS / "build_bench.sh")], check=False).returncode == 0


def test_build_only_release_tag(fake_root: SimpleNamespace) -> None:
    fx = fake_root
    proc = run_build(fx, "b100")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    res = fx.root / "results" / "bisect_builds" / "b100"
    status = json.loads((res / "status.json").read_text())
    assert (status["status"], status["mode"], status["commit_verified"]) == ("built", "build_only", True)
    assert status["cpu_no_op_offload_flag"] == "-nopo 1"
    assert (fx.root / "bins" / "b100" / "llama-bench").is_file()
    assert (res / "DONE").is_file()
    assert _lines(fx.log / "curl_urls") == ["https://github.com/ggml-org/llama.cpp/archive/refs/tags/b100.tar.gz"]
    configure = [c for c in _lines(fx.log / "cmake_calls") if c.startswith("configure")]
    assert len(configure) == 1
    assert "-DGGML_METAL=ON" in configure[0] and "-DLLAMA_BUILD_TOOLS=ON" in configure[0]
    assert _lines(res / "runs.tsv")[1:] == []  # no benchmark
    assert not list(res.glob("*_metal*.json"))
    assert not (fx.root / "build" / "b100").exists() and not (fx.root / "src" / "b100").exists()
    assert not (fx.root / "results" / "b100").exists()

    again = run_build(fx, "b100")  # an existing binary is kept
    assert again.returncode == 0 and "not rebuilt" in again.stderr
    assert len(_lines(fx.log / "curl_urls")) == 1


def test_build_only_commit(fake_root: SimpleNamespace) -> None:
    fx = fake_root
    tag = f"c{fx.sha[:12]}"
    proc = run_build(fx, tag)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    status = json.loads((fx.root / "results" / "bisect_builds" / tag / "status.json").read_text())
    assert status["status"] == "built"
    assert status["release_commit"] == status["tarball_commit"] == fx.sha
    assert status["commit_verified"] is True
    assert _lines(fx.log / "curl_urls") == [f"https://github.com/ggml-org/llama.cpp/archive/{fx.sha}.tar.gz"]
    assert (fx.root / "bins" / tag / "llama-bench").is_file()


def test_build_only_failures(fake_root: SimpleNamespace) -> None:
    fx = fake_root
    proc = run_build(fx, "b101", STUB_FAIL_BUILD="1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    res = fx.root / "results" / "bisect_builds" / "b101"
    status = json.loads((res / "status.json").read_text())
    assert status["status"] == "build_failed"
    assert status["failure_reason"]
    assert not (fx.root / "bins" / "b101").exists()
    assert (res / "DONE").is_file()

    fx.root.joinpath("src", "b100.tar.gz").unlink(missing_ok=True)
    proc = run_build(fx, "b100", STUB_CURL_FAIL="1")
    status = json.loads((fx.root / "results" / "bisect_builds" / "b100" / "status.json").read_text())
    assert status["status"] == "download_failed"
    assert not (fx.root / "results" / "bisect_builds" / "b100" / "DONE").exists()


def test_build_only_refuses_the_campaign_results_root(fake_root: SimpleNamespace) -> None:
    fx = fake_root
    campaign = fx.root / "results" / "b100"
    campaign.mkdir(parents=True)
    (campaign / "DONE").write_text("campaign result\n")
    proc = run_build(fx, "b100", RESULTS_ROOT=str(fx.root / "results"))
    assert proc.returncode == 2
    assert "must not be" in proc.stderr
    assert (campaign / "DONE").read_text() == "campaign result\n"
    assert _lines(fx.log / "curl_urls") == []
    proc = run_build(fx, "b100", RESULTS_ROOT=str(fx.root / "results") + "/")
    assert proc.returncode == 2


def test_build_bench_rejects_bad_tags(fake_root: SimpleNamespace) -> None:
    for bad in ("b12x", "c123", "cXYZ1234", "1234"):
        proc = run_build(fake_root, bad)
        assert proc.returncode == 2 and "usage" in proc.stderr
    assert _lines(fake_root.log / "curl_urls") == []
