# Analysis scripts (steps 0 to 5)

These scripts carry out the study design of Section 3 of the paper: re-measurement protocol version 1.2 with decision rule version 1.1. The top-level `README.md` gives the order of the steps and their cost. All commands below run from the repository root, written `<repo>` in the stored logs. The interpreter line is:

```
uv run --no-project --with pandas --with numpy --with matplotlib python3 -I <script>
```

Steps 0 to 2 read only `results/<tag>/`, `src/<tag>.tar.gz`, `bins/` and `data/`, and write only under `results/analysis/`. Steps 0 and 1 do not occupy the machine (no build, no benchmark, no network). Step 2 occupies the machine, and by default it starts only inside its time window (`--window`, local time 07:00-17:30).

On the measurement machine the `python3` that `uv` selected was x86_64 (under Rosetta). Wherever a script calls a native tool (the compiler macro probe, llama-bench), it therefore goes through `/usr/bin/arch -arm64`; otherwise `cc -mcpu=native` would take the host for x86.

## Step 0: effective configuration, `step0_effective_config.py`

```
uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step0_effective_config.py
```

About 30 seconds. Options: `--no-compiler-probe` (do not run `cc -dM -E`), `-v`.

Inputs:

| Source | What is taken |
|---|---|
| `results/<tag>/records.csv` and raw JSON | Values used in the runs: n_threads, n_batch, n_ubatch, flash_attn, type_k/type_v (f16_kv in old releases), use_mmap/use_direct_io/load_mode, poll, cpu_mask, repack, backends, cpu_info, extra_args |
| `results/<tag>/llama-bench_help.txt` | Defaults the binary declares (`help_*` columns), checked against the run values |
| `results/<tag>/build_meta.tsv` | Compiler, CMake, macOS, cmake_args, option_era, binary size, non-system dynamic libraries |
| `results/<tag>/cmake_configure.log` | Whether Accelerate, BLAS, Metal and OpenMP were found, llamafile, CPU variant flags, ARM features, check results |
| `src/<tag>.tar.gz` (read in memory only) | Defaults of CMake options and the logic of the ARM compile flags: an interpreter for a subset of CMake evaluates them under the conditions of this machine (APPLE, arm64, AppleClang), with check results taken from the configure log; from b4318 the flags are set inside CMake functions, so the flags printed in the configure log are used directly |
| `cc -dM -E -x c /dev/null` (preprocessing only) | The `__ARM_FEATURE_*` macros that each set of CPU compile flags defines |
| `repo/` (blob-less clone), `git log` and `git tag --contains` | Metadata of the commits related to build failures; run with `GIT_NO_LAZY_FETCH=1` and `-c protocol.allow=never`, so no object is fetched from the remote |

Outputs:

- `results/analysis/effective_config.csv`: 81 rows, the raw columns and normalized `eff_*` columns. Spellings with the same meaning map to one value: without a type_k field, f16_kv=true is recorded as f16/f16; without n_ubatch it equals n_batch; mmap=1,dio=0 and load_mode=mmap are both recorded as mmap; before `-nopo` existed Metal took no offloaded work, so the CPU back end is recorded as off.
- `results/analysis/config_changes.csv`: the change points, read by step 1. Columns: `kind` (A run configuration or default, B build option, info for the record only), `backends` and `tests` (scope), `expected` (prior effect on throughput: likely, possible or unlikely).
- `results/analysis/config_changes.md`: the table of change points, the items that did not change, the tables of CPU flags and ARM macros by release range, and the reasons for the three build failures with a minimal patch (not verified by a build).

## Step 1: candidates, `step1_candidate_events.py`

```
uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step1_candidate_events.py
```

Run step 0 first. Options: `--min-rel 0.10 --k-sd 3 --near 1.25 --load-k 1.5 --drift 0.15 --no-plot`.

Rules:

- 12 series = 3 models x {metal, cpu} x {pp512, tg128}, ordered by build number. Qwen2.5 fails to load up to b1778 and at b2761, and those points are skipped.
- Adjacent sampled releases: `lr = ln(new mean / old mean)`, `tau = max(ln 1.10, 3 x pooled SD)`, where the pooled SD combines the SDs of ln(throughput) over the 5 repetitions at both ends, weighted by degrees of freedom. `|lr| >= tau` makes a candidate. The comparison is on the log scale, so gains and losses are symmetric (+10% and -9.1% are equivalent). Reports convert the change and tau to percentages.
- Candidates with overlapping intervals are merged into events, numbered by time from E01. The `series_json` column keeps the release pair of each series; only the Qwen2.5 intervals across b2761 differ from the ends of the event.
- Noise flags, per series: `near` means |lr| < 1.25 tau. `load` means load1_before at either end exceeds the Tukey upper fence Q3 + 1.5 IQR of the same model and back end, and the change did not persist to the next sample. `spike` means a one-point spike of a single model: the next sample returns to within tau of the old level, all series with a spike in the same direction at this release belong to one model, and no class A or B configuration item changed at this release and changed back. A one-point spike of several models at once is marked `shared-spike` and does not count as noise, because it may be a regression that was repaired soon after. `drift` (last 2 repetitions over the first 2, minus 1, above 15%) and `persist` are for information only.
- Classes, per event: when every series carries a noise flag, the class is **D**. Otherwise each series without a noise flag is checked against the likely or possible class A and B changes in the interval whose back end and test scope cover it. If all are explained, the class is **A** (a class A change is involved) or **B**. If any is not explained, the class is **C**; `class_candidates` names the classes that explain some series and `unexplained_series` lists the others.

Outputs: `results/analysis/candidate_events.csv` (interval, dates, releases and commits in the interval, series, size, class, reason, `series_detail`, `series_json`); `candidate_events.md` (a table sorted by size, one paragraph per interval, noise statistics per series); the diagnostic plots `timeline.pdf` and `timeline.svg` (3 x 4 panels, logarithmic axis, one SD, bands by class). The plots are not stored in this package; the script regenerates them.

## Step 1b: change points, `step1b_changepoints.py`

E-Divisive means (alpha = 1, minimum segment length 3, 999 permutations, p < 0.01) on the log of the median of samples_ts of each release. Isolated spikes are set aside first and listed separately. Outputs: `changepoints.csv`, `spikes.csv`, `changepoint_events.csv` (persistent changes that step 1 missed, events CP01 and on, class CP), `changepoints.md`, and the plots `changepoints.pdf` and `changepoints.svg` (regenerated, not stored). To re-measure these events add `--events results/analysis/changepoint_events.csv --classes CP`; the default `--classes` leaves out CP. Run it as one single-threaded process; the command is in the docstring of the script.

## Step 2: interleaved re-measurement, `step2_interleaved.py`

Plan only (at any time; no process is started and no file is written):

```
uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step2_interleaved.py --dry-run
```

Real run (with nohup; outside the window it refuses to start, exit code 3):

```
nohup uv run --no-project --with pandas --with numpy --with matplotlib python3 -I scripts/analysis/step2_interleaved.py --classes C,A,B > results/analysis/interleaved_nohup.out 2>&1 &
```

Summaries only: `... step2_interleaved.py --summarize-only`. To stop midway: `kill -TERM <pid>`, which ends the current llama-bench process group and then writes the summaries.

How it works:

- Event selection: `--classes` (default A,B,C,D, that is all) or `--event-ids E49,E19`, and `--max-events`. The default order is C, A, B, D, within a class by decreasing size (`--order-by chronological` changes this).
- Each event is grouped by the release pair of each series and by (model, back end). The binaries `bins/<tag>/llama-bench` are reused, started through `/usr/bin/arch -arm64` with `GGML_METAL_PATH_RESOURCES=bins/<tag>` (as in the campaign) and the arguments `-m <model> -p 512 -n 128 -r 5 -o json`.
- **Fixed phase**: the same explicit configuration on both sides, `-ngl 99|0 -t 4|8 -b 512 -ub 512 -fa 0|off -ctk f16 -ctv f16 -mmp 1 [-dio 0] | -lm mmap --poll 50 [-nopo 1] [--repack 1]`. Each option is passed only when the `--help` output of the binary lists it. An option that is not supported is left out and recorded: as equivalent when the old release has a single behavior equal to the fixed value (no ubatch, no flash attention, f16_kv by default, mmap by default, no offloading before b6556), otherwise as not equivalent (for example `--poll` against a release before b3610, which has no thread pool), and the group is then marked `fixed config NOT fully aligned`. The order alternates ABBA (AB, BA, AB; protocol v1.1, `--order abab` gives the older order) over `--rounds 3` rounds (the protocol asks for at least 3, and fewer is an error). `-r` is `--reps` 5 for mistral-7b and `--reps-small` 10 for the two small models.
- **Default phase**: each side runs with the arguments of the campaign (`extra_args` in `results/<tag>/runs.tsv`) and the `-r 5` of the campaign, `--default-rounds 1`.
- Every run is its own process. There is a pause of `--cooldown 20` seconds between runs. Before a run the script waits until the CPU idle share is at least `--idle-min 80` (measured as in the campaign), the macOS thermal state is at most `--thermal-max 1` (from `bin/thermal_state`, built from `thermal_state.swift`; the machine is a fanless MacBook Air) and no other llama-bench, llama-server or llama-cli process runs. It waits at most `--load-wait-max 300` seconds, and a timeout is handled by `--on-load-timeout proceed|skip|stop` (default proceed, with `load_settled=0` in runs.tsv). load1, the idle share and the thermal state all go into runs.tsv; load1 gates a run only when `--load-max` is above 0 (the version 1 condition `load1 < 2` was almost never met on this machine).
- Window `--window 07:00-17:30` (local time): outside it the script refuses to start. Before every run it checks whether the time left suffices for the next run (the campaign's wall_s, the cooldown and 30 seconds) and otherwise stops; completed runs are kept and skipped on the next start (`--force` repeats them). It also refuses to start while the process in the campaign lock is alive or another step 2 instance runs (`interleaved/.step2.lock`). `--window 00:00-24:00` removes the limit.
- Built-in verdict of this script, per series, on the log scale, with the thresholds of step 1 and the expected sign from step 1: in the fixed phase, `lr` of the means of the rounds and tau pooled over all samples of both sides. `|lr| >= tau` with the expected sign and the same sign in every round gives **C** (a change of the implementation or the build). Otherwise the same test on the default phase gives **A**. If neither passes the verdict is **noise**, a fixed-phase change in the opposite direction above the threshold gives **reversed**, and missing rounds give **incomplete**. Event verdict: C > A > reversed > noise > incomplete. A further column, the reproduction deviation, is the mean of the default re-runs over the campaign value, minus 1; it shows the points where the time of the campaign run affected the value. The verdicts of the paper come from `step2b_judge.py`, below.

Outputs: `results/analysis/interleaved/<event>_<old>_<new>/` (plan.json, runs.tsv, the JSON and log of every run, summary.csv, summary.md), `interleaved/summary.csv`, `summary.md` (all events), `run.log`.

Duration (dry run of 2026-10-13, estimated from the campaign's wall_s, without waiting for a quiet machine): all 54 events, 896 runs, about 15.1 h; the 31 events of classes C, A and B, 632 runs, about 10.7 h; the 23 events of class D, 264 runs, about 4.4 h. The default window is 10.5 h long.

## Queue, judgment and protocol version 1.2

- `continuous_chain.sh` runs the queue `queues/continuous.tsv` without a time window, passing `--window 00:00-24:00` to re-measurement and bisection (`parse_window` reads 24:00 as midnight, and equal start and end mean the whole day). The queue is read again before every item, and the first line whose name is not in `results/analysis/chain_runs/continuous_done.txt` runs, so lines can be appended or reordered during a run. Item kinds: `step2`, `judge`, `step3`, `bisect_confirmed` and `end`. `bisect_confirmed` reads the latest judgment, picks for every confirmed event the most reliable series with verdict C (the largest |fixed_z|, `confirmed_targets.py`) and bisects the events in order of decreasing change; `end` stops the chain. With an empty queue it looks again every 5 minutes and exits after 24 hours. A sampler process appends the CPU idle share and the busiest processes to `chain_runs/activity.log` every 5 minutes, for flagging noisy stretches afterwards. `DRY_RUN=1` lists the items with their commands and state; `AFTER_PID` makes it wait for a process to exit.
- Protocol version 1.2 (from 2026-10-14, about 10:00 local time; Section 3.4 of the paper):
  - **Warm-up run**: `step2_interleaved.py` starts every group with one run of the fixed command of side A (`phase=warmup`, used in no statistic, `--no-warmup` turns it off); `step3_bisect.py` starts every step with one run of the first pending command (`role=warmup`, written to `warmup_*.json`, also used in no statistic).
  - **`-pg 0,0`**: the fixed configuration adds `-pg 0,0` for releases that support `-pg`.
  - **Sensitivity judgment**: `step2b_judge.py --drop-round1-unwarmed --suffix _norm1` leaves out round 1 of the groups without a warm-up run and judges again, with the outputs `judge_v11_*_norm1.csv` and `MEMO_v11_norm1.md`. In the queue every `judge` item is followed by a `_norm1` item.
  - **Tests**: `test_step2_warmup.py` (warm-up and `-pg` in re-measurement), `test_step3_bisect.py` (warm-up in bisection, also after a resume), `test_step2b_judge.py` (sensitivity judgment).
- **Visibility re-measurement** (from 2026-10-15): `make_visibility_events.py` reads the events the latest judgment confirms (verdict C) and writes one event `V<event>` each to `results/analysis/visibility_events.csv`, listing both tests of the (model, back end) groups that step 2 did not measure. `step2b_judge.py` judges V events two-sided (`visible` or `not_visible`, and `vis: k/n series visible` at event level). Tests: `test_make_visibility_events.py` and `test_step2b_judge.py`.
- `control_events.csv`: the A/A control (b11559 against itself, 6 groups of model and back end).
- `step2b_judge.py`: decision rule version 1.1. The statistic of a run is ln(median of samples_ts). The noise scale takes the larger of the within-side SD of the group and the SD of the same series pooled over the A/A control and the within-side repetitions of all events. A phase confirms when |lr| >= ln 1.05, |lr| / SE >= 3 and the sign agrees. The script reads `interleaved/*/plan.json` and the JSON of every run. It takes the verdicts of `step2_interleaved.py` from the summary.csv of each event directory, because each step 2 call rewrites the global summary.csv with the events of that call. Outputs: `judge_v11_series.csv`, `judge_v11_events.csv`, `noise_model_v11.csv`, `MEMO_v11.md`. Tests: `test_step2b_judge.py`. The sign from step 1 is taken per (event, series, release pair): when a series lists two adjacent pairs in one event (E14 TinyLlama Metal pp512, +0.58 and -0.56), each pair uses its own sign.
- **Windows of outside load** (from 2026-10-26): `results/analysis/load_windows.tsv` records the known outside load during the measurements (other projects, system tasks, tests and builds of this study). `load_window_check.py` lists the runs that overlap a window (`load_window_runs.tsv`) and the bisection steps affected (`load_window_bisect_steps.csv`). `step2b_judge.py --exclude-windows results/analysis/load_windows.tsv --suffix _nowin` judges again without the overlapping re-measurement runs. `load_window_macros` of `make_numbers.py` reads these files. Test: `test_step2b_judge.py::test_exclude_windows`.

## Step 3: bisection, `step3_bisect.py`

Occupies the machine (builds and benchmarks), and by default runs only inside its time window. Besides `results/analysis/bisect/` it writes `results/bisect_builds/`, `bins/<tag>/` and `src/<tag>.tar.gz` (build products).

Plan only (at any time; no process is started and no file is written):

```
uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step3_bisect.py --lo b8545 --hi b8740 --model mistral-7b --backend metal --test pp512 --direction up --dry-run
```

Real run (outside the window it refuses to start, exit code 3; while step 2 or the campaign runs it refuses too, exit code 4):

```
nohup uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step3_bisect.py --from-step2 E49 > results/analysis/bisect_nohup.out 2>&1 &
```

To stop midway: `kill -TERM <pid>`, which ends the running llama-bench; a build in progress finishes first. The same command then resumes from the stored state, and completed runs and builds are not repeated. Summaries only: `--summarize-only`.

Input:

- `--from-step2 E49` reads the series with verdict C from `results/analysis/interleaved/E49_*/summary.csv` (the verdicts of `step2_interleaved.py`); it stops with exit code 2 when the file cannot be read or holds no C. `--step2-rule v11` reads `interleaved/judge_v11_series.csv` (rule version 1.1, `step2b_judge.py`) instead. Several C series are bisected one after the other by significance (|z| or |lr|/tau) and share binaries through `bins/`; `--series mistral-7b/metal/pp512` selects one.
- Or give `--lo --hi --model --backend --test --direction up|down` directly. `--event-id` sets the directory name; the default is the event of that pair in candidate_events.csv.
- Reference effect, the basis of effect_lost: `--ref-lr`, otherwise |lr| of the fixed phase of step 2, otherwise |ln ratio| of step 1 (only without a step 2 result; the source goes into target.json and log.md). A resumed run keeps the reference of its start unless `--ref-lr` is given.

Procedure:

1. Candidates are all release tags of `data/releases.csv` with a build number strictly between lo and hi. Each step takes the median candidate as mid (the left one of two). An existing `bins/<mid>/llama-bench` is reused; otherwise the script runs `BUILD_ONLY=1 RESULTS_ROOT=results/bisect_builds /usr/bin/arch -arm64 /bin/bash scripts/build_bench.sh <mid>` (build only, no benchmark; started as arm64 because the `python3` of `uv` is x86_64 and child processes would otherwise compile for an x86 host). A failed build is recorded as a skip and counts as a build, and the nearest other candidate is tried (left and right in turn). Tags on which another series already failed to build (`results/bisect_builds/<tag>/status.json`) are skipped without a build and not counted. A successful build also needs the tarball commit check to pass and an arm64 binary.
2. Three-way interleaving: round 1 runs lo, mid, hi and round 2 runs hi, mid, lo (`--rounds 2`, at least 2). Every run is its own process with the arguments of the fixed phase of step 2 (`binary_caps` and `fixed_args` imported from step 2), measuring only the test of interest (pp512: `-p 512 -n 0`; tg128: `-p 0 -n 128`), with `-r` 5 for mistral-7b and 10 for the two small models, `GGML_METAL_PATH_RESOURCES=bins/<tag>`, started through `/usr/bin/arch -arm64`. Before a run there is a pause of 20 s after the previous run or build, and then the same wait for a quiet machine as in step 2: CPU idle at least 80%, macOS thermal state at most `--thermal-max 1` (-1 turns this off), no other llama-bench, llama-server or llama-cli, at most 300 s. On a timeout `--on-quiet-timeout proceed` runs anyway and records settled=0 in runs.tsv, and `stop` pauses. The idle share, thermal state and load1 go into runs.tsv.
3. Verdict: for every run y = ln(median of samples_ts); the mean over the runs of each end gives L_lo, L_mid, L_hi, and f = (L_mid - L_lo)/(L_hi - L_lo). f <= 0.35 looks old (lo = mid); f >= 0.65 looks new (hi = mid). Values in between are intermediate (possibly two changes), the search continues by f < 0.5 or f >= 0.5, and steps.csv, log.md and result.json mark them. f < -0.35 or f > 1.35 is also noted as `mid outside [lo, hi]` (not monotonic). Each step first checks that L_hi - L_lo has the expected sign and is at least half the reference effect, otherwise it records effect_lost and stops the series. A mid without a valid run (load or run failure) skips that candidate; lo or hi without a valid run stops the series (run_failed).
4. End: lo and hi are adjacent release tags (located), or the next mid needs a build and `--max-builds 8` is reached (stopped_max_builds; a larger `--max-builds` resumes), or all remaining candidates fail to build (stopped_unbuildable). `--commit-level` (off by default) continues over first-parent commits when adjacent tags are more than one commit apart. Commit points are written `c<first 12 characters of the sha>`, and their source comes from `archive/<sha>.tar.gz`.
5. At the end the commits between lo and hi are read from `repo/` (blob-less, no-checkout clone): commit id, date, author, title and changed file names (only trees are read, no blobs). A `(#12345)` at the end of a title gives the pull request number and its link. The script sets `GIT_NO_LAZY_FETCH=1` and `-c protocol.allow=never`, so no object is fetched over the network.
6. Window `--window 07:00-17:30` (local time): outside it the script refuses to start. A build needs at least `--build-est 600` s left in the window, and a run its estimated length, the cooldown and 30 s (checked again after the wait for a quiet machine); otherwise the script pauses, and the same command resumes later. Mutual exclusion: it refuses to start while the process of the campaign lock or of `interleaved/.step2.lock` is alive, and it holds `bisect/.step3.lock` itself.

Outputs in `results/analysis/bisect/<event>_<model>_<backend>_<test>/`:

| File | Content |
|---|---|
| target.json | Series, direction, reference effect and its source; checked on resume, and another series in the same directory is refused |
| steps.csv | One row per step, skipped candidates included: lo, mid, hi, candidates left and position of mid, build (built, reused or a failure status), valid runs and t/s of the three ends (mean of the logs, transformed back), d = L_hi - L_lo, d over the reference, f, verdict (old, new, intermediate, effect_lost, build_failed, run_failed), decision (lo=mid, hi=mid, skip, stop), note |
| builds.tsv | Every build attempt of this series, failures included; the build count is taken from here |
| runs.tsv | One row per run: command, environment, exit code, wall clock, seconds waited, idle share, thermal state, load1, whether the machine was quiet, median t/s |
| `s<step>_r<round>_<role>_<tag>.json/.log`, `build_<tag>.log` | Raw output |
| result.json | Status, boundary lo and hi with their commits, steps, builds, intermediate steps, skipped candidates, commit list with pull request links and changed files |
| log.md | The readable course of the bisection (builds, configuration and verdict of each step, pauses) and the conclusion (table of commits) |

Summaries: `results/analysis/bisect/summary.csv`, `summary.md`, `run.log`. Build products: `results/bisect_builds/<tag>/` (build_meta.tsv, status.json, CMake logs), `bins/<tag>/`, `src/<tag>.tar.gz`.

Status values: located (adjacent releases or commits reached), effect_lost, stopped_max_builds, stopped_unbuildable, endpoint_unbuildable, run_failed, incomplete (paused, with `pause_reason` window, signal or busy; can be resumed).

Duration (dry run of E49 on mistral-7b/metal/pp512): 133 candidates, at most 8 steps. A run takes about 27 s, a step of 6 runs with 5 pauses of 20 s about 4.4 min, plus about 2 min for a build; 8 steps take about 1 h, without waiting for a quiet machine.

`scripts/build_bench.sh` has a matching mode: with `BUILD_ONLY=1` it only downloads, configures, compiles, saves `--help`, copies the binary to `bins/<tag>/` and writes status.json (built, build_failed or download_failed), and it runs no benchmark. In this mode `RESULTS_ROOT` must not be `results/` itself, because the script starts with `rm -rf $RESULTS_ROOT/<tag>` (otherwise exit code 2). An existing `bins/<tag>/llama-bench` is not rebuilt unless `BUILD_FORCE=1`. The argument may also be `c<7 to 40 hexadecimal digits of a sha>`: the source then comes from `archive/<sha>.tar.gz`, and the commit check compares against the sha itself, completed offline in `repo/`.

Tests (fake builds and fake measurements; `build_bench.sh` runs in build-only mode in a temporary directory with stand-ins for curl and cmake, without network and compilation):

```
uv run --no-project --with pytest --with pandas --with numpy python3 -I -m pytest -p no:cacheprovider scripts/analysis/test_step3_bisect.py -q
```

## Step 3b: switch controls and re-tests of two cells, `step3b_switch_controls.py`

The design was fixed before these runs (Section 3.5 of the paper). There are four experiments, each with a few arms (a binary and options) measured interleaved on one series:

| Experiment | Series (rounds) | A | B | C |
|---|---|---|---|---|
| S19 (E19, #8672) | TinyLlama, Mistral-7B CPU pp512 (6) | b3643 | b3644 `--poll 50` | b3644 `--poll 0` |
| S46 (E46, #16739) | Mistral-7B CPU pp512 (6), Qwen2.5 and TinyLlama CPU pp512 (3) | b7141 | b7142 | `bins/b7142-norepack` (`build_norepack.sh`: the same source archive with `-DGGML_CPU_REPACK=OFF`) |
| T04 | Mistral-7B CPU tg128, tg128 alone (6) | b1561 | b1621 | none |
| T50 | Mistral-7B Metal pp512 (6) | b8916 | b9076 | none |

- The procedure is that of step 2: one process per run, the fixed configuration of the earlier re-measurement of the same pair, one warm-up run per group, 20 s of cooldown, and the wait for CPU idle at least 80% and thermal state at most 1 (`step2_interleaved.wait_quiet` and `execute_run` are called directly, and runs.tsv has the same format). Three arms follow ABC, BCA, CAB, CBA, ACB, BAC (groups of three rounds use the first three), and two arms alternate AB, BA. Load and the busiest processes are recorded every 60 s (`activity.log`, written at run time and not stored in this package).
- Path check: every arm of S19 and S46 first runs once alone with `-r 1 -v` and `GGML_SCHED_DEBUG=2`. Its log holds the buffer type of the weights and the back end of every matrix-multiplication node (`path/`, `path_summary.csv`; only the last graph is taken, which is the measured batch). No statistic uses it.
  - Arm C first used `-ot .=CPU`. The path check showed that b7142 moves weights overridden to the CPU back to `CPU_REPACK` (`llama-model.cpp`), so arm C of S46 was changed to the rebuilt binary before the timed runs. The earlier path logs are kept as `*_ot.*`.
- Statistics use `step2b_judge.phase_test` and `run_value`: for two arms X and Y, lr = mean(y_Y) - mean(y_X), s is the larger of sigma_fixed of the series and the pooled within-arm SD of the two arms, and a difference meets the rule when |lr| >= ln 1.05 and |z| >= 3. Three arms also give the recovered share R.
- Outputs in `results/analysis/switch/`: one directory per group (runs.tsv and the JSON and log of every run), `arms.csv`, `comparisons.csv`, `path_summary.csv`, `MEMO.md`. `--dry-run` prints the plan, and `--summarize-only` recomputes only the tables.
- Downstream: `step4_visibility.py` takes the A to B result of T04 and T50 for these two cells (fixed in the design, with T04 or T50 in the source column), and `switch_macros` of `make_numbers.py` generates the numbers of the text (`sw*`, `path*`, `pollDefaultNewest`).

Run (a timed measurement; stop other work on the machine first):

```
nohup nice -n 5 uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step3b_switch_controls.py > results/analysis/switch/nohup.out 2>&1 &
```

## Steps 4 and 5: visibility and the smallest covering set, `step4_visibility.py`

```
uv run --no-project --with pandas --with numpy python3 -I scripts/analysis/step4_visibility.py
```

The script fills the matrix of 12 series for every confirmed event from the re-measurement of the event (E..R first, then the event itself) and the visibility re-measurement (V..), and takes T04 and T50 for their two cells. Every cell uses the thresholds of the judgment, two-sided. Step 5 lists the events each series sees and searches all subsets of series for the smallest sets that see all events. Outputs: `step4_visibility.csv`, `step4_visibility.md`, `step5_test_matrix.md`. Nothing is measured.

## Thresholds and classes at a glance

| Item | Value |
|---|---|
| Candidate threshold | abs(ln(new/old)) >= max(ln 1.10, 3 x pooled ln SD) |
| near | abs(ln ratio) < 1.25 tau |
| High load | load1_before > Q3 + 1.5 IQR of the same model and back end, and the change does not persist |
| spike | One-point spike of a single model; the next sample returns to within tau |
| A / B | Likely or possible changes of the run configuration / build options in the interval cover all series without a noise flag |
| C | At least one series without a noise flag has no configuration or build explanation |
| D | All series carry a noise flag |
| Step 2 C / A / noise | Persists with the fixed configuration / only with the release defaults / neither |

## Known limits

- **Sparse sampling**: the 81 tags, about one every two weeks, show only changes visible between sampled releases. A regression repaired inside an interval, or several changes that cancel, stay invisible, and the duration of an event is known only as an interval (from the previous sampled tag to the next).
- The SD of step 1 comes from the 5 repetitions of one call and holds no noise across time. On tinyllama/metal and qwen/metal/pp512 the variation within a run often exceeds 10% (the GPU clocks down within a run), so candidates of these groups rest mainly on step 2.
- The measurement order is fixed. The first run of every tag is tinyllama/metal, right after the compilation, and load1_before there is usually 2 to 8; the `load` flag catches only outliers at the same position. load1 exceeds 2 on this machine even when idle (98% of the calls of the campaign had load1 >= 2), so from version 1.1 step 2 gates on the CPU idle share.
- On the CPU back end `-t 8` runs on 4 performance and 6 efficiency cores, and the kind of core a thread lands on varies between runs, which makes the CPU results of small models especially noisy. The fixed phase keeps 8 threads, as in the campaign, without core binding.
- Classes A and B only say that a configuration or build explanation is possible, not that it is proven. Class B differences are compiled into the binaries and therefore appear as C in step 2 with fixed run options; separating B from C needs rebuilds with equal compile options (step 3 or a separate experiment).
- The source defaults of step 0 come from an interpreter for a subset of CMake, covering if, foreach, set, option, list, string and check results; function bodies are not expanded (newer releases use the configure log instead). Uncertain values carry a `?`.
- The patches for the three tags that failed to build (b1296, b1381, b1432) are suggestions, not verified by a build.
