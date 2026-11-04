# E03: b1505 → b1561 (step-1 class C)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b1505→b1561 | -69.4% | -68.2% (20.4%, ---) | -68.1% (14.2%) | +4.6%/+9.1% | C |
| mistral-7b/cpu/tg128 (not listed) | b1505→b1561 | -13.4% | -0.9% (12.6%, +--) | -4.6% (10.0%) | +7.1%/+18.0% | info |
| tinyllama-1.1b/cpu/pp512 | b1505→b1561 | -64.1% | -65.1% (30.7%, ---) | -64.4% (30.5%) | -6.0%/-6.6% | C |
| tinyllama-1.1b/cpu/tg128 (not listed) | b1505→b1561 | +9.9% | -6.4% (17.6%, +--) | +11.3% (10.2%) | +6.5%/+7.9% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
