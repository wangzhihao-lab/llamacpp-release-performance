#!/bin/bash
# continuous_chain.sh -- steps 2 and 3 back to back, day and night, until the queue is done.
#
# From 2026-10-14 the re-measurements and bisections ran as one continuous chain without a time
# window: every step2/step3 call gets --window 00:00-24:00 (no limit).
#
# 1. If AFTER_PID is set, first waits until that process has exited. Before every item it waits
#    while another step2/step3 instance holds its lock.
# 2. Live queue: before every item the queue file is read again and the first line whose name is
#    not yet in the done file runs, so lines can be appended, reordered or removed while the chain
#    runs (the running item is not affected). Tab separated: name, kind, arguments (split on
#    blanks, no quoting). Kinds:
#      step2             step2_interleaved.py ARGS --rounds 3 --default-rounds 1 --window 00:00-24:00
#      judge             step2b_judge.py ARGS
#      step3             step3_bisect.py ARGS --window 00:00-24:00
#      bisect_confirmed  one step3 --from-step2 EVENT --step2-rule v11 --series SERIES for every
#                        event the latest judgement confirms (confirmed_targets.py: the most
#                        reliable C series of each event, biggest change first); each event is
#                        recorded as NAME:EVENT
#      end               stop the chain
#    An item is recorded in the done file when it ends, whatever its rc (to rerun, use a new name).
#    step2 skips runs whose output is complete and step3 resumes from its state, so nothing is
#    measured twice. A failing item (e.g. step3 for an event step 2 did not confirm) is logged and
#    the queue goes on.
# 3. With nothing left, polls the queue every 5 minutes; exits after IDLE_EXIT_H hours.
# 4. Noise record: a sampler appends the CPU idle share and the top CPU processes to ACTIVITY_LOG
#    every 5 minutes, and every item start logs other heavy processes, so that noisy stretches
#    (the machine was also in daily use) can be flagged and attributed afterwards.
#
# results/analysis/chain_runs/ (the item logs, DONE_FILE and ACTIVITY_LOG) is created by this script.
#
# Environment: QUEUE (scripts/analysis/queues/continuous.tsv), DONE_FILE
# (results/analysis/chain_runs/continuous_done.txt), ACTIVITY_LOG
# (results/analysis/chain_runs/activity.log), SAMPLE_S (300), AFTER_PID, IDLE_EXIT_H (24), DRY_RUN (1: print the
# pending items and their commands, then exit).
#
# Run: nohup bash scripts/analysis/continuous_chain.sh > results/analysis/chain_continuous.log 2>&1 &

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1
QUEUE="${QUEUE:-scripts/analysis/queues/continuous.tsv}"
DONE_FILE="${DONE_FILE:-results/analysis/chain_runs/continuous_done.txt}"
ACTIVITY_LOG="${ACTIVITY_LOG:-results/analysis/chain_runs/activity.log}"
AFTER_PID="${AFTER_PID:-}"
IDLE_EXIT_H="${IDLE_EXIT_H:-24}"
SAMPLE_S="${SAMPLE_S:-300}"
DRY_RUN="${DRY_RUN:-0}"
WINDOW=00:00-24:00
LOCK2="$ROOT/results/analysis/interleaved/.step2.lock"
LOCK3="$ROOT/results/analysis/bisect/.step3.lock"
RUNLOG_DIR="$ROOT/results/analysis/chain_runs"
UVPY=(uv run --no-project --with pandas --with numpy python3 -I)
UVPLAIN=(uv run --no-project python3 -I)
NAME=""; KIND=""; ARGS=""

log() { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') $*"; }

lock_alive() {
  local pid
  [ -f "$1" ] || return 1
  pid="$(tr -dc '0-9' < "$1" 2> /dev/null)"
  [ -n "$pid" ] && kill -0 "$pid" 2> /dev/null
}

is_done() { [ -f "$DONE_FILE" ] && grep -qxF "$1" "$DONE_FILE"; }
mark_done() { echo "$1" >> "$DONE_FILE"; }

others_report() {
  local p
  p="$(pgrep -fl "llama-server|limactl|qemu-system|com.apple.Virtualization.VirtualMachine" | cut -c1-140 | tr '\n' ';')"
  [ -n "$p" ] && log "other heavy processes running: $p"
  return 0
}

# Prints the command of a step2/judge/step3 item, one word per line (bash 3.2: no namerefs).
item_command() {
  local kind="$1" args="$2"
  local -a extra=()
  read -r -a extra <<< "$args"
  case "$kind" in
    step2) printf '%s\n' "${UVPY[@]}" scripts/analysis/step2_interleaved.py ${extra[@]+"${extra[@]}"} \
             --rounds 3 --default-rounds 1 --window "$WINDOW" ;;
    judge) printf '%s\n' "${UVPY[@]}" scripts/analysis/step2b_judge.py ${extra[@]+"${extra[@]}"} ;;
    step3) printf '%s\n' "${UVPY[@]}" scripts/analysis/step3_bisect.py ${extra[@]+"${extra[@]}"} --window "$WINDOW" ;;
    *) return 1 ;;
  esac
}

# Sets NAME, KIND, ARGS to the first queue line not yet done; returns 1 if there is none.
next_item() {
  local name kind args
  NAME=""; KIND=""; ARGS=""
  [ -f "$QUEUE" ] || return 1
  while IFS=$'\t' read -r name kind args || [ -n "$name" ]; do
    case "$name" in '' | '#'*) continue ;; esac
    is_done "$name" && continue
    NAME="$name"; KIND="${kind:-}"; ARGS="${args:-}"
    return 0
  done < "$QUEUE"
  return 1
}

# run_cmd NAME WORD... : waits for the locks, runs the command (stdin closed), logs rc.
run_cmd() {
  local name="$1"; shift
  local runlog="$RUNLOG_DIR/continuous_${name//:/_}.log" rc
  if lock_alive "$LOCK2" || lock_alive "$LOCK3"; then log "another step2/step3 instance holds a lock; waiting before $name"; fi
  while lock_alive "$LOCK2" || lock_alive "$LOCK3"; do sleep 60; done
  others_report
  log "start $name: $* (log $runlog)"
  nice -n 5 "$@" < /dev/null >> "$runlog" 2>&1
  rc=$?
  log "end $name rc=$rc"
  return $rc
}

# Prints EVENT<TAB>SERIES lines of the confirmed events; returns 1 without a judge result.
confirmed_targets() { "${UVPLAIN[@]}" scripts/analysis/confirmed_targets.py 2>> "$RUNLOG_DIR/confirmed_targets.log"; }

run_bisect_confirmed() {
  local name="$1" targets ev series
  if ! targets="$(confirmed_targets)"; then log "$name: no judge result to read; skipped"; return 1; fi
  [ -n "$targets" ] || { log "$name: no confirmed events"; return 0; }
  log "$name: confirmed events: $(echo "$targets" | cut -f1 | tr '\n' ' ')"
  while IFS=$'\t' read -r ev series; do
    [ -n "$ev" ] || continue
    is_done "$name:$ev" && continue
    run_cmd "$name:$ev" "${UVPY[@]}" scripts/analysis/step3_bisect.py --from-step2 "$ev" --step2-rule v11 \
      --series "$series" --window "$WINDOW"
    mark_done "$name:$ev"
  done <<< "$targets"
}

mkdir -p "$RUNLOG_DIR"
log "chain start (pid $$), queue $QUEUE, done file $DONE_FILE, window $WINDOW (no limit)"

if [ "$DRY_RUN" = 1 ]; then
  while IFS=$'\t' read -r name kind args || [ -n "$name" ]; do
    case "$name" in '' | '#'*) continue ;; esac
    if is_done "$name"; then log "dry-run $name: done"; continue; fi
    case "${kind:-}" in
      end) log "dry-run $name: end of chain" ;;
      bisect_confirmed)
        if t="$(confirmed_targets)"; then log "dry-run $name: step3 for each confirmed event (event/series): $(echo "$t" | tr '\t\n' '/ ')"
        else log "dry-run $name: step3 for each confirmed event (no judge result yet)"; fi ;;
      *) if words="$(item_command "${kind:-}" "${args:-}")"; then log "dry-run $name: nice -n 5 $(echo "$words" | tr '\n' ' ')"
         else log "dry-run $name: unknown kind '${kind:-}'"; fi ;;
    esac
  done < "$QUEUE"
  exit 0
fi

if [ -n "$AFTER_PID" ]; then
  log "waiting for pid $AFTER_PID to exit"
  while kill -0 "$AFTER_PID" 2> /dev/null; do sleep 30; done
fi

# The sampler closes the inherited stdout (else a pipe reading the chain's output would stay open)
# and checks every 5 s whether the chain is still alive, so it ends with the chain.
( exec > /dev/null 2>&1
  while kill -0 $$ 2> /dev/null; do
    { echo "== $(date '+%Y-%m-%dT%H:%M:%S%z') $(top -l 2 -s 1 -n 0 | grep 'CPU usage' | tail -n 1)"
      ps -Ao pcpu=,pid=,comm= -r | head -n 8 | cut -c1-120; } >> "$ACTIVITY_LOG" 2>&1
    i=0
    while [ "$i" -lt "$SAMPLE_S" ] && kill -0 $$ 2> /dev/null; do sleep 5; i=$((i + 5)); done
  done ) &
log "activity sampler pid $! -> $ACTIVITY_LOG"

idle_since=""
while :; do
  if ! next_item; then
    if [ -z "$idle_since" ]; then idle_since="$(date +%s)"; log "queue empty; polling every 5 min (exit after ${IDLE_EXIT_H} h)"; fi
    if [ $(($(date +%s) - idle_since)) -ge $((IDLE_EXIT_H * 3600)) ]; then log "idle for ${IDLE_EXIT_H} h; exiting"; break; fi
    sleep 300
    continue
  fi
  idle_since=""
  case "$KIND" in
    end) mark_done "$NAME"; log "end item $NAME; exiting"; break ;;
    bisect_confirmed) run_bisect_confirmed "$NAME" ;;
    *)
      if ! words="$(item_command "$KIND" "$ARGS")"; then
        log "unknown kind '$KIND' for $NAME; skipped"
      else
        cmd=()
        while IFS= read -r w; do cmd+=("$w"); done <<< "$words"
        run_cmd "$NAME" "${cmd[@]}"
      fi ;;
  esac
  mark_done "$NAME"
done
log "chain done"
