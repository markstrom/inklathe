#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$script_dir/common.sh"

require_root
ensure_engine_layout

remove_engine_env INKLATHE_LUCIDA_COMMAND HF_HOME

if [[ -L "$engine_root/lucida" ]]; then
  unlink "$engine_root/lucida"
fi
if [[ "$engine_root" == "/var/lib/inklathe/engines" ]]; then
  rm -rf -- "$engine_root/lucida-cache"
fi

restart_inklathe
echo "Lucida and its downloaded model cache have been removed from InkLathe."
