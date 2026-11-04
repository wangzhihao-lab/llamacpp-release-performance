# E26: b4318 → b4394 (step-1 class C)

Event verdict: **A**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/cpu/pp512 | b4318→b4394 | -15.6% | +0.5% (53.9%, -++) | +10.0% (10.0%) | +2.0%/+33.0% | noise |
| qwen2.5-1.5b/cpu/tg128 | b4318→b4394 | -33.3% | -9.2% (55.9%, -++) | +4.3% (10.0%) | +1.2%/+58.2% | noise |
| tinyllama-1.1b/cpu/pp512 | b4318→b4394 | +18.5% | +1.6% (18.8%, -++) | +11.7% (10.0%) | +6.8%/+0.6% | A |
| tinyllama-1.1b/cpu/tg128 | b4318→b4394 | +20.7% | +0.6% (14.5%, -++) | +8.7% (13.0%) | +9.7%/-1.2% | noise |
| tinyllama-1.1b/metal/pp512 | b4318→b4394 | -27.7% | +1.0% (33.1%, +--) | +4.1% (56.8%) | -24.1%/+9.4% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b4318→b4394 | +2.7% | +0.6% (26.3%, +-+) | +3.2% (29.2%) | +25.0%/+25.7% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
