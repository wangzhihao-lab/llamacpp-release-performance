"""Tests for make_numbers.py on a small synthetic results tree built in a tmp directory.

Run: taskpolicy -b nice -n 19 uv run --no-project --with pandas --with numpy --with pytest python3 -m pytest -q -p no:cacheprovider scripts/paper/test_make_numbers.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_numbers as mn

TINY_M_PP = "tinyllama-1.1b/metal/pp512"
MIS_C_PP = "mistral-7b/cpu/pp512"
QWEN_M_PP = "qwen2.5-1.5b/metal/pp512"


def _csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _bisect(an: Path, label: str, **kw: object) -> None:
    d = an / "bisect" / label
    d.mkdir(parents=True, exist_ok=True)
    base = {"event_id": label.split("_")[0], "series": "", "status": "located", "level": "release",
            "lo": "", "hi": "", "lo_commit": "a" * 40, "hi_commit": "b" * 40, "measured_steps": 1,
            "builds": 1, "n_commits": 1, "ref_lr": 0.5}
    base.update(kw)
    (d / "result.json").write_text(json.dumps(base))


def make_tree(root: Path) -> None:
    """Three tags (one failed build), two step-1 events (E01 C, E02 noise), one CP, one R, one A/A."""
    res = root / "results"
    _csv(res / "progress.csv", [
        {"tag": "b1", "commit_date_utc": "2023-09-01T00:00:00Z", "status": "ok"},
        {"tag": "b2", "commit_date_utc": "2024-01-15T00:00:00Z", "status": "build_failed"},
        {"tag": "b3", "commit_date_utc": "2024-03-02T00:00:00Z", "status": "ok"}])
    rec = []
    for tag in ("b1", "b3"):
        for m in ("tinyllama-1.1b", "mistral-7b"):
            for b in ("metal", "cpu"):
                for t in ("pp512", "tg128"):
                    rec.append({"tag": tag, "model": m, "backend": b, "test": t, "status": "ok", "n_samples": 5})
    rec.append({"tag": "b1", "model": "qwen2.5-1.5b", "backend": "cpu", "test": "pp512",
                "status": "load_failed", "n_samples": 0})
    _csv(res / "b1" / "records.csv", [r for r in rec if r["tag"] == "b1"])
    _csv(res / "b3" / "records.csv", [r for r in rec if r["tag"] == "b3"])
    for tag, start in (("b1", "2023-10-01T10:00:00Z"), ("b3", "2023-10-01T11:00:00Z")):
        pd.DataFrame([{"model": "m", "started_at_utc": start, "wall_s": 1800.0}]).to_csv(
            res / tag / "runs.tsv", sep="\t", index=False)
    an = res / "analysis"
    _csv(an / "candidate_events.csv", [
        {"event_id": "E01", "tag_old": "b1", "tag_new": "b3", "commits_between": 40, "class": "C"},
        {"event_id": "E02", "tag_old": "b3", "tag_new": "b4", "commits_between": 7, "class": "D"},
        {"event_id": "E03", "tag_old": "b4", "tag_new": "b5", "commits_between": 9, "class": "A"}])
    _csv(an / "changepoints.csv", [
        {"step1_same_group": "E01:b1-b3", "step1_events_overlapping": "E01(C);E02(D)", "cp_event_id": ""},
        {"step1_same_group": "E01:b1-b3", "step1_events_overlapping": "E01(C)", "cp_event_id": ""},
        {"step1_same_group": "", "step1_events_overlapping": "E02(D)", "cp_event_id": "CP01"}])
    _csv(an / "changepoint_events.csv", [{"event_id": "CP01", "tag_old": "b3", "tag_new": "b4", "class": "CP"}])
    _csv(an / "remeasure_events.csv", [{"event_id": "E01R", "tag_old": "b1", "tag_new": "b3", "class": "C"}])
    _csv(an / "control_events.csv", [{"event_id": "AA1", "tag_old": "b3", "tag_new": "b3", "class": "AA"}])
    ev = [{"event_id": "E01", "verdict_v11": "C"}, {"event_id": "E01R", "verdict_v11": "C"},
          {"event_id": "E02", "verdict_v11": "noise"}, {"event_id": "E03", "verdict_v11": "C"},
          {"event_id": "CP01", "verdict_v11": "noise"}, {"event_id": "AA1", "verdict_v11": "aa: 1/2"}]
    il = an / "interleaved"
    _csv(il / "judge_v11_events.csv", ev)
    ev1 = [dict(r) for r in ev]
    ev1[2]["verdict_v11"] = "C"  # E02 flips under the sensitivity judge
    _csv(il / "judge_v11_events_norm1.csv", ev1)
    se = [{"event_id": "AA1", "series": TINY_M_PP, "tag_a": "b3", "tag_b": "b3", "verdict": "aa_ok"},
          {"event_id": "AA1", "series": MIS_C_PP, "tag_a": "b3", "tag_b": "b3", "verdict": "aa_false_positive"},
          {"event_id": "E01", "series": TINY_M_PP, "tag_a": "b1", "tag_b": "b3", "verdict": "C"},
          {"event_id": "E02", "series": MIS_C_PP, "tag_a": "b3", "tag_b": "b4", "verdict": "noise"}]
    _csv(il / "judge_v11_series.csv", se)
    se1 = [dict(r) for r in se]
    se1[3]["verdict"] = "C"
    _csv(il / "judge_v11_series_norm1.csv", se1)
    vis = []
    for evid in ("E01", "E03"):
        for s in mn.SERIES:
            vis.append({"event_id": evid, "series": s, "state": "none", "lr_pct": 1.0, "z": 0.1, "source": evid})
    vis_df = pd.DataFrame(vis)

    def put(evid: str, s: str, state: str, pct: float, z: float) -> None:
        m = (vis_df.event_id == evid) & (vis_df.series == s)
        vis_df.loc[m, ["state", "lr_pct", "z"]] = [state, pct, z]

    put("E01", TINY_M_PP, "up", 158.6, 19.0)
    put("E01", QWEN_M_PP, "up", 40.2, 5.0)
    put("E01", MIS_C_PP, "down", -22.2, -4.0)
    put("E03", MIS_C_PP, "down", -64.6, -16.0)
    put("E03", "tinyllama-1.1b/metal/tg128", "n/a", float("nan"), float("nan"))
    vis_df.to_csv(an / "step4_visibility.csv", index=False)
    _bisect(an, "E01_tinyllama-1.1b_metal_pp512", event_id="E01", lo="b10", hi="b12", measured_steps=6,
            builds=6, n_commits=3)
    _bisect(an, "E01c_tinyllama-1.1b_metal_pp512", event_id="E01c", level="commit", lo="c1", hi="c2",
            lo_commit="1234567890abc", hi_commit="abcdef0123456", measured_steps=4, builds=4, n_commits=1)
    _bisect(an, "E01cpu_mistral-7b_cpu_pp512", event_id="E01cpu", status="effect_lost", measured_steps=1, builds=0)
    _bisect(an, "E03_mistral-7b_cpu_pp512", event_id="E03", lo="b4", hi="b5", measured_steps=5, builds=5,
            n_commits=2, ref_lr=-1.0)
    _bisect(an, "E03_tinyllama-1.1b_cpu_pp512", event_id="E03", lo="b4", hi="b5", measured_steps=5, builds=0,
            n_commits=2, ref_lr=-1.1)


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    make_tree(tmp_path)
    return tmp_path


def _values(macros: list[mn.Macro]) -> dict[str, str]:
    return {m.name: m.value for m in macros}


def test_number_words() -> None:
    assert mn.event_word("E01") == "EOne"
    assert mn.event_word("E46") == "EFortySix"
    assert mn.event_word("E50") == "EFifty"
    assert mn.macro_prefix("E19") == "eNineteen"
    with pytest.raises(ValueError):
        mn.event_word("E01R")
    assert mn.signed_pct(-64.6) == "$-$65" and mn.signed_pct(158.6) == "+159" and mn.signed_pct(0.2) == "0"


def test_campaign(tree: Path) -> None:
    v = _values(mn.campaign_macros(tree))
    assert v["nTagsSampled"] == "3" and v["nTagsBuilt"] == "2" and v["nTagsFailed"] == "1"
    assert v["nRecords"] == "16" and v["nRecordsFailed"] == "1"
    assert v["nModels"] == "2" and v["nBackends"] == "2" and v["nTests"] == "2" and v["nSeries"] == "8"
    assert v["nRepsCampaign"] == "5"
    assert (v["campaignStartMonth"], v["campaignStartYear"]) == ("September", "2023")
    assert (v["campaignEndMonth"], v["campaignEndYear"], v["campaignSpanMonths"]) == ("March", "2024", "6")
    # runs.tsv: 10:00 to 11:00 + 1800 s -> 1.5 h on one date, two calls
    assert v["campaignCalls"] == "2" and v["campaignSessionHours"] == "1.5" and v["campaignSessionDays"] == "1"


def test_release_macros(tree: Path) -> None:
    assert mn.release_macros(tree) == []  # no data/ in the synthetic tree
    data = tree / "data"
    _csv(data / "releases.csv", [
        {"tag": f"b{i}", "build_number": i, "commits_since_prev": c} for i, c in ((1, 1), (2, 1), (3, 2), (4, 1), (9, 5))])
    _csv(data / "selected_tags.csv", [
        {"grid_point_utc": "2023-09-01T00:00:00Z", "tag": "b1", "build_number": 1},
        {"grid_point_utc": "2023-09-15T00:00:00Z", "tag": "b2", "build_number": 2},
        {"grid_point_utc": "newest", "tag": "b4", "build_number": 4}])
    v = _values(mn.release_macros(tree))
    assert v["nReleasesWindow"] == "4" and v["releaseOneCommitPct"] == "75"
    assert v["tagGridPoints"] == "2" and v["tagGridDays"] == "14.0"


def test_campaign_without_runs(tree: Path) -> None:
    for f in (tree / "results").glob("b*/runs.tsv"):
        f.unlink()
    assert "campaignCalls" not in _values(mn.campaign_macros(tree))


def _fake_scripts(root: Path) -> Path:
    """Minimal scripts/ tree with the defaults protocol_macros reads."""
    sc = root / "scripts"
    an = sc / "analysis"
    (an / "queues").mkdir(parents=True)
    params = "from dataclasses import dataclass\n@dataclass(frozen=True)\nclass Params:\n"
    (an / "step1_candidate_events.py").write_text(
        params + "    min_rel: float = 0.12\n    k_sd: float = 2.5\n"
        "ap.add_argument('--min-rel', type=float, default=Params.min_rel)\n")
    (an / "step1b_changepoints.py").write_text(
        params + "    alpha: float = 1.0\n    min_size: int = 4\n    n_perm: int = 199\n    p_max: float = 0.05\n")
    opts2 = {"--rounds": 3, "--default-rounds": 1, "--reps": 6, "--reps-small": 11, "--threads-metal": 4,
             "--threads-cpu": 8, "--batch": 256, "--ubatch": 128, "--cooldown": 15.0, "--idle-min": 85.0,
             "--thermal-max": 1, "--load-wait-max": 240.0}
    body = "".join(f"ap.add_argument({k!r}, type=float, default={v!r})\n" for k, v in opts2.items())
    (an / "step2_interleaved.py").write_text(body + 'X = ["--poll", "40"]\n')
    (an / "step2b_judge.py").write_text(
        "ap.add_argument('--min-rel', type=float, default=0.07)\nap.add_argument('--z-min', type=float, default=3.5)\n")
    opts3 = {"--rounds": 2, "--max-builds": 9, "--f-old": 0.3, "--f-new": 0.7, "--lost-frac": 0.5}
    (an / "step3_bisect.py").write_text(
        "".join(f"ap.add_argument({k!r}, default={v!r})\n" for k, v in opts3.items()))
    (an / "queues" / "continuous.tsv").write_text("bisect_E16R\tstep3\t--from-step2 E16R --rounds 6\n")
    (sc / "build_bench.sh").write_text("\n".join(
        f'{k}="${{{k}:-{v}}}"' for k, v in {"REPS": 5, "CPU_THREADS": 8, "COOLDOWN_S": 10, "QUIET_IDLE_PCT": 80,
                                             "QUIET_MAX_WAIT_S": 300, "QUIET_TAG_BUDGET_S": 900}.items()) + "\n")
    return sc


def test_protocol_macros_synthetic(tmp_path: Path) -> None:
    v = _values(mn.protocol_macros(_fake_scripts(tmp_path)))
    assert v["protCandMinRel"] == "12" and v["protCandKSd"] == "2.5"
    assert (v["protCpAlpha"], v["protCpMinSize"], v["protCpPerm"], v["protCpPMax"]) == ("1", "4", "199", "0.05")
    assert v["protRepsLarge"] == "6" and v["protRepsSmall"] == "11" and v["protCooldown"] == "15"
    assert v["protIdleMin"] == "85" and v["protWaitMax"] == "240" and v["protUbatch"] == "128"
    assert v["protJudgeMinRel"] == "7" and v["protJudgeZ"] == "3.5"
    assert (v["protMaxBuilds"], v["protFOld"], v["protFNew"], v["protLostFrac"]) == ("9", "0.3", "0.7", "0.5")
    assert v["protPoll"] == "40" and v["protBisectRoundsNoisy"] == "6"
    assert v["campCooldown"] == "10" and v["campTagWaitBudget"] == "900"
    assert v["protNoWarmupEvents"] == "18"


def test_protocol_macros_missing_default(tmp_path: Path) -> None:
    sc = _fake_scripts(tmp_path)
    (sc / "analysis" / "step2b_judge.py").write_text("ap.add_argument('--min-rel', type=float, default=0.07)\n")
    with pytest.raises(KeyError):
        mn.protocol_macros(sc)


def test_protocol_macros_repository() -> None:
    """The real scripts: the constants the paper states (protocol v1.1 and v1.2)."""
    v = _values(mn.protocol_macros())
    assert (v["protJudgeMinRel"], v["protJudgeZ"], v["protCandMinRel"], v["protCandKSd"]) == ("5", "3", "10", "3")
    assert (v["protRoundsFixed"], v["protRepsSmall"], v["protRepsLarge"], v["protCooldown"]) == ("3", "10", "5", "20")
    assert (v["protIdleMin"], v["protThermalMax"], v["protWaitMax"]) == ("80", "1", "300")
    assert (v["protFOld"], v["protFNew"], v["protMaxBuilds"], v["protBisectRounds"]) == ("0.35", "0.65", "8", "2")
    assert (v["protCpAlpha"], v["protCpMinSize"], v["protCpPerm"], v["protCpPMax"]) == ("1", "3", "999", "0.01")


def test_candidates_and_changepoints(tree: Path) -> None:
    an = tree / "results" / "analysis"
    v = _values(mn.candidate_macros(pd.read_csv(an / "candidate_events.csv"), "x"))
    assert v["nCandidates"] == "3" and v["nCandidatesClassC"] == "1" and v["nCandidatesClassD"] == "1"
    assert v["nCandidatesClassA"] == "1" and v["nCandidatesClassB"] == "0"
    v = _values(mn.changepoint_macros(pd.read_csv(an / "changepoints.csv"),
                                      pd.read_csv(an / "changepoint_events.csv"), "x", "y"))
    assert v["nChangepoints"] == "3" and v["nChangepointsMissed"] == "1"
    assert v["nChangepointEvents"] == "1" and v["nCandidatesOnChangepoint"] == "1"


def test_judge_and_sensitivity(tree: Path) -> None:
    an = tree / "results" / "analysis"
    il = an / "interleaved"
    ev, se = pd.read_csv(il / "judge_v11_events.csv"), pd.read_csv(il / "judge_v11_series.csv")
    v = _values(mn.judge_macros(ev, se, pd.read_csv(an / "candidate_events.csv"),
                                pd.read_csv(an / "changepoint_events.csv"), pd.read_csv(an / "remeasure_events.csv"),
                                pd.read_csv(an / "control_events.csv"), "e", "s"))
    assert v["nConfirmed"] == "2" and v["nNoise"] == "1" and v["confirmedEventList"] == "E01, E03"
    assert v["nConfirmedClassC"] == "1" and v["nConfirmedClassA"] == "1" and v["nConfirmedClassD"] == "0"
    assert v["nChangepointConfirmed"] == "0" and v["nChangepointNoise"] == "1"
    assert v["nRemeasured"] == "1" and v["nRemeasuredAgree"] == "1"
    assert v["nAASeries"] == "2" and v["nAAFalsePositives"] == "1"
    v = _values(mn.sensitivity_macros(ev, pd.read_csv(il / "judge_v11_events_norm1.csv"), se,
                                      pd.read_csv(il / "judge_v11_series_norm1.csv"), "x"))
    assert v["nSensitivityEventDisagree"] == "1" and v["nSensitivitySeriesDisagree"] == "1"
    assert v["nSensitivitySeriesFlipC"] == "1" and v["sensitivitySeriesDisagreeEvents"] == "E02"


def test_visibility_and_cover(tree: Path) -> None:
    vis = mn.read_visibility(tree / "results" / "analysis" / "step4_visibility.csv")
    assert (vis.state == "n/a").sum() == 1  # 'n/a' must not be read as NaN
    v = _values(mn.visibility_macros(vis, (("E01", MIS_C_PP),), "x"))
    assert v["nVisibleCellsRaw"] == "4" and v["nVisibleCells"] == "3" and v["nVisibleCellsTg"] == "0"
    assert v["nVisibilityCellsNA"] == "1" and v["nExcludedCells"] == "1"
    # raw: mistral cpu sees E01+E03 -> one series covers both; after excluding E01 x mistral cpu it takes two
    assert v["coverMinSeriesRaw"] == "1" and v["coverNOptimalRaw"] == "1" and v["coverSingleMaxRaw"] == "2"
    assert v["coverMinSeries"] == "2" and v["coverNOptimal"] == "2" and v["coverSingleMax"] == "1"
    assert v["coverSingleMiss"] == "1" and v["nUndetectable"] == "0"


def test_bisect_and_events(tree: Path) -> None:
    an = tree / "results" / "analysis"
    runs = mn.read_bisect(an / "bisect")
    assert set(runs.event_id) == {"E01", "E03"}
    v = _values(mn.bisect_total_macros(runs, "x"))
    assert v["bisectRuns"] == "5" and v["bisectRunsLocated"] == "4" and v["bisectRunsEffectLost"] == "1"
    assert v["bisectBuildsTotal"] == "15" and v["bisectStepsTotal"] == "21" and v["nEventsLocated"] == "2"
    vis = mn.read_visibility(an / "step4_visibility.csv")
    v = _values(mn.event_macros(["E01", "E03"], pd.read_csv(an / "candidate_events.csv"), vis,
                                (("E01", MIS_C_PP),), runs, "c", "v", "b"))
    assert v["eOneTagOld"] == "b1" and v["eOneTagNew"] == "b3" and v["eOneCommitsBetween"] == "40"
    assert v["eOnePct"] == "159" and v["eOnePctSigned"] == "+159"
    assert v["eOnePctMin"] == "40" and v["eOnePctMax"] == "159"
    assert v["eOneNVisible"] == "2" and v["eOneNVisibleRaw"] == "3"
    assert v["eOneBisectLo"] == "b10" and v["eOneBisectHi"] == "b12"
    assert v["eOneBisectSteps"] == "10" and v["eOneBisectBuilds"] == "10" and v["eOneBisectBuildsAll"] == "10"
    assert v["eOneBisectLoCommit"] == "123456789" and v["eOneBisectCommit"] == "abcdef012"
    assert v["eOneReleaseBoundaryCommits"] == "3" and "eThreeReleaseBoundaryCommits" not in v
    assert v["eThreePct"] == "65" and v["eThreePctSigned"] == "$-$65"
    # primary run is the one that built (5 builds), the other reused builds
    assert v["eThreeBisectSteps"] == "5" and v["eThreeBisectBuilds"] == "5" and v["eThreeBisectBuildsAll"] == "5"
    assert "eThreeBisectCommit" not in v  # two commits in the boundary: no culprit macro
    b = _values(mn.boundary_macros(["E01", "E03"], runs, "b"))
    assert b == {"nBoundarySingleCommit": "1", "bisectMaxBoundaryCommits": "2"}  # E01 via its commit-level run


def test_main_writes_valid_tex(tree: Path) -> None:
    out = tree / "paper" / "numbers.tex"
    before = {p: p.read_bytes() for p in (tree / "results").rglob("*") if p.is_file()}
    assert mn.main(["--root", str(tree)]) == 0
    after = {p: p.read_bytes() for p in (tree / "results").rglob("*") if p.is_file()}
    assert before == after  # results/ untouched
    lines = out.read_text().splitlines()
    defs = [ln for ln in lines if ln.startswith("\\newcommand")]
    assert all(ln.startswith(("%", "\\newcommand")) or not ln for ln in lines)
    names = [re.match(r"\\newcommand\{\\([A-Za-z]+)\}\{.*\}$", ln).group(1) for ln in defs]  # type: ignore[union-attr]
    assert len(names) == len(set(names))
    idx = [i for i, ln in enumerate(lines) if ln.startswith("\\newcommand")]
    assert all(lines[i - 1].startswith("% ") for i in idx)  # each macro has a provenance comment above
    assert "\\newcommand{\\coverMinSeries}{2}" in lines


def test_main_cli_exclusions(tree: Path) -> None:
    out = tree / "n.tex"
    assert mn.main(["--root", str(tree), "--out", str(out), "--no-default-exclusions"]) == 0
    assert "\\newcommand{\\coverMinSeries}{1}" in out.read_text()
    assert mn.main(["--root", str(tree), "--out", str(out), "--exclude", f"E03:{MIS_C_PP}"]) == 0
    text = out.read_text()
    assert "\\newcommand{\\nExcludedCells}{1}" in text and "\\newcommand{\\nUndetectable}{1}" in text


def test_missing_file(tmp_path: Path) -> None:
    assert mn.main(["--root", str(tmp_path)]) == 1


# ---------------------------------------------------------------- Results-section macros


def test_series_word_and_signed_num() -> None:
    assert mn.series_word(MIS_C_PP) == "MistralCpuPp" and mn.series_word("qwen2.5-1.5b/metal/tg128") == "QwenMetalTg"
    assert mn.signed_num(1.57) == "1.6" and mn.signed_num(-1.08) == "$-$1.1" and mn.signed_num(-0.01) == "0.0"


def test_visibility_cells_and_cover_series(tree: Path) -> None:
    vis = mn.read_visibility(tree / "results" / "analysis" / "step4_visibility.csv")
    v = _values(mn.visibility_cell_macros(vis, "x"))
    assert v["visEOneTinyMetalPp"] == "+159" and v["visEOneTinyMetalPpZ"] == "19.0"
    assert v["visEOneMistralCpuPp"] == "$-$22" and v["visEOneMistralCpuPpZ"] == "$-$4.0"
    assert "visEThreeTinyMetalTg" not in v  # n/a cell has no value
    c = _values(mn.cover_series_macros(vis, (("E01", MIS_C_PP),), "x"))
    assert c["coverSeesMistralCpuPp"] == "1" and c["coverSeesTinyMetalPp"] == "1" and c["coverSeesTinyCpuTg"] == "0"
    assert len(c) == len(mn.SERIES)


def _judge_series_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {"event_id": "E14", "series": QWEN_M_PP, "tag_a": "b1", "tag_b": "b3", "fixed_lr": 0.0677, "fixed_z": 1.17,
         "fixed_s": 0.0716, "verdict": "noise"},
        {"event_id": "E14", "series": QWEN_M_PP, "tag_a": "b3", "tag_b": "b4", "fixed_lr": -0.9, "fixed_z": -9.0,
         "fixed_s": 0.5, "verdict": "C"},
        {"event_id": "E50", "series": TINY_M_PP, "tag_a": "b1", "tag_b": "b3", "fixed_lr": 0.31, "fixed_z": 5.1,
         "fixed_s": 0.0766, "verdict": "C"}])


def test_rejected_and_noise_examples() -> None:
    sj = json.dumps([{"series": QWEN_M_PP, "tag_old": "b1", "tag_new": "b3", "delta": -0.503},
                     {"series": QWEN_M_PP, "tag_old": "b3", "tag_new": "b4", "delta": 0.2},
                     {"series": TINY_M_PP, "tag_old": "b1", "tag_new": "b3", "delta": 0.9}])
    cand = pd.DataFrame([{"event_id": "E14", "tag_old": "b1", "tag_new": "b4", "series_json": sj},
                         {"event_id": "E50", "tag_old": "b1", "tag_new": "b3", "series_json": "[]"}])
    se = _judge_series_rows()
    v = _values(mn.change_example_macros(cand, se, "c", "s", (("E14", QWEN_M_PP), ("E99", QWEN_M_PP))))
    # largest |delta| of the series (-50.3%) and the judge row of the same tag pair (b1 -> b3)
    assert v == {"eFourteenCampPct": "$-$50", "eFourteenRemPct": "+7", "eFourteenRemZ": "1.2"}
    n = _values(mn.noise_example_macros(cand, se, "s", (("E50", TINY_M_PP), ("E50", MIS_C_PP))))
    assert n == {"eFiftyTinyMetalPpNoise": "0.08"}


def _bench_json(path: Path, pp: float, tg: float) -> None:
    path.write_text(json.dumps([{"n_prompt": 512, "n_gen": 0, "samples_ts": [pp, pp]},
                                {"n_prompt": 0, "n_gen": 128, "samples_ts": [tg]}]))


def test_first_run_bias_and_macros(tmp_path: Path) -> None:
    d = tmp_path / "results" / "analysis" / "interleaved" / "E01_b1_b2"
    d.mkdir(parents=True)
    rows = []
    # unwarmed group: A first (fast), then B, B, A, A, B
    vals = [("A", 130.0), ("B", 100.0), ("B", 100.0), ("A", 100.0), ("A", 100.0), ("B", 104.0)]
    for i, (side, pp) in enumerate(vals):
        j = f"r{i}.json"
        _bench_json(d / j, pp, 50.0)
        rows.append({"model": "mistral-7b", "backend": "cpu", "phase": "fixed", "side": side, "tag": f"b{side}",
                     "started_at_utc": f"2026-10-14T00:0{i}:00Z", "json_file": j, "exit_code": 0})
    # warmed group: skipped
    for i, ph in enumerate(("warmup", "fixed", "fixed")):
        j = f"w{i}.json"
        _bench_json(d / j, 300.0, 50.0)
        rows.append({"model": "tinyllama-1.1b", "backend": "cpu", "phase": ph, "side": "AB"[i % 2], "tag": "bx",
                     "started_at_utc": f"2026-10-14T01:0{i}:00Z", "json_file": j, "exit_code": 0})
    pd.DataFrame(rows).to_csv(d / "runs.tsv", sep="\t", index=False)
    bias = mn.first_run_bias(tmp_path)
    first = bias[bias.role == "first"]
    assert set(first.model) == {"mistral-7b"} and len(first) == 2
    assert first[first.test == "pp512"].dev.iloc[0] == pytest.approx(0.30)
    assert first[first.test == "tg128"].dev.iloc[0] == pytest.approx(0.0)
    ref = bias[(bias.role == "reference") & (bias.test == "pp512")]
    assert ref.dev.iloc[0] == pytest.approx(100.0 / 102.0 - 1)
    v = _values(mn.bias_macros(bias, "x"))
    assert v["biasGroups"] == "1" and v["biasEvents"] == "1" and v["biasBand"] == "10"
    assert v["biasLargeN"] == "1" and v["biasLargeFasterPct"] == "100" and v["biasFasterPct"] == "50"
    assert v["biasMistralCpuMax"] == "30" and v["biasMistralWithinBandPct"] == "50"
    assert v["biasMistralCpuMaxEvent"] == "E01"
    assert v["biasMedianMin"] == "0" and v["biasMedianMax"] == "+30"
    assert mn.bias_macros(bias.iloc[0:0], "x") == []


def test_lifetime_macros(tmp_path: Path) -> None:
    root = tmp_path
    _csv(root / "data" / "releases.csv", [
        {"tag": "b12", "commit_date_utc": "2023-11-13T14:55:52Z"},
        {"tag": "b74", "commit_date_utc": "2023-11-28T08:32:03Z"},
        {"tag": "b100", "commit_date_utc": "2025-11-19T06:19:00Z"},
        {"tag": "b548", "commit_date_utc": "2026-03-27T07:05:21Z"}])
    _csv(root / "results" / "progress.csv", [{"tag": t} for t in ("b90", "b100", "b545", "b740")])
    for tag, line in (("b90", "no probe here"), ("b100", "has tensor            = false"),
                      ("b545", "has tensor = false"), ("b740", "has tensor = true")):
        (root / "results" / tag).mkdir(parents=True, exist_ok=True)
        (root / "results" / tag / "llama-bench_help.txt").write_text(f"ggml_metal_device_init: {line}\n")
    an = root / "results" / "analysis"
    _bisect(an, "E03_tinyllama-1.1b_cpu_pp512", event_id="E03", lo="b10", hi="b12", builds=5)
    _bisect(an, "E04_tinyllama-1.1b_cpu_pp512", event_id="E04", lo="b73", hi="b74", builds=5)
    _bisect(an, "E49_tinyllama-1.1b_metal_pp512", event_id="E49", lo="b547", hi="b548", builds=7)
    v = _values(mn.lifetime_macros(root, mn.read_bisect(an / "bisect")))
    assert v["eThreeLifetimeDays"] == "15"
    assert v["nTagsTensorOff"] == "2" and v["nTagsTensorOn"] == "1"
    assert v["tensorOffFirst"] == "b100" and v["tensorOffLast"] == "b545" and v["tensorOnFirst"] == "b740"
    assert v["tensorOffDays"] == "128"
    assert mn.lifetime_macros(tmp_path / "nothing", mn.read_bisect(an / "bisect")) == []


CATEGORY_CSV = """category,name,events
Metal,Metal kernels and capability probes,E01;E49;E50
Blas,BLAS dispatch on the CPU,E03;E04;E16
Thread,CPU thread runtime,E19
Repack,Weight repacking on the CPU,E46
"""


def test_coding_agreement_macros(tmp_path: Path) -> None:
    p = tmp_path / "coding.csv"
    p.write_text("event,pr,first,second\nE01,2959,Metal,Metal\nE03,4060,Blas,Blas\n")
    v = _values(mn.coding_agreement_macros(p, ["E01", "E03"], tmp_path))
    assert v == {"nCodedChanges": "2", "codedAgreeText": "all two"}
    p.write_text("event,pr,first,second\nE01,2959,Metal,Metal\nE03,4060,Blas,Thread\n")
    assert _values(mn.coding_agreement_macros(p, ["E01", "E03"], tmp_path))["codedAgreeText"] == "1 of the 2"
    with pytest.raises(ValueError, match="differ"):
        mn.coding_agreement_macros(p, ["E01"], tmp_path)
    assert mn.coding_agreement_macros(tmp_path / "missing.csv", ["E01"], tmp_path) == []


def test_session_spread_macros(tmp_path: Path) -> None:
    il = tmp_path / "results" / "analysis" / "interleaved"
    for name, value in (("E01_a_b", 100.0), ("E02_a_c", 150.0)):
        d = il / name
        d.mkdir(parents=True)
        (d / "x.json").write_text(json.dumps([{"n_prompt": 512, "n_gen": 0, "samples_ts": [value]}]))
        (d / "runs.tsv").write_text("exit_code\tphase\ttag\tmodel\tbackend\tjson_file\n0\tfixed\tb1\tm\tcpu\tx.json\n0\twarmup\tb1\tm\tcpu\t\n")
    v = _values(mn.session_spread_macros(tmp_path))
    assert v["sessionCases"] == "1" and v["sessionMedianPct"] == "50" and v["sessionTwentyPct"] == "100"
    assert v["sessionWarmCases"] == "1"
    assert mn.session_spread_macros(tmp_path / "none") == []


def test_default_phase_macros(tmp_path: Path) -> None:
    p = tmp_path / "noise.csv"
    p.write_text("sigma_default\n0.1\n0.2\n")
    v = _values(mn.default_phase_macros(p, 3.0, "noise.csv"))
    assert v == {"defaultMdeMin": "53", "defaultMdeMax": "134"}
    assert mn.default_phase_macros(tmp_path / "missing.csv", 3.0, "x") == []


def test_latest_rows_prefers_the_repeat() -> None:
    frame = pd.DataFrame({"exp": ["F", "FR", "FS", "F"], "series": ["a", "a", "a", "b"], "v": [1, 2, 3, 4]})
    assert list(mn.latest_rows(frame, ("F", "FR", "FS")).v) == [3, 4]
    cells = pd.DataFrame({"exp": ["GE16", "GE16R", "GE19"], "event_id": ["E16", "E16", "E19"], "series": ["a", "a", "a"], "v": [1, 2, 3]})
    assert list(mn.latest_rows(cells, ("GE16", "GE19", "GE16R")).v) == [2, 3]


def test_category_macros(tmp_path: Path) -> None:
    p = tmp_path / "root_cause_categories.csv"
    p.write_text(CATEGORY_CSV)
    conf = ["E01", "E03", "E04", "E16", "E19", "E46", "E49", "E50"]
    v = _values(mn.category_macros(p, conf, tmp_path))
    assert v == {"nRootCauseCategories": "4", "nRootCauseCategoriesWord": "four", "catMetalN": "3", "catBlasN": "3",
                 "catThreadN": "1", "catRepackN": "1"}
    with pytest.raises(ValueError, match="differ"):
        mn.category_macros(p, conf[:-1], tmp_path)
    p.write_text(CATEGORY_CSV.replace("Blas,", "Dispatch,"))
    with pytest.raises(ValueError, match="Blas"):
        mn.category_macros(p, conf, tmp_path)
    assert mn.category_macros(tmp_path / "missing.csv", conf, tmp_path) == []


# ---------------------------------------------------------------- events made of two changes (E01 + E01a)


def _steps(an: Path, label: str, rows: list[dict[str, object]]) -> None:
    _csv(an / "bisect" / label / "steps.csv", rows)


def _two_change_tree(tmp_path: Path) -> Path:
    an = tmp_path / "results" / "analysis"
    _bisect(an, "E01_tinyllama-1.1b_metal_pp512", event_id="E01", lo0="b1", hi0="b9", lo="b5", hi="b9",
            measured_steps=3, builds=3, n_commits=4, intermediate=1)
    _bisect(an, "E01c_tinyllama-1.1b_metal_pp512", event_id="E01c", level="commit", lo0="b5", hi0="b9",
            lo="c1", hi="c2", lo_commit="1234567890abc", hi_commit="abcdef0123456", measured_steps=2, builds=2)
    # more builds than E01c: must not be taken as the continuation of the primary run
    _bisect(an, "E01a_tinyllama-1.1b_metal_pp512", event_id="E01a", level="commit", lo0="b1", hi0="b3",
            lo="c3", hi="c4", lo_commit="feedface12345", hi_commit="cafebabe98765", measured_steps=8, builds=8)
    # a further series over the whole interval (as E49 on Qwen2.5): not a segment
    _bisect(an, "E01_qwen2.5-1.5b_metal_pp512", event_id="E01", lo0="b1", hi0="b9", lo="b5", hi="b9",
            measured_steps=3, builds=0, n_commits=4)
    _steps(an, "E01_tinyllama-1.1b_metal_pp512", [
        {"step": 1, "mid": "b3", "ts_lo": 100.0, "ts_mid": 150.0, "ts_hi": 330.0, "f": 0.47,
         "verdict": "intermediate", "decision": "lo=mid"},
        {"step": 2, "mid": "b4", "ts_lo": 150.0, "ts_mid": 151.0, "ts_hi": 330.0, "f": 0.01,
         "verdict": "old", "decision": "lo=mid"},
        {"step": 3, "mid": "b5", "ts_lo": 151.0, "ts_mid": 160.0, "ts_hi": 330.0, "f": 0.07,
         "verdict": "old", "decision": "lo=mid"}])
    _steps(an, "E01c_tinyllama-1.1b_metal_pp512", [
        {"step": 1, "mid": "cx", "ts_lo": 160.0, "ts_mid": 320.0, "ts_hi": 320.0, "f": 1.0,
         "verdict": "new", "decision": "hi=mid"},
        {"step": 2, "mid": "cy", "ts_lo": 160.0, "ts_mid": 160.0, "ts_hi": 320.0, "f": 0.0,
         "verdict": "old", "decision": "lo=mid"}])
    _steps(an, "E01a_tinyllama-1.1b_metal_pp512", [
        {"step": 1, "mid": "b2", "ts_lo": 100.0, "ts_mid": 150.0, "ts_hi": 150.0, "f": 1.0,
         "verdict": "new", "decision": "hi=mid"},
        {"step": 2, "mid": "c4", "ts_lo": 100.0, "ts_mid": 150.0, "ts_hi": 150.0, "f": 1.0,
         "verdict": "new", "decision": "hi=mid"}])
    return an


def test_primary_bisect_ignores_segment_run(tmp_path: Path) -> None:
    an = _two_change_tree(tmp_path)
    runs = mn.read_bisect(an / "bisect")
    rel, com = mn.primary_bisect(runs[runs.event_id == "E01"])
    assert rel is not None and com is not None
    assert rel.dir.startswith("E01_") and com.dir.startswith("E01c_")
    assert list(mn.segment_runs(runs[runs.event_id == "E01"]).dir) == ["E01a_tinyllama-1.1b_metal_pp512"]
    t = _values(mn.bisect_total_macros(runs, "x"))
    assert t["bisectRuns"] == "4" and t["bisectBuildsTotal"] == "13" and t["bisectStepsTotal"] == "16"
    assert t["bisectIntermediateSteps"] == "1" and t["bisectRunsIntermediate"] == "1"
    b = _values(mn.boundary_macros(["E01"], runs, "b"))
    assert b == {"nBoundarySingleCommit": "1", "bisectMaxBoundaryCommits": "1"}


def test_boundary_throughput() -> None:
    st = pd.DataFrame([{"step": 1, "ts_lo": 1.0, "ts_mid": 2.0, "ts_hi": 3.0, "decision": "lo=mid"},
                       {"step": 2, "ts_lo": 4.0, "ts_mid": 5.0, "ts_hi": 6.0, "decision": "hi=mid"}])
    assert mn.boundary_throughput(st) == (4.0, 5.0)
    assert mn.boundary_throughput(st.iloc[:1]) == (2.0, 3.0)
    with pytest.raises(ValueError):
        mn.boundary_throughput(st.assign(decision="stop"))


def test_segment_macros(tmp_path: Path) -> None:
    an = _two_change_tree(tmp_path)
    runs = mn.read_bisect(an / "bisect")
    v = _values(mn.segment_macros(["E01"], runs, an / "bisect", "s"))
    # first part: E01a, 100 -> 150 (+50%); second part: E01c last step lo=mid, 160 -> 320 (+100%)
    assert v["eOneFirstTsOld"] == "100" and v["eOneFirstTsNew"] == "150" and v["eOneFirstPct"] == "50"
    assert v["eOneSecondTsOld"] == "160" and v["eOneSecondTsNew"] == "320" and v["eOneSecondPct"] == "100"
    # interval 100 -> 330 (+230%); product 1.5 * 2 = 3 (+200%); residual 3.3 / 3 - 1 = 10%
    assert v["eOneIntervalPct"] == "230" and v["eOneProductPct"] == "200" and v["eOneResidualPct"] == "10"
    assert v["eOneSegLo"] == "b1" and v["eOneSegHi"] == "b3"
    assert v["eOneSegSteps"] == "8" and v["eOneSegBuilds"] == "8" and v["eOneSegCommits"] == "1"
    assert v["eOneSegCommit"] == "cafebabe9" and v["eOneSegLoCommit"] == "feedface1"
    assert v["eOneIntermediateMid"] == "b3" and v["eOneIntermediateF"] == "0.47"
    assert v["eOneIntermediateStep"] == "1"
    # the event-level macros still describe the main chain (E01 + E01c), builds over all runs include E01a
    e = _values(mn.event_macros(["E01"], pd.DataFrame(columns=["event_id"]), _empty_vis(), (), runs, "c", "v", "b"))
    assert e["eOneBisectCommit"] == "abcdef012" and e["eOneBisectLoCommit"] == "123456789"
    assert e["eOneBisectSteps"] == "5" and e["eOneBisectBuilds"] == "5" and e["eOneBisectBuildsAll"] == "13"
    # an event without a segment run gives no segment macros
    assert mn.segment_macros(["E03"], runs, an / "bisect", "s") == []


def _empty_vis() -> pd.DataFrame:
    return pd.DataFrame(columns=["event_id", "series", "state", "lr_pct", "z", "source"])


# ---------------------------------------------------------------- power, sensitivity, drift, re-checks

def _noise_model() -> pd.DataFrame:
    rows = []
    for s in mn.SERIES:
        m, b, t = s.split("/")
        rows.append({"model": m, "backend": b, "test": t, "sigma_fixed": 0.06 if t == "pp512" else 0.1})
    return pd.DataFrame(rows)


def _judge_series() -> pd.DataFrame:
    base = {"listed": 1, "fixed_n_a": 3, "fixed_n_b": 3}
    rows = [
        # E02: campaign -0.5, re-measured 0.0 +- 3 * 0.05 -> refuted
        {**base, "event_id": "E02", "series": MIS_C_PP, "tag_a": "b3", "tag_b": "b4", "step1_lr": -0.5,
         "fixed_lr": 0.0, "fixed_se": 0.05, "fixed_z": 0.0, "verdict": "noise"},
        # E05: campaign -0.12, re-measured -0.05 +- 0.15 -> inconclusive
        {**base, "event_id": "E05", "series": TINY_M_PP, "tag_a": "b5", "tag_b": "b6", "step1_lr": -0.12,
         "fixed_lr": -0.05, "fixed_se": 0.05, "fixed_z": -1.0, "verdict": "noise"},
        # E01: confirmed at z = 3.2, lr = 0.08 (survives z 3 / floor 5%, not z 3.5 or floor 10%)
        {**base, "event_id": "E01", "series": TINY_M_PP, "tag_a": "b1", "tag_b": "b3", "step1_lr": 0.6,
         "fixed_lr": 0.08, "fixed_se": 0.025, "fixed_z": 3.2, "verdict": "C"},
        # CP01: refuted
        {**base, "event_id": "CP01", "series": QWEN_M_PP, "tag_a": "b3", "tag_b": "b4", "step1_lr": 0.4,
         "fixed_lr": 0.01, "fixed_se": 0.04, "fixed_z": 0.25, "verdict": "noise"},
        # A/A: z 2.6 -> false positive only at z = 2.5
        {"event_id": "AA1", "series": MIS_C_PP, "tag_a": "b9", "tag_b": "b9", "listed": 1, "step1_lr": 0.0,
         "fixed_lr": 0.13, "fixed_se": 0.05, "fixed_z": 2.6, "fixed_n_a": 3, "fixed_n_b": 3, "verdict": "aa_ok"},
    ]
    return pd.DataFrame(rows)


def test_power_macros() -> None:
    pair = {("E02", MIS_C_PP, "b3", "b4"): -0.5, ("E05", TINY_M_PP, "b5", "b6"): -0.12,
            ("CP01", QWEN_M_PP, "b3", "b4"): 0.4}
    v = _values(mn.power_macros(_noise_model(), _judge_series(), {"": ["E02", "E05"], "Cp": ["CP01"]}, pair,
                                ["AA1"], 3.0, 3, "n", "s"))
    # exp(3 * 0.06 * sqrt(2/3)) - 1 = 15.8%; exp(3 * 0.1 * sqrt(2/3)) - 1 = 27.8%
    assert v["mdeMin"] == "16" and v["mdeMax"] == "28" and v["mdePpMax"] == "16" and v["mdeTgMin"] == "28"
    assert v["mdePowerMin"] == "21"  # exp(3.8416 * 0.06 * 0.8165) - 1 = 20.7%
    assert v["aaHalfWidthMin"] == "16" and v["aaFpUpperPct"] == "95"  # 1 - 0.05^(1/1)
    assert v["nNoiseRefuted"] == "1" and v["nNoiseInconclusive"] == "1"
    assert v["nNoiseRefutedCp"] == "1" and v["nNoiseInconclusiveCp"] == "0"
    assert v["nNoiseRefutedAll"] == "2" and v["nNoiseInconclusiveAll"] == "1"
    assert v["nNoiseRowsRefuted"] == "2" and v["nNoiseRows"] == "3"


def test_campaign_pair_lr() -> None:
    cand = pd.DataFrame([{"event_id": "E02", "series_json": json.dumps(
        [{"series": MIS_C_PP, "tag_old": "b3", "tag_new": "b4", "log_ratio": -0.5}])}])
    assert mn.campaign_pair_lr([cand, pd.DataFrame({"event_id": []})]) == {("E02", MIS_C_PP, "b3", "b4"): -0.5}


def test_threshold_sensitivity() -> None:
    judge = mn.load_judge()
    vis = _empty_vis()
    vis = pd.concat([vis, pd.DataFrame([
        {"event_id": "E01", "series": TINY_M_PP, "state": "up", "lr_pct": 8.3, "z": 3.2, "source": "E01"},
        {"event_id": "E01", "series": "tinyllama-1.1b/metal/tg128", "state": "none", "lr_pct": 4.0, "z": 2.7,
         "source": "E01"},
        {"event_id": "E01", "series": MIS_C_PP, "state": "excluded", "lr_pct": -22.0, "z": -4.0, "source": "E01"}])],
        ignore_index=True)
    vis["lr_pct"] = vis.lr_pct.astype(float)
    vis["z"] = vis.z.astype(float)
    v = _values(mn.threshold_sensitivity_macros(_judge_series(), ["E01", "E02", "E05"], ["CP01"], ["AA1"], vis,
                                                judge, "x", default=(3.0, 0.05)))
    assert v["sensConfZThreeFloorFive"] == "1" and v["sensConfZThreeHalfFloorFive"] == "0"
    assert v["sensConfZThreeFloorTen"] == "0" and v["sensConfZTwoHalfFloorThree"] == "1"
    assert v["sensAAZTwoHalfFloorFive"] == "1" and v["sensAAZThreeFloorFive"] == "0"
    assert v["sensCpMax"] == "0"
    # tg128 cell (4%, z 2.7) visible only at z 2.5 with the 3% floor; the excluded cell never counts
    assert v["sensVisTgZTwoHalfFloorThree"] == "1" and v["sensVisTgZTwoHalfFloorFive"] == "0"
    assert v["sensVisPpZThreeFloorFive"] == "1" and v["sensVisPpZThreeHalfFloorFive"] == "0"
    assert v["sensConfMin"] == "0" and v["sensConfMax"] == "1"
    bad = _judge_series().assign(verdict="noise")
    with pytest.raises(ValueError):
        mn.threshold_sensitivity_macros(bad, ["E01"], [], [], vis, judge, "x", default=(3.0, 0.05))
    assert mn.threshold_sensitivity_macros(pd.DataFrame({"event_id": []}), [], [], [], vis, judge, "x") == []


def test_spearman() -> None:
    rho, p = mn._spearman(pd.Series([1.0, 2, 3, 4, 5]), pd.Series([2.0, 4, 6, 8, 10]))
    assert rho == pytest.approx(1.0) and p < 0.05
    rho, _ = mn._spearman(pd.Series([1.0, 2, 3, 4]), pd.Series([4.0, 3, 2, 1]))
    assert rho == pytest.approx(-1.0)


class _FakeJudge:
    """Stand-in for step2b_judge: campaign values from a dict, re-runs from a list."""

    def __init__(self, camp: dict[tuple[str, str, str, str], float], values: list[object]) -> None:
        self.camp, self.values = camp, values

    def campaign_value(self, results: Path, tag: str, model: str, backend: str, test: str) -> float | None:
        return self.camp.get((tag, model, backend, test))

    def collect(self, interleaved: Path) -> tuple[list[object], list[object]]:
        return self.values, []


def _recovery_tree(root: Path) -> None:
    tags = ["b10", "b11", "b12", "b13"]
    _csv(root / "results" / "progress.csv", [{"tag": t, "status": "ok"} for t in tags])
    _csv(root / "data" / "releases.csv", [{"tag": t, "commit_date_utc": f"2024-01-{1 + 10 * i:02d}T00:00:00Z"}
                                          for i, t in enumerate(tags)])


def test_recovery_macros(tmp_path: Path) -> None:
    _recovery_tree(tmp_path)
    cand = pd.DataFrame([{"event_id": "E03", "tag_old": "b10", "tag_new": "b11"},
                         {"event_id": "E04", "tag_old": "b11", "tag_new": "b12"},
                         {"event_id": "E46", "tag_old": "b10", "tag_new": "b11"}])
    vis = pd.DataFrame([{"event_id": "E03", "series": MIS_C_PP, "state": "down", "lr_pct": -60.0},
                        {"event_id": "E04", "series": MIS_C_PP, "state": "up", "lr_pct": 150.0},
                        {"event_id": "E46", "series": TINY_M_PP, "state": "down", "lr_pct": -20.0}])
    mis, tiny = ("mistral-7b", "cpu", "pp512"), ("tinyllama-1.1b", "metal", "pp512")
    camp = {("b10", *mis): 4.0, ("b11", *mis): 3.0, ("b12", *mis): 3.98, ("b13", *mis): 4.2,
            ("b10", *tiny): 5.0, ("b11", *tiny): 4.8, ("b12", *tiny): 4.8, ("b13", *tiny): 4.8}
    v = _values(mn.recovery_macros(tmp_path, ["E03", "E04", "E46"], cand, vis, _FakeJudge(camp, []), 0.05, "s"))
    assert v["campNewestTag"] == "b13"
    assert v["eThreeCampFate"] == "back at b12" and v["eThreeCampFateDays"] == "10"
    assert v["eFourCampFate"] == "kept"  # 4.2 - 3.0 > ln 1.05
    assert v["eFortySixCampFate"] == "not back" and v["eFortySixCampOpenDays"] == "20"


def test_drift_macros(tmp_path: Path) -> None:
    res = tmp_path / "results"
    tags = [f"b{i}" for i in range(1, 7)]
    _csv(res / "progress.csv", [{"tag": t, "status": "ok"} for t in tags])
    camp, values = {}, []
    for i, t in enumerate(tags):
        (res / t).mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"model": "mistral-7b", "backend": "cpu", "exit_code": 0,
                       "started_at_utc": f"2026-10-12T14:{10 * i:02d}:00Z", "idle_pct_before": 80.0 + i}]).to_csv(
            res / t / "runs.tsv", sep="\t", index=False)
        camp[(t, "mistral-7b", "cpu", "pp512")] = 4.0 + 0.01 * i  # residual grows with time and idle share
        values.append(type("V", (), {})())
        values[-1].__dict__.update({"phase": "default", "tag": t, "model": "mistral-7b", "backend": "cpu",
                                    "test": "pp512", "y": 4.0})
    cp = pd.DataFrame([{"event_id": "CP01", "tag_old": "b2", "tag_new": "b3",
                        "series_json": json.dumps([{"series": MIS_C_PP}])}])
    v = _values(mn.drift_macros(tmp_path, _FakeJudge(camp, values), cp))
    assert v["driftSeries"] == "1" and v["driftReleasesMin"] == "6"
    assert v["driftRhoTimeMax"] == "1.00" and v["driftRhoIdleMin"] == "1.00" and v["driftIdlePos"] == "1"
    assert v["driftTimeSig"] == "1" and v["cpGapMinutesMin"] == "10"
    assert v["driftRhoTimeMedian"] == "1.00" and v["driftRhoIdleMedian"] == "1.00"
    assert mn.drift_macros(tmp_path, _FakeJudge(camp, []), cp) == []


def test_eone_recheck_macros(tmp_path: Path) -> None:
    an = tmp_path / "results" / "analysis"
    d = an / "bisect" / "E01cpu_mistral-7b_cpu_pp512"
    d.mkdir(parents=True)
    pd.DataFrame([{"started_at_utc": "2026-10-26T12:10:00Z"}]).to_csv(d / "runs.tsv", sep="\t", index=False)
    _csv(d / "steps.csv", [{"step": 1, "ts_lo": 71.28, "ts_mid": 70.28, "ts_hi": 67.48}])
    for name, day in (("E01_b1_b2", "14"), ("E01R_b1_b2", "15")):
        (an / "interleaved" / name).mkdir(parents=True)
        pd.DataFrame([{"started_at_utc": f"2026-10-{day}T20:00:00Z"}]).to_csv(
            an / "interleaved" / name / "runs.tsv", sep="\t", index=False)
    hc = an / "harness_check_E01"
    hc.mkdir()
    (hc / "run.sh").write_text("for r in 1 2; do\n")
    for f, ts in (("r1_b1137_n0", 100.0), ("r2_b1137_n0", 100.0), ("r1_b1245_n0", 96.0), ("r2_b1245_n0", 96.0)):
        (hc / f"{f}.json").write_text(json.dumps([{"n_prompt": 512, "n_gen": 0, "samples_ts": [ts]}]))
    runs = pd.DataFrame([{"dir": d.name, "run_id": "E01cpu", "ref_lr": 0.248}])
    v = _values(mn.eone_recheck_macros(tmp_path, runs))
    assert v["eOneRecheckDaysMin"] == "11" and v["eOneRecheckDaysMax"] == "12"
    assert v["eOneCpuBisectPct"] == "$-$5.3" and v["eOneCpuRefPct"] == "$-$22"
    assert v["eOneHarnessPct"] == "$-$4" and v["eOneHarnessRounds"] == "2"
    assert mn.eone_recheck_macros(tmp_path, runs.assign(run_id="E16")) == []


def test_borderline_macros() -> None:
    vis = pd.DataFrame([
        {"event_id": "E04", "series": "mistral-7b/cpu/tg128", "state": "none", "lr_pct": 16.4, "z": 2.967},
        {"event_id": "E50", "series": "mistral-7b/metal/pp512", "state": "none", "lr_pct": 36.0, "z": 1.57},
        {"event_id": "E01", "series": MIS_C_PP, "state": "excluded", "lr_pct": -22.0, "z": -3.97},
        {"event_id": "E03", "series": MIS_C_PP, "state": "down", "lr_pct": -68.0, "z": -18.0}])
    v = _values(mn.borderline_macros(vis, "x", 3.0))
    assert v["nBorderlineCells"] == "1"
    assert v["borderlineCellList"] == "E04 on Mistral-7B CPU tg128 (+16\\%, $z = 2.97$)"
    assert v["nLargeNotVisibleCells"] == "2" and v["nLargeNotVisibleCellsTg"] == "1"
    assert v["nTgCellsMeasured"] == "1"


def test_and_list() -> None:
    """English enumeration used in the load-window macros."""
    assert mn.and_list([]) == "none"
    assert mn.and_list(["E01"]) == "E01"
    assert mn.and_list(["E01", "E14", "E44"]) == "E01, E14 and E44"


def test_load_window_macros_skip_without_files(tmp_path: Path) -> None:
    """Without the load-window outputs the macros are skipped, not invented."""
    cand = pd.DataFrame({"event_id": ["E01"]})
    ev = pd.DataFrame({"event_id": ["E01"], "verdict_v11": ["C"]})
    vis = pd.DataFrame(columns=["event_id", "series", "state", "z", "lr_pct"])
    assert mn.load_window_macros(tmp_path, cand, ev, vis) == []


def test_cost_macros_skip_without_logs(tmp_path: Path) -> None:
    """Without run and build logs the cost macros are skipped."""
    assert mn.cost_macros(tmp_path, 20.0) == []


def test_switch_macros(tmp_path: Path) -> None:
    """Step-3b comparisons become sw* macros; without the outputs nothing is invented."""
    sw = tmp_path / "results" / "analysis" / "switch"
    sw.mkdir(parents=True)
    tiny = "tinyllama-1.1b/cpu/pp512"
    pd.DataFrame([
        {"exp": "S19", "series": tiny, "x": "A", "y": "B", "n_x": 6, "n_y": 6, "lr": math.log(0.58), "z": -20.04},
        {"exp": "S19", "series": tiny, "x": "A", "y": "C", "n_x": 6, "n_y": 6, "lr": math.log(1.01), "z": 0.44},
        {"exp": "S19", "series": tiny, "x": "R", "y": "R", "n_x": None, "n_y": None, "lr": 1.02, "z": None},
        {"exp": "T04", "series": "mistral-7b/cpu/tg128", "x": "A", "y": "B", "n_x": 6, "n_y": 6,
         "lr": math.log(1.02), "z": 0.51}]).to_csv(sw / "comparisons.csv", index=False)
    pd.DataFrame([{"exp": "S19", "series": tiny, "arm": "A", "n": 6},
                  {"exp": "S46", "series": "qwen2.5-1.5b/cpu/pp512", "arm": "A", "n": 3}]).to_csv(sw / "arms.csv",
                                                                                                index=False)
    se = pd.DataFrame([{"event_id": "E04", "series": "mistral-7b/cpu/tg128", "fixed_lr": math.log(1.16),
                        "fixed_z": 2.97}])
    v = _values(mn.switch_macros(tmp_path, se))
    assert v["swNineteenTinyBA"] == "$-$42" and v["swNineteenTinyCA"] == "+1" and v["swNineteenTinyRecovered"] == "102"
    assert v["swNineteenTinyBAZ"] == "$-$20.0" and v["swFourBA"] == "+2" and v["swFourBAZ"] == "0.5"
    assert v["swFourFirstPct"] == "+16" and v["swFourFirstZ"] == "2.97"
    assert v["swRoundsLong"] == "6" and v["swRoundsShort"] == "3" and "pollDefaultNewest" not in v
    assert mn.switch_macros(tmp_path / "elsewhere", se) == []


def test_long_term_macros(tmp_path: Path) -> None:
    head = "tag,model,backend,test,status,param_set,avg_ts\n"
    for i, tag in enumerate(("b1", "b2", "b3", "b4", "b5", "b6")):
        d = tmp_path / "results" / tag
        d.mkdir(parents=True)
        (d / "records.csv").write_text(head + f"{tag},mistral-7b,cpu,pp512,ok,main,{10 * (1 + i // 3)}\n"
                                       + f"{tag},mistral-7b,cpu,tg128,ok,main,{5 + i // 3}\n"
                                       + f"{tag},tinyllama-1.1b,cpu,tg128,ok,main,8\n")
    vis = mn.pd.DataFrame({"event_id": ["E01"], "series": ["mistral-7b/cpu/pp512"], "state": ["down"],
                           "lr_pct": [-50.0], "z": [-5.0], "source": ["E01"]})
    cand = mn.pd.DataFrame({"event_id": ["E01"], "b_old": [1], "b_new": [3]})
    cps = mn.pd.DataFrame({"b_left_end": [1, 4], "b_right_start": [2, 5]})
    v = _values(mn.long_term_macros(tmp_path, vis, (), cand, cps, ["E01"], "v", "c"))
    assert v["netMistralCpuPp"] == "2.00" and v["netConfMistralCpuPp"] == "0.50"
    assert v["netTgMin"] == "1.00" and v["netTgMax"] == "1.20"
    assert v["nCpInConfirmed"] == "1" and v["nConfirmedWithCp"] == "1"


def test_direction_macros() -> None:
    vis = pd.DataFrame([
        {"event_id": "E01", "series": TINY_M_PP, "state": "up", "lr_pct": 10.0, "z": 5.0, "source": "E01"},
        {"event_id": "E03", "series": MIS_C_PP, "state": "down", "lr_pct": -10.0, "z": -5.0, "source": "E03"},
        {"event_id": "E03", "series": TINY_M_PP, "state": "none", "lr_pct": 1.0, "z": 0.5, "source": "E03"},
    ])
    vals = {m.name: m.value for m in mn.direction_macros(vis, (), "src")}
    assert vals["nRegressions"] == "1" and vals["nImprovements"] == "1"
    assert vals["nRegressionsWord"] == "one" and vals["nRegressionsCap"] == "One"
    mixed = pd.concat([vis, pd.DataFrame([{"event_id": "E01", "series": MIS_C_PP, "state": "down", "lr_pct": -9.0,
                                           "z": -5.0, "source": "E01"}])], ignore_index=True)
    vals = {m.name: m.value for m in mn.direction_macros(mixed, (), "src")}
    assert vals["nRegressions"] == "1" and vals["nImprovements"] == "0"
