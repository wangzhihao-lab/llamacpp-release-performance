# Step 3 bisection: E01a tinyllama-1.1b/metal/pp512 (b1137 → b1183, expected increase)

Reference magnitude |ln ratio| = 0.4440 (+55.9%, source: --ref-lr); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-26 07:15 PDT (pid 25811)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level on, window 00:00-24:00.

- Build b1162 (6460f758dbd4) started at 07:15:15
  - Succeeded in 10 s; builds of this series: 1/8
- Step 1 (release level, 28 candidates, mid is number 14, built in this run): lo b1137 / mid b1162 / hi b1183
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 520.3 / mid 815.0 / hi 812.7 t/s (valid runs 2/2/2); L_hi − L_lo = +56.2% (1.00 times the reference); f = 1.01 → looks new, hi = b1162
- Build b1147 (5d6f19f16b21) started at 07:18:56
  - Succeeded in 9 s; builds of this series: 2/8
- Step 2 (release level, 13 candidates, mid is number 7, built in this run): lo b1137 / mid b1147 / hi b1162
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 523.2 / mid 525.6 / hi 817.5 t/s (valid runs 2/2/2); L_hi − L_lo = +56.3% (1.00 times the reference); f = 0.01 → looks old, lo = b1147
- Build b1151 (21f3d1be867b) started at 07:22:41
  - Succeeded in 12 s; builds of this series: 3/8
- Step 3 (release level, 6 candidates, mid is number 3, built in this run): lo b1147 / mid b1151 / hi b1162
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 525.4 / mid 526.0 / hi 816.6 t/s (valid runs 2/2/2); L_hi − L_lo = +55.4% (0.99 times the reference); f = 0.00 → looks old, lo = b1151
- Build b1155 (bc054af97ac6) started at 07:26:29
  - Succeeded in 9 s; builds of this series: 4/8
- Step 4 (release level, 3 candidates, mid is number 2, built in this run): lo b1151 / mid b1155 / hi b1162
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 529.9 / mid 530.0 / hi 823.1 t/s (valid runs 2/2/2); L_hi − L_lo = +55.3% (0.99 times the reference); f = 0.00 → looks old, lo = b1155
- Build b1157 (c42f0ec6b344) started at 07:30:25
  - Succeeded in 9 s; builds of this series: 5/8
- Step 5 (release level, 1 candidates, mid is number 1, built in this run): lo b1155 / mid b1157 / hi b1162
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 529.6 / mid 530.0 / hi 823.2 t/s (valid runs 2/2/2); L_hi − L_lo = +55.4% (0.99 times the reference); f = 0.00 → looks old, lo = b1157
- Build ccff7b0bf07cb (cff7b0bf07cb) started at 07:34:10
  - Succeeded in 9 s; builds of this series: 6/8
- Step 6 (commit level, 4 candidates, mid is number 2, built in this run): lo b1157 / mid ccff7b0bf07cb / hi b1162
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 529.7 / mid 518.3 / hi 822.1 t/s (valid runs 2/2/2); L_hi − L_lo = +55.2% (0.99 times the reference); f = -0.05 → looks old, lo = ccff7b0bf07cb
- Build c6a31a3bd9806 (6a31a3bd9806) started at 07:37:55
  - Succeeded in 10 s; builds of this series: 7/8
- Step 7 (commit level, 2 candidates, mid is number 1, built in this run): lo ccff7b0bf07cb / mid c6a31a3bd9806 / hi b1162
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 529.7 / mid 529.6 / hi 822.6 t/s (valid runs 2/2/2); L_hi − L_lo = +55.3% (0.99 times the reference); f = -0.00 → looks old, lo = c6a31a3bd9806
- Build cca82cf7bac0c (ca82cf7bac0c) started at 07:41:41
  - Succeeded in 10 s; builds of this series: 8/8
- Step 8 (commit level, 1 candidates, mid is number 1, built in this run): lo c6a31a3bd9806 / mid cca82cf7bac0c / hi b1162
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 529.6 / mid 822.4 / hi 822.6 t/s (valid runs 2/2/2); L_hi − L_lo = +55.3% (0.99 times the reference); f = 1.00 → looks new, hi = cca82cf7bac0c

## Conclusion (2026-10-26 07:45 PDT)

Status: **located** (search ended at adjacent points).
Boundary: c6a31a3bd9806 → cca82cf7bac0c (commit level, commits between: 1); steps measured: 8, builds: 8, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [ca82cf7bac](https://github.com/ggml-org/llama.cpp/commit/ca82cf7bac0c91d03e3d320b3a865dd006f854ac) | 2023-09-03 | metal : more optimizations (#2959) | [#2959](https://github.com/ggml-org/llama.cpp/pull/2959) | 2 |

