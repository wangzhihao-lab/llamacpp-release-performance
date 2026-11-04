# Step 3 bisection: E04 tinyllama-1.1b/cpu/pp512 (b1561 → b1621, expected increase)

Reference magnitude |ln ratio| = 1.0823 (+195.1%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-14 22:48 PDT (pid 71959)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Build b1597 (03562f3a86d6) started at 22:48:48
  - Succeeded in 44 s; builds of this series: 1/8
- Step 1 (release level, 44 candidates, mid is number 22, built in this run): lo b1561 / mid b1597 / hi b1621
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512 -ctk f16 -ctv f16`
  - Omission: mid b1597: -ctk/-ctv not supported and omitted (equivalent: f16_kv defaults to true)
  - Omission: lo b1561: -ctk/-ctv not supported and omitted (equivalent: f16_kv defaults to true)
  - Runs planned: 6
  - Result: lo 139.7 / mid 411.5 / hi 435.6 t/s (valid runs 2/2/2); L_hi − L_lo = +211.8% (1.05 times the reference); f = 0.95 → looks new, hi = b1597
- Build b1579 (954e22858c5c) started at 22:54:42
  - Succeeded in 11 s; builds of this series: 2/8
- Step 2 (release level, 21 candidates, mid is number 11, built in this run): lo b1561 / mid b1579 / hi b1597
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 136.4 / mid 412.7 / hi 435.6 t/s (valid runs 2/2/2); L_hi − L_lo = +219.3% (1.07 times the reference); f = 0.95 → looks new, hi = b1579
- Build b1569 (3e73d31d9cc0) started at 23:00:07
  - Succeeded in 11 s; builds of this series: 3/8
- Step 3 (release level, 10 candidates, mid is number 5, built in this run): lo b1561 / mid b1569 / hi b1579
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 134.6 / mid 135.8 / hi 398.4 t/s (valid runs 2/2/2); L_hi − L_lo = +196.0% (1.00 times the reference); f = 0.01 → looks old, lo = b1569
- Build b1573 (b38a16dfcff8) started at 23:06:24
  - Succeeded in 11 s; builds of this series: 4/8
- Step 4 (release level, 5 candidates, mid is number 3, built in this run): lo b1569 / mid b1573 / hi b1579
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 137.0 / mid 135.2 / hi 389.5 t/s (valid runs 2/2/2); L_hi − L_lo = +184.4% (0.97 times the reference); f = -0.01 → looks old, lo = b1573
- Build b1574 (8406b0924bf3) started at 23:12:41
  - Succeeded in 11 s; builds of this series: 5/8
- Step 5 (release level, 2 candidates, mid is number 1, built in this run): lo b1573 / mid b1574 / hi b1579
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 6
  - Result: lo 136.2 / mid 409.2 / hi 397.2 t/s (valid runs 2/2/2); L_hi − L_lo = +191.7% (0.99 times the reference); f = 1.03 → looks new, hi = b1574

## Conclusion (2026-10-14 23:18 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b1573 → b1574 (release level, commits between: 1); steps measured: 5, builds: 5, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [8406b0924b](https://github.com/ggml-org/llama.cpp/commit/8406b0924bf323f37d536dee8b8165c1f3d9d11d) | 2023-11-28 | ggml : re-enable BLAS for CPU when src0 != F32 + remove redundant full offload checks in llama.cpp (#4240) | [#4240](https://github.com/ggml-org/llama.cpp/pull/4240) | 2 |

