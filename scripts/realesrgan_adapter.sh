#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: realesrgan_adapter.sh INPUT OUTPUT SCALE" >&2
  exit 64
fi

: "${INKLATHE_REALESRGAN_BIN:?Set INKLATHE_REALESRGAN_BIN to the Real-ESRGAN executable}"

input=$1
output=$2
scale=$3
model=${INKLATHE_REALESRGAN_MODEL:-realesrgan-x4plus}

case "$scale" in
  2|4) ;;
  *)
    echo "InkLathe supports Real-ESRGAN scale 2 or 4, received: $scale" >&2
    exit 64
    ;;
esac

arguments=(
  -i "$input"
  -o "$output"
  -s "$scale"
  -n "$model"
  -f png
)

if [[ -n ${INKLATHE_REALESRGAN_MODEL_DIR:-} ]]; then
  arguments+=(-m "$INKLATHE_REALESRGAN_MODEL_DIR")
fi

exec "$INKLATHE_REALESRGAN_BIN" "${arguments[@]}"
