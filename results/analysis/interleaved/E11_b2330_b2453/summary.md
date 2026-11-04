# E11: b2330 → b2453 (step-1 class D)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b2330→b2453 | +20.4% | +3.0% (20.5%, ++-) | -0.1% (10.0%) | +35.3%/+12.3% | noise |
| mistral-7b/cpu/tg128 (not listed) | b2330→b2453 | +23.4% | +0.3% (63.0%, +--) | -3.0% (11.4%) | +61.3%/+26.7% | info |
| qwen2.5-1.5b/cpu/pp512 (not listed) | b2330→b2453 | -5.0% | +1.3% (33.3%, -+-) | +9.2% (30.7%) | +10.0%/+26.5% | info |
| qwen2.5-1.5b/cpu/tg128 | b2330→b2453 | -9.9% | +5.9% (58.6%, +++) | +11.8% (26.1%) | +7.9%/+33.9% | noise |

Omissions in the fixed configuration:

- A=b2330: -ub not supported and omitted (equivalent: no ubatch; the whole batch of 512 is processed at once)

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
