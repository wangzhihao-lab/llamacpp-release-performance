# E04: b1561 → b1621 (step-1 class C)

Event verdict: **C**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| mistral-7b/cpu/pp512 | b1561→b1621 | +244.2% | +175.1% (64.6%, +++) | +272.1% (27.5%) | -8.5%/-1.1% | C |
| mistral-7b/cpu/tg128 | b1561→b1621 | +20.5% | +14.6% (18.5%, +++) | +0.9% (49.1%) | +13.6%/-4.9% | noise |
| mistral-7b/metal/pp512 | b1561→b1621 | +12.5% | +2.3% (21.8%, +-+) | -2.0% (17.1%) | -19.7%/-30.0% | noise |
| mistral-7b/metal/tg128 (not listed) | b1561→b1621 | +11.0% | -0.3% (10.0%, +--) | -1.2% (10.0%) | -4.5%/-15.0% | info |
| tinyllama-1.1b/cpu/pp512 | b1561→b1621 | +227.1% | +198.2% (29.6%, +++) | +221.4% (26.5%) | -3.8%/-5.5% | C |
| tinyllama-1.1b/cpu/tg128 (not listed) | b1561→b1621 | +15.8% | +8.2% (17.6%, +++) | +5.7% (10.8%) | +11.2%/+1.4% | info |

Omissions in the fixed configuration:

- A=b1561: -ctk/-ctv not supported and omitted (equivalent: f16_kv defaults to true)

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
