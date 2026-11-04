# Step 3 bisection: E19 tinyllama-1.1b/cpu/pp512 (b3610 → b3665, expected decrease)

Reference magnitude |ln ratio| = 0.5267 (-40.9%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-14 23:38 PDT (pid 82380)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Build b3631 (7d787ed96c32) started at 23:38:33
  - Succeeded in 17 s; builds of this series: 1/8
- Step 1 (release level, 38 candidates, mid is number 19, built in this run): lo b3610 / mid b3631 / hi b3665
  - Fixed configuration (not fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -pg 0,0`
  - Omission: mid b3631: --poll not supported and omitted (not equivalent)
  - Omission: lo b3610: --poll not supported and omitted (not equivalent)
  - Runs planned: 6
  - Result: lo 659.4 / mid 660.1 / hi 382.4 t/s (valid runs 2/2/2); L_hi − L_lo = -42.0% (1.03 times the reference); f = -0.00 → looks old, lo = b3631
- Build b3647 (0ab30f8d82fc) started at 23:42:37
  - Succeeded in 18 s; builds of this series: 2/8
- Step 2 (release level, 19 candidates, mid is number 10, built in this run): lo b3631 / mid b3647 / hi b3665
  - Fixed configuration (not fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -pg 0,0`
  - Omission: lo b3631: --poll not supported and omitted (not equivalent)
  - Runs planned: 6
  - Result: lo 660.9 / mid 382.2 / hi 387.6 t/s (valid runs 2/2/2); L_hi − L_lo = -41.3% (1.01 times the reference); f = 1.03 → looks new, hi = b3647
- Build b3636 (78eb487bb003) started at 23:46:53
  - Succeeded in 17 s; builds of this series: 3/8
- Step 3 (release level, 9 candidates, mid is number 5, built in this run): lo b3631 / mid b3636 / hi b3647
  - Fixed configuration (not fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -pg 0,0`
  - Omission: mid b3636: --poll not supported and omitted (not equivalent)
  - Omission: lo b3631: --poll not supported and omitted (not equivalent)
  - Runs planned: 6
  - Result: lo 660.2 / mid 660.3 / hi 383.3 t/s (valid runs 2/2/2); L_hi − L_lo = -41.9% (1.03 times the reference); f = -0.00 → looks old, lo = b3636
- Build b3643 (9f7d4bcf5c27) started at 23:50:56
  - Succeeded in 50 s; builds of this series: 4/8
- Step 4 (release level, 4 candidates, mid is number 2, built in this run): lo b3636 / mid b3643 / hi b3647
  - Fixed configuration (not fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -pg 0,0`
  - Omission: mid b3643: --poll not supported and omitted (not equivalent)
  - Omission: lo b3636: --poll not supported and omitted (not equivalent)
  - Runs planned: 6
  - Result: lo 659.6 / mid 659.8 / hi 388.5 t/s (valid runs 2/2/2); L_hi − L_lo = -41.1% (1.00 times the reference); f = -0.00 → looks old, lo = b3643
- Build b3644 (42c76d135802) started at 23:55:32
  - Succeeded in 18 s; builds of this series: 5/8
- Step 5 (release level, 2 candidates, mid is number 1, built in this run): lo b3643 / mid b3644 / hi b3647
  - Fixed configuration (not fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 --poll 50 -pg 0,0`
  - Omission: lo b3643: --poll not supported and omitted (not equivalent)
  - Runs planned: 6
  - Result: lo 658.5 / mid 386.9 / hi 399.1 t/s (valid runs 2/2/2); L_hi − L_lo = -39.4% (0.95 times the reference); f = 1.06 → looks new, hi = b3644

## Conclusion (2026-10-14 23:59 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b3643 → b3644 (release level, commits between: 1); steps measured: 5, builds: 5, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [42c76d1358](https://github.com/ggml-org/llama.cpp/commit/42c76d1358021ccdbe8ba89109c143dd7ae166df) | 2024-08-30 | Threadpool: take 2 (#8672) | [#8672](https://github.com/ggml-org/llama.cpp/pull/8672) | 22 |

