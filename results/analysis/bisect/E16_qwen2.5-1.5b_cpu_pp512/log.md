# Step 3 bisection: E16 qwen2.5-1.5b/cpu/pp512 (b3130 → b3222, expected increase)

Reference magnitude |ln ratio| = 0.2265 (+25.4%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-15 07:12 PDT (pid 3837)

Parameters: rounds 2, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Step 1 (release level, 65 candidates, mid is number 33, existing binary reused): lo b3130 / mid b3177 / hi b3222
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 421.6 / mid 515.2 / hi 515.9 t/s (valid runs 2/2/2); L_hi − L_lo = +22.4% (0.89 times the reference); f = 0.99 → looks new, hi = b3177
- Step 2 (release level, 32 candidates, mid is number 16, existing binary reused): lo b3130 / mid b3152 / hi b3177
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 6
  - Result: lo 477.6 / mid 523.7 / hi 529.2 t/s (valid runs 2/2/2); L_hi − L_lo = +10.8% (0.45 times the reference) → **effect_lost**: wrong sign or below half the reference magnitude, stopping (L_hi-L_lo = +0.1028 (+10.8%); needs sign + and |.| >= 0.1132 (0.5 x reference 0.2265))

## Conclusion (2026-10-15 07:20 PDT)

Status: **effect_lost** (the effect was lost); L_hi-L_lo = +0.1028 (+10.8%); needs sign + and |.| >= 0.1132 (0.5 x reference 0.2265).
Boundary: b3130 → b3177 (release level, commits between: 47); steps measured: 2, builds: 0, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [b96f9afb0d](https://github.com/ggml-org/llama.cpp/commit/b96f9afb0d58b003ac8d1d0c94cd99393a3bc437) | 2024-06-18 | chore: clean useless beam search param (#7985) | [#7985](https://github.com/ggml-org/llama.cpp/pull/7985) | 1 |
| [1193778105](https://github.com/ggml-org/llama.cpp/commit/1193778105c9a81bd38f72c61aaafbaf85dc9c04) | 2024-06-18 | readme : update UI list (#7943) | [#7943](https://github.com/ggml-org/llama.cpp/pull/7943) | 1 |
| [5326bcceeb](https://github.com/ggml-org/llama.cpp/commit/5326bcceeb7dd34f16d0fe61b134d1e074a8e65d) | 2024-06-18 | ggml : sync |  | 1 |
| [e6ecc2be47](https://github.com/ggml-org/llama.cpp/commit/e6ecc2be470e3c5c6c5c9d8b90aa83a1f7725084) | 2024-06-18 | whisper : use ggml_backend_sched (whisper/2239) |  | 2 |
| [a94e6ff877](https://github.com/ggml-org/llama.cpp/commit/a94e6ff8774b7c9f950d9545baf0ce35e8d1ed2f) | 2024-06-17 | update: support Qwen2-57B-A14B (#7835) | [#7835](https://github.com/ggml-org/llama.cpp/pull/7835) | 4 |
| [5b6da18750](https://github.com/ggml-org/llama.cpp/commit/5b6da187508f49a9fa9d95fa22ae804a0780d256) | 2024-06-17 | Make updates to type cast based on compiler instead of OS (#7851) | [#7851](https://github.com/ggml-org/llama.cpp/pull/7851) | 1 |
| [7c26775adb](https://github.com/ggml-org/llama.cpp/commit/7c26775adb579e92b59c82e8084c07a1d0f75e9c) | 2024-06-17 | llama : disable FA if KV head size do not match (#7982) | [#7982](https://github.com/ggml-org/llama.cpp/pull/7982) | 1 |
| [b473e95084](https://github.com/ggml-org/llama.cpp/commit/b473e95084c286780165568cf0f385f21141d68d) | 2024-06-17 | Add Nix and Flox install instructions (#7899) | [#7899](https://github.com/ggml-org/llama.cpp/pull/7899) | 1 |
| [99052cd227](https://github.com/ggml-org/llama.cpp/commit/99052cd227c7182fcf53343d2e7d33bfa180a9cf) | 2024-06-17 | sched : offload_op also requires supports_op (#7977) | [#7977](https://github.com/ggml-org/llama.cpp/pull/7977) | 1 |
| [c637fcd34d](https://github.com/ggml-org/llama.cpp/commit/c637fcd34d135a9ff4f97d3a53ad03a910a4a31f) | 2024-06-17 | fix: divide 0 exception in mamba (#7932) | [#7932](https://github.com/ggml-org/llama.cpp/pull/7932) | 1 |
| [6a2f0b3474](https://github.com/ggml-org/llama.cpp/commit/6a2f0b3474d479bda4ac2ee7cfd5dcdcf0be1f79) | 2024-06-17 | Implement non-mapped async IO for CUDA on Windows.  (#7896) | [#7896](https://github.com/ggml-org/llama.cpp/pull/7896) | 1 |
| [21be9cab94](https://github.com/ggml-org/llama.cpp/commit/21be9cab94e0b5b53cb6edeeebf8c8c799baad03) | 2024-06-17 | rpc : fix load/store misaligned addresses (#7948) | [#7948](https://github.com/ggml-org/llama.cpp/pull/7948) | 1 |
| [006167aaf6](https://github.com/ggml-org/llama.cpp/commit/006167aaf6b6aaa4daa52961035f7460af19f469) | 2024-06-17 | gguf-dump.py: add --markdown dump output (#7853) | [#7853](https://github.com/ggml-org/llama.cpp/pull/7853) | 1 |
| [df68d4fa5d](https://github.com/ggml-org/llama.cpp/commit/df68d4fa5dc929217d3e64d673e099d7a417b206) | 2024-06-17 | [SYCL] Update README-sycl.md for Chapter "Recommended release" and "News" (#7946) | [#7946](https://github.com/ggml-org/llama.cpp/pull/7946) | 1 |
| [43b35e38ba](https://github.com/ggml-org/llama.cpp/commit/43b35e38ba371f9a7faa6dca4c5d1e8f698ffd87) | 2024-06-17 | Add support for sqrt on CUDA (#7953) | [#7953](https://github.com/ggml-org/llama.cpp/pull/7953) | 5 |
| [19b7a836f6](https://github.com/ggml-org/llama.cpp/commit/19b7a836f6658e18e973af532a5cc6ad6b3a27f8) | 2024-06-16 | cuda : fix bounds check for src0 rows in MMVQ kernel (whisper/2231) |  | 1 |
| [b5fcf8ef5c](https://github.com/ggml-org/llama.cpp/commit/b5fcf8ef5c29df53cfff60e180b4992a3b2332a6) | 2024-06-16 | ggml : fix and optimize ppc64le (ggml/849) |  | 1 |
| [398105ff43](https://github.com/ggml-org/llama.cpp/commit/398105ff4373eea385ea8e8625cb417b2ae51134) | 2024-06-16 | ggml : remove duplicate include of ggml-common.h (ggml/853) |  | 1 |
| [bc6c457fa3](https://github.com/ggml-org/llama.cpp/commit/bc6c457fa35f6791e9a2bb61108e7d49e8fc98bd) | 2024-06-16 | flake.lock: Update (#7951) | [#7951](https://github.com/ggml-org/llama.cpp/pull/7951) | 1 |
| [52399254b3](https://github.com/ggml-org/llama.cpp/commit/52399254b3bceda279b4ea9111a983e32310166e) | 2024-06-16 | unicode : avoid char32_t (#7957) | [#7957](https://github.com/ggml-org/llama.cpp/pull/7957) | 3 |
| [6fe1c62741](https://github.com/ggml-org/llama.cpp/commit/6fe1c627413725ddc1f9e323f6b13fe388c53e0a) | 2024-06-16 | readme : update UI list [no ci] (#7958) | [#7958](https://github.com/ggml-org/llama.cpp/pull/7958) | 1 |
| [cddaf028ad](https://github.com/ggml-org/llama.cpp/commit/cddaf028adc738b5a7ecc60809cb78e0ba0f97c1) | 2024-06-16 | ggml : fix handling of zero blocks in IQ quants (#7955) | [#7955](https://github.com/ggml-org/llama.cpp/pull/7955) | 1 |
| [c8a82194a8](https://github.com/ggml-org/llama.cpp/commit/c8a82194a888f68f259e0d0fa96f3332ac7c5cb6) | 2024-06-16 | github : update pr template |  | 1 |
| [7c7836d9d4](https://github.com/ggml-org/llama.cpp/commit/7c7836d9d4062d6858e3fb337b135c417ccee6ce) | 2024-06-16 | Vulkan Shader Refactor, Memory Debugging Option (#7947) | [#7947](https://github.com/ggml-org/llama.cpp/pull/7947) | 54 |
| [0c7b3595b9](https://github.com/ggml-org/llama.cpp/commit/0c7b3595b9e5ad2355818e259f06b0dc3f0065b3) | 2024-06-15 | Add `cvector-generator` example (#7514) | [#7514](https://github.com/ggml-org/llama.cpp/pull/7514) | 12 |
| [7b2f4a7d19](https://github.com/ggml-org/llama.cpp/commit/7b2f4a7d193ef2475259bbe7656fcccfab4b1217) | 2024-06-15 | [SYCL] remove global variables (#7710) | [#7710](https://github.com/ggml-org/llama.cpp/pull/7710) | 9 |
| [f8ec8877b7](https://github.com/ggml-org/llama.cpp/commit/f8ec8877b75774fc6c47559d529dac423877bcad) | 2024-06-14 | ci : fix macos x86 build (#7940) | [#7940](https://github.com/ggml-org/llama.cpp/pull/7940) | 1 |
| [76d66ee0be](https://github.com/ggml-org/llama.cpp/commit/76d66ee0be91e2bec93206e821ee1db8d023cff5) | 2024-06-14 | CUDA: faster q2_K, q3_K MMQ + int8 tensor cores (#7921) | [#7921](https://github.com/ggml-org/llama.cpp/pull/7921) | 6 |
| [66ef1ceedf](https://github.com/ggml-org/llama.cpp/commit/66ef1ceedf983773c8ceb4d925285d41d4e50e2a) | 2024-06-14 | metal : utilize max shared memory for mul_mat_id (#7935) | [#7935](https://github.com/ggml-org/llama.cpp/pull/7935) | 1 |
| [e65bbf606c](https://github.com/ggml-org/llama.cpp/commit/e65bbf606c61f49dc06c7ac060cd5ba7ae446025) | 2024-06-14 | llama-bench : fix RPC indication (#7936) | [#7936](https://github.com/ggml-org/llama.cpp/pull/7936) | 1 |
| [6fcd1331ef](https://github.com/ggml-org/llama.cpp/commit/6fcd1331efbfbb89c8c96eba2321bb7b4d0c40e4) | 2024-06-14 | llama : more checks before assuming FIM tokens (#7644) | [#7644](https://github.com/ggml-org/llama.cpp/pull/7644) | 1 |
| [41b9260f18](https://github.com/ggml-org/llama.cpp/commit/41b9260f18eb7f325c952006ac46afc1d0d8ad2f) | 2024-06-14 | convert : add Poro-34B-chat tokenizer support (#7713) | [#7713](https://github.com/ggml-org/llama.cpp/pull/7713) | 4 |
| [172c825684](https://github.com/ggml-org/llama.cpp/commit/172c8256840ffd882ab9992ecedbb587d9b21f15) | 2024-06-13 | rpc : fix ggml_backend_rpc_supports_buft() (#7918) | [#7918](https://github.com/ggml-org/llama.cpp/pull/7918) | 1 |
| [a55eb1bf0f](https://github.com/ggml-org/llama.cpp/commit/a55eb1bf0fa2fd84147bdfd384391e029d988253) | 2024-06-13 | readme : Remove outdated instructions from README.md (#7914) [no ci] | [#7914](https://github.com/ggml-org/llama.cpp/pull/7914) | 1 |
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

