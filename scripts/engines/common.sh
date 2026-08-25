#!/usr/bin/env bash
set -euo pipefail

engine_root=/var/lib/inklathe/engines
engine_env=/var/lib/inklathe/engines.env

require_root() {
  if [[ ${EUID} -ne 0 ]]; then
    echo "Run this command with sudo." >&2
    exit 77
  fi
}

ensure_engine_layout() {
  install -d -o root -g inklathe -m 0750 "$engine_root"
}

set_engine_env() {
  local key=$1
  local value=$2
  local temporary
  temporary=$(mktemp)
  if [[ -f "$engine_env" ]]; then
    grep -v "^${key}=" "$engine_env" >"$temporary" || true
  fi
  printf '%s=%s\n' "$key" "$value" >>"$temporary"
  install -o root -g inklathe -m 0640 "$temporary" "$engine_env"
  rm -f "$temporary"
}

remove_engine_env() {
  local temporary
  local key
  [[ -f "$engine_env" ]] || return 0
  temporary=$(mktemp)
  cp "$engine_env" "$temporary"
  for key in "$@"; do
    sed -i "/^${key}=/d" "$temporary"
  done
  install -o root -g inklathe -m 0640 "$temporary" "$engine_env"
  rm -f "$temporary"
}

restart_inklathe() {
  systemctl restart inklathe
  systemctl is-active --quiet inklathe
}
