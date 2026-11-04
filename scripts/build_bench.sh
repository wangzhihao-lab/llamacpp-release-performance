#!/usr/bin/env bash
# Build llama-bench for one llama.cpp release tag and run the benchmark matrix.
#
# Steps
#   1. Download https://github.com/ggml-org/llama.cpp/archive/refs/tags/<tag>.tar.gz
#      to src/<tag>.tar.gz (kept), verify the embedded commit id against
#      data/releases.csv, extract to src/<tag>/.
#   2. Configure + build only the llama-bench target (Release, -j $JOBS) in
#      build/<tag>/ with version-adapted CMake options (see "Version adaptation" below),
#      timing configure and build separately.
#   3. For every model x backend x parameter set run llama-bench -o json:
#        backends : metal = -ngl 99 (all layers on Metal, default threads)
#                   cpu   = -ngl 0 -t $CPU_THREADS, plus -nopo 1 when the binary
#                           supports it (from b6556 the Metal backend otherwise
#                           offloads batched MUL_MAT to the GPU even with -ngl 0)
#        sets     : main = -p 512 -n 128 ; long = -p 2048 -n 32 ; both -r $REPS
#      Raw output: results/<tag>/<model>_<backend>.json (main) and
#      results/<tag>/<model>_<backend>_long.json (long), stderr in *.log.
#   4. parse_bench.py finalize -> records.csv + status.json, then DONE marker.
#   5. Copy build/<tag>/bin to bins/<tag>/ and delete src/<tag>/ and build/<tag>/
#      (set KEEP_BUILD=1 to keep them).
# Failures never abort the script: they are recorded in status.json/records.csv.
#
# Environment overrides [default]:
#   MODELS_DIR [<root>/models]   RESULTS_ROOT [<root>/results]
#   MODELS ["tinyllama-1.1b mistral-7b qwen2.5-1.5b"]  BACKENDS ["metal cpu"]
#   PARAM_SETS ["main long"]  REPS [5]  JOBS [8]  CPU_THREADS [8]
#   BENCH_TIMEOUT_S [3600]  BUILD_TIMEOUT_S [3600]  COOLDOWN_S [10]  KEEP_BUILD [0]
#   QUIET_IDLE_PCT [80]  QUIET_MAX_WAIT_S [300]  QUIET_TAG_BUDGET_S [900]
# The campaign of the paper ran with PARAM_SETS=main (pp512 and tg128 only).
#
# Build-only mode (BUILD_ONLY=1; used by scripts/analysis/step3_bisect.py): steps 1, 2 and 5
# only -- download, configure, build llama-bench, save its --help, copy the binary to
# bins/<tag>/, write status.json (status built | build_failed | download_failed) and DONE
# (not after a download failure); no benchmark is run. RESULTS_ROOT must then point somewhere
# other than <root>/results itself (step 3 uses <root>/results/bisect_builds), because the
# script starts with rm -rf $RESULTS_ROOT/<tag>; otherwise it exits with status 2. An existing
# bins/<tag>/llama-bench is kept (exit 0, nothing done) unless BUILD_FORCE=1.
#
# Commits: instead of a release tag the argument may be c<7-40 hex digits>, a commit of
# llama.cpp (commit-level bisection). The source is then
# https://github.com/ggml-org/llama.cpp/archive/<sha>.tar.gz (the sha resolved to the full id
# in repo/ when possible, offline), and the expected commit recorded for verification is that
# sha instead of the data/releases.csv entry.
#
# Run: bash scripts/build_bench.sh b11559
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
TAG="${1:-}"
if ! [[ "$TAG" =~ ^b[0-9]+$ || "$TAG" =~ ^c[0-9a-f]{7,40}$ ]]; then
  echo "usage: build_bench.sh <tag like b1137 | c<7-40 hex digit commit sha>>" >&2
  exit 2
fi

MODELS_DIR="${MODELS_DIR:-$ROOT/models}"
RESULTS_ROOT="${RESULTS_ROOT:-$ROOT/results}"
MODELS="${MODELS:-tinyllama-1.1b mistral-7b qwen2.5-1.5b}"
BACKENDS="${BACKENDS:-metal cpu}"
PARAM_SETS="${PARAM_SETS:-main long}"
REPS="${REPS:-5}"
JOBS="${JOBS:-8}"
CPU_THREADS="${CPU_THREADS:-8}"
BENCH_TIMEOUT_S="${BENCH_TIMEOUT_S:-3600}"
BUILD_TIMEOUT_S="${BUILD_TIMEOUT_S:-3600}"
COOLDOWN_S="${COOLDOWN_S:-10}"
KEEP_BUILD="${KEEP_BUILD:-0}"
BUILD_ONLY="${BUILD_ONLY:-0}"

RES="$RESULTS_ROOT/$TAG"
SRC_TGZ="$ROOT/src/$TAG.tar.gz"
SRC_DIR="$ROOT/src/$TAG"
BUILD_DIR="$ROOT/build/$TAG"
BINS_DIR="$ROOT/bins/$TAG"
SHA=""
FULL_SHA=""
if [[ "$TAG" == c* ]]; then
  # Commit build: resolve the sha in the local blob-less clone (no network, no object fetch).
  SHA="${TAG#c}"
  FULL_SHA="$(GIT_NO_LAZY_FETCH=1 git -c protocol.allow=never -C "$ROOT/repo" rev-parse --verify --quiet "$SHA^{commit}" 2> /dev/null)"
  URL="https://github.com/ggml-org/llama.cpp/archive/${FULL_SHA:-$SHA}.tar.gz"
else
  URL="https://github.com/ggml-org/llama.cpp/archive/refs/tags/$TAG.tar.gz"
fi
PARSER="$SCRIPT_DIR/parse_bench.py"

if [ "$BUILD_ONLY" = "1" ]; then
  # Guards (build-only mode only; the default path is unchanged).
  mkdir -p "$RESULTS_ROOT"
  if [ "$(cd "$RESULTS_ROOT" && pwd -P)" = "$(cd "$ROOT/results" 2> /dev/null && pwd -P)" ]; then
    echo "BUILD_ONLY=1: RESULTS_ROOT must not be $ROOT/results (the script starts with rm -rf \$RESULTS_ROOT/<tag>); use e.g. $ROOT/results/bisect_builds" >&2
    exit 2
  fi
  if [ -x "$BINS_DIR/llama-bench" ] && [ "${BUILD_FORCE:-0}" != "1" ]; then
    echo "BUILD_ONLY=1: $BINS_DIR/llama-bench exists; not rebuilt (BUILD_FORCE=1 rebuilds)" >&2
    exit 0
  fi
fi

# Run a command with a wall-clock limit (macOS has no timeout(1)); the command
# runs in its own process group so make/clang children are killed too.
# Exit status 124 means the limit was hit.
with_timeout() {
  local limit="$1"; shift
  perl -e '
    my $t = shift @ARGV;
    my $pid = fork();
    die "fork failed\n" unless defined $pid;
    if ($pid == 0) { setpgrp(0, 0); exec @ARGV or exit 127; }
    $SIG{ALRM} = sub { kill "TERM", -$pid; sleep 5; kill "KILL", -$pid; waitpid($pid, 0); exit 124; };
    alarm $t;
    waitpid($pid, 0);
    my $st = $?;
    alarm 0;
    exit(($st & 127) ? 128 + ($st & 127) : ($st >> 8));
  ' "$limit" "$@"
}

now() { perl -MTime::HiRes=time -e 'printf "%.3f\n", time'; }
utc_now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
elapsed() { perl -e 'printf "%.3f\n", $ARGV[1] - $ARGV[0]' "$1" "$2"; }
log() { printf '%s [%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$TAG" "$*"; }
meta() { printf '%s\t%s\n' "$1" "$(printf '%s' "$2" | tr '\t\n' '  ')" >> "$RES/build_meta.tsv"; }

model_file() {
  case "$1" in
    tinyllama-1.1b) echo "$MODELS_DIR/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" ;;
    mistral-7b)     echo "$MODELS_DIR/mistral-7b-instruct-v0.2.Q4_K_M.gguf" ;;
    qwen2.5-1.5b)   echo "$MODELS_DIR/qwen2.5-1.5b-instruct-q4_k_m.gguf" ;;
    qwen2.5-0.5b)   echo "$MODELS_DIR/qwen2.5-0.5b-instruct-q4_k_m.gguf" ;;
    *)              echo "" ;;
  esac
}

# CPU idle percentage over a 1-second sample (second sample of top).
cpu_idle_pct() { top -l 2 -s 1 -n 0 2> /dev/null | awk '/CPU usage/ {v = $7} END {sub("%", "", v); print v + 0}'; }

# Wait until the machine is quiet before a measurement: no foreign llama-bench
# process and CPU idle >= QUIET_IDLE_PCT. Each call waits at most
# QUIET_MAX_WAIT_S; the whole tag at most QUIET_TAG_BUDGET_S, after which the
# run proceeds anyway (idle% and waited seconds are recorded in runs.tsv).
# Sets globals LAST_WAITED and LAST_IDLE.
QUIET_IDLE_PCT="${QUIET_IDLE_PCT:-80}"
QUIET_MAX_WAIT_S="${QUIET_MAX_WAIT_S:-300}"
QUIET_TAG_BUDGET_S="${QUIET_TAG_BUDGET_S:-900}"
QUIET_SPENT=0
wait_for_quiet() {
  local waited=0 idle
  idle="$(cpu_idle_pct)"
  while [ "$waited" -lt "$QUIET_MAX_WAIT_S" ] && [ "$QUIET_SPENT" -lt "$QUIET_TAG_BUDGET_S" ]; do
    if ! pgrep -x llama-bench > /dev/null 2>&1 && awk -v i="$idle" -v t="$QUIET_IDLE_PCT" 'BEGIN {exit !(i >= t)}'; then
      break
    fi
    sleep 15
    waited=$((waited + 17)); QUIET_SPENT=$((QUIET_SPENT + 17))
    idle="$(cpu_idle_pct)"
  done
  LAST_WAITED="$waited"; LAST_IDLE="$idle"
}

# BUILD_ONLY: status.json straight from build_meta.tsv (there are no runs, so parse_bench
# finalize would report bench_failed). commit_verified: the tarball's embedded commit starts
# with the expected one (releases.csv for a tag, the sha itself for c<sha>).
write_build_status() {
  python3 -I - "$RES" "$SCRIPT_DIR" "$BINS_DIR" > "$RES/parse.log" 2>&1 << 'PY' || log "build status failed (see parse.log)"
import json
import sys
from pathlib import Path

res, scripts, bins = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
sys.path.insert(0, scripts)
import parse_bench as pb

meta = pb.read_tsv_kv(res / "build_meta.tsv")
tag, stage = meta.get("tag", res.name), meta.get("stage", "")
rel, tar = meta.get("release_commit", ""), meta.get("tarball_commit", "")
if stage == "built":
    status, reason = "built", ""
elif stage == "build_failed":
    status, reason = "build_failed", pb.build_failure_reason(res, str(pb.ROOT / "src" / tag) + "/")
else:
    status, reason = stage or "unknown", meta.get("failure", "")
keys = ("build_number", "commit_date_utc", "configure_rc", "build_rc", "configure_s", "build_s", "compile_s",
        "binary_bytes", "dylib_bytes", "linked_libs", "option_era", "bench_src_dir", "cmake_args",
        "cpu_no_op_offload_flag", "started_at_utc", "finished_at_utc", "tarball_sha256", "source_url")
out = {"tag": tag, "mode": "build_only", "status": status, "commit": tar or rel, "release_commit": rel,
       "tarball_commit": tar, "commit_verified": bool(tar) and len(rel) >= 7 and tar.startswith(rel),
       **{k: meta.get(k, "") for k in keys}, "bins_dir": bins, "failure_reason": reason[:pb.REASON_CHARS],
       "failure_detail": reason[:4000]}
(res / "status.json").write_text(json.dumps(out, indent=2) + "\n")
print(f"{tag}: status={status} commit_verified={out['commit_verified']}")
PY
}

finish() {
  # $1 = stage reached (download_failed | build_failed | benchmarked | built [BUILD_ONLY])
  meta stage "$1"
  meta finished_at_utc "$(utc_now)"
  if [ "$BUILD_ONLY" = "1" ]; then
    write_build_status
  else
    python3 -I "$PARSER" finalize "$RES" > "$RES/parse.log" 2>&1 || log "parse_bench finalize failed (see parse.log)"
  fi
  if [ -x "$BUILD_DIR/bin/llama-bench" ]; then
    rm -rf "$BINS_DIR"; mkdir -p "$BINS_DIR"
    cp -p "$BUILD_DIR"/bin/* "$BINS_DIR"/ 2>/dev/null
  fi
  if [ "$KEEP_BUILD" != "1" ]; then rm -rf "$BUILD_DIR" "$SRC_DIR"; fi
  # A download failure is transient (network): leave no DONE marker so a resumed
  # campaign retries the tag instead of skipping it.
  if [ "$1" != "download_failed" ]; then
    date -u '+%Y-%m-%dT%H:%M:%SZ' > "$RES/DONE"
  fi
  log "done stage=$1 -> $RES"
  exit 0
}

# ---------------------------------------------------------------- setup
rm -rf "$RES"
mkdir -p "$RES" "$ROOT/src" "$ROOT/build"
: > "$RES/build_meta.tsv"
printf 'model\tmodel_file\tbackend\tparam_set\tn_prompt\tn_gen\treps\textra_args\tjson_file\tlog_file\texit_code\twall_s\tload1_before\twaited_s\tstarted_at_utc\tidle_pct_before\n' > "$RES/runs.tsv"

if [ -n "$SHA" ]; then
  # commit build: expected commit = the sha itself (full id when repo/ resolved it), date from repo/
  cdate="$(TZ=UTC GIT_NO_LAZY_FETCH=1 git -c protocol.allow=never -C "$ROOT/repo" show -s --date=format-local:%Y-%m-%dT%H:%M:%SZ --format=%cd "${FULL_SHA:-$SHA}" 2> /dev/null)"
  rel="$(printf '%s\t%s\t' "${FULL_SHA:-$SHA}" "$cdate")"
else
  rel="$(awk -F, -v t="$TAG" '$1 == t {print $3 "\t" $4 "\t" $2}' "$ROOT/data/releases.csv" 2>/dev/null)"
fi
meta tag "$TAG"
meta release_commit "$(printf '%s' "$rel" | cut -f1)"
meta commit_date_utc "$(printf '%s' "$rel" | cut -f2)"
meta build_number "$(printf '%s' "$rel" | cut -f3)"
meta started_at_utc "$(utc_now)"
meta host_model "$(sysctl -n hw.model 2>/dev/null)"
meta cpu "$(sysctl -n machdep.cpu.brand_string 2>/dev/null)"
meta macos "$(sw_vers -productVersion 2>/dev/null)"
meta compiler "$(cc --version 2>/dev/null | head -1)"
meta cmake "$(cmake --version 2>/dev/null | head -1)"
meta power "$(pmset -g batt 2>/dev/null | head -1)"
meta reps "$REPS"
meta jobs "$JOBS"
meta cpu_threads "$CPU_THREADS"
meta source_url "$URL"
if [ "$BUILD_ONLY" = "1" ]; then meta mode build_only; fi
log "start (reps=$REPS jobs=$JOBS)"
if [ "$BUILD_ONLY" = "1" ]; then log "build-only mode: no benchmark"; fi

# ---------------------------------------------------------------- 1. source
if [ ! -s "$SRC_TGZ" ] || ! gzip -t "$SRC_TGZ" 2> /dev/null; then
  rm -f "$SRC_TGZ"
  if ! curl -fL --retry 8 --retry-delay 30 --retry-all-errors -sS -o "$SRC_TGZ.part" "$URL" 2> "$RES/download.log"; then
    rm -f "$SRC_TGZ.part"
    meta failure "download failed: $(tail -1 "$RES/download.log")"
    finish download_failed
  fi
  mv "$SRC_TGZ.part" "$SRC_TGZ"
fi
meta tarball_sha256 "$(shasum -a 256 "$SRC_TGZ" | awk '{print $1}')"
meta tarball_commit "$(gzip -dc "$SRC_TGZ" | git get-tar-commit-id 2> /dev/null)"
rm -rf "$SRC_DIR"; mkdir -p "$SRC_DIR"
if ! tar -xzf "$SRC_TGZ" -C "$SRC_DIR" --strip-components=1 2> "$RES/extract.log"; then
  meta failure "extract failed: $(tail -1 "$RES/extract.log")"
  rm -f "$SRC_TGZ"
  finish download_failed
fi

# ---------------------------------------------------------------- 2. build
# Version adaptation (verified on the selected tags):
#   * <= b3354: options are LLAMA_*; Metal default is OFF before ~b1245, so
#     LLAMA_METAL=ON is always passed; LLAMA_METAL_EMBED_LIBRARY exists from
#     ~b2330 (default OFF -> would need `xcrun metal`, absent here) -> ON.
#   * >= b3355: ggml/ subproject, options are GGML_* (EMBED default ON).
#   * llama-bench lives in examples/ (needs LLAMA_BUILD_EXAMPLES=ON) until it
#     moved to tools/ (>= b5273, LLAMA_BUILD_TOOLS).
#   * Always: static libs (single self-contained binary, comparable size),
#     no ccache, no tests/server/curl, CMake 4 policy floor.
CMAKE_ARGS=(-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
            -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_CURL=OFF)
if [ -f "$SRC_DIR/ggml/CMakeLists.txt" ]; then
  ERA="ggml"
  CMAKE_ARGS+=(-DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON -DGGML_CCACHE=OFF)
else
  ERA="llama"
  CMAKE_ARGS+=(-DLLAMA_METAL=ON)
  grep -q 'LLAMA_CCACHE' "$SRC_DIR/CMakeLists.txt" && CMAKE_ARGS+=(-DLLAMA_CCACHE=OFF)
  grep -q 'LLAMA_METAL_EMBED_LIBRARY' "$SRC_DIR/CMakeLists.txt" && CMAKE_ARGS+=(-DLLAMA_METAL_EMBED_LIBRARY=ON)
fi
if [ -d "$SRC_DIR/tools/llama-bench" ]; then
  BENCH_SRC="tools"
  CMAKE_ARGS+=(-DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_TOOLS=ON)
else
  BENCH_SRC="examples"
  CMAKE_ARGS+=(-DLLAMA_BUILD_EXAMPLES=ON)
fi
meta option_era "$ERA"
meta bench_src_dir "$BENCH_SRC"
meta cmake_args "${CMAKE_ARGS[*]}"

rm -rf "$BUILD_DIR"
t0="$(now)"
with_timeout "$BUILD_TIMEOUT_S" cmake -S "$SRC_DIR" -B "$BUILD_DIR" "${CMAKE_ARGS[@]}" > "$RES/cmake_configure.log" 2>&1
cfg_rc=$?
t1="$(now)"
bld_rc=-1
if [ "$cfg_rc" -eq 0 ]; then
  with_timeout "$BUILD_TIMEOUT_S" cmake --build "$BUILD_DIR" --config Release -j "$JOBS" --target llama-bench > "$RES/cmake_build.log" 2>&1
  bld_rc=$?
fi
t2="$(now)"
meta configure_rc "$cfg_rc"
meta build_rc "$bld_rc"
meta configure_s "$(elapsed "$t0" "$t1")"
meta build_s "$(elapsed "$t1" "$t2")"
meta compile_s "$(elapsed "$t0" "$t2")"

BIN="$BUILD_DIR/bin/llama-bench"
if [ "$bld_rc" -ne 0 ] || [ ! -x "$BIN" ]; then
  meta binary_bytes ""
  log "build failed (configure_rc=$cfg_rc build_rc=$bld_rc)"
  finish build_failed
fi
meta binary_bytes "$(stat -f %z "$BIN")"
meta dylib_bytes "$(find "$BUILD_DIR" -name '*.dylib' -type f -exec stat -f %z {} + 2>/dev/null | awk '{s += $1} END {print s + 0}')"
meta linked_libs "$(otool -L "$BIN" 2>/dev/null | tail -n +2 | awk '{print $1}' | grep -v '^/System\|^/usr/lib' | tr '\n' ' ')"
log "build ok in $(elapsed "$t0" "$t2") s"

"$BIN" --help > "$RES/llama-bench_help.txt" 2>&1
NOPO_ARGS=()
if grep -q -- '--no-op-offload' "$RES/llama-bench_help.txt"; then NOPO_ARGS=(-nopo 1); fi
meta cpu_no_op_offload_flag "${NOPO_ARGS[*]:-unsupported}"
if [ "$BUILD_ONLY" = "1" ]; then finish built; fi

# ---------------------------------------------------------------- 3. bench
export GGML_METAL_PATH_RESOURCES="$BUILD_DIR/bin"
first=1
for model in $MODELS; do
  mf="$(model_file "$model")"
  for backend in $BACKENDS; do
    case "$backend" in
      metal) BARGS=(-ngl 99) ;;
      cpu)   BARGS=(-ngl 0 -t "$CPU_THREADS" ${NOPO_ARGS[@]+"${NOPO_ARGS[@]}"}) ;;
      *)     log "unknown backend $backend"; continue ;;
    esac
    for pset in $PARAM_SETS; do
      case "$pset" in
        main) np=512;  ng=128; suffix="" ;;
        long) np=2048; ng=32;  suffix="_long" ;;
        *)    log "unknown param set $pset"; continue ;;
      esac
      base="${model}_${backend}${suffix}"
      json="$base.json"; errlog="$base.log"
      started="$(utc_now)"
      if [ -z "$mf" ] || [ ! -f "$mf" ]; then
        printf 'missing model file: %s\n' "${mf:-<unknown model $model>}" > "$RES/$errlog"
        : > "$RES/$json"
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
          "$model" "$mf" "$backend" "$pset" "$np" "$ng" "$REPS" "${BARGS[*]}" "$json" "$errlog" "-1" "0" "" "0" "$started" "" >> "$RES/runs.tsv"
        continue
      fi
      [ "$first" -eq 1 ] || sleep "$COOLDOWN_S"
      first=0
      wait_for_quiet
      load1="$(sysctl -n vm.loadavg | awk '{print $2}')"
      started="$(utc_now)"
      s0="$(now)"
      with_timeout "$BENCH_TIMEOUT_S" "$BIN" -m "$mf" -p "$np" -n "$ng" -r "$REPS" -o json "${BARGS[@]}" \
        > "$RES/$json" 2> "$RES/$errlog"
      rc=$?
      s1="$(now)"
      printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$model" "$mf" "$backend" "$pset" "$np" "$ng" "$REPS" "${BARGS[*]}" "$json" "$errlog" "$rc" "$(elapsed "$s0" "$s1")" "$load1" "$LAST_WAITED" "$started" "$LAST_IDLE" >> "$RES/runs.tsv"
      log "$base rc=$rc $(elapsed "$s0" "$s1") s (idle ${LAST_IDLE}% waited ${LAST_WAITED} s)"
    done
  done
done

finish benchmarked
