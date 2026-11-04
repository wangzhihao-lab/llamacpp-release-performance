"""Tests of the v1.2 warm-up run in step2_interleaved.run_plans (fake runs; nothing is measured).

Run: uv run --no-project --with pandas --with numpy --with pytest python3 -I -m pytest -q scripts/analysis/test_step2_warmup.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step2_interleaved as s2

FULL_DAY = s2.parse_window("00:00-24:00")
MODELS = ("m1", "m2")


def _bench_json(path: Path) -> None:
    """A llama-bench JSON with both tests, so output_complete() is true."""
    recs = [{"n_prompt": 512, "n_gen": 0, "avg_ts": 2.0, "samples_ts": [1.0, 2.0, 3.0]},
            {"n_prompt": 0, "n_gen": 128, "avg_ts": 2.0, "samples_ts": [1.0, 2.0, 3.0]}]
    path.write_text(json.dumps(recs))


def make_plan(out: Path) -> s2.EventPlan:
    """Two groups, each: warm-up, then three ABBA rounds of the fixed phase."""
    plan = s2.EventPlan("E99", "b1", "b2", "C", 0.5, out)
    for model in MODELS:
        grp = s2.Group("b1", "b2", model, "metal", [], [], [], [], True)
        grp.runs.append(s2.Run("E99", "warmup", 0, "A", "b1", model, "metal", ["true"], {}, 1.0,
                               f"warmup_r0_A_b1_{model}_metal"))
        for rnd, side in s2.order_sides(3, "abba"):
            tag = "b1" if side == "A" else "b2"
            grp.runs.append(s2.Run("E99", "fixed", rnd, side, tag, model, "metal", ["true"], {}, 1.0,
                                   f"fixed_r{rnd}_{side}_{tag}_{model}_metal"))
        plan.groups.append(grp)
    return plan


@pytest.fixture
def executed(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace execute_run by a fake that writes the JSON and records the stem; no event summary."""
    calls: list[str] = []

    def fake_execute(run: s2.Run, out: Path, ns: argparse.Namespace) -> dict[str, Any]:
        calls.append(run.stem)
        _bench_json(out / f"{run.stem}.json")
        return {"event_id": run.event_id, "phase": run.phase, "round": run.rnd, "side": run.side,
                "exit_code": 0, "wall_s": "1", "load1_before": "1", "waited_s": "0"}

    monkeypatch.setattr(s2, "execute_run", fake_execute)
    monkeypatch.setattr(s2, "write_event_summary", lambda plan, ns: [])
    monkeypatch.setattr(s2, "STOP", {"flag": False, "child": None})
    return calls


def _ns(force: bool = False) -> argparse.Namespace:
    return argparse.Namespace(cooldown=0.0, force=force, on_load_timeout="proceed")


def test_each_group_starts_with_its_warmup(tmp_path: Path, executed: list[str]) -> None:
    plan = make_plan(tmp_path / "E99")
    assert s2.run_plans([plan], _ns(), FULL_DAY) == "done"
    assert executed == [r.stem for g in plan.groups for r in g.runs]
    assert [s for s in executed if s.startswith("warmup")] == [f"warmup_r0_A_b1_{m}_metal" for m in MODELS]


def test_complete_group_gets_no_warmup_and_partial_group_does(tmp_path: Path, executed: list[str]) -> None:
    plan = make_plan(tmp_path / "E99")
    plan.out.mkdir(parents=True)
    g1, g2 = plan.groups
    for r in g1.runs[1:] + g2.runs[1:3]:  # group m1 measured completely, m2 only round 1
        _bench_json(plan.out / f"{r.stem}.json")
    assert s2.run_plans([plan], _ns(), FULL_DAY) == "done"
    assert executed == [g2.runs[0].stem, *(r.stem for r in g2.runs[3:])]


def test_warmup_is_repeated_on_every_resume(tmp_path: Path, executed: list[str]) -> None:
    plan = make_plan(tmp_path / "E99")
    plan.out.mkdir(parents=True)
    g2 = plan.groups[1]
    for r in plan.groups[0].runs:  # an old warm-up file must not count as done
        _bench_json(plan.out / f"{r.stem}.json")
    _bench_json(plan.out / f"{g2.runs[0].stem}.json")
    assert s2.run_plans([plan], _ns(), FULL_DAY) == "done"
    assert executed == [r.stem for r in g2.runs]


def test_force_reruns_everything_with_warmups(tmp_path: Path, executed: list[str]) -> None:
    plan = make_plan(tmp_path / "E99")
    plan.out.mkdir(parents=True)
    for r in plan.runs:
        _bench_json(plan.out / f"{r.stem}.json")
    assert s2.run_plans([plan], _ns(force=True), FULL_DAY) == "done"
    assert executed == [r.stem for r in plan.runs]


def test_full_day_window_and_pg_flag() -> None:
    assert s2.window_left(s2.local_now(), FULL_DAY) == float("inf")
    assert s2.window_hours(FULL_DAY) == 24.0
    a = s2.Caps("b2761", Path("/fake/b2761"), flags={"-ngl", "-t", "-b"})
    b = s2.Caps("b2874", Path("/fake/b2874"), flags={"-ngl", "-t", "-b", "-pg"})
    fa, fb, notes, equivalent = s2.fixed_args(a, b, "cpu", {"metal": 4, "cpu": 8}, 512, 512)
    assert "-pg" not in fa and fb[fb.index("-pg") + 1] == "0,0"
    assert equivalent and any("-pg" in n for n in notes)
