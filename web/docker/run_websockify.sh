#!/bin/sh
set -eu

TOKEN_FILE="${NOVNC_TOKEN_FILE:-/app/storage/novnc/tokens}"
mkdir -p "$(dirname "$TOKEN_FILE")"
touch "$TOKEN_FILE"

exec websockify \
  --web /usr/share/novnc/ \
  --token-plugin TokenFile \
  --token-source "$TOKEN_FILE" \
  6080
