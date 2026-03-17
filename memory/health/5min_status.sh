cat > memory/health/5min_status.sh << 'SH'
#!/usr/bin/env bash
set -euo pipefailLOG="memory/volume_spikes.log"TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%MZ")
SPIKES=$(grep -i spike "$LOG" 2>/dev/null | wc -l || echo 0)
echo "[$TIMESTAMP] cadence=5min, spikes_seen=$SPIKES"
