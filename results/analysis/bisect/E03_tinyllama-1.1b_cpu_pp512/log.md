# Step 3 bisection: E03 tinyllama-1.1b/cpu/pp512 (b1505 → b1561, expected decrease)

Reference magnitude |ln ratio| = 1.0376 (-64.6%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-14 22:20 PDT (pid 66944)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Build b1533 (5ad387e994dd) started at 22:20:16
  - Succeeded in 11 s; builds of this series: 1/8
- Step 1 (release level, 39 candidates, mid is number 20, built in this run): lo b1505 / mid b1533 / hi b1561
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 410.8 / mid 135.0 / hi 133.5 t/s (valid runs 2/2/2); L_hi − L_lo = -67.5% (1.08 times the reference); f = 0.99 → looks new, hi = b1533
- Build b1520 (91f6499393d2) started at 22:26:10
  - Succeeded in 10 s; builds of this series: 2/8
- Step 2 (release level, 19 candidates, mid is number 10, built in this run): lo b1505 / mid b1520 / hi b1533
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 409.9 / mid 134.9 / hi 133.4 t/s (valid runs 2/2/2); L_hi − L_lo = -67.5% (1.08 times the reference); f = 0.99 → looks new, hi = b1520
- Build b1515 (36eed0c42c5b) started at 22:32:03
  - Succeeded in 11 s; builds of this series: 3/8
- Step 3 (release level, 9 candidates, mid is number 5, built in this run): lo b1505 / mid b1515 / hi b1520
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 410.7 / mid 134.4 / hi 132.1 t/s (valid runs 2/2/2); L_hi − L_lo = -67.8% (1.09 times the reference); f = 0.98 → looks new, hi = b1515
- Build b1510 (4760e7cc0b68) started at 22:37:57
  - Succeeded in 10 s; builds of this series: 4/8
- Step 4 (release level, 4 candidates, mid is number 2, built in this run): lo b1505 / mid b1510 / hi b1515
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 432.6 / mid 411.3 / hi 139.4 t/s (valid runs 2/2/2); L_hi − L_lo = -67.8% (1.09 times the reference); f = 0.04 → looks old, lo = b1510
- Build b1512 (3d68f364f157) started at 22:42:55
  - Succeeded in 11 s; builds of this series: 5/8
- Step 5 (release level, 2 candidates, mid is number 1, built in this run): lo b1510 / mid b1512 / hi b1515
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 409.3 / mid 135.2 / hi 134.7 t/s (valid runs 2/2/2); L_hi − L_lo = -67.1% (1.07 times the reference); f = 1.00 → looks new, hi = b1512

## Conclusion (2026-10-14 22:48 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b1510 → b1512 (release level, commits between: 2); steps measured: 5, builds: 5, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [3d68f364f1](https://github.com/ggml-org/llama.cpp/commit/3d68f364f15778dc326f5024f2e5af1ad6dfddef) | 2023-11-13 | ggml : sync (im2col, GPU conv, 32-bit arm compat) (#4060) | [#4060](https://github.com/ggml-org/llama.cpp/pull/4060) | 8 |
| [c049b37d7b](https://github.com/ggml-org/llama.cpp/commit/c049b37d7baf558944501705b91ac89b26ee3e41) | 2023-11-13 | readme : update hot topics |  | 1 |

