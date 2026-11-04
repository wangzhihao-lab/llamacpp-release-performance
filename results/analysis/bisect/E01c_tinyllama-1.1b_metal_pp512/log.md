# Step 3 bisection: E01c tinyllama-1.1b/metal/pp512 (b1226 → b1245, expected increase)

Reference magnitude |ln ratio| = 0.4630 (+58.9%, source: --ref-lr); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-15 01:40 PDT (pid 47842)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level on, window 00:00-24:00.

- Build cc2ab6fe661af (c2ab6fe661af) started at 01:40:19
  - Succeeded in 10 s; builds of this series: 1/8
- Step 1 (commit level, 18 candidates, mid is number 9, built in this run): lo b1226 / mid cc2ab6fe661af / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 852.2 / mid 854.5 / hi 1352.6 t/s (valid runs 2/2/2); L_hi − L_lo = +58.7% (1.00 times the reference); f = 0.01 → looks old, lo = cc2ab6fe661af
- Build c8c00b7a6ff38 (8c00b7a6ff38) started at 01:44:30
  - Succeeded in 43 s; builds of this series: 2/8
- Step 2 (commit level, 9 candidates, mid is number 5, built in this run): lo cc2ab6fe661af / mid c8c00b7a6ff38 / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 856.8 / mid 1358.8 / hi 1359.0 t/s (valid runs 2/2/2); L_hi − L_lo = +58.6% (1.00 times the reference); f = 1.00 → looks new, hi = c8c00b7a6ff38
- Build ca51b68765799 (a51b68765799) started at 01:48:21
  - Succeeded in 9 s; builds of this series: 3/8
- Step 3 (commit level, 4 candidates, mid is number 2, built in this run): lo cc2ab6fe661af / mid ca51b68765799 / hi c8c00b7a6ff38
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 853.8 / mid 1360.1 / hi 1359.4 t/s (valid runs 2/2/2); L_hi − L_lo = +59.2% (1.00 times the reference); f = 1.00 → looks new, hi = ca51b68765799
- Build c76164fe2e65c (76164fe2e65c) started at 01:51:38
  - Succeeded in 9 s; builds of this series: 4/8
- Step 4 (commit level, 1 candidates, mid is number 1, built in this run): lo cc2ab6fe661af / mid c76164fe2e65c / hi ca51b68765799
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 856.3 / mid 856.3 / hi 1355.1 t/s (valid runs 2/2/2); L_hi − L_lo = +58.3% (0.99 times the reference); f = -0.00 → looks old, lo = c76164fe2e65c

## Conclusion (2026-10-15 01:54 PDT)

Status: **located** (search ended at adjacent points).
Boundary: c76164fe2e65c → ca51b68765799 (commit level, commits between: 1); steps measured: 4, builds: 4, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [a51b687657](https://github.com/ggml-org/llama.cpp/commit/a51b68765799e75e17c7622f376bfbeb66f1bd70) | 2023-09-15 | metal : relax conditions on fast matrix multiplication kernel (#3168) | [#3168](https://github.com/ggml-org/llama.cpp/pull/3168) | 4 |

