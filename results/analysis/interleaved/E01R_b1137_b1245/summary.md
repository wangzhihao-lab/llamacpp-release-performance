# E01R: b1137 → b1245 (step-1 class C)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b1137→b1245 | -24.6% | -22.4% (16.9%, ---) | -21.4% (10.0%) | -7.6%/-3.6% | C |
| mistral-7b/cpu/tg128 (not listed) | b1137→b1245 | +9.1% | -4.7% (10.5%, ---) | -3.5% (10.0%) | +32.7%/+17.4% | info |
| mistral-7b/metal/pp512 (not listed) | b1137→b1245 | +8.9% | +48.4% (10.0%, +++) | +47.0% (10.0%) | -19.6%/+8.6% | info |
| mistral-7b/metal/tg128 | b1137→b1245 | -23.2% | +1.7% (10.0%, +++) | +0.4% (10.0%) | -10.8%/+16.7% | noise |
| tinyllama-1.1b/cpu/pp512 (not listed) | b1137→b1245 | -6.1% | -12.9% (63.5%, +--) | -8.0% (80.2%) | +2.5%/+0.5% | info |
| tinyllama-1.1b/cpu/tg128 | b1137→b1245 | -50.3% | -0.5% (17.5%, +--) | +7.6% (17.5%) | -18.6%/+76.5% | noise |
| tinyllama-1.1b/metal/pp512 | b1137→b1245 | +150.9% | +158.3% (10.0%, +++) | +159.8% (10.0%) | -2.6%/+0.8% | C |
| tinyllama-1.1b/metal/tg128 (not listed) | b1137→b1245 | -26.1% | +1.9% (10.0%, +++) | +2.5% (10.0%) | +3.2%/+43.2% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
