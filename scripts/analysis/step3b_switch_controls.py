#!/usr/bin/env python3
"""Root-cause protocol, step 3b: switch controls for E19 and E46 and re-tests of two cells.

The design was fixed on 2026-10-28, before any run (Section 3 of the paper).  Each experiment
measures a few arms (a binary plus options) interleaved on one series:

* ``S19`` (E19, #8672 thread pool): b3643, b3644 ``--poll 50`` (its default) and b3644
  ``--poll 0`` on TinyLlama and Mistral-7B CPU pp512;
* ``S46`` (E46, #16739 Q4_K repacking): b7141, b7142, and b7142 rebuilt with
  ``-DGGML_CPU_REPACK=OFF`` (``bins/b7142-norepack``, ``build_norepack.sh``), which keeps every
  weight in the plain CPU buffer, on Mistral-7B, Qwen2.5 and TinyLlama CPU pp512;
* ``T04`` (E04 on Mistral-7B CPU tg128, the borderline cell): b1561 against b1621, tg128 alone;
* ``T50`` (E50 on Mistral-7B Metal pp512, large but not visible): b8916 against b9076.

A path check runs each S19/S46 arm once with ``-r 1 -v`` and ``GGML_SCHED_DEBUG=2`` and records
the buffer types of the weights and the back end of every matrix multiplication; no statistic
uses it (``--path-only`` runs just this part).

Timed runs follow step 2: one process per run, the fixed configuration of the earlier
re-measurement of the same pair, a warm-up run of arm A before each group, a 20 s cooldown and
the wait for a quiet machine of ``step2_interleaved.wait_quiet`` (CPU idle >= 80%, thermal state
<= 1, no other llama process, at most 300 s).  Three arms follow a Williams design (ABC BCA CAB
CBA ACB BAC; three-round groups use the first three), two arms alternate AB BA.  A sampler records
the load and the busiest processes every 60 s.  Completed runs are skipped on a restart.

Statistics, with the functions of ``step2b_judge.py``: y = ln(median(samples_ts)) per run; for
arms X and Y, lr = mean(y_Y) - mean(y_X), s = max(sigma_fixed of the series from
``interleaved/noise_model_v11.csv``, pooled within-arm SD), SE = s sqrt(1/n_X + 1/n_Y),
z = lr / SE; a difference meets the rule when |lr| >= ln 1.05 and |z| >= 3.  For three arms,
R = (mean y_C - mean y_B) / (mean y_A - mean y_B) is the share of the event that arm C recovers.

Outputs (``results/analysis/switch/``): ``<exp>_<model>_<backend>_<test>/`` with runs.tsv and one
JSON and log per run; ``path/`` with the path-check logs and ``path_summary.csv``;
``arms.csv``, ``comparisons.csv``, ``MEMO.md``.  ``--dry-run`` prints the plan;
``--summarize-only`` rebuilds the tables from the stored runs.

Run: nohup nice -n 5 uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step3b_switch_controls.py > results/analysis/switch/nohup.out 2>&1 &
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import logging
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step2_interleaved as s2
from step2b_judge import phase_test, run_value

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "analysis" / "switch"
NOISE = ROOT / "results" / "analysis" / "interleaved" / "noise_model_v11.csv"
WILLIAMS = ("ABC", "BCA", "CAB", "CBA", "ACB", "BAC")
TEST_ARGS = {"pp512": ["-p", "512", "-n", "0"], "tg128": ["-p", "0", "-n", "128"]}
CPU_OLD = ["-ngl", "0", "-t", "8", "-b", "512"]
CPU_2024 = CPU_OLD + ["-ub", "512", "-fa", "0", "-ctk", "f16", "-ctv", "f16", "-mmp", "1"]
CPU_2025 = CPU_2024 + ["--poll", "50", "-nopo", "1", "-pg", "0,0"]
METAL_2026 = ["-ngl", "99", "-t", "4", "-b", "512", "-ub", "512", "-fa", "0", "-ctk", "f16", "-ctv", "f16",
              "-mmp", "1", "-dio", "0", "--poll", "50", "-pg", "0,0"]
MIN_REL, Z_MIN = 0.05, 3.0
NODE_RE = re.compile(r"node #\s*\d+ \(\s*MUL_MAT\): .*?\[\s*(\S+)\s")
BUF_RE = re.compile(r"(\S+) (?:model )?buffer size =\s*([\d.]+) MiB")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Arm:
    """One binary with its options.

    Attributes:
        label: A, B or C.
        tag: Release tag.
        args: Options after the test and repetition flags.
        note: Short description for the tables.
    """

    label: str
    tag: str
    args: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class Group:
    """One series measured with the arms of an experiment.

    Attributes:
        exp: Experiment id (S19, S46, T04, T50).
        model: Model name.
        backend: cpu or metal.
        test: pp512 or tg128.
        rounds: Rounds of the design.
        arms: Arms in label order.
    """

    exp: str
    model: str
    backend: str
    test: str
    rounds: int
    arms: tuple[Arm, ...]

    @property
    def name(self) -> str:
        """Directory name of the group."""
        return f"{self.exp}_{self.model}_{self.backend}_{self.test}"

    @property
    def reps(self) -> int:
        """llama-bench -r as in step 2 (5 for mistral-7b, 10 for the small models)."""
        return 5 if self.model == "mistral-7b" else 10


S19_ARMS = (Arm("A", "b3643", tuple(CPU_2024 + ["-pg", "0,0"]), "b3643"),
            Arm("B", "b3644", tuple(CPU_2024 + ["--poll", "50", "-pg", "0,0"]), "b3644 --poll 50"),
            Arm("C", "b3644", tuple(CPU_2024 + ["--poll", "0", "-pg", "0,0"]), "b3644 --poll 0"))
S46_ARMS = (Arm("A", "b7141", tuple(CPU_2025), "b7141"),
            Arm("B", "b7142", tuple(CPU_2025), "b7142"),
            Arm("C", "b7142-norepack", tuple(CPU_2025), "b7142 built with -DGGML_CPU_REPACK=OFF"))
# Arm C first used "-ot .=CPU"; the path check showed that b7142 maps a CPU override back onto
# CPU_REPACK (llama-model.cpp: "when overriding to a CPU buffer, consider the extra buffer
# types"), so before any timed S46 run it became a rebuild of b7142 without the repacking code
# (scripts/analysis/build_norepack.sh; design amended on 2026-10-28).
GROUPS = (
    Group("S19", "tinyllama-1.1b", "cpu", "pp512", 6, S19_ARMS),
    Group("S19", "mistral-7b", "cpu", "pp512", 6, S19_ARMS),
    Group("S46", "mistral-7b", "cpu", "pp512", 6, S46_ARMS),
    Group("S46", "qwen2.5-1.5b", "cpu", "pp512", 3, S46_ARMS),
    Group("S46", "tinyllama-1.1b", "cpu", "pp512", 3, S46_ARMS),
    Group("T04", "mistral-7b", "cpu", "tg128", 6,
          (Arm("A", "b1561", tuple(CPU_OLD), "b1561"), Arm("B", "b1621", tuple(CPU_OLD + ["-ctk", "f16", "-ctv", "f16"]),
                                                            "b1621"))),
    Group("T50", "mistral-7b", "metal", "pp512", 6,
          (Arm("A", "b8916", tuple(METAL_2026), "b8916"), Arm("B", "b9076", tuple(METAL_2026), "b9076"))),
)
PATH_CHECKS = [(g, a) for g in GROUPS if g.exp == "S46" for a in g.arms] + \
              [(g, a) for g in GROUPS if g.exp == "S19" and g.model == "mistral-7b" for a in g.arms[:2]]


def order(group: Group) -> list[tuple[int, str]]:
    """(round, arm label) in execution order: Williams sequences for three arms, AB BA for two.

    Args:
        group: The group.

    Returns:
        The sequence.
    """
    seq = []
    for r in range(1, group.rounds + 1):
        labels = WILLIAMS[r - 1] if len(group.arms) == 3 else ("AB" if r % 2 == 1 else "BA")
        seq += [(r, lab) for lab in labels]
    return seq


def command(group: Group, arm: Arm, reps: int, extra: tuple[str, ...] = ()) -> list[str]:
    """Full llama-bench command of one run."""
    model = str(s2.MODELS_DIR / s2.MODEL_FILES[group.model])
    return ["/usr/bin/arch", "-arm64", str(s2.BINS / arm.tag / "llama-bench"), "-m", model, *TEST_ARGS[group.test],
            "-r", str(reps), "-o", "json", *arm.args, *extra]


def make_run(group: Group, arm: Arm, phase: str, rnd: int, argv: list[str], env: dict[str, str]) -> s2.Run:
    """A step-2 Run object, so that step 2's execute_run and runs.tsv format apply unchanged."""
    stem = f"{phase}_r{rnd}_{arm.label}_{arm.tag}" if phase != "path" else f"path_{group.exp}_{group.model}_{arm.label}_{arm.tag}"
    return s2.Run(event_id=group.exp, phase=phase, rnd=rnd, side=arm.label, tag=arm.tag, model=group.model,
                  backend=group.backend, argv=argv, env={"GGML_METAL_PATH_RESOURCES": str(s2.BINS / arm.tag), **env},
                  est_s=0.0, stem=stem)


def group_runs(group: Group) -> list[s2.Run]:
    """Warm-up run of arm A, then the design."""
    arms = {a.label: a for a in group.arms}
    runs = [make_run(group, arms["A"], "warmup", 0, command(group, arms["A"], group.reps), {})]
    runs += [make_run(group, arms[lab], "fixed", r, command(group, arms[lab], group.reps), {})
             for r, lab in order(group)]
    return runs


def has_test(path: Path, test: str) -> bool:
    """Whether a run's JSON holds a result for ``test``."""
    return test in s2.test_samples(s2.load_bench_json(path))


def sampler(path: Path, stop: threading.Event, every: float = 60.0) -> None:
    """Append load average and the five busiest processes to ``path`` until ``stop`` is set."""
    while not stop.wait(every):
        try:
            res = subprocess.run(["ps", "-Ao", "pid,pcpu,comm", "-r"], capture_output=True, text=True, timeout=20,
                                 check=False)
            top = " | ".join(" ".join(line.split()[:2] + [Path(line.split()[2]).name]) for line in
                             res.stdout.splitlines()[1:6] if len(line.split()) >= 3)
        except (OSError, subprocess.TimeoutExpired) as exc:
            top = f"ps failed: {exc}"
        stamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        with path.open("a") as fh:
            fh.write(f"{stamp}\tload1={os.getloadavg()[0]:.2f}\t{top}\n")


def execute(runs: list[s2.Run], out: Path, ns: argparse.Namespace, test: str | None) -> int:
    """Run in order, skipping completed runs, with the step-2 cooldown; returns the number of failures."""
    out.mkdir(parents=True, exist_ok=True)
    failures, first = 0, True
    for run in runs:
        if s2.STOP["flag"]:
            break
        jpath = out / f"{run.stem}.json"
        if jpath.is_file() and (test is None or has_test(jpath, test)) and not ns.force:
            continue
        if not first:
            time.sleep(ns.cooldown)
        first = False
        logger.info("%s %s r%d %s %s", run.event_id, run.model, run.rnd, run.side, run.phase)
        row = s2.execute_run(run, out, ns)
        s2.append_row(out / "runs.tsv", row)
        if str(row.get("exit_code")) != "0" or (test is not None and not has_test(jpath, test)):
            failures += 1
            logger.warning("run failed: %s (exit %s)", run.stem, row.get("exit_code"))
    return failures


def run_group(group: Group, ns: argparse.Namespace) -> None:
    """Measure one group; a failed run is repeated once at the end of the group."""
    out = OUT / group.name
    runs = group_runs(group)
    if execute(runs, out, ns, group.test):
        logger.info("%s: repeating failed runs once", group.name)
        execute(runs, out, ns, group.test)


def path_summary(path_dir: Path) -> pd.DataFrame:
    """Buffer types and back ends of the matrix multiplications from the path-check logs.

    The scheduler prints one block per graph it splits (the reserve graphs, the warm-up and the
    measured batch); the counts are those of the last block, the measured pp512 batch.

    Args:
        path_dir: Directory of the path-check logs.

    Returns:
        One row per log.
    """
    rows = []
    for log in sorted(path_dir.glob("path_*.log")):
        text = log.read_text(errors="replace")
        blocks = re.split(r"\n## SPLIT #0:", text)
        last = blocks[-1] if len(blocks) > 1 else ""
        counts: dict[str, int] = {}
        for backend in NODE_RE.findall(last):
            counts[backend] = counts.get(backend, 0) + 1
        buffers = "; ".join(f"{name} {size} MiB" for name, size in BUF_RE.findall(text))
        rows.append({"log": log.name, "graphs": len(blocks) - 1, "mul_mat_by_backend": counts, "buffers": buffers})
    return pd.DataFrame(rows)


def noise_floor() -> dict[tuple[str, str, str], float]:
    """sigma_fixed per (model, backend, test) from the v1.1 noise model."""
    df = pd.read_csv(NOISE)
    return {(r.model, r.backend, r.test): float(r.sigma_fixed) for r in df.itertuples()}


def summarize() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Arm table and pairwise comparisons from the stored runs.

    Returns:
        (arms, comparisons).
    """
    floor = noise_floor()
    arm_rows, cmp_rows = [], []
    for g in GROUPS:
        runs_tsv = OUT / g.name / "runs.tsv"
        if not runs_tsv.is_file():
            continue
        with runs_tsv.open(newline="") as fh:
            rows = [r for r in csv.DictReader(fh, delimiter="\t") if r["phase"] == "fixed"]
        ys: dict[str, list[float]] = {a.label: [] for a in g.arms}
        seen = set()
        for r in rows:  # a repeated run replaces nothing: the last row of each file counts once
            if r["json_file"] in seen:
                continue
            y = run_value(OUT / g.name / r["json_file"], g.test)
            if y is not None:
                ys[r["side"]].append(y)
                seen.add(r["json_file"])
        sigma = floor[(g.model, g.backend, g.test)]
        for a in g.arms:
            v = np.array(ys[a.label])
            arm_rows.append({"exp": g.exp, "series": f"{g.model}/{g.backend}/{g.test}", "arm": a.label, "tag": a.tag,
                             "note": a.note, "n": len(v), "ts_geomean": float(np.exp(v.mean())) if len(v) else np.nan,
                             "sd_y": float(v.std(ddof=1)) if len(v) > 1 else np.nan})
        pairs = [("A", "B"), ("B", "C"), ("A", "C")] if len(g.arms) == 3 else [("A", "B")]
        for x, y in pairs:
            res = phase_test(np.array(ys[x]), np.array(ys[y]), sigma, use_own=True)
            meets = (not math.isnan(res["z"]) and abs(res["lr"]) >= math.log1p(MIN_REL) and abs(res["z"]) >= Z_MIN)
            cmp_rows.append({"exp": g.exp, "series": f"{g.model}/{g.backend}/{g.test}", "x": x, "y": y,
                             "n_x": res["n_a"], "n_y": res["n_b"], "lr": res["lr"],
                             "pct": 100 * math.expm1(res["lr"]) if not math.isnan(res["lr"]) else np.nan,
                             "s": res["s"], "se": res["se"], "z": res["z"], "meets_rule": bool(meets)})
        if len(g.arms) == 3 and all(ys[k] for k in "ABC"):
            ya, yb, yc = (float(np.mean(ys[k])) for k in "ABC")
            cmp_rows.append({"exp": g.exp, "series": f"{g.model}/{g.backend}/{g.test}", "x": "R", "y": "R",
                             "lr": (yc - yb) / (ya - yb) if ya != yb else np.nan})
    return pd.DataFrame(arm_rows), pd.DataFrame(cmp_rows)


def md_table(df: pd.DataFrame) -> str:
    """A Markdown table of ``df`` (floats with three decimals), without the tabulate package."""
    def cell(v: object) -> str:
        return f"{v:.3f}" if isinstance(v, float) else str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    rule = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(cell(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([head, rule, *body])


def write_tables() -> None:
    """Write arms.csv, comparisons.csv, path_summary.csv and MEMO.md."""
    arms, cmps = summarize()
    arms.to_csv(OUT / "arms.csv", index=False)
    cmps.to_csv(OUT / "comparisons.csv", index=False)
    lines = ["# Step 3b: switch controls and dedicated re-tests (generated by `step3b_switch_controls.py`)", "",
             ("The design is given in Section 3 of the paper. Comparison X→Y: lr = mean(y_Y) − mean(y_X); a difference "
              "meets the rule when |lr| ≥ ln 1.05 and |z| ≥ 3."), ""]
    if not arms.empty:
        lines += ["## Arms", "", md_table(arms), ""]
    if not cmps.empty:
        lines += ["## Comparisons (in the rows with x = R, the lr column holds the recovered share R)", "",
                  md_table(cmps), ""]
    path_dir = OUT / "path"
    if path_dir.is_dir():
        ps = path_summary(path_dir)
        ps.to_csv(OUT / "path_summary.csv", index=False)
        lines += ["## Path check", "", md_table(ps), ""]
    (OUT / "MEMO.md").write_text("\n".join(lines) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Command-line interface (the waiting options are those of step 2)."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--only", type=lambda s: [x.strip() for x in s.split(",") if x.strip()], default=None,
                    help="experiments to run (default all: S19,S46,T04,T50)")
    ap.add_argument("--path-only", action="store_true", help="run only the path checks")
    ap.add_argument("--skip-path", action="store_true", help="do not run the path checks")
    ap.add_argument("--cooldown", type=float, default=20.0)
    ap.add_argument("--idle-min", type=float, default=80.0)
    ap.add_argument("--thermal-max", type=int, default=1)
    ap.add_argument("--load-max", type=float, default=0.0)
    ap.add_argument("--load-wait-max", type=float, default=300.0)
    ap.add_argument("--on-load-timeout", choices=("proceed", "skip", "stop"), default="proceed")
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--force", action="store_true", help="re-run runs whose output exists")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summarize-only", action="store_true")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the exit code."""
    ns = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    groups = [g for g in GROUPS if ns.only is None or g.exp in ns.only]
    checks = [(g, a) for g, a in PATH_CHECKS if ns.only is None or g.exp in ns.only]
    path_runs = [make_run(g, a, "path", 0, command(g, a, 1, ("-v",)), {"GGML_SCHED_DEBUG": "2"}) for g, a in checks]
    if ns.dry_run:
        for run in ([] if ns.skip_path else path_runs):
            print("path", " ".join(f"{k}={v}" for k, v in run.env.items()), " ".join(run.argv))
        for g in ([] if ns.path_only else groups):
            runs = group_runs(g)
            print(f"\n{g.name}: {len(runs)} runs (1 warm-up), order {' '.join(lab for _, lab in order(g))}")
            for run in runs[:len(g.arms) + 1]:
                print(" ", run.phase, run.rnd, run.side, " ".join(run.argv[2:]))
        return 0
    if ns.summarize_only:
        write_tables()
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, s2.handle_signal)
    signal.signal(signal.SIGINT, s2.handle_signal)
    stop = threading.Event()
    thread = threading.Thread(target=sampler, args=(OUT / "activity.log", stop), daemon=True)
    thread.start()
    try:
        if not ns.skip_path:
            execute(path_runs, OUT / "path", ns, "pp512")  # every path check is a pp512 run
        if not ns.path_only:
            for g in groups:
                if s2.STOP["flag"]:
                    break
                run_group(g, ns)
    finally:
        stop.set()
        thread.join(timeout=5)
    write_tables()
    logger.info("done%s", " (stopped)" if s2.STOP["flag"] else "")
    return 1 if s2.STOP["flag"] else 0


if __name__ == "__main__":
    sys.exit(main())
