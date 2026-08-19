#!/usr/bin/env bash
set +e
export PATH="/usr/bin:/bin:/usr/local/bin:$PATH"
KEY="${OREP_DEPLOY_KEY:-$HOME/.ssh/orep_codex_deploy}"
HOST="${OREP_DEPLOY_HOST:-root@39.96.213.213}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/artifacts/compare20_v4_launch.log"
RSH="ssh -4 -i $KEY -o ConnectTimeout=25 -o ConnectionAttempts=1 -o GSSAPIAuthentication=no -o PreferredAuthentications=publickey -o IdentitiesOnly=yes -o IPQoS=throughput -o NumberOfPasswordPrompts=0"
echo "$(date) sparse watcher start" >> "$LOG"
for i in $(seq 1 40); do
  out=$($RSH "$HOST" "echo UP" 2>&1)
  if [ $? -eq 0 ] && echo "$out" | grep -q UP; then
    echo "$(date) SSH up on try $i" >> "$LOG"
    rsync -avz -e "$RSH" "$ROOT/tmp_compare20_v4_cases.json" "$ROOT/scripts/run_compare20_prod.py" "$HOST:/tmp/" >> "$LOG" 2>&1
    $RSH -o ConnectTimeout=40 "$HOST" "set -e
      docker cp /tmp/tmp_compare20_v4_cases.json orep-ai-scoring:/tmp/tmp_compare20_v4_cases.json
      docker cp /tmp/run_compare20_prod.py orep-ai-scoring:/tmp/run_compare20_prod.py
      docker exec orep-ai-scoring sh -c 'pkill -f run_compare20_prod.py || true'
      sleep 1
      docker exec -d orep-ai-scoring sh -c 'cd /app && PYTHONPATH=/app python -u /tmp/run_compare20_prod.py /tmp/tmp_compare20_v4_cases.json /tmp/compare20_v4_out.json > /tmp/compare20_v4_run.log 2>&1'
      sleep 3
      docker exec orep-ai-scoring sh -c 'ps aux | grep -v grep | grep run_compare20 || true; tail -5 /tmp/compare20_v4_run.log || true'
    " >> "$LOG" 2>&1
    echo "$(date) LAUNCHED" >> "$LOG"
    for j in $(seq 1 80); do
      sleep 45
      status=$($RSH -o ConnectTimeout=30 "$HOST" "docker exec orep-ai-scoring sh -c 'ps aux | grep -v grep | grep run_compare20 || echo NO_PROC; tail -3 /tmp/compare20_v4_run.log 2>/dev/null'" 2>&1)
      echo "$(date) poll $j" >> "$LOG"
      echo "$status" | tail -6 >> "$LOG"
      if echo "$status" | grep -qE 'WROTE|SUMMARY|overall_avg'; then echo "$(date) DONE" >> "$LOG"; break; fi
      if echo "$status" | grep -q NO_PROC; then
        n=$($RSH "$HOST" "docker exec orep-ai-scoring python -c 'import json,os;p=\"/tmp/compare20_v4_out.json\";print(len(json.load(open(p))) if os.path.exists(p) else 0)'" 2>/dev/null)
        echo "$(date) process ended n=$n" >> "$LOG"
        [ "${n:-0}" -ge 20 ] && break
      fi
    done
    $RSH -o ConnectTimeout=40 "$HOST" "docker cp orep-ai-scoring:/tmp/compare20_v4_out.json /tmp/; docker cp orep-ai-scoring:/tmp/compare20_v4_out_summary.json /tmp/ 2>/dev/null; docker cp orep-ai-scoring:/tmp/compare20_v4_run.log /tmp/ 2>/dev/null; true" >> "$LOG" 2>&1
    rsync -avz -e "$RSH" "$HOST:/tmp/compare20_v4_out.json" "$HOST:/tmp/compare20_v4_out_summary.json" "$HOST:/tmp/compare20_v4_run.log" "$ROOT/artifacts/" >> "$LOG" 2>&1 || true
    echo "$(date) DOWNLOADED" >> "$LOG"
    exit 0
  fi
  echo "$(date) wait ssh $i (sparse 180s)" >> "$LOG"
  sleep 180
done
echo "$(date) never got SSH sparse" >> "$LOG"
exit 1
