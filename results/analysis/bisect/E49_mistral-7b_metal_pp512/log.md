# Step 3 bisection: E49 mistral-7b/metal/pp512 (b8545 → b8740, expected increase)

Reference magnitude |ln ratio| = 0.4627 (+58.8%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-14 16:12 PDT (pid 19694)

Parameters: rounds 2, -r 5, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Step 1 (release level, 133 candidates, mid is number 67, existing binary reused): lo b8545 / mid b8646 / hi b8740
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 222.7 / mid 450.5 / hi 450.4 t/s (valid runs 2/2/2); L_hi − L_lo = +102.2% (1.52 times the reference); f = 1.00 → looks new, hi = b8646
- Step 2 (release level, 66 candidates, mid is number 33, existing binary reused): lo b8545 / mid b8590 / hi b8646
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 221.4 / mid 447.5 / hi 448.1 t/s (valid runs 2/2/2); L_hi − L_lo = +102.4% (1.52 times the reference); f = 1.00 → looks new, hi = b8590
- Step 3 (release level, 32 candidates, mid is number 16, existing binary reused): lo b8545 / mid b8565 / hi b8590
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 223.9 / mid 447.7 / hi 448.3 t/s (valid runs 2/2/2); L_hi − L_lo = +100.2% (1.50 times the reference); f = 1.00 → looks new, hi = b8565
- Step 4 (release level, 15 candidates, mid is number 8, existing binary reused): lo b8545 / mid b8554 / hi b8565
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 223.9 / mid 447.5 / hi 447.3 t/s (valid runs 2/2/2); L_hi − L_lo = +99.8% (1.50 times the reference); f = 1.00 → looks new, hi = b8554
- Step 5 (release level, 7 candidates, mid is number 4, existing binary reused): lo b8545 / mid b8550 / hi b8554
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 224.6 / mid 449.1 / hi 449.0 t/s (valid runs 2/2/2); L_hi − L_lo = +100.0% (1.50 times the reference); f = 1.00 → looks new, hi = b8550
- Step 6 (release level, 3 candidates, mid is number 2, existing binary reused): lo b8545 / mid b8547 / hi b8550
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 224.3 / mid 224.3 / hi 448.2 t/s (valid runs 2/2/2); L_hi − L_lo = +99.8% (1.50 times the reference); f = -0.00 → looks old, lo = b8547
- Step 7 (release level, 1 candidates, mid is number 1, existing binary reused): lo b8547 / mid b8548 / hi b8550
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 224.5 / mid 448.6 / hi 449.1 t/s (valid runs 2/2/2); L_hi − L_lo = +100.1% (1.50 times the reference); f = 1.00 → looks new, hi = b8548

## Conclusion (2026-10-14 16:40 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b8547 → b8548 (release level, commits between: 1); steps measured: 7, builds: 0, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [9bcb4eff4d](https://github.com/ggml-org/llama.cpp/commit/9bcb4eff4d7e7755276645c767948c25c00481b8) | 2026-03-27 | metal : Fix dimension constraint violation in matmul2d descriptor (#21048) | [#21048](https://github.com/ggml-org/llama.cpp/pull/21048) | 1 |

