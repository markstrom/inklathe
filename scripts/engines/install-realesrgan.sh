#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$script_dir/common.sh"

require_root
ensure_engine_layout

configuration=${INKLATHE_NIXOS_CONFIGURATION:-server}
package="/etc/nixos#nixosConfigurations.${configuration}.config.services.inklathe.realEsrganPackage"

echo "Installing Real-ESRGAN from the locked NixOS package set..."
nix --extra-experimental-features "nix-command flakes" build \
  --out-link "$engine_root/realesrgan" "$package"

set_engine_env INKLATHE_AI_UPSCALER_COMMAND /run/current-system/sw/bin/inklathe-realesrgan-adapter
set_engine_env INKLATHE_REALESRGAN_BIN "$engine_root/realesrgan/bin/realesrgan-ncnn-vulkan"
set_engine_env INKLATHE_REALESRGAN_MODEL realesrgan-x4plus
remove_engine_env INKLATHE_REALESRGAN_MODEL_DIR

restart_inklathe
echo "Real-ESRGAN is installed and available in InkLathe."
