# E06: b1697 → b1778 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b1697→b1778 | -19.6% | -8.1% (69.8%, -++) | -2.5% (14.9%) | -37.9%/-24.7% | noise |
| mistral-7b/metal/tg128 | b1697→b1778 | -15.9% | -10.8% (52.1%, --+) | -5.2% (10.0%) | -30.1%/-21.2% | noise |
| tinyllama-1.1b/cpu/pp512 (not listed) | b1697→b1778 | -20.0% | +4.5% (35.6%, +++) | +17.3% (64.6%) | -26.4%/+7.8% | info |
| tinyllama-1.1b/cpu/tg128 | b1697→b1778 | -42.1% | +4.1% (16.9%, +++) | +8.7% (10.0%) | -22.9%/+44.7% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
