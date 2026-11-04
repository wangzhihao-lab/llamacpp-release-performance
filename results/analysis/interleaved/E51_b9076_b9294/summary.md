# E51: b9076 → b9294 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/cpu/pp512 | b9076→b9294 | -21.8% | -0.1% (16.8%, -+-) | -10.3% (60.8%) | -15.7%/-3.4% | noise |
| tinyllama-1.1b/cpu/tg128 | b9076→b9294 | -45.0% | -1.7% (37.8%, -+-) | -27.1% (112.6%) | -32.2%/-10.2% | noise |
| tinyllama-1.1b/metal/pp512 (not listed) | b9076→b9294 | -20.5% | -4.1% (46.5%, ---) | -3.9% (10.0%) | -2.1%/+18.4% | info |
| tinyllama-1.1b/metal/tg128 | b9076→b9294 | -30.9% | +4.5% (15.9%, +++) | +6.4% (11.6%) | -8.8%/+40.4% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
