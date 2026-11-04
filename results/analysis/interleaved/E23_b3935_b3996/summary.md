# E23: b3935 → b3996 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b3935→b3996 | +13.4% | -5.9% (15.6%, --+) | +3.3% (10.0%) | +22.2%/+11.3% | noise |
| mistral-7b/cpu/tg128 (not listed) | b3935→b3996 | +7.1% | -4.3% (14.3%, ---) | -0.8% (10.1%) | +38.0%/+27.8% | info |
| mistral-7b/metal/pp512 (not listed) | b3935→b3996 | +18.4% | +0.7% (10.0%, ++-) | -0.3% (10.0%) | +43.3%/+20.7% | info |
| mistral-7b/metal/tg128 | b3935→b3996 | +18.3% | +0.6% (10.0%, ++-) | +2.0% (10.0%) | +46.5%/+26.4% | noise |
| tinyllama-1.1b/cpu/pp512 | b3935→b3996 | +14.4% | +0.4% (10.0%, +--) | -0.0% (10.0%) | +53.3%/+34.0% | noise |
| tinyllama-1.1b/cpu/tg128 (not listed) | b3935→b3996 | +9.1% | +1.3% (16.8%, +--) | +1.4% (18.1%) | +94.8%/+80.9% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
