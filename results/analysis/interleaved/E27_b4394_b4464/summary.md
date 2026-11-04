# E27: b4394 → b4464 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b4394→b4464 | -29.6% | -6.8% (40.9%, --+) | -0.2% (13.1%) | -29.5%/-0.2% | noise |
| mistral-7b/metal/tg128 | b4394→b4464 | -22.4% | -4.6% (28.9%, -++) | -0.7% (11.2%) | -25.5%/-4.7% | noise |
| qwen2.5-1.5b/cpu/pp512 (not listed) | b4394→b4464 | +8.7% | +1.8% (16.2%, +--) | +6.8% (10.0%) | +26.5%/+24.3% | info |
| qwen2.5-1.5b/cpu/tg128 | b4394→b4464 | +30.4% | +0.6% (10.0%, +--) | +2.6% (10.0%) | +54.9%/+21.8% | noise |
| tinyllama-1.1b/cpu/pp512 | b4394→b4464 | -16.8% | -2.1% (11.7%, -+-) | +6.3% (10.0%) | -5.1%/+21.3% | noise |
| tinyllama-1.1b/cpu/tg128 | b4394→b4464 | -22.9% | -0.4% (15.0%, -++) | +8.3% (11.6%) | -8.5%/+28.5% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
