# E01: b1137 → b1245 (step-1 class C)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b1137→b1245 | -24.6% | -16.8% (11.8%, ---) | +21.9% (10.0%) | -24.7%/+21.8% | C |
| mistral-7b/cpu/tg128 (not listed) | b1137→b1245 | +9.1% | -10.3% (10.0%, ---) | -0.7% (24.1%) | +22.7%/+11.7% | info |
| mistral-7b/metal/pp512 (not listed) | b1137→b1245 | +8.9% | +41.2% (16.6%, +++) | +40.8% (10.0%) | -44.5%/-28.2% | info |
| mistral-7b/metal/tg128 | b1137→b1245 | -23.2% | +1.3% (11.3%, +-+) | +2.2% (10.0%) | -36.3%/-15.3% | noise |
| tinyllama-1.1b/cpu/pp512 (not listed) | b1137→b1245 | -6.1% | +6.2% (27.1%, +++) | +11.5% (31.2%) | -16.3%/-0.6% | info |
| tinyllama-1.1b/cpu/tg128 | b1137→b1245 | -50.3% | -1.5% (14.7%, +--) | +4.3% (13.6%) | -46.3%/+12.8% | noise |
| tinyllama-1.1b/metal/pp512 | b1137→b1245 | +150.9% | +141.3% (33.7%, +++) | +158.3% (53.3%) | -26.5%/-24.4% | C |
| tinyllama-1.1b/metal/tg128 (not listed) | b1137→b1245 | -26.1% | +0.7% (23.2%, ++-) | +4.2% (33.9%) | -15.8%/+18.7% | info |

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
