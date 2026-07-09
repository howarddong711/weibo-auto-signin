#!/bin/sh
set -eu

RUN_AT="${RUN_AT:-06:00}"
COOKIE_FILE="${COOKIE_FILE:-/app/data/cookies.txt}"
RUN_ON_START="${RUN_ON_START:-false}"

run_checkin() {
  if [ ! -s "$COOKIE_FILE" ]; then
    echo "$(date '+%F %T') | missing cookie file: $COOKIE_FILE"
    return 1
  fi

  echo "$(date '+%F %T') | starting weibo check-in"
  weibo-checkin --config "$COOKIE_FILE" || true
  echo "$(date '+%F %T') | finished weibo check-in"
}

if [ "$RUN_ON_START" = "true" ]; then
  run_checkin
fi

last_run_date=""

while true; do
  now_time="$(date '+%H:%M')"
  today="$(date '+%F')"

  if [ "$now_time" = "$RUN_AT" ] && [ "$last_run_date" != "$today" ]; then
    run_checkin
    last_run_date="$today"
  fi

  sleep 30
done
