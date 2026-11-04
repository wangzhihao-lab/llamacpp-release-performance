# E46: b7100 → b7245 (step-1 class C)

Event verdict: **A**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b7100→b7245 | -17.2% | -22.4% (36.0%, ---) | -23.6% (10.0%) | -3.8%/-11.3% | A |
| mistral-7b/cpu/tg128 (not listed) | b7100→b7245 | -8.7% | -10.5% (31.7%, ---) | -6.1% (24.7%) | -11.2%/-8.6% | info |
| mistral-7b/metal/pp512 | b7100→b7245 | +11.3% | +1.7% (10.3%, +++) | -0.9% (10.0%) | -4.7%/-15.2% | noise |
| mistral-7b/metal/tg128 | b7100→b7245 | +16.8% | +5.1% (15.4%, +++) | -2.0% (13.3%) | +1.9%/-14.5% | noise |
| tinyllama-1.1b/cpu/pp512 | b7100→b7245 | +23.4% | +2.4% (18.3%, +-+) | +9.7% (10.4%) | +8.5%/-3.5% | noise |
| tinyllama-1.1b/cpu/tg128 | b7100→b7245 | +37.7% | -1.7% (26.7%, +--) | +11.1% (13.3%) | +21.4%/-2.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
