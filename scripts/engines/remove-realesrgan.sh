#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$script_dir/common.sh"

require_root
ensure_engine_layout

remove_engine_env \
  INKLATHE_AI_UPSCALER_COMMAND \
  INKLATHE_REALESRGAN_BIN \
  INKLATHE_REALESRGAN_MODEL \
  INKLATHE_REALESRGAN_MODEL_DIR

if [[ -L "$engine_root/realesrgan" ]]; then
  unlink "$engine_root/realesrgan"
fi

restart_inklathe
echo "Real-ESRGAN has been removed from InkLathe. Its Nix store data can be reclaimed by normal garbage collection."
