#!/bin/bash
# Copy the installed Alfred workflow back into workflow/ and rebuild the package.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UID_DIR="user.workflow.B8E4C1D2-3F47-4A96-8C05-1D2E3F4A5B6C"

expand_tilde() {
  local path="$1"
  # Do not use ${path#~/}. Bash tilde-expands the pattern before it strips.
  if [[ "$path" == "~" ]]; then
    printf '%s\n' "$HOME"
  elif [[ "$path" == "~/"* ]]; then
    printf '%s\n' "$HOME/${path:2}"
  else
    printf '%s\n' "$path"
  fi
}

syncfolder="$(defaults read com.runningwithcrayons.Alfred-Preferences syncfolder 2>/dev/null || true)"
prefs=""
if [[ -n "$syncfolder" ]]; then
  syncfolder="$(expand_tilde "$syncfolder")"
  if [[ -d "$syncfolder/Alfred.alfredpreferences/workflows/$UID_DIR" ]]; then
    prefs="$syncfolder/Alfred.alfredpreferences"
  fi
fi

if [[ -z "$prefs" && -d "$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows/$UID_DIR" ]]; then
  prefs="$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences"
fi

src=""
if [[ -n "$prefs" ]]; then
  src="$prefs/workflows/$UID_DIR"
fi

if [[ ! -f "${src:-}/info.plist" ]]; then
  echo "Installed workflow not found." >&2
  echo "Expected $UID_DIR in Alfred's workflows folder." >&2
  exit 1
fi

mkdir -p "$ROOT/workflow"
cp "$src/info.plist" "$src/sync_pad.py" "$src/icon.png" "$ROOT/workflow/"
chmod +x "$ROOT/workflow/sync_pad.py"
"$ROOT/scripts/package.sh"
echo "Exported from $src"
