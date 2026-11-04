# E25: b4080 → b4212 (step-1 class C)

Event verdict: **noise**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/metal/pp512 | b4080→b4212 | +27.7% | -10.5% (87.7%, ---) | -0.5% (15.6%) | +0.2%/-22.0% | noise |
| mistral-7b/metal/tg128 | b4080→b4212 | +17.8% | -15.6% (69.6%, ---) | +0.8% (10.0%) | +1.3%/-13.3% | noise |
| tinyllama-1.1b/cpu/pp512 (not listed) | b4080→b4212 | +11.8% | -8.9% (15.6%, ---) | -3.2% (10.0%) | +34.4%/+16.4% | info |
| tinyllama-1.1b/cpu/tg128 | b4080→b4212 | +39.5% | -2.1% (18.3%, +--) | +8.5% (13.5%) | +54.0%/+19.7% | noise |
| tinyllama-1.1b/metal/pp512 | b4080→b4212 | +77.6% | +0.6% (27.6%, +--) | +4.1% (42.4%) | +27.4%/-25.3% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b4080→b4212 | +7.5% | +3.6% (22.2%, +++) | +8.1% (30.5%) | +30.7%/+31.4% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
