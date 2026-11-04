# E38: b5672 → b5782 (step-1 class C)

Event verdict: **A**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/cpu/pp512 | b5672→b5782 | +18.0% | +2.2% (19.1%, +-+) | +15.3% (10.0%) | +5.3%/+2.9% | A |
| qwen2.5-1.5b/cpu/tg128 (not listed) | b5672→b5782 | +2.5% | -0.9% (10.0%, -++) | +3.2% (10.0%) | -1.1%/-0.4% | info |
| tinyllama-1.1b/metal/pp512 | b5672→b5782 | +41.3% | +2.2% (32.2%, +-+) | +0.8% (10.0%) | +40.8%/+0.4% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b5672→b5782 | -4.5% | +0.7% (23.1%, +--) | +0.2% (10.0%) | +30.7%/+37.1% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
