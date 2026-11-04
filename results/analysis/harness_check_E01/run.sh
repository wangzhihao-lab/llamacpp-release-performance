#!/bin/bash
# E01 harness check (2026-10-26): does adding -n 128 change pp512 of b1245 vs b1137 on mistral-7b CPU?
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT" || exit 1
O=results/analysis/harness_check_E01
M="${MODELS_DIR:-$ROOT/models}/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
for r in 1 2; do
  if [ $r = 1 ]; then order="b1137:128 b1245:128 b1245:0 b1137:0"; else order="b1137:0 b1245:0 b1245:128 b1137:128"; fi
  for it in warm $order; do
    if [ $it = warm ]; then t=b1137; n=128; stem=warm_r$r; else t=${it%%:*}; n=${it##*:}; stem=r${r}_${t}_n${n}; fi
    echo "$(date -u +%H:%M:%S) start $stem" >> $O/log.txt
    /usr/bin/arch -arm64 bins/$t/llama-bench -m "$M" -p 512 -n $n -r 5 -o json -ngl 0 -t 8 -b 512 > $O/$stem.json 2> $O/$stem.err
    echo "$(date -u +%H:%M:%S) end $stem rc=$?" >> $O/log.txt
    sleep 20
  done
done
echo done >> $O/log.txt
