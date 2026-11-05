# Replication package

This is the replication package of the paper "What Changes the Speed of an LLM Inference Engine? Re-measuring and Bisecting Three Years of llama.cpp Releases" by Xiaoyan Tian, Min Yu and Zhihao Wang.

The study sampled 81 llama.cpp releases from September 2023 to October 2026 (b1137 to b11559), rebuilt them with one toolchain, and measured each of the 78 that built once on one machine (the campaign). It then re-measured every candidate change with interleaved runs, bisected the confirmed changes to their commits, and checked in which benchmark series each change is visible. The package holds the build and measurement scripts, all raw results, the re-measurement and bisection logs, and the analysis scripts that generate every result and figure of the paper.

All commands below run from the repository root.

## Quick check: numbers and figures from the stored data

This path needs neither models nor llama.cpp binaries, and it took about one minute in total. It needs `uv` and Python 3.11 or later, and it was checked on macOS.

```
py() { uv run --no-project --with pandas --with numpy --with matplotlib python3 -I "$@"; }
py scripts/analysis/step2b_judge.py
py scripts/analysis/step2b_judge.py --drop-round1-unwarmed --suffix _norm1
py scripts/analysis/step2b_judge.py --exclude-windows results/analysis/load_windows.tsv --suffix _nowin
py scripts/analysis/load_window_check.py
py scripts/analysis/step3b_switch_controls.py --summarize-only
py scripts/analysis/step4_visibility.py
py scripts/paper/make_numbers.py
py scripts/paper/make_figures.py
py scripts/paper/make_fig_overview.py
py scripts/paper/make_fig_flow.py
```

The first six commands rewrite the derived tables under `results/analysis/` from the stored runs, with the same content. `make_numbers.py` writes `paper/numbers.tex` (and creates `paper/`): 788 LaTeX macros, one for every measured number of the paper, each preceded by a comment that names its source file and computation. `make_figures.py` writes the data figures, `make_fig_overview.py` the study overview and `make_fig_flow.py` the code paths and the decision flow to `paper/figs/`, as PDF and SVG; the last two read `paper/numbers.tex`, so `make_numbers.py` comes first. The figures use Times New Roman when the font is installed.

## Contents

| Path | Content |
|---|---|
| `scripts/list_releases.py`, `select_tags.py` | List the release tags and sample them in time |
| `scripts/fetch_models.sh` | Download and verify the three models |
| `scripts/build_bench.sh`, `run_campaign.sh`, `parse_bench.py` | Build one release and benchmark it; run the campaign; parse its output |
| `scripts/analysis/` | Detection, re-measurement, judgment, bisection, switch controls, visibility, with tests; `scripts/analysis/README.md` documents each step and its options |
| `scripts/analysis/queues/continuous.tsv` | The queue of re-measurement, judgment and bisection items, in the order of the study |
| `scripts/analysis/thermal_state.swift` | Source of the thermal-state probe |
| `scripts/paper/` | `make_numbers.py`, `make_figures.py`, `make_fig_overview.py`, `make_fig_flow.py`, their style and glyph modules, tests |
| `data/releases.csv` | All 7,189 `b<N>` tags from b1046 to b11559 with commit, commit date and commits since the previous tag |
| `data/selected_tags.txt`, `selected_tags.csv` | The 81 sampled releases |
| `data/models.tsv` | The three models: file, URL pinned to a Hugging Face commit, size, sha256 |
| `results/progress.csv` | One row per sampled release |
| `results/<tag>/` | Raw campaign output of one release (see "Output files") |
| `results/bisect_builds/<tag>/` | Build records of the 60 further builds of the bisections |
| `results/analysis/` | Events, effective configuration, re-measurements, judgments, bisections, switch controls, visibility |

Where the results of the paper are:

| Paper | Files (under `results/analysis/` unless the path starts with `results/`) |
|---|---|
| Sections 3.1 and 3.2, Table 2 | `results/progress.csv`, `results/<tag>/`, `effective_config.csv`, `config_changes.csv` |
| RQ1 | `candidate_events.csv`, `changepoints.csv`, `changepoint_events.csv`, `control_events.csv`, `remeasure_events.csv`, `interleaved/` (`judge_v11_series.csv`, `judge_v11_events.csv`, `noise_model_v11.csv`, the `_norm1` tables, one directory per event) |
| RQ2, Tables 3 and 4 | `bisect/` (one directory per bisection with `result.json`, `steps.csv`, `log.md`), `switch/`, `root_cause_categories.csv`, `root_cause_coding.csv` |
| RQ3 | `visibility_events.csv`, `step4_visibility.csv`, `step4_visibility.md` |
| RQ4 | `step5_test_matrix.md` |
| Section 5.2, Table 6 | `pr_reported.csv`, the numbers quoted from the pull-request threads, with where they stand |
| Section 6 | `load_windows.tsv`, `load_window_runs.tsv`, `load_window_bisect_steps.csv`, `interleaved/judge_v11_*_nowin.csv`, `harness_check_E01/` |

`control_events.csv`, `remeasure_events.csv`, `load_windows.tsv`, `root_cause_categories.csv` and `root_cause_coding.csv` are inputs of the scripts, not outputs, and `pr_reported.csv` is a record for readers that no script uses. `root_cause_categories.csv` holds the grouping of the confirmed events that results from reading the boundary commits (Section 4.2 of the paper).

Not in this package:

- The model files. `data/models.tsv` gives their URLs and sha256 sums, and `scripts/fetch_models.sh` downloads them.
- The llama.cpp source and binaries. `data/selected_tags.txt` and `scripts/build_bench.sh` recreate them from GitHub; they would go to `src/`, `bins/`, `build/` and `repo/`.
- The source of the manuscript. `make_numbers.py` and the figure scripts create `paper/` for their output.

## Environment

Measurements and builds (`build_meta.tsv` of every release):

| Item | Value |
|---|---|
| Machine | MacBook Air (Mac17,4), fanless; Apple M5, 4 performance and 6 efficiency cores; 32 GB; on mains power |
| Operating system | macOS 27.0 |
| Compiler | Apple clang version 17.0.0 (clang-1700.6.3.2) |
| CMake | 4.4.0 |
| Build jobs, CPU threads | 8 and 8 |
| Other | Homebrew `openssl@3`, which the releases from b7738 on link |

The analysis of the stored data was checked with `uv` 0.10.7, Python 3.11.13 and numpy 2.4.4, pandas 3.0.2, matplotlib 3.10.9 and pytest 9.1.1: it reproduces every macro of the paper. The scripts use `datetime.UTC`, which needs Python 3.11 or later. The `python3` that `uv` selected on the measurement machine was an x86_64 build under Rosetta; the scripts start native tools through `/usr/bin/arch -arm64` for this reason.

Measuring needs macOS on Apple silicon, with the Xcode command line tools (clang, git, swiftc), CMake, curl, perl, `uv` and a `python3` of version 3.11 or later. The manuscript was built with TeX Live 2022.

## Reproducing the study from zero

The paper numbers its steps by what they do, and the scripts by the order of the protocol:

| Step in the paper | Scripts |
|---|---|
| 1. Build and benchmark each release once | `build_bench.sh`, `run_campaign.sh` |
| 2. Detect changes | `step0_effective_config.py`, `step1_candidate_events.py`, `step1b_changepoints.py` |
| 3. Re-measure side by side | `step2_interleaved.py`, `step2b_judge.py` |
| 4. Bisect to commits | `step3_bisect.py`, `step3b_switch_controls.py` |
| 5. Check visibility on all series | `make_visibility_events.py`, `step2_interleaved.py`, `step4_visibility.py` |
| 6. Find the smallest covering set | `step4_visibility.py` |

### Cost

"Alone" marks the steps that time llama-bench: stop other work on the machine while they run. The other steps only read files, or are limited by the network. The times of the measuring steps are those of the study, taken from `progress.csv`, `runs.tsv` and `builds.tsv`. The times of the analysis steps were measured at background priority.

| Step | Alone | Time |
|---|---|---|
| Clone the llama.cpp history | no | Limited by the network |
| Select the tags | no | Under 1 s |
| Download the models | no | Limited by the network, 6.2 GB |
| Campaign | yes | 7.3 h for 468 llama-bench processes, of which 4.9 h benchmarking and 0.5 h compiling the 78 releases |
| Effective configuration (`step0`) | no | About 30 s |
| Candidates (`step1`) | no | About 20 s |
| Change points (`step1b`) | no | About 1 min |
| Re-measurement of all events | yes | 1,413 runs of 73 event directories: 15.3 h benchmarking, 7.8 h of pauses between runs, 1.1 h of waiting for a quiet machine; median 9 min per event |
| Bisection | yes | 16 bisections: 622 runs, 2.8 h benchmarking, 60 builds of 17 s (median) |
| Queue as a whole (re-measurement, judgment and 14 of the bisections) | yes | 30.9 h from 2026-10-14 14:01 UTC to 2026-10-15 20:58 UTC |
| Switch controls (`step3b`) | yes | 117 runs: 0.8 h benchmarking, with a pause of 20 s between runs |
| E01 harness check | yes | 13 min |
| Judgment (`step2b`), each variant | no | About 10 s |
| Load windows, step 3b tables, visibility tables | no | Under 5 s each |
| `make_numbers.py` | no | About 10 s |
| `make_figures.py`, `make_fig_overview.py`, `make_fig_flow.py` | no | About 20 s |

### Commands

`step2_interleaved.py` and `step3_bisect.py` start only inside a time window, 07:00 to 17:30 local time by default; the queue passes `--window 00:00-24:00`, and a manual run can do the same. Absolute throughput depends on the machine, and the results of E49 depend on the macOS version (Section 6 of the paper). `py` is the function of the quick check.

1. Prepare. Move the stored results aside, because `run_campaign.sh` skips every release that has a `DONE` file and the analysis scripts always work on `results/`. Build the thermal probe, or the `--thermal-max` condition silently has no effect: `thermal_state()` then returns -1.

   ```
   mkdir -p logs scripts/analysis/bin
   swiftc -O -o scripts/analysis/bin/thermal_state scripts/analysis/thermal_state.swift
   scripts/analysis/bin/thermal_state      # prints 0 (nominal), 1 (fair), 2 (serious) or 3 (critical)
   mv results results.published
   mkdir -p results/analysis/harness_check_E01 results/analysis/switch
   cp results.published/analysis/{control_events.csv,remeasure_events.csv,load_windows.tsv,root_cause_categories.csv,root_cause_coding.csv} results/analysis/
   cp results.published/analysis/harness_check_E01/run.sh results/analysis/harness_check_E01/
   ```

2. Select the releases. `list_releases.py` clones llama.cpp into `repo/` without blobs, which steps 0 and 3 need. With `--out` it leaves the list of the study in place. `select_tags.py` lays 80 equally spaced grid points from 2023-09-01 to the newest tag, takes the first release at or after each point, and adds the newest release. On `data/releases.csv` it reproduces `data/selected_tags.txt` and `selected_tags.csv` exactly; a newer list moves the grid and changes most tags.

   ```
   python3 -I scripts/list_releases.py --out data/releases_now.csv
   python3 -I scripts/select_tags.py
   ```

3. Download the models. The script takes the pinned URLs of `data/models.tsv` and checks size and sha256 of each file. The directory is the first argument, otherwise the environment variable `MODELS_DIR`, otherwise `models/`. Every later step reads `MODELS_DIR` with the same default.

   ```
   bash scripts/fetch_models.sh
   ```

4. Build and benchmark the releases (the campaign). `PARAM_SETS=main` gives the matrix of the paper (pp512 and tg128); the default also runs a long parameter set (pp2048 and tg32). The downloads go to `src/<tag>.tar.gz` and the binaries to `bins/<tag>/`.

   ```
   PARAM_SETS=main nohup bash scripts/run_campaign.sh > logs/campaign.nohup.out 2>&1 &
   ```

5. Detect changes. Step 0 reads `src/` and `repo/`.

   ```
   py scripts/analysis/step0_effective_config.py
   py scripts/analysis/step1_candidate_events.py
   OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1 py scripts/analysis/step1b_changepoints.py
   ```

6. Re-measure, judge and bisect with the queue. `queues/continuous.tsv` records the items of the study in their order: candidates of classes C and A, the A/A control, the change-point events, the class D candidates, the visibility re-measurement and the R events, with a judgment after each stage and the bisection of the confirmed events. `make_visibility_events.py` is not a queue item, so the queue runs in two parts. Finished items are recorded in `results/analysis/chain_runs/continuous_done.txt`, so the second part continues where the first stopped. The item `bisect_E01_commit` has its release pair and reference effect written in the queue; a different outcome of the bisection of E01 changes these arguments.

   ```
   awk -F'\t' '$1 == "visibility" {exit} {print}' scripts/analysis/queues/continuous.tsv > scripts/analysis/queues/part1.tsv
   printf 'stop_before_visibility\tend\n' >> scripts/analysis/queues/part1.tsv
   QUEUE=scripts/analysis/queues/part1.tsv nohup bash scripts/analysis/continuous_chain.sh > results/analysis/chain_part1.log 2>&1 &
   # when it has finished
   py scripts/analysis/make_visibility_events.py
   nohup bash scripts/analysis/continuous_chain.sh > results/analysis/chain_part2.log 2>&1 &
   ```

7. Run the checks of E01 outside the queue: the bisection of its first half, the bisection of its CPU change (one step, then effect lost) and the harness check.

   ```
   py scripts/analysis/step3_bisect.py --window 00:00-24:00 --lo b1137 --hi b1183 --model tinyllama-1.1b --backend metal --test pp512 --direction up --event-id E01a --ref-lr 0.444 --commit-level
   py scripts/analysis/step3_bisect.py --window 00:00-24:00 --lo b1137 --hi b1245 --model mistral-7b --backend cpu --test pp512 --direction down --event-id E01cpu --ref-lr 0.248 --rounds 4
   bash results/analysis/harness_check_E01/run.sh
   ```

8. Run the switch controls. `build_norepack.sh` needs `src/b7142.tar.gz` and `results/bisect_builds/b7142/`, both left by the bisection of E46, and adds `bins/b7142-norepack/`.

   ```
   bash scripts/analysis/build_norepack.sh
   nohup nice -n 5 uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step3b_switch_controls.py > results/analysis/switch/nohup.out 2>&1 &
   ```

9. Finish with the commands of the quick check. `load_windows.tsv` lists the outside load of the original measurements, so a new measurement needs its own entries, or none.

10. Build the PDF, where the manuscript source is available in `paper/`:

    ```
    cd paper && latexmk -pdf main.tex
    ```

## Running the campaign

- `START_AT=HH:MM` waits, awake, until the next such local time. `STOP_AT=HH:MM` starts no new release after the next such time following the start; a running release finishes. `touch logs/STOP` stops before the next release.
- The lock directory `logs/campaign.lock/` keeps a second campaign from starting; a stale lock of a dead process is taken over. `caffeinate -i` prevents idle sleep during the run, but closing the lid of a laptop still sleeps.
- To resume, run the same command again. Releases with `DONE` are skipped, and an interrupted release is rebuilt from scratch. Failed builds, failed benchmarks and partial results also write `DONE` and are not retried; delete `results/<tag>/` to retry one, and `progress.csv` then has two rows for it, of which the last counts. A failed download writes no `DONE` and is retried.
- To stop at once: `touch logs/STOP`, `pkill -TERM -f scripts/build_bench.sh`, `pkill -TERM -x llama-bench`. Killing the campaign process alone does not stop the current release.
- Do not edit `run_campaign.sh` while it runs, because bash reads the file as it executes. `build_bench.sh` and `parse_bench.py` start anew for every release.
- Before every llama-bench call `build_bench.sh` pauses `COOLDOWN_S` (10) seconds and waits for a quiet machine: CPU idle at least `QUIET_IDLE_PCT` (80) percent in `top` and no other llama-bench process, at most `QUIET_MAX_WAIT_S` (300) seconds per call and `QUIET_TAG_BUDGET_S` (900) per release. After that it measures anyway and records the idle share and the seconds waited. The head of `scripts/build_bench.sh` lists all environment variables.
- `bash scripts/build_bench.sh <tag>` builds and benchmarks a single release. It starts by deleting `results/<tag>/`, and it does not write `progress.csv`.
- Binaries can be re-run from `bins/<tag>/`. Releases up to b2172 have no embedded Metal library and read `ggml-metal.metal` at run time, so they need `GGML_METAL_PATH_RESOURCES=bins/<tag>`.

## Adapting the build to each release

`build_bench.sh` decides from the extracted source. All releases get `CMAKE_BUILD_TYPE=Release BUILD_SHARED_LIBS=OFF CMAKE_POLICY_VERSION_MINIMUM=3.5 LLAMA_BUILD_TESTS=OFF LLAMA_BUILD_SERVER=OFF LLAMA_CURL=OFF` and only the target `llama-bench`.

| Condition in the source | Sampled releases | Options added |
|---|---|---|
| No `ggml/CMakeLists.txt` | b1137 to b3222 | `LLAMA_METAL=ON`, and where the root `CMakeLists.txt` has them `LLAMA_CCACHE=OFF` (from b1939) and `LLAMA_METAL_EMBED_LIBRARY=ON` (from b2330) |
| `ggml/CMakeLists.txt` exists | From b3355 | `GGML_METAL=ON GGML_METAL_EMBED_LIBRARY=ON GGML_CCACHE=OFF` |
| No `tools/llama-bench/` | b1137 to b5159 | `LLAMA_BUILD_EXAMPLES=ON` |
| `tools/llama-bench/` exists | From b5273 | `LLAMA_BUILD_EXAMPLES=OFF LLAMA_BUILD_TOOLS=ON` |

On the CPU back end `-nopo 1` is passed when `llama-bench --help` lists `--no-op-offload`. It is available from b5416 and needed from b6556, where the Metal back end starts to take over large matrix multiplications even with `-ngl 0`. Other options, such as native CPU flags and BLAS, keep the defaults of each release; `results/analysis/config_changes.md` lists how they change.

## Output files

One directory `results/<tag>/` per release:

| File | Content |
|---|---|
| `build_meta.tsv` | Key and value lines: release, environment, CMake arguments, durations and return codes of each stage |
| `runs.tsv` | One row per llama-bench call: arguments, exit code, wall time, load, idle share, seconds waited |
| `<model>_<backend>.json`, `.log` | Raw llama-bench output and its stderr |
| `records.csv` | One row per model, back end and test |
| `status.json` | Summary of the release |
| `cmake_configure.log`, `cmake_build.log`, `download.log`, `extract.log`, `parse.log` | Logs of the stages |
| `llama-bench_help.txt` | `--help` output; for recent releases its head also shows the Metal start-up log |
| `DONE` | Finish time; its presence means the release is done |

`records.csv` columns:

| Column | Meaning |
|---|---|
| `tag`, `build_number`, `commit_date_utc`, `build_commit` | Release; `build_commit` is the commit embedded in the source archive |
| `model`, `backend`, `param_set`, `test`, `n_prompt`, `n_gen` | What was run; pp512 is prompt processing of 512 tokens and tg128 token generation of 128 tokens |
| `status`, `load_ok`, `error` | `ok`, `load_failed` (the release cannot load the model), `run_failed`, `timeout` or `missing_model`; the first related error line |
| `avg_ts`, `stddev_ts`, `n_samples` | Mean and sample SD of the throughput over the repetitions, in tokens per second, as llama-bench reports them |
| `build_commit_reported`, `build_number_reported` | What the binary reports; a source archive has no `.git`, so use `build_commit` and `build_number` |
| `n_threads`, `n_gpu_layers`, `no_op_offload`, `flash_attn`, `n_batch`, `n_ubatch`, `type_k` | Configuration from the JSON; empty for fields that old releases lack |
| `model_type`, `model_size`, `backends_reported`, `cpu_info`, `gpu_info`, `test_time` | Further JSON fields; `model_type` varies between releases, so do not use it as a key |
| `exit_code`, `wall_s`, `load1_before`, `idle_pct_before`, `waited_s`, `extra_args` | Per llama-bench call: exit code (124 timeout, -1 missing model file), wall time with model loading, 1-minute load and idle share before the call, seconds waited, arguments |

`status` in `status.json` and `progress.csv`: `ok` (every record is ok or load_failed), `partial`, `bench_failed`, `build_failed`, `download_failed`. `progress.csv` adds `script_error` (no `DONE` was written) and `parse_error`. `status.json` also holds the commit check (`commit_verified`), CMake arguments, durations, binary size, linked libraries (`linked_libs`) and the environment. `scripts/analysis/README.md` lists the outputs of the analysis steps.

## Failed records in the data

- b1296, b1381 and b1432 failed to build: the upstream script `scripts/build-info.cmake` does not check the return code of git and leaves the build number empty in a source archive without `.git`. The campaign data have no records for them.
- b1137, b1245, b1505, b1561, b1621, b1697, b1778 and b2761 cannot load Qwen2.5-1.5B: the older ones lack the architecture, and the cause at b2761 was not identified. These are the 32 `load_failed` records.
- 70 JSON files hold only a single `[`. They are the records of those failed loads of the model in early releases: llama-bench had printed the opening bracket before it stopped. There are 16 in `results/<tag>/` and 54 in `results/analysis/interleaved/VE01_*`, `VE03_*` and `VE04_*`. They are not valid JSON, and the scripts treat them as failed runs.

## Path replacement

The stored logs and tables were written on the measurement machine. In this package `<repo>` stands for the project directory there and `<models>` for its model directory, for example in the `cmd`, `env` and `model_file` columns of `runs.tsv`, in `plan.json` and in the log files. Replace them to rerun a stored command. Apart from these paths, the stored data are unchanged, except that the explanatory text of the generated reports and of a few note columns was translated into English, with no number changed.

## Tests

```
uv run --no-project --with pandas --with numpy --with matplotlib --with pytest python3 -m pytest -p no:cacheprovider scripts -q
```

The tests use fake builds and measurements, without network and without llama-bench.

## License

The code is released under the MIT License (`LICENSE`). The data under `results/` and `data/` are released under CC BY 4.0 (`LICENSE-DATA`). llama.cpp and the models are not distributed here and keep their own licenses.
