# E24: b3996 → b4080 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 (not listed) | b3996→b4080 | -21.8% | -8.0% (50.3%, --+) | +1.4% (20.2%) | -21.8%/+1.4% | info |
| mistral-7b/metal/tg128 | b3996→b4080 | -20.3% | -8.9% (33.0%, --+) | -0.9% (10.0%) | -18.5%/+1.3% | noise |
| qwen2.5-1.5b/cpu/pp512 (not listed) | b3996→b4080 | -3.1% | +4.1% (27.3%, ++-) | +6.5% (10.0%) | +9.0%/+19.8% | info |
| qwen2.5-1.5b/cpu/tg128 | b3996→b4080 | +30.2% | +1.3% (10.0%, +-+) | +2.4% (10.0%) | +35.5%/+6.5% | noise |
| tinyllama-1.1b/cpu/pp512 | b3996→b4080 | -21.5% | -0.7% (10.9%, ---) | +5.2% (10.0%) | +5.8%/+41.8% | noise |
| tinyllama-1.1b/cpu/tg128 | b3996→b4080 | -30.0% | -0.1% (16.2%, -+-) | +7.8% (13.1%) | +9.7%/+69.0% | noise |
| tinyllama-1.1b/metal/pp512 | b3996→b4080 | -42.9% | +2.3% (28.7%, +-+) | +5.6% (39.0%) | -27.2%/+34.5% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b3996→b4080 | -8.9% | -0.2% (21.3%, +--) | +3.1% (33.3%) | +21.4%/+37.3% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
