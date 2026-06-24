#!/bin/bash
# Toggle Packy bot on/off

PIDFILE="/tmp/packy-bot.pid"
LOGFILE="/tmp/packy-bot.log"
DIR="$HOME/gargoyle-packy"

start_bot() {
  cd "$DIR" || exit 1
  nohup node src/bot/index.js > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  echo "Packy started (PID: $!)"
}

stop_bot() {
  if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill "$PID" 2>/dev/null; then
      echo "Packy stopped (PID: $PID)"
      rm -f "$PIDFILE"
    else
      echo "Packy was not running. Cleaning up."
      rm -f "$PIDFILE"
    fi
  else
    echo "Packy is not running."
  fi
}

status_bot() {
  if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "Packy is running (PID: $(cat $PIDFILE))"
    echo "Log: tail -f $LOGFILE"
  else
    echo "Packy is not running."
  fi
}

case "${1:-toggle}" in
  start)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
      echo "Packy is already running."
      exit 0
    fi
    start_bot
    ;;
  stop)
    stop_bot
    ;;
  status)
    status_bot
    ;;
  toggle|*)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
      stop_bot
    else
      start_bot
    fi
    ;;
esac
