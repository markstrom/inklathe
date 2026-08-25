#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$script_dir/common.sh"

require_root
ensure_engine_layout

configuration=${INKLATHE_NIXOS_CONFIGURATION:-server}
package="/etc/nixos#nixosConfigurations.${configuration}.config.services.inklathe.lucidaPackage"
cache_dir="$engine_root/lucida-cache"

echo "Installing the Lucida worker and its Python dependencies..."
nix --extra-experimental-features "nix-command flakes" build \
  --out-link "$engine_root/lucida" "$package"
install -d -o inklathe -g inklathe -m 0750 "$cache_dir"

echo "Downloading and validating the Lucida model (about 1 GB)..."
sudo -u inklathe env HF_HOME="$cache_dir" \
  "$engine_root/lucida/bin/inklathe-lucida" prepare --model lucida

set_engine_env INKLATHE_LUCIDA_COMMAND "$engine_root/lucida/bin/inklathe-lucida"
set_engine_env HF_HOME "$cache_dir"

restart_inklathe
echo "Lucida is installed and available in InkLathe."
