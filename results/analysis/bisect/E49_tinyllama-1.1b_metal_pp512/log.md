# Step 3 bisection: E49 tinyllama-1.1b/metal/pp512 (b8545 → b8740, expected increase)

Reference magnitude |ln ratio| = 0.6397 (+89.6%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-14 15:25 PDT (pid 19694)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Build b8646 (0c58ba3365d2) started at 15:25:06
  - Succeeded in 44 s; builds of this series: 1/8
- Step 1 (release level, 133 candidates, mid is number 67, built in this run): lo b8545 / mid b8646 / hi b8740
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 1496.1 / mid 2867.9 / hi 2866.2 t/s (valid runs 2/2/2); L_hi − L_lo = +91.6% (1.02 times the reference); f = 1.00 → looks new, hi = b8646
- Build b8590 (5ce013cd7e9c) started at 15:28:52
  - Succeeded in 37 s; builds of this series: 2/8
- Step 2 (release level, 66 candidates, mid is number 33, built in this run): lo b8545 / mid b8590 / hi b8646
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 1496.2 / mid 2868.8 / hi 2868.6 t/s (valid runs 2/2/2); L_hi − L_lo = +91.7% (1.02 times the reference); f = 1.00 → looks new, hi = b8590
- Build b8565 (b0f0dd3e516a) started at 15:32:25
  - Succeeded in 38 s; builds of this series: 3/8
- Step 3 (release level, 32 candidates, mid is number 16, built in this run): lo b8545 / mid b8565 / hi b8590
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 1495.9 / mid 2867.9 / hi 2868.4 t/s (valid runs 2/2/2); L_hi − L_lo = +91.8% (1.02 times the reference); f = 1.00 → looks new, hi = b8565
- Build b8554 (871f1a2d2f54) started at 15:35:58
  - Succeeded in 37 s; builds of this series: 4/8
- Step 4 (release level, 15 candidates, mid is number 8, built in this run): lo b8545 / mid b8554 / hi b8565
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 1497.0 / mid 2868.0 / hi 2868.5 t/s (valid runs 2/2/2); L_hi − L_lo = +91.6% (1.02 times the reference); f = 1.00 → looks new, hi = b8554
- Build b8550 (a308e584cae3) started at 15:39:30
  - Succeeded in 37 s; builds of this series: 5/8
- Step 5 (release level, 7 candidates, mid is number 4, built in this run): lo b8545 / mid b8550 / hi b8554
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 1497.2 / mid 2865.7 / hi 2868.7 t/s (valid runs 2/2/2); L_hi − L_lo = +91.6% (1.02 times the reference); f = 1.00 → looks new, hi = b8550
- Build b8547 (6861f6509a2b) started at 15:43:02
  - Succeeded in 37 s; builds of this series: 6/8
- Step 6 (release level, 3 candidates, mid is number 2, built in this run): lo b8545 / mid b8547 / hi b8550
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 1496.7 / mid 1496.4 / hi 2869.7 t/s (valid runs 2/2/2); L_hi − L_lo = +91.7% (1.02 times the reference); f = -0.00 → looks old, lo = b8547
- Build b8548 (9bcb4eff4d7e) started at 15:46:39
  - Succeeded in 69 s; builds of this series: 7/8
- Step 7 (release level, 1 candidates, mid is number 1, built in this run): lo b8547 / mid b8548 / hi b8550
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 1496.5 / mid 2869.9 / hi 2868.8 t/s (valid runs 2/2/2); L_hi − L_lo = +91.7% (1.02 times the reference); f = 1.00 → looks new, hi = b8548

## Conclusion (2026-10-14 15:50 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b8547 → b8548 (release level, commits between: 1); steps measured: 7, builds: 7, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [9bcb4eff4d](https://github.com/ggml-org/llama.cpp/commit/9bcb4eff4d7e7755276645c767948c25c00481b8) | 2026-03-27 | metal : Fix dimension constraint violation in matmul2d descriptor (#21048) | [#21048](https://github.com/ggml-org/llama.cpp/pull/21048) | 1 |

