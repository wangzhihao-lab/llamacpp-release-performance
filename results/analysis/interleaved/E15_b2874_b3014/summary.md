# E15: b2874 → b3014 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b2874→b3014 | +20.5% | -0.5% (26.1%, +--) | +4.0% (10.0%) | +11.9%/-3.4% | noise |
| mistral-7b/cpu/tg128 (not listed) | b2874→b3014 | +15.6% | +8.7% (90.0%, +-+) | +10.3% (45.6%) | -0.3%/-4.9% | info |
| tinyllama-1.1b/cpu/pp512 | b2874→b3014 | -27.4% | +1.6% (37.7%, +-+) | +0.5% (23.6%) | +12.9%/+56.3% | noise |
| tinyllama-1.1b/cpu/tg128 | b2874→b3014 | -26.3% | +1.3% (63.5%, +-+) | +1.8% (10.0%) | +26.3%/+74.5% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
