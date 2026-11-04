# Step 3 bisection: E01 tinyllama-1.1b/metal/pp512 (b1137 → b1245, expected increase)

Reference magnitude |ln ratio| = 0.8355 (+130.6%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-14 23:18 PDT (pid 77176)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Build b1183 (de2fe892af92) started at 23:18:10
  - Succeeded in 10 s; builds of this series: 1/8
- Step 1 (release level, 57 candidates, mid is number 29, built in this run): lo b1137 / mid b1183 / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 527.5 / mid 822.5 / hi 1365.7 t/s (valid runs 2/2/2); L_hi − L_lo = +158.9% (1.14 times the reference); f = 0.47 → **intermediate** (possibly two stacked changes), treated as f < 0.5, lo = b1183
- Build b1204 (e64f5b55783e) started at 23:21:44
  - Succeeded in 9 s; builds of this series: 2/8
- Step 2 (release level, 28 candidates, mid is number 14, built in this run): lo b1183 / mid b1204 / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 822.9 / mid 823.5 / hi 1366.6 t/s (valid runs 2/2/2); L_hi − L_lo = +66.1% (0.61 times the reference); f = 0.00 → looks old, lo = b1204
- Build b1218 (84e723653ca9) started at 23:25:06
  - Succeeded in 9 s; builds of this series: 3/8
- Step 3 (release level, 14 candidates, mid is number 7, built in this run): lo b1204 / mid b1218 / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 823.8 / mid 860.8 / hi 1366.6 t/s (valid runs 2/2/2); L_hi − L_lo = +65.9% (0.61 times the reference); f = 0.09 → looks old, lo = b1218
- Build b1222 (35f73049af6c) started at 23:28:28
  - Succeeded in 10 s; builds of this series: 4/8
- Step 4 (release level, 7 candidates, mid is number 4, built in this run): lo b1218 / mid b1222 / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 860.9 / mid 861.0 / hi 1367.6 t/s (valid runs 2/2/2); L_hi − L_lo = +58.9% (0.55 times the reference); f = 0.00 → looks old, lo = b1222
- Build b1225 (980ab41afba9) started at 23:31:51
  - Succeeded in 9 s; builds of this series: 5/8
- Step 5 (release level, 3 candidates, mid is number 2, built in this run): lo b1222 / mid b1225 / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 860.7 / mid 860.6 / hi 1368.2 t/s (valid runs 2/2/2); L_hi − L_lo = +59.0% (0.56 times the reference); f = -0.00 → looks old, lo = b1225
- Build b1226 (990a5e226a1a) started at 23:35:11
  - Succeeded in 9 s; builds of this series: 6/8
- Step 6 (release level, 1 candidates, mid is number 1, built in this run): lo b1225 / mid b1226 / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 99 -t 4 -b 512`; mid `-ngl 99 -t 4 -b 512`; hi `-ngl 99 -t 4 -b 512`
  - Runs planned: 6
  - Result: lo 860.7 / mid 860.8 / hi 1367.2 t/s (valid runs 2/2/2); L_hi − L_lo = +58.9% (0.55 times the reference); f = 0.00 → looks old, lo = b1226

## Conclusion (2026-10-14 23:38 PDT)

Status: **located** (search ended at adjacent points).
Boundary: b1226 → b1245 (release level, commits between: 19); steps measured: 6, builds: 6, intermediate steps: 1, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [69eb67e282](https://github.com/ggml-org/llama.cpp/commit/69eb67e28275cd2d57693405f768754a7b2245ad) | 2023-09-15 | fix build numbers by setting fetch-depth=0 (#3197) | [#3197](https://github.com/ggml-org/llama.cpp/pull/3197) | 1 |
| [4fe09dfe66](https://github.com/ggml-org/llama.cpp/commit/4fe09dfe665c58a753dc9eb638dd4dca1cd35488) | 2023-09-15 | llama : add support for StarCoder model architectures (#3187) | [#3187](https://github.com/ggml-org/llama.cpp/pull/3187) | 3 |
| [80291a1d02](https://github.com/ggml-org/llama.cpp/commit/80291a1d02a07f7f66666fb576c5b1e75aa48b46) | 2023-09-15 | common : do not use GNU zero-length __VA_ARGS__ extension (#3195) | [#3195](https://github.com/ggml-org/llama.cpp/pull/3195) | 1 |
| [c6f1491da0](https://github.com/ggml-org/llama.cpp/commit/c6f1491da032238241e01021c8c58d7b540a043f) | 2023-09-15 | metal : fix bug in soft_max kernels (out-of-bounds access) (#3194) | [#3194](https://github.com/ggml-org/llama.cpp/pull/3194) | 1 |
| [e3d87a6c36](https://github.com/ggml-org/llama.cpp/commit/e3d87a6c36eadd84d58763143c6d56a0c771ca40) | 2023-09-15 | convert : make ftype optional in simple scripts (#3185) | [#3185](https://github.com/ggml-org/llama.cpp/pull/3185) | 3 |
| [8c00b7a6ff](https://github.com/ggml-org/llama.cpp/commit/8c00b7a6ff38e27fa1e471452b8a480913772c2a) | 2023-09-15 | sync : ggml (Metal F32 support + reduce ggml-alloc size) (#3192) | [#3192](https://github.com/ggml-org/llama.cpp/pull/3192) | 6 |
| [7e50d34be6](https://github.com/ggml-org/llama.cpp/commit/7e50d34be68aae2cc766203703dd188e910e033a) | 2023-09-15 | cmake : fix building shared libs for clang (rocm) on windows (#3176) | [#3176](https://github.com/ggml-org/llama.cpp/pull/3176) | 1 |
| [235f7c193b](https://github.com/ggml-org/llama.cpp/commit/235f7c193b02dacfb56319e41a28684b3a2c6db0) | 2023-09-15 | flake : use pkg-config instead of pkgconfig (#3188) | [#3188](https://github.com/ggml-org/llama.cpp/pull/3188) | 1 |
| [a51b687657](https://github.com/ggml-org/llama.cpp/commit/a51b68765799e75e17c7622f376bfbeb66f1bd70) | 2023-09-15 | metal : relax conditions on fast matrix multiplication kernel (#3168) | [#3168](https://github.com/ggml-org/llama.cpp/pull/3168) | 4 |
| [76164fe2e6](https://github.com/ggml-org/llama.cpp/commit/76164fe2e65c058e9ee2c3afd0ad6b182ca57e25) | 2023-09-15 | cmake : fix llama.h location when built outside of root directory (#3179) | [#3179](https://github.com/ggml-org/llama.cpp/pull/3179) | 1 |
| [c2ab6fe661](https://github.com/ggml-org/llama.cpp/commit/c2ab6fe661af9834ca6dd75f14e2439938cc22ac) | 2023-09-15 | ci : Cloud-V for RISC-V builds (#3160) | [#3160](https://github.com/ggml-org/llama.cpp/pull/3160) | 1 |
| [2d770505a8](https://github.com/ggml-org/llama.cpp/commit/2d770505a89a99ce78a5950cf14fc06d3176ffa4) | 2023-09-15 | llama : remove mtest (#3177) | [#3177](https://github.com/ggml-org/llama.cpp/pull/3177) | 5 |
| [98311c4277](https://github.com/ggml-org/llama.cpp/commit/98311c427739e3b06527c3ce6b5c021ab6692740) | 2023-09-14 | llama : make quantize example up to 2.7x faster (#3115) | [#3115](https://github.com/ggml-org/llama.cpp/pull/3115) | 1 |
| [feea179e9f](https://github.com/ggml-org/llama.cpp/commit/feea179e9f9921e96e8fb1b8855d4a8f83682455) | 2023-09-14 | flake : allow $out/include to already exist (#3175) | [#3175](https://github.com/ggml-org/llama.cpp/pull/3175) | 1 |
| [769266a543](https://github.com/ggml-org/llama.cpp/commit/769266a543f68377a1d904ec2a8c27b38a4025ab) | 2023-09-14 | cmake : compile ggml-rocm with -fpic when building shared library (#3158) | [#3158](https://github.com/ggml-org/llama.cpp/pull/3158) | 1 |
| [cf8238e7f4](https://github.com/ggml-org/llama.cpp/commit/cf8238e7f43cb82a36426af392037e85cd2a3df6) | 2023-09-14 | flake : include llama.h in nix output (#3159) | [#3159](https://github.com/ggml-org/llama.cpp/pull/3159) | 1 |
| [4b8560e72a](https://github.com/ggml-org/llama.cpp/commit/4b8560e72a936b5d536ebd1e7a5dd579984769f3) | 2023-09-14 | make : fix clang++ detection, move some definitions to CPPFLAGS (#3155) | [#3155](https://github.com/ggml-org/llama.cpp/pull/3155) | 1 |
| [83a53b753a](https://github.com/ggml-org/llama.cpp/commit/83a53b753a9499a2a3535c93975b430cb2c828a9) | 2023-09-14 | CI: add FreeBSD & simplify CUDA windows (#3053) | [#3053](https://github.com/ggml-org/llama.cpp/pull/3053) | 2 |
| [5c872dbca2](https://github.com/ggml-org/llama.cpp/commit/5c872dbca2c7979b1f6dafc97db0774b8bbf9372) | 2023-09-14 | falcon : use stated vocab size (#2914) | [#2914](https://github.com/ggml-org/llama.cpp/pull/2914) | 1 |

