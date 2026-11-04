# Step 3 bisection: E50 tinyllama-1.1b/metal/pp512 (b8916 → b9076, expected increase)

Reference magnitude |ln ratio| = 0.3178 (+37.4%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-14 23:59 PDT (pid 91310)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Build b8987 (5f0ab726f798) started at 23:59:48
  - Succeeded in 40 s; builds of this series: 1/8
- Step 1 (release level, 111 candidates, mid is number 56, built in this run): lo b8916 / mid b8987 / hi b9076
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 2867.6 / mid 3658.2 / hi 3655.9 t/s (valid runs 2/2/2); L_hi − L_lo = +27.5% (0.76 times the reference); f = 1.00 → looks new, hi = b8987
- Build b8953 (434b2a1ff6a7) started at 00:03:18
  - Succeeded in 38 s; builds of this series: 2/8
- Step 2 (release level, 55 candidates, mid is number 28, built in this run): lo b8916 / mid b8953 / hi b8987
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 2863.3 / mid 3658.4 / hi 3660.4 t/s (valid runs 2/2/2); L_hi − L_lo = +27.8% (0.77 times the reference); f = 1.00 → looks new, hi = b8953
- Build b8935 (f454bd7eb894) started at 00:06:46
  - Succeeded in 38 s; builds of this series: 3/8
- Step 3 (release level, 27 candidates, mid is number 14, built in this run): lo b8916 / mid b8935 / hi b8953
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 2865.3 / mid 3658.9 / hi 3657.1 t/s (valid runs 2/2/2); L_hi − L_lo = +27.6% (0.77 times the reference); f = 1.00 → looks new, hi = b8935
- Build b8925 (0adede866ddb) started at 00:10:13
  - Succeeded in 39 s; builds of this series: 4/8
- Step 4 (release level, 13 candidates, mid is number 7, built in this run): lo b8916 / mid b8925 / hi b8935
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 2871.8 / mid 2849.6 / hi 3656.2 t/s (valid runs 2/2/2); L_hi − L_lo = +27.3% (0.76 times the reference); f = -0.03 → looks old, lo = b8925
- Build b8929 (9d34231bb895) started at 00:13:41
  - Succeeded in 72 s; builds of this series: 5/8
- Step 5 (release level, 6 candidates, mid is number 3, built in this run): lo b8925 / mid b8929 / hi b8935
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 2873.5 / mid 2869.2 / hi 3658.0 t/s (valid runs 2/2/2); L_hi − L_lo = +27.3% (0.76 times the reference); f = -0.01 → looks old, lo = b8929
- Build b8933 (dcad77cc3b08) started at 00:17:42
  - Succeeded in 38 s; builds of this series: 6/8
- Step 6 (release level, 3 candidates, mid is number 2, built in this run): lo b8929 / mid b8933 / hi b8935
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 2861.7 / mid 3656.3 / hi 3659.0 t/s (valid runs 2/2/2); L_hi − L_lo = +27.9% (0.77 times the reference); f = 1.00 → looks new, hi = b8933
- Build b8931 (9725a313be05) started at 00:21:09
  - Succeeded in 38 s; builds of this series: 7/8
- Step 7 (release level, 1 candidates, mid is number 1, built in this run): lo b8929 / mid b8931 / hi b8933
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; mid `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`; hi `-ngl 99 -t 4 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -dio 0 --poll 50 -pg 0,0`
  - Runs planned: 6
  - Result: lo 2869.6 / mid 3654.8 / hi 3665.7 t/s (valid runs 2/2/2); L_hi − L_lo = +27.7% (0.77 times the reference); f = 0.99 → looks new, hi = b8931

## Conclusion (2026-10-15 00:24 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b8929 → b8931 (release level, commits between: 2); steps measured: 7, builds: 7, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [9725a313be](https://github.com/ggml-org/llama.cpp/commit/9725a313be0528214c4a02fed906ddaf7b3f712e) | 2026-04-25 | CUDA: reduce MMQ stream-k overhead (#22298) | [#22298](https://github.com/ggml-org/llama.cpp/pull/22298) | 1 |
| [d1649047a3](https://github.com/ggml-org/llama.cpp/commit/d1649047a33d436142c9d496e190742992c08942) | 2026-04-25 | metal : optimize Metal Tensor API usage for GGML_OP_MUL_MAT (#20962) | [#20962](https://github.com/ggml-org/llama.cpp/pull/20962) | 6 |

