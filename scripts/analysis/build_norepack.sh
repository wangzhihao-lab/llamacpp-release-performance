#!/usr/bin/env bash
# Build llama-bench of b7142 without the CPU repacking code (arm C of experiment S46, step 3b).
#
# Same source tarball (src/b7142.tar.gz, sha256 checked against results/bisect_builds/b7142) and
# the same CMake options that scripts/build_bench.sh used for b7142, plus -DGGML_CPU_REPACK=OFF,
# which leaves GGML_USE_CPU_REPACK undefined, so the CPU_REPACK buffer type does not exist and
# every weight stays in the plain CPU buffer.  (llama-bench -ot .=CPU cannot do this in b7142:
# llama-model.cpp maps an override to the CPU buffer type back onto the extra buffer types.)
#
# Outputs: bins/b7142-norepack/ (copy of build/bin), results/analysis/switch/build_b7142_norepack/
# (configure and build logs, llama-bench --help, build_meta.tsv).  src/ and build/ copies are
# deleted afterwards.
#
# Run: bash scripts/analysis/build_norepack.sh

set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAG=b7142
OUT_TAG=b7142-norepack
TGZ="$ROOT/src/$TAG.tar.gz"
SRC_DIR="$ROOT/src/$OUT_TAG"
BUILD_DIR="$ROOT/build/$OUT_TAG"
RES="$ROOT/results/analysis/switch/build_$(echo "$OUT_TAG" | tr '-' '_')"
JOBS=8
mkdir -p "$RES"
meta() { printf '%s\t%s\n' "$1" "$2" >> "$RES/build_meta.tsv"; }
: > "$RES/build_meta.tsv"

want="$(awk -F'\t' '$1 == "tarball_sha256" {print $2}' "$ROOT/results/bisect_builds/$TAG/build_meta.tsv")"
have="$(shasum -a 256 "$TGZ" | awk '{print $1}')"
meta tag "$OUT_TAG"
meta source_tarball "$TGZ"
meta tarball_sha256 "$have"
if [ "$want" != "$have" ]; then
  echo "tarball sha256 $have differs from the recorded $want" >&2
  exit 2
fi

rm -rf "$SRC_DIR" "$BUILD_DIR"
mkdir -p "$SRC_DIR"
tar -xzf "$TGZ" -C "$SRC_DIR" --strip-components=1 || exit 3
CMAKE_ARGS=(-DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
            -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_CURL=OFF
            -DGGML_METAL=ON -DGGML_METAL_EMBED_LIBRARY=ON -DGGML_CCACHE=OFF
            -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_TOOLS=ON -DGGML_CPU_REPACK=OFF)
meta cmake_args "${CMAKE_ARGS[*]}"
meta compiler "$(clang --version | head -1)"
meta started_at_utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cmake -S "$SRC_DIR" -B "$BUILD_DIR" "${CMAKE_ARGS[@]}" > "$RES/cmake_configure.log" 2>&1 || exit 4
cmake --build "$BUILD_DIR" --config Release -j "$JOBS" --target llama-bench > "$RES/cmake_build.log" 2>&1 || exit 5
meta finished_at_utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BIN="$BUILD_DIR/bin/llama-bench"
[ -x "$BIN" ] || exit 6
meta binary_bytes "$(stat -f %z "$BIN")"
"$BIN" --help > "$RES/llama-bench_help.txt" 2>&1
rm -rf "$ROOT/bins/$OUT_TAG"
mkdir -p "$ROOT/bins/$OUT_TAG"
cp -R "$BUILD_DIR/bin/." "$ROOT/bins/$OUT_TAG/"
meta flags_files_defining_repack "$(grep -rl GGML_USE_CPU_REPACK "$BUILD_DIR" --include=flags.make | wc -l | tr -d ' ')"
rm -rf "$SRC_DIR" "$BUILD_DIR"
echo "built $ROOT/bins/$OUT_TAG/llama-bench"
