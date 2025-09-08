#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
/usr/bin/env python3 guard.py >> cron.log 2>&1 || true
tail -n 200 cron.log > cron.log.tmp && mv cron.log.tmp cron.log
