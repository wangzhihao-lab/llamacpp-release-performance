# Step 3 bisection: E16R qwen2.5-1.5b/cpu/pp512 (b3130 → b3222, expected increase)

Reference magnitude |ln ratio| = 0.2146 (+23.9%, source: step 2 fixed phase (v11)); every step requires L_hi − L_lo to have the expected sign and to reach at least 0.5 times the reference magnitude, otherwise the series stops as effect_lost.
Decision: f = (L_mid − L_lo)/(L_hi − L_lo); f ≤ 0.35 looks old (lo = mid), f ≥ 0.65 looks new (hi = mid), and values in between are intermediate (possibly two stacked changes), continued by f < 0.5 / ≥ 0.5.

## Run 2026-10-15 12:35 PDT (pid 77855)

Parameters: rounds 4, -r 10, cooldown 20 s, idle share ≥ 80%, thermal state ≤ 1 (wait at most 300 s), max-builds 8, commit-level off, window 00:00-24:00.

- Step 1 (release level, 65 candidates, mid is number 33, existing binary reused): lo b3130 / mid b3177 / hi b3222
  - Fixed configuration (fully aligned): lo `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; mid `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`; hi `-ngl 0 -t 8 -b 512 -ub 512 -fa 0 -ctk f16 -ctv f16 -mmp 1 -pg 0,0`
  - Runs planned: 12
  - Result: lo 482.8 / mid 528.4 / hi 515.6 t/s (valid runs 4/4/4); L_hi − L_lo = +6.8% (0.31 times the reference) → **effect_lost**: wrong sign or below half the reference magnitude, stopping (L_hi-L_lo = +0.0657 (+6.8%); needs sign + and |.| >= 0.1073 (0.5 x reference 0.2146))

## Conclusion (2026-10-15 12:42 PDT)

Status: **effect_lost** (the effect was lost); L_hi-L_lo = +0.0657 (+6.8%); needs sign + and |.| >= 0.1073 (0.5 x reference 0.2146).
Boundary: b3130 → b3222 (release level, commits between: 92); steps measured: 1, builds: 0, intermediate steps: 0, skipped candidates: none.

| Commit | Date | Subject | PR | Files changed |
|---|---|---|---|---|
| [48e6b92cc3](https://github.com/ggml-org/llama.cpp/commit/48e6b92cc378c937e59719f2c0f482bf76c9ca81) | 2024-06-25 | Add chat template support for llama-cli (#8068) | [#8068](https://github.com/ggml-org/llama.cpp/pull/8068) | 7 |
| [3791ad2193](https://github.com/ggml-org/llama.cpp/commit/3791ad219323389106dc3fd80814eb5bbb7b80de) | 2024-06-25 | SimpleChat v3.1: Boolean chat request options in Settings UI, cache_prompt (#7950) | [#7950](https://github.com/ggml-org/llama.cpp/pull/7950) | 3 |
| [f702a90e24](https://github.com/ggml-org/llama.cpp/commit/f702a90e245499283d6de0b287701c723cda2a87) | 2024-06-25 | Update control vector help (#8104) | [#8104](https://github.com/ggml-org/llama.cpp/pull/8104) | 1 |
| [083bacce14](https://github.com/ggml-org/llama.cpp/commit/083bacce14c1aaf9976aa40e8266cdc25ac749d3) | 2024-06-25 | [SYCL] Re-enabled mul_mat_batched_sycl (#8095) | [#8095](https://github.com/ggml-org/llama.cpp/pull/8095) | 1 |
| [2df373ac40](https://github.com/ggml-org/llama.cpp/commit/2df373ac40ea581ccca8a58c713f03ad9d4b658d) | 2024-06-25 | CUDA: fix matrix multiplication algorithm choice (#8102) | [#8102](https://github.com/ggml-org/llama.cpp/pull/8102) | 1 |
| [3b099bcd9c](https://github.com/ggml-org/llama.cpp/commit/3b099bcd9cbf2434f90cbe40eba6fa2189ed1d02) | 2024-06-24 | CUDA: fix MMQ writeback for int8 tensor cores (#8100) | [#8100](https://github.com/ggml-org/llama.cpp/pull/8100) | 1 |
| [a818f3028d](https://github.com/ggml-org/llama.cpp/commit/a818f3028d1497a51cb2b8eb7d993ad58784940e) | 2024-06-24 | CUDA: use MMQ instead of cuBLAS by default (#8075) | [#8075](https://github.com/ggml-org/llama.cpp/pull/8075) | 8 |
| [d62e4aaa02](https://github.com/ggml-org/llama.cpp/commit/d62e4aaa02540c89be8b59426340b909d02bbc9e) | 2024-06-24 | gguf-py : fix tensor groups for encoder-decoder models in gguf-dump.py (#8090) | [#8090](https://github.com/ggml-org/llama.cpp/pull/8090) | 1 |
| [9a590c8226](https://github.com/ggml-org/llama.cpp/commit/9a590c82262dd518137f85406e65e452fdf2aca3) | 2024-06-24 | CUDA: optimize MMQ int8 tensor core performance (#8062) | [#8062](https://github.com/ggml-org/llama.cpp/pull/8062) | 3 |
| [52fc8705a0](https://github.com/ggml-org/llama.cpp/commit/52fc8705a0617452df08333e1161838726c322b4) | 2024-06-24 | Option to split during conversion (#6942) | [#6942](https://github.com/ggml-org/llama.cpp/pull/6942) | 3 |
| [8cb508d0d5](https://github.com/ggml-org/llama.cpp/commit/8cb508d0d5c024e12692370d85237b45469a004b) | 2024-06-24 | disable publishing the full-rocm docker image (#8083) | [#8083](https://github.com/ggml-org/llama.cpp/pull/8083) | 1 |
| [646ef4a9cf](https://github.com/ggml-org/llama.cpp/commit/646ef4a9cfb6f40236d3b9ef07ac03700b6efcc7) | 2024-06-24 | embedding : more cli arguments (#7458) | [#7458](https://github.com/ggml-org/llama.cpp/pull/7458) | 4 |
| [de0d6a68ac](https://github.com/ggml-org/llama.cpp/commit/de0d6a68ac99f307fe889c48e21124bc3b7ca29a) | 2024-06-24 | gguf-py, convert-hf : model conversion support for T5 and FLAN-T5 model variants (#5763) | [#5763](https://github.com/ggml-org/llama.cpp/pull/5763) | 4 |
| [95f57bb5d5](https://github.com/ggml-org/llama.cpp/commit/95f57bb5d5b18ef0beb2702a0d6c06e46804075c) | 2024-06-24 | ggml : remove ggml_task_type and GGML_PERF (#8017) | [#8017](https://github.com/ggml-org/llama.cpp/pull/8017) | 8 |
| [e112b610a1](https://github.com/ggml-org/llama.cpp/commit/e112b610a1a75cb7fa8351e1a933e2e7a755a5ce) | 2024-06-23 | llama : add support for BitnetForCausalLM (#7931) | [#7931](https://github.com/ggml-org/llama.cpp/pull/7931) | 4 |
| [6a2f298bd7](https://github.com/ggml-org/llama.cpp/commit/6a2f298bd784403c5c33eebb822217ec5d9b5590) | 2024-06-23 | server : fix JSON-Scheme typo (#7975) | [#7975](https://github.com/ggml-org/llama.cpp/pull/7975) | 1 |
| [11318d9aa1](https://github.com/ggml-org/llama.cpp/commit/11318d9aa1f668aa10407a5cb9614371af32f3ce) | 2024-06-23 | Fix typo in llama_set_embeddings comment (#8077) | [#8077](https://github.com/ggml-org/llama.cpp/pull/8077) | 1 |
| [b6b9a8e606](https://github.com/ggml-org/llama.cpp/commit/b6b9a8e606da7764bd3649c2ea574979c85abd43) | 2024-06-23 | fix CI failures (#8066) | [#8066](https://github.com/ggml-org/llama.cpp/pull/8066) | 2 |
| [45c0e2e4c1](https://github.com/ggml-org/llama.cpp/commit/45c0e2e4c1268c2d7c8c45536f15e3c9a731ecdc) | 2024-06-23 | Refactor Vulkan backend to allow multiple contexts (#7961) | [#7961](https://github.com/ggml-org/llama.cpp/pull/7961) | 8 |
| [b5a5f34efa](https://github.com/ggml-org/llama.cpp/commit/b5a5f34efadec8d8f0057b35cb04742abfeb2ef5) | 2024-06-22 | Removing extra blank lines that were breaking Lint. (#8067) | [#8067](https://github.com/ggml-org/llama.cpp/pull/8067) | 1 |
| [3e58b0ee35](https://github.com/ggml-org/llama.cpp/commit/3e58b0ee355f78be41cf5211b68426761339bc3c) | 2024-06-22 | cvector: fix CI + correct help message (#8064) | [#8064](https://github.com/ggml-org/llama.cpp/pull/8064) | 4 |
| [adf480c3ab](https://github.com/ggml-org/llama.cpp/commit/adf480c3ab3abedc964c8ae381476257583ae134) | 2024-06-22 | cvector-generator: Moe Moe Fixie-Fixie for Lots of Formats~! ♡(ᐢ ᴥ ᐢ)♡ (#8052) | [#8052](https://github.com/ggml-org/llama.cpp/pull/8052) | 3 |
| [3aa184a8c7](https://github.com/ggml-org/llama.cpp/commit/3aa184a8c7c553b5dfcc142d919f3db695df297a) | 2024-06-22 | convert-hf : change assert to exception (#8015) | [#8015](https://github.com/ggml-org/llama.cpp/pull/8015) | 1 |
| [5b48cd53a8](https://github.com/ggml-org/llama.cpp/commit/5b48cd53a87928db0c6447f0c9dac4db5802102d) | 2024-06-22 | Update llama-quantize ppl/file size output from LLaMA-v1 to Llama-3 values (#8058) | [#8058](https://github.com/ggml-org/llama.cpp/pull/8058) | 1 |
| [c5a8d4b749](https://github.com/ggml-org/llama.cpp/commit/c5a8d4b749352645afd4c024f85d6eca2ca72c6d) | 2024-06-21 | JSON Schema to GBNF integration tests (#7790) | [#7790](https://github.com/ggml-org/llama.cpp/pull/7790) | 2 |
| [557b653dc9](https://github.com/ggml-org/llama.cpp/commit/557b653dc9ed91e8c313e87500e0050c775f81b6) | 2024-06-21 | vulkan: detect multiple devices by deviceUUID instead of deviceID (#8022) | [#8022](https://github.com/ggml-org/llama.cpp/pull/8022) | 1 |
| [7d5e8777ae](https://github.com/ggml-org/llama.cpp/commit/7d5e8777ae1d21af99d4f95be10db4870720da91) | 2024-06-21 | ggml : AVX IQ quants (#7845) | [#7845](https://github.com/ggml-org/llama.cpp/pull/7845) | 1 |
| [a927b0f3dd](https://github.com/ggml-org/llama.cpp/commit/a927b0f3dd9a86ee042cd2bdcc8c9da4a855926b) | 2024-06-21 | llama : optimize long word tokenization with WPM (#8034) | [#8034](https://github.com/ggml-org/llama.cpp/pull/8034) | 2 |
| [80ea089d77](https://github.com/ggml-org/llama.cpp/commit/80ea089d771f0c2d97afa8bead80ded412f600d7) | 2024-06-21 | llama : allow pooled embeddings on any model (#7477) | [#7477](https://github.com/ggml-org/llama.cpp/pull/7477) | 6 |
| [0e64591e82](https://github.com/ggml-org/llama.cpp/commit/0e64591e8290037db6412665a56354b789a0597e) | 2024-06-21 | swiftui : enable stream updating (#7754) | [#7754](https://github.com/ggml-org/llama.cpp/pull/7754) | 1 |
| [b1ef562bc1](https://github.com/ggml-org/llama.cpp/commit/b1ef562bc17fbf8ba436ddf2d89b78efd10d3e03) | 2024-06-20 | requirements : Bump torch and numpy for python3.12 (#8041) | [#8041](https://github.com/ggml-org/llama.cpp/pull/8041) | 3 |
| [17b291a6a5](https://github.com/ggml-org/llama.cpp/commit/17b291a6a581c47f24f99bad926b42617894f99f) | 2024-06-20 | convert-hf : Fix the encoding in the convert-hf-to-gguf-update.py (#8040) | [#8040](https://github.com/ggml-org/llama.cpp/pull/8040) | 1 |
| [abd894ad96](https://github.com/ggml-org/llama.cpp/commit/abd894ad96a242043b8e197ec130d8649eead22e) | 2024-06-20 | common: fix warning (#8036) | [#8036](https://github.com/ggml-org/llama.cpp/pull/8036) | 1 |
| [de391e4c80](https://github.com/ggml-org/llama.cpp/commit/de391e4c803383bbea054b6edd016e78c024a74d) | 2024-06-20 | [SYCL] Fix windows build and inference (#8003) | [#8003](https://github.com/ggml-org/llama.cpp/pull/8003) | 7 |
| [d50f8897a7](https://github.com/ggml-org/llama.cpp/commit/d50f8897a797a5a03f31228d1b5a7b8130ee1bc2) | 2024-06-20 | CUDA: stream-k decomposition for MMQ (#8018) | [#8018](https://github.com/ggml-org/llama.cpp/pull/8018) | 4 |
| [2075a66a96](https://github.com/ggml-org/llama.cpp/commit/2075a66a96cc1b04eabec7cf4b3051193d6f719e) | 2024-06-20 | metal : fix `ggml_metal_supports_op` for BF16 (#8021) | [#8021](https://github.com/ggml-org/llama.cpp/pull/8021) | 1 |
| [ba58993152](https://github.com/ggml-org/llama.cpp/commit/ba5899315283eb1df3902363daf79bdc5eefe426) | 2024-06-20 | server : fix smart slot selection (#8020) | [#8020](https://github.com/ggml-org/llama.cpp/pull/8020) | 1 |
| [a7854743c5](https://github.com/ggml-org/llama.cpp/commit/a7854743c5e6216a6178824a603aa9479728ddd5) | 2024-06-19 | un-ignore `build-info.cmake` and `build-info.sh` (#7996) | [#7996](https://github.com/ggml-org/llama.cpp/pull/7996) | 1 |
| [9c77ec1d74](https://github.com/ggml-org/llama.cpp/commit/9c77ec1d74874ee22bdef8f110e8e8d41389abf2) | 2024-06-19 | ggml : synchronize threads using barriers (#7993) | [#7993](https://github.com/ggml-org/llama.cpp/pull/7993) | 2 |
| [a04a953cab](https://github.com/ggml-org/llama.cpp/commit/a04a953cab583f0229e7b4b506346e3e9a85c8d0) | 2024-06-19 | codecov : remove (#8004) | [#8004](https://github.com/ggml-org/llama.cpp/pull/8004) | 3 |
| [623494a478](https://github.com/ggml-org/llama.cpp/commit/623494a478134432fd2d7ee40135770a3340674f) | 2024-06-19 | [SYCL] refactor (#6408) | [#6408](https://github.com/ggml-org/llama.cpp/pull/6408) | 13 |
| [37bef89433](https://github.com/ggml-org/llama.cpp/commit/37bef8943312d91183ff06d8f1214082a17344a5) | 2024-06-18 | tokenizer : BPE fixes (#7530) | [#7530](https://github.com/ggml-org/llama.cpp/pull/7530) | 5 |
| [91c188d6c2](https://github.com/ggml-org/llama.cpp/commit/91c188d6c296bd3384f2a02a83b71187aa3d18b3) | 2024-06-18 | Only use FIM middle token if it exists (#7648) | [#7648](https://github.com/ggml-org/llama.cpp/pull/7648) | 2 |
| [84f6de17f6](https://github.com/ggml-org/llama.cpp/commit/84f6de17f6a8602e7ff7f7c7bda36a73f510a2dd) | 2024-06-18 | Fix no gcc pragma on Windows (#7751) | [#7751](https://github.com/ggml-org/llama.cpp/pull/7751) | 1 |
| [61665277af](https://github.com/ggml-org/llama.cpp/commit/61665277afde2add00c0d387acb94ed5feb95917) | 2024-06-18 | Allow compiling with CUDA without CUDA runtime installed (#7989) | [#7989](https://github.com/ggml-org/llama.cpp/pull/7989) | 1 |
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
(another 32 commits are in result.json)

