"""Synthetic-data tests for step2b_judge.py (decision rule v1.1).

Run: uv run --no-project --with pytest --with pandas --with numpy python3 -I -m pytest scripts/analysis/test_step2b_judge.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step2b_judge

MODEL, BACKEND = "tinyllama-1.1b", "metal"


def bench_json(pp: list[float], tg: list[float]) -> str:
    """A minimal llama-bench JSON array with pp512 and tg128 records."""
    return json.dumps([
        {"n_prompt": 512, "n_gen": 0, "avg_ts": float(np.mean(pp)), "samples_ts": pp},
        {"n_prompt": 0, "n_gen": 128, "avg_ts": float(np.mean(tg)), "samples_ts": tg},
    ])


def make_event(root: Path, event_id: str, tag_a: str, tag_b: str, level_a: float, level_b: float,
               rng: np.random.Generator, sd: float = 0.02, a_r1: float | None = None, warm: bool = False) -> None:
    """Write plan.json and run JSONs of one event (3 fixed rounds ABBA, 1 default round).

    ``a_r1`` overrides the level of the fixed round-1 A run (a first-run deviation); ``warm`` adds
    the v1.2 warm-up run before the group.
    """
    out = root / "interleaved" / f"{event_id}_{tag_a}_{tag_b}"
    out.mkdir(parents=True)
    runs = []
    if warm:
        stem = f"warmup_r0_A_{tag_a}_{MODEL}_{BACKEND}"
        (out / f"{stem}.json").write_text(bench_json([level_a] * 10, [100.0] * 10))
        runs.append({"phase": "warmup", "round": 0, "side": "A", "tag": tag_a, "stem": stem})
    order = [(1, "A"), (1, "B"), (2, "B"), (2, "A"), (3, "A"), (3, "B")]
    for phase, seq in (("fixed", order), ("default", [(1, "A"), (1, "B")])):
        for rnd, side in seq:
            tag = tag_a if side == "A" else tag_b
            stem = f"{phase}_r{rnd}_{side}_{tag}_{MODEL}_{BACKEND}"
            lvl = level_a if side == "A" else level_b
            if a_r1 is not None and (phase, rnd, side) == ("fixed", 1, "A"):
                lvl = a_r1
            pp = list(np.exp(np.log(lvl) + rng.normal(0, sd, 10)))
            tg = list(np.exp(np.log(100.0) + rng.normal(0, sd, 10)))
            (out / f"{stem}.json").write_text(bench_json(pp, tg))
            runs.append({"phase": phase, "round": rnd, "side": side, "tag": tag, "stem": stem})
    plan = {"event_id": event_id, "groups": [{"tag_a": tag_a, "tag_b": tag_b, "model": MODEL, "backend": BACKEND,
                                              "series": [f"{MODEL}/{BACKEND}/pp512"], "equivalent": True,
                                              "runs": runs}]}
    (out / "plan.json").write_text(json.dumps(plan))
    for tag, lvl in ((tag_a, level_a), (tag_b, level_b)):
        camp = root / "results" / tag
        camp.mkdir(parents=True, exist_ok=True)
        pp = list(np.exp(np.log(lvl) + rng.normal(0, sd, 5)))
        tg = list(np.exp(np.log(100.0) + rng.normal(0, sd, 5)))
        (camp / f"{MODEL}_{BACKEND}.json").write_text(bench_json(pp, tg))


def events_csv(root: Path, rows: list[tuple[str, str, str, float]]) -> None:
    """candidate_events.csv with one listed series per event."""
    recs = []
    for event_id, tag_a, tag_b, lr in rows:
        s = [{"series": f"{MODEL}/{BACKEND}/pp512", "model": MODEL, "backend": BACKEND, "test": "pp512",
              "tag_old": tag_a, "tag_new": tag_b, "log_ratio": lr}]
        recs.append({"event_id": event_id, "tag_old": tag_a, "tag_new": tag_b, "series_json": json.dumps(s)})
    (root / "analysis").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(recs).to_csv(root / "analysis" / "candidate_events.csv", index=False)


def test_verdicts(tmp_path: Path) -> None:
    """A real +30% step is C, a campaign artifact is noise, an A/A pair has no false positive."""
    rng = np.random.default_rng(7)
    make_event(tmp_path, "E01", "b100", "b200", 1000.0, 1300.0, rng)   # real change
    make_event(tmp_path, "E02", "b300", "b400", 1000.0, 1000.0, rng)   # campaign said +30%, re-run says 0
    make_event(tmp_path, "AA1", "b500", "b500", 1000.0, 1000.0, rng)
    events_csv(tmp_path, [("E01", "b100", "b200", 0.26), ("E02", "b300", "b400", 0.26)])
    rc = step2b_judge.main(["--interleaved", str(tmp_path / "interleaved"), "--analysis", str(tmp_path / "analysis"),
                            "--results", str(tmp_path / "results")])
    assert rc == 0
    ser = pd.read_csv(tmp_path / "interleaved" / "judge_v11_series.csv")
    pp = ser[ser.series.str.endswith("pp512")].set_index("event_id")
    assert pp.loc["E01", "verdict"] == "C"
    assert abs(np.expm1(pp.loc["E01", "fixed_lr"]) - 0.30) < 0.05
    assert pp.loc["E02", "verdict"] == "noise"
    assert pp.loc["AA1", "verdict"] == "aa_ok"
    ev = pd.read_csv(tmp_path / "interleaved" / "judge_v11_events.csv").set_index("event_id")
    assert ev.loc["E01", "verdict_v11"] == "C"
    noise = pd.read_csv(tmp_path / "interleaved" / "noise_model_v11.csv")
    assert (noise.sigma_fixed < 0.05).all()
    assert (tmp_path / "interleaved" / "MEMO_v11.md").is_file()


def test_reversed(tmp_path: Path) -> None:
    """A significant change against the step-1 sign is 'reversed'."""
    rng = np.random.default_rng(11)
    make_event(tmp_path, "E05", "b100", "b200", 1000.0, 800.0, rng)
    events_csv(tmp_path, [("E05", "b100", "b200", 0.2)])
    step2b_judge.main(["--interleaved", str(tmp_path / "interleaved"), "--analysis", str(tmp_path / "analysis"),
                       "--results", str(tmp_path / "results")])
    ser = pd.read_csv(tmp_path / "interleaved" / "judge_v11_series.csv")
    assert ser[ser.series.str.endswith("pp512")].verdict.iloc[0] == "reversed"


def test_drop_round1_sensitivity(tmp_path: Path) -> None:
    """A first-run outlier on side A hides a real +30% step in the fixed phase; leaving out round 1 of
    unwarmed groups recovers it, while a group with a warm-up run keeps its round 1."""
    rng = np.random.default_rng(3)
    make_event(tmp_path, "E07", "b100", "b200", 1000.0, 1300.0, rng, a_r1=1700.0)             # no warm-up
    # warmed, no outlier (an outlier kept here would inflate the pooled sigma_fixed for every event)
    make_event(tmp_path, "E08", "b300", "b400", 1000.0, 1300.0, rng, warm=True)
    events_csv(tmp_path, [("E07", "b100", "b200", 0.26), ("E08", "b300", "b400", 0.26)])
    args = ["--interleaved", str(tmp_path / "interleaved"), "--analysis", str(tmp_path / "analysis"),
            "--results", str(tmp_path / "results")]
    assert step2b_judge.main(args) == 0
    assert step2b_judge.main([*args, "--drop-round1-unwarmed", "--suffix", "_norm1"]) == 0
    main = pd.read_csv(tmp_path / "interleaved" / "judge_v11_series.csv")
    sens = pd.read_csv(tmp_path / "interleaved" / "judge_v11_series_norm1.csv")

    def pick(df: pd.DataFrame) -> pd.DataFrame:
        return df[df.series.str.endswith("pp512")].set_index("event_id")

    # the fixed phase is drowned by the outlier, so only the default phase confirms: a real implementation
    # change would be mislabeled A (configuration)
    assert pick(main).loc["E07", "verdict"] == "A"
    assert pick(sens).loc["E07", "verdict"] == "C"
    assert abs(np.expm1(pick(sens).loc["E07", "fixed_lr"]) - 0.30) < 0.05
    assert pick(sens).loc["E08", "fixed_lr"] == pick(main).loc["E08", "fixed_lr"]  # warmed: round 1 kept
    assert (tmp_path / "interleaved" / "MEMO_v11_norm1.md").is_file()


def test_visibility_events_are_two_sided(tmp_path: Path) -> None:
    """V events (visibility re-tests) are judged two-sided: a drop counts as visible like a rise."""
    rng = np.random.default_rng(5)
    make_event(tmp_path, "VE09", "b100", "b200", 1000.0, 800.0, rng)    # a -20% change: visible
    make_event(tmp_path, "VE10", "b300", "b400", 1000.0, 1000.0, rng)   # no change: not visible
    events_csv(tmp_path, [("E99", "b900", "b901", 0.1)])  # a step-1 file must exist; V events need no entry
    step2b_judge.main(["--interleaved", str(tmp_path / "interleaved"), "--analysis", str(tmp_path / "analysis"),
                       "--results", str(tmp_path / "results")])
    ser = pd.read_csv(tmp_path / "interleaved" / "judge_v11_series.csv")
    pp = ser[ser.series.str.endswith("pp512")].set_index("event_id")
    assert pp.loc["VE09", "verdict"] == "visible"
    assert pp.loc["VE10", "verdict"] == "not_visible"
    ev = pd.read_csv(tmp_path / "interleaved" / "judge_v11_events.csv").set_index("event_id")
    assert ev.loc["VE09", "verdict_v11"].startswith("vis: 1/")


def test_exclude_windows(tmp_path: Path) -> None:
    """Runs overlapping a recorded load window are left out: an outlier run inside the window no longer
    hides a real +30% step, and runs outside every window are kept."""
    rng = np.random.default_rng(3)
    make_event(tmp_path, "E07", "b100", "b200", 1000.0, 1300.0, rng, a_r1=1700.0)
    events_csv(tmp_path, [("E07", "b100", "b200", 0.26)])
    out = tmp_path / "interleaved" / "E07_b100_b200"
    plan = json.loads((out / "plan.json").read_text())
    lines = ["started_at_utc\tfinished_at_utc\tjson_file"]
    for k, r in enumerate(plan["groups"][0]["runs"]):
        lines.append(f"2026-10-14T10:{k:02d}:00Z\t2026-10-14T10:{k:02d}:40Z\t{r['stem']}.json")
    (out / "runs.tsv").write_text("\n".join(lines) + "\n")
    windows = tmp_path / "load_windows.tsv"
    windows.write_text("start_utc\tend_utc\tsource\tnote\n2026-10-14T10:00:30Z\t2026-10-14T10:00:50Z\ttest\tr1 A\n")
    args = ["--interleaved", str(tmp_path / "interleaved"), "--analysis", str(tmp_path / "analysis"),
            "--results", str(tmp_path / "results")]
    assert step2b_judge.main(args) == 0
    assert step2b_judge.main([*args, "--exclude-windows", str(windows), "--suffix", "_nowin"]) == 0
    main = pd.read_csv(tmp_path / "interleaved" / "judge_v11_series.csv")
    sens = pd.read_csv(tmp_path / "interleaved" / "judge_v11_series_nowin.csv")
    pp_main = main[main.series.str.endswith("pp512")].iloc[0]
    pp_sens = sens[sens.series.str.endswith("pp512")].iloc[0]
    assert pp_main.verdict != "C"   # the outlier run inflates the within-side SD
    assert pp_sens.verdict == "C"
    assert step2b_judge.overlapping_stems(out, step2b_judge.load_windows(windows)) == {"fixed_r1_A_b100_tinyllama-1.1b_metal"}


def test_expected_lr_per_pair(tmp_path: Path) -> None:
    """One series listed for two adjacent pairs with opposite signs keeps both signs (E14)."""
    s = f"{MODEL}/{BACKEND}/pp512"
    series = [{"series": s, "tag_old": "b1", "tag_new": "b2", "log_ratio": 0.5},
              {"series": s, "tag_old": "b2", "tag_new": "b3", "log_ratio": -0.5}]
    (tmp_path / "analysis").mkdir()
    pd.DataFrame([{"event_id": "E14", "tag_old": "b1", "tag_new": "b3", "series_json": json.dumps(series)}]).to_csv(
        tmp_path / "analysis" / "candidate_events.csv", index=False)
    exp = step2b_judge.expected_lr(tmp_path / "analysis")
    assert exp[("E14", s, "b1", "b2")] == 0.5
    assert exp[("E14", s, "b2", "b3")] == -0.5
