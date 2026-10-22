#!/bin/bash
# Build Sync.Pad.alfredworkflow from workflow/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/Sync.Pad.alfredworkflow"

rm -f "$OUT"
(
  cd "$ROOT/workflow"
  zip -r -X "$OUT" info.plist icon.png sync_pad.py -x '*.DS_Store' -x '__MACOSX/*' -x '__pycache__/*'
)
echo "Wrote $OUT"
