# Step 3 bisection: E01cpu mistral-7b/cpu/pp512 (b1137 → b1245, expected decrease)

Reference magnitude |ln ratio| = 0.2480 (-22.0%, source: --ref-lr); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-26 05:12 PDT (pid 19954)

Parameters: rounds 4, -r 5, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level on, window 00:00-24:00.

- Step 1 (release level, 57 candidates, mid is number 29, existing binary reused): lo b1137 / mid b1183 / hi b1245
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512`; mid `-ngl 0 -t 8 -b 512`; hi `-ngl 0 -t 8 -b 512`
  - Runs planned: 12
  - Result: lo 71.3 / mid 70.3 / hi 67.5 t/s (valid runs 4/4/4); L_hi − L_lo = -5.3% (0.22 times the reference) → **effect_lost**: wrong sign or below half the reference magnitude, stopping (L_hi-L_lo = -0.0549 (-5.3%); needs sign - and |.| >= 0.1240 (0.5 x reference 0.2480))

## Conclusion (2026-10-26 05:25 PDT)

Status: **effect_lost** (the effect was lost); L_hi-L_lo = -0.0549 (-5.3%); needs sign - and |.| >= 0.1240 (0.5 x reference 0.2480).
Boundary: b1137 → b1245 (release level, commits between: 108); steps measured: 1, builds: 0, intermediate steps: 0, skipped candidates: none.

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
| [990a5e226a](https://github.com/ggml-org/llama.cpp/commit/990a5e226a1a0ac858abe3aa7e5f3b000d4fa665) | 2023-09-14 | cmake : add relocatable Llama package (#2960) | [#2960](https://github.com/ggml-org/llama.cpp/pull/2960) | 5 |
| [980ab41afb](https://github.com/ggml-org/llama.cpp/commit/980ab41afba96106cd29cdf3aa6f948c251cb71f) | 2023-09-14 | docker : add gpu image CI builds (#3103) | [#3103](https://github.com/ggml-org/llama.cpp/pull/3103) | 2 |
| [e394084166](https://github.com/ggml-org/llama.cpp/commit/e394084166baac09e8ee9a08a4686f907f7e5291) | 2023-09-14 | gguf-py : support identity operation in TensorNameMap (#3095) | [#3095](https://github.com/ggml-org/llama.cpp/pull/3095) | 2 |
| [4c8643dd6e](https://github.com/ggml-org/llama.cpp/commit/4c8643dd6ea1a163bc5979cb69c1e7ab0975bc93) | 2023-09-14 | feature : support Baichuan serial models (#3009) | [#3009](https://github.com/ggml-org/llama.cpp/pull/3009) | 4 |
| [35f73049af](https://github.com/ggml-org/llama.cpp/commit/35f73049af6c676a106a5a990a819ae0bc3fcd7d) | 2023-09-14 | speculative : add heuristic algorithm (#3006) | [#3006](https://github.com/ggml-org/llama.cpp/pull/3006) | 1 |
| [71ca2fad7d](https://github.com/ggml-org/llama.cpp/commit/71ca2fad7d6c0ef95ef9944fb3a1a843e481f314) | 2023-09-13 | whisper : tokenizer fix + re-enable tokenizer test for LLaMa (#3096) | [#3096](https://github.com/ggml-org/llama.cpp/pull/3096) | 6 |
| [1b6c650d16](https://github.com/ggml-org/llama.cpp/commit/1b6c650d16048d6427dd502a9627e72837265844) | 2023-09-13 | cmake : add a compiler flag check for FP16 format (#3086) | [#3086](https://github.com/ggml-org/llama.cpp/pull/3086) | 1 |
| [0a5eebb45d](https://github.com/ggml-org/llama.cpp/commit/0a5eebb45d5697127b84418576dc479c400c4b3d) | 2023-09-13 | CUDA: mul_mat_q RDNA2 tunings (#2910) | [#2910](https://github.com/ggml-org/llama.cpp/pull/2910) | 3 |
| [84e723653c](https://github.com/ggml-org/llama.cpp/commit/84e723653ca99d51a74b454984acf2c077468561) | 2023-09-13 | speculative: add --n-gpu-layers-draft option (#3063) | [#3063](https://github.com/ggml-org/llama.cpp/pull/3063) | 3 |
| [b52b29ab9d](https://github.com/ggml-org/llama.cpp/commit/b52b29ab9d601bb298050bcd2261169bc917ba2c) | 2023-09-12 | arm64 support for windows (#3007) | [#3007](https://github.com/ggml-org/llama.cpp/pull/3007) | 4 |
| [4f7cd6ba9c](https://github.com/ggml-org/llama.cpp/commit/4f7cd6ba9c88d3ca9a207b6e04f8b2b1efd707b8) | 2023-09-13 | CUDA: fix LoRAs (#3130) | [#3130](https://github.com/ggml-org/llama.cpp/pull/3130) | 1 |
| [89e89599fd](https://github.com/ggml-org/llama.cpp/commit/89e89599fd095172f8d67903b5e227467420f036) | 2023-09-11 | CUDA: fix mul_mat_q not used for output tensor (#3127) | [#3127](https://github.com/ggml-org/llama.cpp/pull/3127) | 1 |
| [d54a4027a6](https://github.com/ggml-org/llama.cpp/commit/d54a4027a6ebda98ab0fef7fa0c2247d0bef132a) | 2023-09-11 | CUDA: lower GPU latency + fix Windows performance (#3110) | [#3110](https://github.com/ggml-org/llama.cpp/pull/3110) | 1 |
| [1b0d09259e](https://github.com/ggml-org/llama.cpp/commit/1b0d09259e37898c519edb6c52d58f4d096f10bd) | 2023-09-11 | cmake : support build for iOS/tvOS (#3116) | [#3116](https://github.com/ggml-org/llama.cpp/pull/3116) | 2 |
| [8a4ca9af56](https://github.com/ggml-org/llama.cpp/commit/8a4ca9af569853023ce87f047eb5165df13f2ff1) | 2023-09-11 | CUDA: add device number to error messages (#3112) | [#3112](https://github.com/ggml-org/llama.cpp/pull/3112) | 1 |
| [f31b6f4e2d](https://github.com/ggml-org/llama.cpp/commit/f31b6f4e2d6def3c0bd7c75f75c0c1e8698e0589) | 2023-09-11 | metal : PP speedup (#3084) | [#3084](https://github.com/ggml-org/llama.cpp/pull/3084) | 2 |
| [6eeb4d9083](https://github.com/ggml-org/llama.cpp/commit/6eeb4d90839bac1e6085e5544654ab5c319ad09a) | 2023-09-10 | convert: remove most of the n_mult usage in convert.py (#3098) | [#3098](https://github.com/ggml-org/llama.cpp/pull/3098) | 1 |
| [21ac3a1503](https://github.com/ggml-org/llama.cpp/commit/21ac3a1503001020122db5dce6adf34b761675f5) | 2023-09-09 | metal : support for Swift (#3078) | [#3078](https://github.com/ggml-org/llama.cpp/pull/3078) | 2 |
| [4fd5477955](https://github.com/ggml-org/llama.cpp/commit/4fd54779550e43e2a29f6840ebcf8f395a2f879e) | 2023-09-09 | metal : support build for iOS/tvOS (#3089) | [#3089](https://github.com/ggml-org/llama.cpp/pull/3089) | 1 |
| [ec2a24fedf](https://github.com/ggml-org/llama.cpp/commit/ec2a24fedf1de8ebd5f170016953b09ff2806924) | 2023-09-08 | flake : add train-text-from-scratch to flake.nix (#3042) | [#3042](https://github.com/ggml-org/llama.cpp/pull/3042) | 1 |
| [7d99aca759](https://github.com/ggml-org/llama.cpp/commit/7d99aca759f2f8a1ff39f3bb02a840f69863428b) | 2023-09-08 | readme : fix typo (#3043) | [#3043](https://github.com/ggml-org/llama.cpp/pull/3043) | 1 |
| [ba7ffbb251](https://github.com/ggml-org/llama.cpp/commit/ba7ffbb2517ff8cf4c689f94a9ad866f3ee71225) | 2023-09-08 | metal : Q3_K speedup (#2995) | [#2995](https://github.com/ggml-org/llama.cpp/pull/2995) | 1 |
| [e64f5b5578](https://github.com/ggml-org/llama.cpp/commit/e64f5b55783e910d8287363895d652b4bea6527a) | 2023-09-08 | examples : make n_ctx warning work again (#3066) | [#3066](https://github.com/ggml-org/llama.cpp/pull/3066) | 5 |
| [94f10b91ed](https://github.com/ggml-org/llama.cpp/commit/94f10b91ed69980f299441e49c8dbdb448f0ccc6) | 2023-09-08 | readme : update hot tpoics |  | 1 |
| [b3e9852e47](https://github.com/ggml-org/llama.cpp/commit/b3e9852e471d12cbbe5dad20c81c4766d969739a) | 2023-09-08 | sync : ggml (CUDA GLM RoPE + POSIX) (#3082) | [#3082](https://github.com/ggml-org/llama.cpp/pull/3082) | 3 |
| [cb6c44c5e0](https://github.com/ggml-org/llama.cpp/commit/cb6c44c5e045709b6bb5cc9bb8c9be107c771a78) | 2023-09-08 | build : do not use _GNU_SOURCE gratuitously (#2035) | [#2035](https://github.com/ggml-org/llama.cpp/pull/2035) | 10 |
| [a21baeb122](https://github.com/ggml-org/llama.cpp/commit/a21baeb12202a9020b48c53beaaf4b355228e8ba) | 2023-09-08 | docker : add git to full-cuda.Dockerfile main-cuda.Dockerfile (#3044) | [#3044](https://github.com/ggml-org/llama.cpp/pull/3044) | 2 |
| [6ff712a6d1](https://github.com/ggml-org/llama.cpp/commit/6ff712a6d1a0c85d996e2f681df57a2554cfe5c1) | 2023-09-08 | Update deprecated GGML TheBloke links to GGUF (#3079) | [#3079](https://github.com/ggml-org/llama.cpp/pull/3079) | 1 |
| [ebc96086af](https://github.com/ggml-org/llama.cpp/commit/ebc96086af49fe70108cafcea6ab4bebd658a41a) | 2023-09-08 | ggml-alloc : correctly check mmap return value for errors (#3075) | [#3075](https://github.com/ggml-org/llama.cpp/pull/3075) | 1 |
| [7f412dab9c](https://github.com/ggml-org/llama.cpp/commit/7f412dab9c8801f5d37904f7dce1faf4c2b43b42) | 2023-09-08 | enable CPU HBM (#2603) | [#2603](https://github.com/ggml-org/llama.cpp/pull/2603) | 3 |
| [6336d834ec](https://github.com/ggml-org/llama.cpp/commit/6336d834ec7bff3e93e24182c0f609d2f2bdce26) | 2023-09-07 | convert : fix F32 ftype not being saved (#3048) | [#3048](https://github.com/ggml-org/llama.cpp/pull/3048) | 1 |
| [00d62adb79](https://github.com/ggml-org/llama.cpp/commit/00d62adb79bf914a95fb9a2e8f42f3029e76d62c) | 2023-09-07 | fix some warnings from gcc and clang-tidy (#3038) | [#3038](https://github.com/ggml-org/llama.cpp/pull/3038) | 22 |
| [4fa2cc1750](https://github.com/ggml-org/llama.cpp/commit/4fa2cc1750b861880de42515cb19c13b2d776ee2) | 2023-09-07 | make : improve test target (#3031) | [#3031](https://github.com/ggml-org/llama.cpp/pull/3031) | 1 |
| [5ffab089a5](https://github.com/ggml-org/llama.cpp/commit/5ffab089a54bc06ae4a9ab533893b558756a1e80) | 2023-09-07 | make : fix CPPFLAGS (#3035) | [#3035](https://github.com/ggml-org/llama.cpp/pull/3035) | 1 |
| [15b67a66c2](https://github.com/ggml-org/llama.cpp/commit/15b67a66c2f2d6032415b28a699b5131962318f1) | 2023-09-07 | llama-bench : use two tokens in the warmup run for prompt evals (#3059) | [#3059](https://github.com/ggml-org/llama.cpp/pull/3059) | 1 |
| [be8c9c245b](https://github.com/ggml-org/llama.cpp/commit/be8c9c245bd129ebabb80e0a7a8dd7daeb4d30af) | 2023-09-07 | metal : parallel RoPE on Metal (#3024) | [#3024](https://github.com/ggml-org/llama.cpp/pull/3024) | 2 |
| [be6beeb8d7](https://github.com/ggml-org/llama.cpp/commit/be6beeb8d75294552c4918fce06d7b84eebf3d79) | 2023-09-07 | metal : correct fix of kernel_norm (#3060) | [#3060](https://github.com/ggml-org/llama.cpp/pull/3060) | 1 |
| [c4f496648c](https://github.com/ggml-org/llama.cpp/commit/c4f496648c1e32efeb714200e7eae7fc7cfbb223) | 2023-09-07 | metal : fix kernel_norm (fixes Falcon on Metal) (#3057) | [#3057](https://github.com/ggml-org/llama.cpp/pull/3057) | 2 |
| [fec2fb19e4](https://github.com/ggml-org/llama.cpp/commit/fec2fb19e4229aac58c98171c46e77144b99f8a3) | 2023-09-07 | ggml : posixify madvise and pagesize (#3037) | [#3037](https://github.com/ggml-org/llama.cpp/pull/3037) | 3 |
| [178b1850eb](https://github.com/ggml-org/llama.cpp/commit/178b1850ebd21b349cebbee887950e435c5aa2d3) | 2023-09-06 | k-quants : fix zero-weight guard in Q6_K (ref #3040) |  | 1 |
| [ea2c85d5d2](https://github.com/ggml-org/llama.cpp/commit/ea2c85d5d2a93d39d0172222917f3195f0e456ff) | 2023-09-06 | convert-llama-ggml-to-gguf: Try to handle files older than GGJTv3 (#3023) | [#3023](https://github.com/ggml-org/llama.cpp/pull/3023) | 2 |
(another 48 commits are in result.json)

