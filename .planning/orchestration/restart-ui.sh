#!/usr/bin/env bash
# restart the Vite dev server on 5193 after a dependency change
P=$(ss -ltnp 2>/dev/null | awk '/:5193 /{print}' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u)
[ -n "$P" ] && kill $P; sleep 1
cd "${MAIN:-$(git rev-parse --show-toplevel)}/frontend" && npm ci --no-audit --no-fund 2>&1 | tail -1
nohup npx vite --host 0.0.0.0 --port 5193 > "$(dirname "$0")/vite.log" 2>&1 &
sleep 8; curl -s -o /dev/null -w 'ui %{http_code}\n' localhost:5193
