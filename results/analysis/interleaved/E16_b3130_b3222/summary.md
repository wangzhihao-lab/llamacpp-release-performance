# E16: b3130 → b3222 (step-1 class C)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b3130→b3222 | +33.5% | +17.9% (30.4%, -++) | +30.7% (10.0%) | +24.2%/+21.5% | A |
| mistral-7b/cpu/tg128 (not listed) | b3130→b3222 | +11.4% | -4.5% (25.4%, -++) | +3.7% (14.0%) | +53.4%/+42.8% | info |
| mistral-7b/metal/pp512 | b3130→b3222 | +14.4% | +1.1% (10.0%, +--) | +1.2% (10.0%) | +41.0%/+24.7% | noise |
| mistral-7b/metal/tg128 (not listed) | b3130→b3222 | +2.0% | +1.1% (11.6%, +--) | +0.2% (10.0%) | +36.8%/+34.3% | info |
| qwen2.5-1.5b/cpu/pp512 | b3130→b3222 | +29.5% | +26.6% (11.3%, +++) | +29.3% (12.0%) | +49.5%/+49.3% | C |
| qwen2.5-1.5b/cpu/tg128 | b3130→b3222 | +14.8% | +2.1% (16.6%, +-+) | +11.0% (10.0%) | +68.4%/+62.9% | A |
| tinyllama-1.1b/cpu/pp512 | b3130→b3222 | +40.0% | +15.5% (10.0%, +++) | +14.2% (10.4%) | +62.0%/+32.1% | C |
| tinyllama-1.1b/cpu/tg128 (not listed) | b3130→b3222 | +10.8% | +1.3% (11.5%, +++) | +9.8% (14.3%) | +89.2%/+87.5% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
