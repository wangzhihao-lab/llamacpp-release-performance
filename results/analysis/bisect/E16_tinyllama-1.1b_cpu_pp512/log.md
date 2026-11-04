# Step 3 bisection: E16 tinyllama-1.1b/cpu/pp512 (b3130 → b3222, expected increase)

Reference magnitude |ln ratio| = 0.1573 (+17.0%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-15 01:23 PDT (pid 40666)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Build b3177 (b96f9afb0d58) started at 01:23:51
  - Succeeded in 19 s; builds of this series: 1/8
- Step 1 (release level, 65 candidates, mid is number 33, built in this run): lo b3130 / mid b3177 / hi b3222
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 520.1 / mid 634.1 / hi 645.3 t/s (valid runs 2/2/2); L_hi − L_lo = +24.1% (1.37 times the reference); f = 0.92 → looks new, hi = b3177
- Build b3152 (7b2f4a7d193e) started at 01:28:21
  - Succeeded in 17 s; builds of this series: 2/8
- Step 2 (release level, 32 candidates, mid is number 16, built in this run): lo b3130 / mid b3152 / hi b3177
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 604.3 / mid 647.7 / hi 657.1 t/s (valid runs 2/2/2); L_hi − L_lo = +8.7% (0.53 times the reference); f = 0.83 → looks new, hi = b3152
- Build b3143 (f578b86b2123) started at 01:32:27
  - Succeeded in 17 s; builds of this series: 3/8
- Step 3 (release level, 15 candidates, mid is number 8, built in this run): lo b3130 / mid b3143 / hi b3152
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 597.2 / mid 654.6 / hi 659.9 t/s (valid runs 2/2/2); L_hi − L_lo = +10.5% (0.64 times the reference); f = 0.92 → looks new, hi = b3143
- Build b3138 (704a35b18374) started at 01:36:21
  - Succeeded in 17 s; builds of this series: 4/8
- Step 4 (release level, 7 candidates, mid is number 4, built in this run): lo b3130 / mid b3138 / hi b3143
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 609.7 / mid 610.2 / hi 634.0 t/s (valid runs 2/2/2); L_hi − L_lo = +4.0% (0.25 times the reference) → **effect_lost**: wrong sign or below half the reference magnitude, stopping (L_hi-L_lo = +0.0391 (+4.0%); needs sign + and |.| >= 0.0787 (0.5 x reference 0.1573))

## Conclusion (2026-10-15 01:40 PDT)

Status: **effect_lost** (the effect was lost); L_hi-L_lo = +0.0391 (+4.0%); needs sign + and |.| >= 0.0787 (0.5 x reference 0.1573).
Boundary: b3130 → b3143 (release level, commits between: 13); steps measured: 4, builds: 4, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [f578b86b21](https://github.com/ggml-org/llama.cpp/commit/f578b86b2123d0f92afbaa98a031df4d4464e582) | 2024-06-13 | move BLAS to a separate backend (#6210) | [#6210](https://github.com/ggml-org/llama.cpp/pull/6210) | 17 |
| [1c641e6aac](https://github.com/ggml-org/llama.cpp/commit/1c641e6aac5c18b964e7b32d9dbbb4bf5301d0d7) | 2024-06-13 | `build`: rename main → llama-cli, server → llama-server, llava-cli → llama-llava-cli, etc... (#7809) | [#7809](https://github.com/ggml-org/llama.cpp/pull/7809) | 138 |
| [963552903f](https://github.com/ggml-org/llama.cpp/commit/963552903f51043ee947a8deeaaa7ec00bc3f1a4) | 2024-06-12 | CUDA: fix broken oob check for FA vec f32 kernel (#7904) | [#7904](https://github.com/ggml-org/llama.cpp/pull/7904) | 1 |
| [a9cae48003](https://github.com/ggml-org/llama.cpp/commit/a9cae48003dfc4fe95b8f5c81682fc6e63425235) | 2024-06-12 | tests : add non-cont unary tests (#7857) | [#7857](https://github.com/ggml-org/llama.cpp/pull/7857) | 8 |
| [bfaa676b08](https://github.com/ggml-org/llama.cpp/commit/bfaa676b0841617d4ef3596e63aca6be1a8eb1b5) | 2024-06-12 | ggml : improve ggml_is_contiguous logic (#7856) | [#7856](https://github.com/ggml-org/llama.cpp/pull/7856) | 1 |
| [704a35b183](https://github.com/ggml-org/llama.cpp/commit/704a35b183748954013bd875bbbfdd9eaca14e62) | 2024-06-12 | server : restore numeric prompts (#7883) | [#7883](https://github.com/ggml-org/llama.cpp/pull/7883) | 1 |
| [dcf752707d](https://github.com/ggml-org/llama.cpp/commit/dcf752707d96eb305f546526c7bc5d01f0831130) | 2024-06-12 | update intel docker oneapi-basekit to 2024.1.1-devel-ubuntu22.04 (#7894) | [#7894](https://github.com/ggml-org/llama.cpp/pull/7894) | 2 |
| [f2b5764beb](https://github.com/ggml-org/llama.cpp/commit/f2b5764beb35583295e2475479c18f249b139b58) | 2024-06-12 | Fix a typo and add Fedora 40 pacakge to install for Vulkan (#7794) [no ci] | [#7794](https://github.com/ggml-org/llama.cpp/pull/7794) | 1 |
| [73bac2b11d](https://github.com/ggml-org/llama.cpp/commit/73bac2b11d7d3e20982fc9ee607625836387db8b) | 2024-06-11 | vulkan: select only one device for single gpu with multiple drivers (#7582) | [#7582](https://github.com/ggml-org/llama.cpp/pull/7582) | 1 |
| [ef52d1d16a](https://github.com/ggml-org/llama.cpp/commit/ef52d1d16afc695d798396cdd13594ea5e45a9dd) | 2024-06-11 | Update Vulkan RoPE implementation (#7818) | [#7818](https://github.com/ggml-org/llama.cpp/pull/7818) | 4 |
| [14f83526cd](https://github.com/ggml-org/llama.cpp/commit/14f83526cd27f638c856ea6eff08110b9860eb2a) | 2024-06-12 | fix broken link in pr template (#7880) [no ci] | [#7880](https://github.com/ggml-org/llama.cpp/pull/7880) | 1 |
| [6fe42d073f](https://github.com/ggml-org/llama.cpp/commit/6fe42d073f0554eada93ac9d40574025aeedb703) | 2024-06-11 | github: move PR template to .github/ root (#7868) | [#7868](https://github.com/ggml-org/llama.cpp/pull/7868) | 2 |
| [148995e5e5](https://github.com/ggml-org/llama.cpp/commit/148995e5e57b313cce2672f75610db58c6327a51) | 2024-06-11 | llama-bench: more compact markdown tables (#7879) | [#7879](https://github.com/ggml-org/llama.cpp/pull/7879) | 1 |

