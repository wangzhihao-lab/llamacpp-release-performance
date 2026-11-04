# VE04: b1561 → b1621 (step-1 class V)

Event verdict: **incomplete**

| Series | A→B | Step-1 Δ | Fixed-phase Δ (τ, round signs) | Default-phase Δ (τ) | Reproduction deviation A/B | Verdict |
|---|---|---|---|---|---|---|
| qwen2.5-1.5b/cpu/pp512 | b1561→b1621 | +0.0% | n/a | n/a | n/a | incomplete |
| qwen2.5-1.5b/cpu/tg128 | b1561→b1621 | +0.0% | n/a | n/a | n/a | incomplete |
| qwen2.5-1.5b/metal/pp512 | b1561→b1621 | +0.0% | n/a | n/a | n/a | incomplete |
| qwen2.5-1.5b/metal/tg128 | b1561→b1621 | +0.0% | n/a | n/a | n/a | incomplete |
| tinyllama-1.1b/metal/pp512 | b1561→b1621 | +11.3% | +7.1% (10.0%, +++) | +7.1% (10.0%) | +5.6%/+1.6% | noise |
| tinyllama-1.1b/metal/tg128 | b1561→b1621 | +25.2% | -0.6% (10.0%, ---) | -0.7% (10.0%) | +55.0%/+22.9% | noise |

Omissions in the fixed configuration:

- A=b1561: -ctk/-ctv not supported and omitted (equivalent: f16_kv defaults to true)

Reproduction deviation = mean of the default-phase re-runs / original campaign value − 1 (a large deviation means that the time of the original measurement affected it). Runs started without a quiet machine after the full wait (CPU idle share below the threshold or another llama process running): 0 (load_settled=0 in runs.tsv).
