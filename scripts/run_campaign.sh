#!/usr/bin/env bash
# Run the benchmark campaign over the selected llama.cpp tags (resumable).
#
# For each tag in the tags file (default data/selected_tags.txt, chronological)
# it calls build_bench.sh unless <results>/<tag>/DONE exists, then appends one
# row to <results>/progress.csv. A failing tag never stops the campaign.
#
# * Sleep prevention: `caffeinate -i -w <this pid>` for the whole run.
# * Single instance: lock directory <log_dir>/campaign.lock (stale locks of
#   dead PIDs are taken over).
# * Scheduling (all optional, local time):
#     START_AT=HH:MM   wait (awake) until the next HH:MM before the first tag
#     STOP_AT=HH:MM    do not start a new tag after the next HH:MM following start
#     touch <log_dir>/STOP   stop before the next tag (file is removed on exit)
# * Resume: just run the script again; finished tags are skipped and the tag
#   that was interrupted is rebuilt from scratch.
#
# Environment: RESULTS_ROOT [<root>/results], LOG_DIR [<root>/logs], plus all
# build_bench.sh overrides (REPS, MODELS, BACKENDS, PARAM_SETS, COOLDOWN_S, ...).
#
# Run: mkdir -p logs && PARAM_SETS=main nohup bash scripts/run_campaign.sh > logs/campaign.nohup.out 2>&1 &
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
TAGS_FILE="${1:-$ROOT/data/selected_tags.txt}"
export RESULTS_ROOT="${RESULTS_ROOT:-$ROOT/results}"
LOG_DIR="${LOG_DIR:-$ROOT/logs}"
LOG="$LOG_DIR/campaign.log"
PROGRESS="$RESULTS_ROOT/progress.csv"
LOCK="$LOG_DIR/campaign.lock"
STOP_FILE="$LOG_DIR/STOP"
PARSER="$SCRIPT_DIR/parse_bench.py"

mkdir -p "$LOG_DIR" "$RESULTS_ROOT"
log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" | tee -a "$LOG"; }

# Next occurrence (epoch seconds) of local time HH:MM, strictly after now.
next_epoch() {
  local target nowe
  target="$(date -j -f '%Y-%m-%d %H:%M:%S' "$(date '+%Y-%m-%d') $1:00" '+%s' 2> /dev/null)" || return 1
  nowe="$(date '+%s')"
  [ "$target" -le "$nowe" ] && target=$((target + 86400))
  echo "$target"
}

if [ ! -f "$TAGS_FILE" ]; then
  log "tags file not found: $TAGS_FILE"
  exit 2
fi

if ! mkdir "$LOCK" 2> /dev/null; then
  oldpid="$(cat "$LOCK/pid" 2> /dev/null)"
  if [ -n "$oldpid" ] && kill -0 "$oldpid" 2> /dev/null; then
    log "another campaign is running (pid $oldpid); exiting"
    exit 1
  fi
  log "taking over stale lock of pid ${oldpid:-unknown}"
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"; rm -f "$STOP_FILE"' EXIT
trap 'log "signal received, stopping"; exit 130' INT TERM HUP

caffeinate -i -w $$ &
log "campaign pid $$ (caffeinate pid $!), tags file $TAGS_FILE, results $RESULTS_ROOT, reps ${REPS:-5}"

if [ -n "${START_AT:-}" ]; then
  start_epoch="$(next_epoch "$START_AT")" || { log "bad START_AT=$START_AT"; exit 2; }
  log "waiting until $(date -r "$start_epoch" '+%Y-%m-%d %H:%M')"
  while [ "$(date '+%s')" -lt "$start_epoch" ]; do
    [ -f "$STOP_FILE" ] && { log "STOP file found while waiting"; exit 0; }
    sleep 30
  done
fi
stop_epoch=""
if [ -n "${STOP_AT:-}" ]; then
  stop_epoch="$(next_epoch "$STOP_AT")" || { log "bad STOP_AT=$STOP_AT"; exit 2; }
  log "no new tag will be started after $(date -r "$stop_epoch" '+%Y-%m-%d %H:%M')"
fi

[ -s "$PROGRESS" ] || python3 -I "$PARSER" progress-header > "$PROGRESS"

total="$(grep -cE '^b[0-9]+$' "$TAGS_FILE")"
i=0
for tag in $(grep -E '^b[0-9]+$' "$TAGS_FILE"); do
  i=$((i + 1))
  if [ -f "$RESULTS_ROOT/$tag/DONE" ]; then
    grep -q "^$tag," "$PROGRESS" || python3 -I "$PARSER" progress-row "$RESULTS_ROOT/$tag" >> "$PROGRESS"
    log "[$i/$total] skip $tag (DONE)"
    continue
  fi
  if [ -f "$STOP_FILE" ]; then log "STOP file found; stopping before $tag"; break; fi
  if [ -n "$stop_epoch" ] && [ "$(date '+%s')" -ge "$stop_epoch" ]; then
    log "STOP_AT reached; stopping before $tag"; break
  fi
  log "[$i/$total] start $tag"
  t0="$(date '+%s')"
  bash "$SCRIPT_DIR/build_bench.sh" "$tag" > "$LOG_DIR/$tag.log" 2>&1
  rc=$?
  if [ -f "$RESULTS_ROOT/$tag/DONE" ]; then
    python3 -I "$PARSER" progress-row "$RESULTS_ROOT/$tag" >> "$PROGRESS"
    log "[$i/$total] end $tag rc=$rc in $(( $(date '+%s') - t0 )) s: $(tail -1 "$PROGRESS" | cut -d, -f5)"
  else
    reason="$(tail -3 "$LOG_DIR/$tag.log" 2> /dev/null | tr '\n' ' ' | cut -c1-200)"
    python3 -I -c 'import csv,sys; csv.writer(sys.stdout, lineterminator="\n").writerow([sys.argv[1]] + [""] * 3 + ["script_error"] + [""] * 11 + [sys.argv[2]])' \
      "$tag" "$reason" >> "$PROGRESS"
    log "[$i/$total] $tag did not finish (rc=$rc); recorded script_error, will retry on next run"
  fi
done
log "campaign loop finished"
