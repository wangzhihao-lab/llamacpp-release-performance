# E34: b5056 → b5159 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 | b5056→b5159 | -12.5% | +0.4% (19.5%, -++) | +16.3% (10.0%) | +1.5%/+34.8% | noise |
| tinyllama-1.1b/cpu/tg128 (not listed) | b5056→b5159 | +5.4% | -10.0% (43.9%, -+-) | +9.3% (20.9%) | +31.8%/+36.6% | info |
| tinyllama-1.1b/metal/pp512 | b5056→b5159 | +33.8% | -0.3% (13.0%, +--) | +0.1% (10.0%) | +33.5%/-0.1% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b5056→b5159 | -3.2% | -1.3% (10.0%, +--) | -5.0% (10.0%) | +25.7%/+23.3% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
