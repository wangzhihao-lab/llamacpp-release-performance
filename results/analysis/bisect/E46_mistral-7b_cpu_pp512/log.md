# Step 3 bisection: E46 mistral-7b/cpu/pp512 (b7100 → b7245, expected decrease)

Reference magnitude |ln ratio| = 0.2603 (-22.9%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-15 00:24 PDT (pid 15730)

Parameters: rounds 2, -r 5, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Build b7177 (6783b11fb088) started at 00:24:37
  - Succeeded in 37 s; builds of this series: 1/8
- Step 1 (release level, 118 candidates, mid is number 59, built in this run): lo b7100 / mid b7177 / hi b7245
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 86.9 / mid 70.1 / hi 70.6 t/s (valid runs 2/2/2); L_hi − L_lo = -18.7% (0.80 times the reference); f = 1.04 → looks new, hi = b7177
- Build b7139 (923ae3c61983) started at 00:32:36
  - Succeeded in 34 s; builds of this series: 2/8
- Step 2 (release level, 58 candidates, mid is number 29, built in this run): lo b7100 / mid b7139 / hi b7177
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 85.8 / mid 84.5 / hi 69.5 t/s (valid runs 2/2/2); L_hi − L_lo = -19.0% (0.81 times the reference); f = 0.07 → looks old, lo = b7139
- Build b7160 (eeb5605de2cd) started at 00:40:14
  - Succeeded in 36 s; builds of this series: 3/8
- Step 3 (release level, 29 candidates, mid is number 15, built in this run): lo b7139 / mid b7160 / hi b7177
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 81.2 / mid 65.9 / hi 64.3 t/s (valid runs 2/2/2); L_hi − L_lo = -20.9% (0.90 times the reference); f = 0.89 → looks new, hi = b7160
- Build b7149 (134e6940caf5) started at 00:48:31
  - Succeeded in 35 s; builds of this series: 4/8
- Step 4 (release level, 14 candidates, mid is number 7, built in this run): lo b7139 / mid b7149 / hi b7160
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 80.9 / mid 65.5 / hi 64.1 t/s (valid runs 2/2/2); L_hi − L_lo = -20.8% (0.89 times the reference); f = 0.91 → looks new, hi = b7149
- Build b7142 (dbb852b549ad) started at 00:56:48
  - Succeeded in 35 s; builds of this series: 5/8
- Step 5 (release level, 6 candidates, mid is number 3, built in this run): lo b7139 / mid b7142 / hi b7149
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 75.6 / mid 60.3 / hi 60.3 t/s (valid runs 2/2/2); L_hi − L_lo = -20.2% (0.87 times the reference); f = 1.00 → looks new, hi = b7142
- Build b7140 (4902eebe33ed) started at 01:05:30
  - Succeeded in 40 s; builds of this series: 6/8
- Step 6 (release level, 2 candidates, mid is number 1, built in this run): lo b7139 / mid b7140 / hi b7142
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 74.5 / mid 72.7 / hi 58.7 t/s (valid runs 2/2/2); L_hi − L_lo = -21.1% (0.91 times the reference); f = 0.10 → looks old, lo = b7140
- Build b7141 (5f55c385cbff) started at 01:14:01
  - Succeeded in 100 s; builds of this series: 7/8
- Step 7 (release level, 1 candidates, mid is number 1, built in this run): lo b7140 / mid b7141 / hi b7142
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -nopo 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 71.5 / mid 67.0 / hi 52.2 t/s (valid runs 2/2/2); L_hi − L_lo = -27.0% (1.21 times the reference); f = 0.21 → looks old, lo = b7141

## Conclusion (2026-10-15 01:23 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b7141 → b7142 (release level, commits between: 1); steps measured: 7, builds: 7, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [dbb852b549](https://github.com/ggml-org/llama.cpp/commit/dbb852b549adf29609ec53b518f7922a982f14b9) | 2025-11-24 | ggml-cpu: arm64: q4_K repack gemm and gemv implementations (i8mm) (#16739) | [#16739](https://github.com/ggml-org/llama.cpp/pull/16739) | 3 |

