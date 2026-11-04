# Step 3 bisection: E16R mistral-7b/cpu/pp512 (b3130 → b3222, expected increase)

Reference magnitude |ln ratio| = 0.2092 (+23.3%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-15 12:42 PDT (pid 77855)

Parameters: rounds 4, -r 5, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Step 1 (release level, 65 candidates, mid is number 33, existing binary reused): lo b3130 / mid b3177 / hi b3222
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 12
  - Result: lo 84.6 / mid 104.6 / hi 104.1 t/s (valid runs 4/4/4); L_hi − L_lo = +23.1% (0.99 times the reference); f = 1.03 → looks new, hi = b3177
- Step 2 (release level, 32 candidates, mid is number 16, existing binary reused): lo b3130 / mid b3152 / hi b3177
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 12
  - Result: lo 79.6 / mid 99.2 / hi 102.8 t/s (valid runs 4/4/4); L_hi − L_lo = +29.2% (1.22 times the reference); f = 0.86 → looks new, hi = b3152
- Step 3 (release level, 15 candidates, mid is number 8, existing binary reused): lo b3130 / mid b3143 / hi b3152
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 12
  - Result: lo 78.3 / mid 102.0 / hi 102.5 t/s (valid runs 4/4/4); L_hi − L_lo = +31.0% (1.29 times the reference); f = 0.98 → looks new, hi = b3143
- Step 4 (release level, 7 candidates, mid is number 4, existing binary reused): lo b3130 / mid b3138 / hi b3143
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 12
  - Result: lo 75.7 / mid 75.8 / hi 99.4 t/s (valid runs 4/4/4); L_hi − L_lo = +31.3% (1.30 times the reference); f = 0.00 → looks old, lo = b3138
- Build b3140 (a9cae48003df) started at 13:31:21
  - Succeeded in 18 s; builds of this series: 1/8
- Step 5 (release level, 3 candidates, mid is number 2, built in this run): lo b3138 / mid b3140 / hi b3143
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 12
  - Result: lo 74.9 / mid 75.9 / hi 99.3 t/s (valid runs 4/4/4); L_hi − L_lo = +32.7% (1.35 times the reference); f = 0.05 → looks old, lo = b3140
- Build b3141 (963552903f51) started at 13:44:35
  - Succeeded in 17 s; builds of this series: 2/8
- Step 6 (release level, 1 candidates, mid is number 1, built in this run): lo b3140 / mid b3141 / hi b3143
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 12
  - Result: lo 75.8 / mid 74.9 / hi 99.2 t/s (valid runs 4/4/4); L_hi − L_lo = +31.0% (1.29 times the reference); f = -0.04 → looks old, lo = b3141

## Conclusion (2026-10-15 13:57 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b3141 → b3143 (release level, commits between: 2); steps measured: 6, builds: 2, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [f578b86b21](https://github.com/ggml-org/llama.cpp/commit/f578b86b2123d0f92afbaa98a031df4d4464e582) | 2024-06-13 | move BLAS to a separate backend (#6210) | [#6210](https://github.com/ggml-org/llama.cpp/pull/6210) | 17 |
| [1c641e6aac](https://github.com/ggml-org/llama.cpp/commit/1c641e6aac5c18b964e7b32d9dbbb4bf5301d0d7) | 2024-06-13 | `build`: rename main → llama-cli, server → llama-server, llava-cli → llama-llava-cli, etc... (#7809) | [#7809](https://github.com/ggml-org/llama.cpp/pull/7809) | 138 |

