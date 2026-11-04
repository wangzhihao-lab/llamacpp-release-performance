#!/usr/bin/env bash
# Download the three benchmark GGUF models of data/models.tsv and verify them.
#
# data/models.tsv is the record of the models used in the study: name, file, url (pinned to a
# Hugging Face repository commit), repo_commit, bytes, sha256, expected_sha256, verified.
# A file that is already present is only verified.  Every file is checked against its byte
# count and sha256 in the table; a model that fails is reported and the script exits with
# status 1.
#
# Model directory, in this order: the first argument, $MODELS_DIR, <root>/models.
#
# Run: bash scripts/fetch_models.sh [models-directory]
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TABLE="$ROOT/data/models.tsv"
MODELS_DIR="${1:-${MODELS_DIR:-$ROOT/models}}"
mkdir -p "$MODELS_DIR"

log() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$*"; }

failed=0
while IFS=$'\t' read -r name file url _ bytes sha _ <&3; do
  [ "$name" = "name" ] && continue  # header line
  dest="$MODELS_DIR/$file"
  if [ ! -f "$dest" ]; then
    log "download $name from $url"
    ok=0
    for attempt in 1 2 3 4 5; do
      if curl -fL --retry 5 --retry-delay 10 -C - -sS -o "$dest.part" "$url"; then ok=1; break; fi
      log "attempt $attempt failed for $name; retrying in 30 s"
      sleep 30
    done
    if [ "$ok" -ne 1 ]; then log "FAILED $name"; failed=1; continue; fi
    mv "$dest.part" "$dest"
  else
    log "file exists for $name, verifying only"
  fi
  have_bytes="$(stat -f %z "$dest")"
  have_sha="$(shasum -a 256 "$dest" | awk '{print $1}')"
  if [ "$have_bytes" = "$bytes" ] && [ "$have_sha" = "$sha" ]; then
    log "done $name bytes=$have_bytes sha256=$have_sha verified=yes"
  else
    log "MISMATCH $name: bytes=$have_bytes (expected $bytes), sha256=$have_sha (expected $sha)"
    failed=1
  fi
done 3< "$TABLE"
if [ "$failed" -eq 0 ]; then log "ALL DONE"; else log "at least one model failed"; fi
exit "$failed"
