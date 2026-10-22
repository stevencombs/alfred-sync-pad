#!/bin/bash
# Copy workflow/ into Alfred's preferences and reload it.
# Prefers the Alfred sync folder, so the installed copy syncs to your other Macs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/workflow"
UID_DIR="user.workflow.B8E4C1D2-3F47-4A96-8C05-1D2E3F4A5B6C"
BUNDLE="com.retrocombs.syncpad"

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
  if [[ -d "$syncfolder/Alfred.alfredpreferences/workflows" ]]; then
    prefs="$syncfolder/Alfred.alfredpreferences"
  else
    echo "Alfred sync folder is set, but workflows were not found:" >&2
    echo "  $syncfolder/Alfred.alfredpreferences/workflows" >&2
    echo "Install will use the local Alfred preferences instead." >&2
  fi
fi

if [[ -z "$prefs" ]]; then
  prefs="$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences"
fi

if [[ ! -d "$prefs/workflows" ]]; then
  echo "Alfred workflows folder not found: $prefs/workflows" >&2
  echo "Install Alfred 5, open it once, then run this script again." >&2
  exit 1
fi

for file in info.plist sync_pad.py icon.png; do
  if [[ ! -f "$SRC/$file" ]]; then
    echo "Missing $SRC/$file" >&2
    exit 1
  fi
done

dest="$prefs/workflows/$UID_DIR"
mkdir -p "$dest"
cp "$SRC/info.plist" "$SRC/sync_pad.py" "$SRC/icon.png" "$dest/"
chmod +x "$dest/sync_pad.py"

if osascript -e "tell application \"Alfred 5\" to reload workflow \"$BUNDLE\"" >/dev/null 2>&1 \
  || osascript -e "tell application \"Alfred\" to reload workflow \"$BUNDLE\"" >/dev/null 2>&1; then
  echo "Installed and reloaded."
else
  echo "Installed. Quit Alfred and open it again if pad does not appear."
fi
echo "$dest"
