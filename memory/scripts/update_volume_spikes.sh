#!/usr/bin/env bash
set -euo pipefail

INDEX="memory/price_index.json"
HISTORY="memory/volume_history.json"
SPIKES="memory/volume_spikes.log"
SIG="memory/signals.log"

# Ensure history file exists and initialize if not
if [ ! -f "$HISTORY" ]; then
  cat <<'JSON' > "$HISTORY"
  {"btc":[],"eth":[],"sol":[],"ada":[],"xrp":[],"bnb":[],"xlm":[]}
JSON
fi

# Load latest history into a temp file
jq '.' "$HISTORY" > /tmp/volume_history.json

# Load latest index (assumes keys btc/eth/sol/ada/xrp/bnb/xlm with volume)
LATEST=$(cat "$INDEX")

# Function to update a single coin's history and compute spike
update_coin() {
  local coin=$1
  local vol=$(echo "$LATEST" | jq -r --arg c "$coin" '.[$c].volume // 0' )
  # Read current history for coin
  local hist=$(jq -r --arg c "$coin" '.[$c] // []' /tmp/volume_history.json)
  # Append latest volume and trim to last 5 entries
  local newhist=$(echo "$hist" | jq --arg v "$vol" '. + [ (if . == null then [] else . end) | .[-5:] // [] ] | . + [ (tonumber($v)) ]' 2>/dev/null || echo "[]")
  # Correct generation of last-5 (fallback if jq command fails)
  if [ "$newhist" = "null" ]; then newhist="[]"; fi
  # Compute moving average of last 5 volumes
  local avg=$(echo "$newhist" | jq -s '.[-5:] | add / length')
  # Current/latest volume is last element in newhist
  local latest=$(echo "$newhist" | tail -c +2 | tail -n 1 | tr -d '\n')
  # Spike if 2x avg or if avg is zero (avoid div by zero)
  local isSpike=0
  if [ -n "$avg" ] && [ "$avg" != "0" ]; then
    # Convert to numbers safely
    if (( $(echo "$latest" | awk '{print ($1 > 2 * $2) ? 1 : 0}') )); then
      isSpike=1
    fi
  fi
  if [ "$isSpike" -eq 1 ]; then
    # Append to per-coin spike log
    local coinlog="memory/${coin}_spikes.log"
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - volume spike: latest=$latest, avg=$avg" >> "$coinlog"
    # Also append to the global spikes log and signals
    echo "${coin}: ${latest} (vol spike, avg=${avg})" >> "$SPIKES"
    echo "Spike detected: ${coin} $latest vs avg $avg" >> "$SIG"
  fi
  # Update the saved history back to disk (append latest and keep last 5) in a robust way
  # Build a new history object with updated array for this coin
  local updated=$(echo "$NEW" 2>/dev/null || true)
}

# The above is a blueprint. For reliability, you should replace with a small Python script that:
# - loads price_index.json, maintains per-coin last-5 histories in memory/volume_history.json
# - computes 5-sample MA for each coin
# - appends spike records when necessary
# - writes back to memory/volume_history.json, volume_spikes.log, per-coin spikes, and signals

# For now, print a helpful message
echo "Volume spike detector script placeholder. Implemented logic should be deployed in a robust language (e.g., Python) for reliability."
