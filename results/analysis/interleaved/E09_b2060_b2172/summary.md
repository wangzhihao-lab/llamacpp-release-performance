# E09: b2060 → b2172 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b2060→b2172 | +18.6% | +2.4% (28.7%, --+) | -2.2% (10.0%) | +46.2%/+20.6% | noise |
| mistral-7b/cpu/tg128 (not listed) | b2060→b2172 | +43.9% | +2.0% (26.0%, +++) | -0.4% (10.0%) | +78.4%/+23.5% | info |
| mistral-7b/metal/pp512 | b2060→b2172 | +16.9% | -0.5% (10.0%, -++) | +0.1% (10.0%) | +67.6%/+43.5% | noise |
| mistral-7b/metal/tg128 (not listed) | b2060→b2172 | +8.6% | +0.2% (10.0%, -++) | +0.7% (11.1%) | +57.0%/+45.7% | info |
| qwen2.5-1.5b/metal/pp512 | b2060→b2172 | -49.5% | +1.2% (34.2%, +-+) | +3.5% (36.7%) | -4.1%/+96.5% | noise |
| qwen2.5-1.5b/metal/tg128 (not listed) | b2060→b2172 | +12.7% | +0.7% (15.8%, +-+) | +2.2% (10.0%) | +91.6%/+73.7% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
