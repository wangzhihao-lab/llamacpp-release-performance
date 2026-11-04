# E50: b8916 → b9076 (step-1 class C)

Event verdict: **A**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b8916→b9076 | +38.8% | +32.4% (86.4%, +++) | +29.8% (13.7%) | -29.8%/-34.4% | A |
| mistral-7b/metal/tg128 (not listed) | b8916→b9076 | -1.5% | -7.6% (48.8%, -+-) | -3.2% (10.0%) | -15.9%/-17.3% | info |
| tinyllama-1.1b/cpu/pp512 | b8916→b9076 | +28.6% | +1.3% (10.0%, +-+) | +5.3% (10.0%) | -7.9%/-24.6% | noise |
| tinyllama-1.1b/cpu/tg128 | b8916→b9076 | +83.0% | +2.1% (10.0%, +++) | +7.6% (13.4%) | -2.8%/-42.8% | noise |
| tinyllama-1.1b/metal/pp512 | b8916→b9076 | +67.2% | +38.2% (52.9%, +++) | +39.5% (32.7%) | +20.2%/+0.2% | A |
| tinyllama-1.1b/metal/tg128 | b8916→b9076 | +51.8% | +0.6% (20.6%, +-+) | +2.1% (13.7%) | +30.6%/-12.1% | noise |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
