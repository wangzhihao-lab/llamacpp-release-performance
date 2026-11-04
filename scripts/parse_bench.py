"""Parse llama-bench outputs of one tag into flat records and a tag status.

Sub-commands
------------
finalize <tag_dir>
    Read ``build_meta.tsv`` and ``runs.tsv`` written by build_bench.sh plus the
    raw ``*.json``/``*.log`` files, and write ``records.csv`` (one row per
    tag x model x backend x test) and ``status.json`` (tag-level summary).
progress-header
    Print the header line of ``results/progress.csv``.
progress-row <tag_dir>
    Print the ``progress.csv`` row of a finished tag (from ``status.json``).
collect [--results DIR] [--out FILE]
    Concatenate all finished ``records.csv`` into one CSV (default
    ``data/bench_records.csv``), ordered by build number.

Record status values: ``ok``, ``load_failed`` (model could not be loaded, i.e.
unsupported by this version), ``run_failed`` (no result for the test after the
model was handled), ``timeout``, ``missing_model``. Tag status values: ``ok``
(every record ok or load_failed), ``partial``, ``bench_failed``,
``build_failed``, ``download_failed``.

Run: python3 -I scripts/parse_bench.py finalize results/b11559
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REASON_CHARS = 200

RECORD_FIELDS = [
    "tag", "build_number", "commit_date_utc", "build_commit", "model", "backend", "param_set", "test",
    "n_prompt", "n_gen", "status", "load_ok", "avg_ts", "stddev_ts", "n_samples", "build_commit_reported",
    "build_number_reported", "n_threads", "n_gpu_layers", "no_op_offload", "flash_attn", "n_batch", "n_ubatch",
    "type_k", "model_type", "model_size", "backends_reported", "cpu_info", "gpu_info", "test_time",
    "exit_code", "wall_s", "load1_before", "idle_pct_before", "waited_s", "extra_args", "error",
]
PROGRESS_FIELDS = [
    "tag", "build_number", "commit_date_utc", "commit", "status", "configure_s", "build_s", "compile_s",
    "binary_bytes", "runs_total", "runs_ok", "records_ok", "records_failed", "models_unsupported",
    "bench_wall_s", "finished_at_utc", "failure_reason",
]
LOAD_FAIL_RE = re.compile(
    r"failed to load model|error loading model|unknown model architecture|unable to load model|"
    r"invalid magic|unknown \(magic, version\)|llama_model_load: error|failed to read magic|"
    r"unsupported model|is not supported",
    re.IGNORECASE,
)
ERROR_RE = re.compile(r"error|failed|GGML_ASSERT|assert|abort|exception|segmentation|unknown", re.IGNORECASE)
CONTEXT_RE = re.compile(r"llama_new_context_with_model:|llama_context:|llama_init_from_model:")
BUILD_ERROR_RES = [
    re.compile(r"\berror:"),
    re.compile(r"CMake Error"),
    re.compile(r"\*\*\*.*Error"),
    re.compile(r"\berror\b", re.IGNORECASE),
]
GPU_FLAGS = ["cuda", "opencl", "vulkan", "kompute", "metal", "sycl", "rpc", "gpu_blas", "blas"]

logger = logging.getLogger(__name__)


def read_tsv_kv(path: Path) -> dict[str, str]:
    """Read ``key<TAB>value`` lines; later keys overwrite earlier ones.

    Args:
        path: TSV file.

    Returns:
        Mapping of keys to values (empty if the file is missing).
    """
    meta: dict[str, str] = {}
    if not path.exists():
        return meta
    for line in path.read_text(errors="replace").splitlines():
        key, _, value = line.partition("\t")
        if key:
            meta[key] = value
    return meta


def parse_entries(text: str) -> list[dict[str, Any]]:
    """Extract llama-bench JSON test entries, tolerating truncated output.

    Args:
        text: Raw stdout of ``llama-bench -o json``.

    Returns:
        List of test dictionaries (possibly empty).
    """
    start = text.find("[")
    if start < 0:
        return []
    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(text, start)
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
    except json.JSONDecodeError:
        pass
    entries: list[dict[str, Any]] = []
    pos = start + 1
    while True:
        brace = text.find("{", pos)
        if brace < 0:
            break
        try:
            obj, pos = decoder.raw_decode(text, brace)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            entries.append(obj)
    return entries


def test_name(n_prompt: int, n_gen: int, n_depth: int = 0) -> str:
    """Return the llama-bench style test name (``pp512``, ``tg128``, ...).

    Args:
        n_prompt: Prompt tokens.
        n_gen: Generated tokens.
        n_depth: Context depth (newer llama-bench only).

    Returns:
        Test name.
    """
    if n_prompt > 0 and n_gen == 0:
        name = f"pp{n_prompt}"
    elif n_gen > 0 and n_prompt == 0:
        name = f"tg{n_gen}"
    else:
        name = f"pp{n_prompt}+tg{n_gen}"
    return f"{name}@d{n_depth}" if n_depth else name


def first_error_line(text: str, pattern: re.Pattern[str] = ERROR_RE) -> str:
    """Return the first log line matching ``pattern`` or the last non-empty line.

    Args:
        text: Log text.
        pattern: Regular expression for interesting lines.

    Returns:
        A single stripped line (may be empty).
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        if pattern.search(line):
            return line
    return lines[-1] if lines else ""


def build_failure_reason(tag_dir: Path, src_prefix: str) -> str:
    """Summarise why configure/build failed, from the CMake logs.

    Args:
        tag_dir: Result directory of the tag.
        src_prefix: Absolute source path to strip from messages.

    Returns:
        Failure text (not truncated).
    """
    for name in ("cmake_configure.log", "cmake_build.log"):
        path = tag_dir / name
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for regex in BUILD_ERROR_RES:
            hits = [ln for ln in lines if regex.search(ln)]
            if hits:
                return f"{name}: {hits[0]}".replace(src_prefix, "")
    return "no binary produced (no error line found in logs)"


def gpu_flags(entry: dict[str, Any]) -> str:
    """Return the backends reported by llama-bench in a version-independent way.

    Args:
        entry: One JSON test entry.

    Returns:
        ``backends`` field if present, else the enabled legacy boolean flags.
    """
    if "backends" in entry:
        return str(entry["backends"])
    return ",".join(flag for flag in GPU_FLAGS if entry.get(flag) is True)


def finalize(tag_dir: Path) -> dict[str, Any]:
    """Write ``records.csv`` and ``status.json`` for one tag.

    Args:
        tag_dir: ``results/<tag>`` directory.

    Returns:
        The status dictionary that was written.
    """
    meta = read_tsv_kv(tag_dir / "build_meta.tsv")
    tag = meta.get("tag", tag_dir.name)
    release_commit = meta.get("release_commit", "")
    tar_commit = meta.get("tarball_commit", "")
    build_commit = tar_commit or release_commit
    src_prefix = str(ROOT / "src" / tag) + "/"
    stage = meta.get("stage", "")

    records: list[dict[str, Any]] = []
    runs: list[dict[str, str]] = []
    runs_path = tag_dir / "runs.tsv"
    if runs_path.exists():
        with runs_path.open(newline="") as fh:
            runs = list(csv.DictReader(fh, delimiter="\t"))

    runs_ok = 0
    run_failures: list[str] = []
    per_model_status: dict[str, set[str]] = {}
    for run in runs:
        n_prompt, n_gen = int(run["n_prompt"]), int(run["n_gen"])
        expected = [name for name, keep in ((test_name(n_prompt, 0), n_prompt > 0), (test_name(0, n_gen), n_gen > 0)) if keep]
        exit_code = int(run["exit_code"])
        json_path, log_path = tag_dir / run["json_file"], tag_dir / run["log_file"]
        raw = json_path.read_text(errors="replace") if json_path.exists() else ""
        log_text = log_path.read_text(errors="replace") if log_path.exists() else ""
        entries = parse_entries(raw)
        by_test = {
            test_name(int(e.get("n_prompt", 0)), int(e.get("n_gen", 0)), int(e.get("n_depth", 0) or 0)): e
            for e in entries
        }
        if exit_code == -1:
            fail_status, error = "missing_model", first_error_line(log_text)
        elif entries:
            fail_status = "timeout" if exit_code == 124 else "run_failed"
            error = f"exit {exit_code}: {first_error_line(log_text)}"
        elif LOAD_FAIL_RE.search(log_text):
            fail_status, error = "load_failed", first_error_line(log_text, LOAD_FAIL_RE)
        elif exit_code == 124:
            fail_status, error = "timeout", f"timeout after {run['wall_s']} s"
        else:
            fail_status, error = "run_failed", f"exit {exit_code}: {first_error_line(log_text)}"
        context_made = bool(CONTEXT_RE.search(log_text))
        all_ok = True
        for name in expected:
            entry = by_test.get(name)
            rec: dict[str, Any] = {
                "tag": tag, "build_number": meta.get("build_number", ""), "commit_date_utc": meta.get("commit_date_utc", ""),
                "build_commit": build_commit, "model": run["model"], "backend": run["backend"],
                "param_set": run["param_set"], "test": name, "n_prompt": n_prompt if name.startswith("pp") else 0,
                "n_gen": n_gen if name.startswith("tg") else 0, "exit_code": exit_code, "wall_s": run["wall_s"],
                "load1_before": run["load1_before"], "idle_pct_before": run.get("idle_pct_before", ""),
                "waited_s": run["waited_s"], "extra_args": run["extra_args"],
            }
            if entry is not None:
                samples = entry.get("samples_ts") or []
                rec.update({
                    "status": "ok", "load_ok": 1, "avg_ts": entry.get("avg_ts", ""), "stddev_ts": entry.get("stddev_ts", ""),
                    "n_samples": len(samples) if isinstance(samples, list) else "",
                    "build_commit_reported": entry.get("build_commit", ""), "build_number_reported": entry.get("build_number", ""),
                    "n_threads": entry.get("n_threads", ""), "n_gpu_layers": entry.get("n_gpu_layers", ""),
                    "no_op_offload": entry.get("no_op_offload", ""), "flash_attn": entry.get("flash_attn", ""),
                    "n_batch": entry.get("n_batch", ""), "n_ubatch": entry.get("n_ubatch", ""), "type_k": entry.get("type_k", ""),
                    "model_type": entry.get("model_type", ""), "model_size": entry.get("model_size", ""),
                    "backends_reported": gpu_flags(entry), "cpu_info": entry.get("cpu_info", ""),
                    "gpu_info": entry.get("gpu_info", ""), "test_time": entry.get("test_time", ""), "error": "",
                })
            else:
                all_ok = False
                load_ok = 0 if fail_status in ("load_failed", "missing_model") else int(bool(entries) or context_made)
                rec.update({"status": fail_status, "load_ok": load_ok, "error": error[:300]})
            per_model_status.setdefault(run["model"], set()).add(rec["status"])
            records.append(rec)
        if all_ok:
            runs_ok += 1
        else:
            run_failures.append(f"{run['model']}/{run['backend']}/{run['param_set']}: {fail_status}: {error}")

    with (tag_dir / "records.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RECORD_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow({k: rec.get(k, "") for k in RECORD_FIELDS})

    n_ok = sum(1 for r in records if r["status"] == "ok")
    n_fail = len(records) - n_ok
    unsupported = sorted(m for m, sts in per_model_status.items() if sts == {"load_failed"})
    hard_fail = [r for r in records if r["status"] not in ("ok", "load_failed")]
    if stage == "download_failed":
        status, reason = "download_failed", meta.get("failure", "download failed")
    elif stage == "build_failed":
        status, reason = "build_failed", build_failure_reason(tag_dir, src_prefix)
    elif not records or n_ok == 0:
        status, reason = "bench_failed", "; ".join(run_failures) or "no benchmark runs recorded"
    elif hard_fail:
        status, reason = "partial", "; ".join(run_failures)
    else:
        status = "ok"
        reason = ("unsupported: " + "; ".join(run_failures)) if run_failures else ""
    wall = sum(float(r["wall_s"] or 0) for r in runs)
    result: dict[str, Any] = {
        "tag": tag, "build_number": meta.get("build_number", ""), "commit_date_utc": meta.get("commit_date_utc", ""),
        "commit": build_commit, "release_commit": release_commit, "tarball_commit": tar_commit,
        "commit_verified": bool(tar_commit) and tar_commit == release_commit, "status": status,
        "configure_s": meta.get("configure_s", ""), "build_s": meta.get("build_s", ""), "compile_s": meta.get("compile_s", ""),
        "configure_rc": meta.get("configure_rc", ""), "build_rc": meta.get("build_rc", ""),
        "binary_bytes": meta.get("binary_bytes", ""), "dylib_bytes": meta.get("dylib_bytes", ""),
        "linked_libs": meta.get("linked_libs", ""), "option_era": meta.get("option_era", ""),
        "bench_src_dir": meta.get("bench_src_dir", ""), "cmake_args": meta.get("cmake_args", ""),
        "cpu_no_op_offload_flag": meta.get("cpu_no_op_offload_flag", ""), "runs_total": len(runs), "runs_ok": runs_ok,
        "records_ok": n_ok, "records_failed": n_fail, "models_unsupported": " ".join(unsupported),
        "bench_wall_s": round(wall, 3), "started_at_utc": meta.get("started_at_utc", ""),
        "finished_at_utc": meta.get("finished_at_utc", ""), "failure_reason": reason[:REASON_CHARS],
        "failure_detail": reason[:4000], "environment": {k: meta.get(k, "") for k in
            ("host_model", "cpu", "macos", "compiler", "cmake", "power", "reps", "jobs", "cpu_threads", "tarball_sha256", "source_url")},
    }
    (tag_dir / "status.json").write_text(json.dumps(result, indent=2) + "\n")
    logger.info("%s: status=%s records ok=%d failed=%d", tag, status, n_ok, n_fail)
    return result


def csv_line(values: list[Any]) -> str:
    """Format one CSV line (with proper quoting) without the trailing newline.

    Args:
        values: Cell values.

    Returns:
        CSV-encoded line.
    """
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow(values)
    return buf.getvalue()


def progress_row(tag_dir: Path) -> str:
    """Build the progress.csv line for a tag.

    Args:
        tag_dir: ``results/<tag>`` directory.

    Returns:
        CSV line; a ``parse_error`` row if ``status.json`` is missing or unreadable.
    """
    try:
        status = json.loads((tag_dir / "status.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        meta = read_tsv_kv(tag_dir / "build_meta.tsv")
        status = {"tag": tag_dir.name, "build_number": meta.get("build_number", ""),
                  "commit_date_utc": meta.get("commit_date_utc", ""), "commit": meta.get("release_commit", ""),
                  "status": "parse_error", "failure_reason": f"status.json unreadable: {exc}"[:REASON_CHARS]}
    return csv_line([status.get(k, "") for k in PROGRESS_FIELDS])


def collect(results: Path, out: Path) -> int:
    """Concatenate ``records.csv`` of all finished tags.

    Args:
        results: Results root (contains ``<tag>/records.csv``).
        out: Output CSV path.

    Returns:
        Number of records written.
    """
    tag_dirs = sorted((p for p in results.glob("b*") if (p / "DONE").exists() and (p / "records.csv").exists()),
                      key=lambda p: int(p.name[1:]) if p.name[1:].isdigit() else 0)
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RECORD_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for tag_dir in tag_dirs:
            with (tag_dir / "records.csv").open(newline="") as src:
                for row in csv.DictReader(src):
                    writer.writerow(row)
                    count += 1
    logger.info("wrote %d records from %d tags to %s", count, len(tag_dirs), out)
    return count


def main() -> None:
    """Dispatch the sub-commands."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_fin = sub.add_parser("finalize")
    p_fin.add_argument("tag_dir", type=Path)
    sub.add_parser("progress-header")
    p_row = sub.add_parser("progress-row")
    p_row.add_argument("tag_dir", type=Path)
    p_col = sub.add_parser("collect")
    p_col.add_argument("--results", type=Path, default=ROOT / "results")
    p_col.add_argument("--out", type=Path, default=ROOT / "data" / "bench_records.csv")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)

    if args.cmd == "finalize":
        finalize(args.tag_dir)
    elif args.cmd == "progress-header":
        sys.stdout.write(csv_line(PROGRESS_FIELDS) + "\n")
    elif args.cmd == "progress-row":
        sys.stdout.write(progress_row(args.tag_dir) + "\n")
    elif args.cmd == "collect":
        collect(args.results, args.out)


if __name__ == "__main__":
    main()
