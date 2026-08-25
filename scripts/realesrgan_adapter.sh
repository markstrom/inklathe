#!/usr/bin/env bash
set -euo pipefail

python_command=${INKLATHE_PYTHON:-python3}
exec "$python_command" -m inklathe.realesrgan_adapter "$@"
