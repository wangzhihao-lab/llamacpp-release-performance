# E45: b6948 → b7100 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b6948→b7100 | +10.8% | -2.8% (13.9%, -++) | -0.1% (10.0%) | +11.4%/+0.5% | noise |
| mistral-7b/cpu/tg128 (not listed) | b6948→b7100 | +8.2% | -5.6% (13.5%, ---) | -5.4% (10.5%) | +24.8%/+9.1% | info |
| tinyllama-1.1b/cpu/pp512 (not listed) | b6948→b7100 | +7.3% | +1.1% (13.3%, +-+) | +0.9% (10.0%) | +33.2%/+25.3% | info |
| tinyllama-1.1b/cpu/tg128 | b6948→b7100 | +27.6% | +1.3% (25.7%, +-+) | +5.4% (10.0%) | +100.4%/+65.6% | noise |
| tinyllama-1.1b/metal/pp512 | b6948→b7100 | -23.7% | -0.5% (10.0%, ---) | -0.3% (10.0%) | +0.3%/+31.0% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b6948→b7100 | -10.4% | -4.2% (10.0%, ---) | -3.7% (10.0%) | +28.1%/+37.7% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
