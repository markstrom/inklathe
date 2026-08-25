#!/usr/bin/env bash
set -euo pipefail

engine_scripts=@PACKAGE_ROOT@/libexec/inklathe/engines
action=${1:-}
engine=${2:-}

case "${action}:${engine}" in
  install:realesrgan) exec "$engine_scripts/install-realesrgan.sh" ;;
  remove:realesrgan) exec "$engine_scripts/remove-realesrgan.sh" ;;
  install:lucida) exec "$engine_scripts/install-lucida.sh" ;;
  remove:lucida) exec "$engine_scripts/remove-lucida.sh" ;;
  *)
    echo "Usage: inklathe-engine {install|remove} {realesrgan|lucida}" >&2
    exit 64
    ;;
esac
