#!/usr/bin/env bash
# Make Waypoint run all the time on this computer, without Docker.
# macOS: a launchd agent. Linux: a systemd user service.
# It starts at login and starts again if it stops.
#   scripts/install-service.sh            install and start
#   scripts/install-service.sh remove     stop and remove
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME=com.waypoint.app
LOG="$ROOT/waypoint.log"

if [ "${1:-}" != "remove" ] && [ ! -f "$ROOT/backend/.env" ]; then
  echo "Make backend/.env first (copy backend/.env.example and add your Seats.aero key)."; exit 1
fi

case "$(uname -s)" in
Darwin)
  PLIST="$HOME/Library/LaunchAgents/$NAME.plist"
  launchctl bootout "gui/$(id -u)/$NAME" 2>/dev/null || true
  if [ "${1:-}" = "remove" ]; then rm -f "$PLIST"; echo "Removed."; exit 0; fi
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$NAME</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$ROOT/run.sh</string></array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>$HOME/.bun/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PLIST
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  ;;
Linux)
  UNIT="$HOME/.config/systemd/user/waypoint.service"
  if [ "${1:-}" = "remove" ]; then systemctl --user disable --now waypoint 2>/dev/null || true; rm -f "$UNIT"; echo "Removed."; exit 0; fi
  mkdir -p "$(dirname "$UNIT")"
  cat > "$UNIT" <<UNIT
[Unit]
Description=Waypoint flight search
After=network-online.target

[Service]
WorkingDirectory=$ROOT
ExecStart=/bin/bash $ROOT/run.sh
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT
  systemctl --user daemon-reload
  systemctl --user enable --now waypoint
  loginctl enable-linger "$USER" 2>/dev/null || echo "Note: run 'sudo loginctl enable-linger $USER' so it also runs when you are logged out."
  ;;
*) echo "This script is for macOS and Linux. On Windows use: docker compose up -d --build"; exit 1 ;;
esac
echo "Waypoint runs at http://127.0.0.1:${PORT:-8000}  (log: ${LOG})"
