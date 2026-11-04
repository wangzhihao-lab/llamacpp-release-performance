# E28: b4464 → b4545 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b4464→b4545 | +10.9% | -13.4% (30.6%, ---) | +6.5% (10.0%) | -7.9%/-11.5% | noise |
| mistral-7b/cpu/tg128 | b4464→b4545 | +25.5% | -13.9% (58.1%, ---) | +3.4% (41.0%) | -9.2%/-25.2% | noise |
| mistral-7b/metal/pp512 | b4464→b4545 | +31.5% | -4.3% (32.3%, ---) | -0.8% (13.3%) | +17.5%/-11.3% | noise |
| mistral-7b/metal/tg128 | b4464→b4545 | +17.4% | +2.0% (27.3%, +--) | +1.9% (11.8%) | +8.7%/-5.6% | noise |
| qwen2.5-1.5b/cpu/pp512 | b4464→b4545 | +11.7% | +1.2% (10.1%, +++) | +8.5% (10.0%) | +20.7%/+17.2% | noise |
| qwen2.5-1.5b/cpu/tg128 (not listed) | b4464→b4545 | +15.1% | +0.4% (10.0%, +--) | +3.8% (10.0%) | +13.6%/+2.5% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
