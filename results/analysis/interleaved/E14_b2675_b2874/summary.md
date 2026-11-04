# E14: b2675 → b2874 (step-1 class C)

Event verdict: **A**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| tinyllama-1.1b/metal/pp512 | b2675→b2761 | +77.8% | -0.0% (38.0%, ++-) | +2.6% (60.5%) | +67.6%/-3.3% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b2675→b2761 | +9.0% | +0.5% (13.8%, ++-) | +4.5% (18.6%) | +42.7%/+36.9% | info |
| qwen2.5-1.5b/cpu/pp512 | b2675→b2874 | -16.5% | -2.0% (57.6%, --+) | +12.4% (11.5%) | -15.7%/+13.5% | noise |
| qwen2.5-1.5b/cpu/tg128 | b2675→b2874 | -25.1% | -10.7% (69.6%, --+) | +15.4% (10.0%) | -17.7%/+26.7% | noise |
| qwen2.5-1.5b/metal/pp512 | b2675→b2874 | -50.3% | +5.6% (29.3%, +++) | +3.6% (35.7%) | -40.1%/+24.8% | noise |
| qwen2.5-1.5b/metal/tg128 (not listed) | b2675→b2874 | +13.4% | +4.9% (25.5%, +++) | +5.2% (24.1%) | +34.5%/+24.7% | info |
| mistral-7b/cpu/pp512 | b2761→b2874 | -11.2% | -3.4% (14.5%, --+) | -3.2% (18.3%) | +2.5%/+11.7% | noise |
| mistral-7b/cpu/tg128 (not listed) | b2761→b2874 | -7.7% | +3.5% (19.6%, -+-) | -17.4% (117.1%) | +10.9%/-0.7% | info |
| tinyllama-1.1b/cpu/pp512 | b2761→b2874 | +28.5% | +3.7% (15.1%, +++) | +7.3% (10.0%) | -0.3%/-16.7% | noise |
| tinyllama-1.1b/cpu/tg128 | b2761→b2874 | +38.3% | +5.1% (16.8%, +++) | +11.4% (10.0%) | +10.5%/-11.0% | A |
| tinyllama-1.1b/metal/pp512 | b2761→b2874 | -43.0% | -1.7% (19.4%, ---) | +1.6% (26.1%) | -28.0%/+28.2% | noise |
| tinyllama-1.1b/metal/tg128 (not listed) | b2761→b2874 | -0.9% | +3.4% (27.2%, +++) | +5.2% (35.8%) | +12.5%/+19.4% | info |

Omissions in the fixed configuration:

- A=b2675: -fa not supported and omitted (equivalent: this release has no flash attention)
- A=b2675: -pg not supported and omitted (equivalent: this release has no combined -pg test)
- A=b2761: -fa not supported and omitted (equivalent: this release has no flash attention)
- A=b2761: -pg not supported and omitted (equivalent: this release has no combined -pg test)

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
