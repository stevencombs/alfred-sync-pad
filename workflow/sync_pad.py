#!/usr/bin/python3
"""Sync Pad for Alfred.

Lists this Mac's text clipboard history beside a 30-clip scratch pad.
The pad file sits next to the synced Alfred preferences so Google Drive
carries it to the other Macs. Alfred's local Workflow Data folder does not.

Return copies a clip. Command-Return shares it. Option-Return removes a
shared clip. Copy writes the clip text to stdout unchanged. Alfred's
Copy to Clipboard object keeps that text as-is and saves it to history.
"""

import datetime
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

MAX_SHARED = 30
MAX_RESULTS = 50
RECENT_LOCAL = 40
# clipboard.ts is seconds since 2001-01-01, not Unix time.
COCOA_UNIX = 978307200
TITLE_LIMIT = 140

CLIPBOARD_DB = Path.home() / "Library/Application Support/Alfred/Databases/clipboard.alfdb"
ICON_LOCAL = "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/ClippingText.icns"
ICON_SHARED = "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/SidebariCloud.icns"

WORKFLOW_DIR = Path(__file__).resolve().parent
HISTORY_TOKEN = re.compile(r"^h:(\d+):([0-9a-f]{64})$")
SHARED_TOKEN = re.compile(
    r"^s:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE,
)


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def pad_path():
    prefs = WORKFLOW_DIR.parent.parent
    if prefs.name == "Alfred.alfredpreferences":
        return prefs.parent / "sync-pad.json"
    return WORKFLOW_DIR / "sync-pad.json"


def lock_path():
    digest = hashlib.sha256(str(pad_path()).encode("utf-8")).hexdigest()[:16]
    return Path("/tmp") / ("sync-pad-%s.lock" % digest)


class PadLock:
    def __enter__(self):
        self.handle = open(lock_path(), "a+")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


def computer_name():
    try:
        name = subprocess.check_output(
            ["scutil", "--get", "ComputerName"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).decode("utf-8", "replace").strip()
        if name:
            return name
    except (OSError, subprocess.SubprocessError):
        pass
    return os.uname().nodename or "Mac"


def digest(text):
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def display_title(text):
    chars = []
    for char in text:
        chars.append(char if char.isprintable() else " ")
    one_line = " ".join("".join(chars).split())
    if len(one_line) <= TITLE_LIMIT:
        return one_line or "(empty clip)"
    return one_line[: TITLE_LIMIT - 1].rstrip() + "…"


def ago(unix_ts):
    delta = max(0, time.time() - float(unix_ts))
    if delta < 45:
        return "just now"
    if delta < 3600:
        return "%dm ago" % int(delta // 60)
    if delta < 86400:
        return "%dh ago" % int(delta // 3600)
    if delta < 7 * 86400:
        return "%dd ago" % int(delta // 86400)
    when = datetime.datetime.fromtimestamp(float(unix_ts))
    return when.strftime("%b %-d")


def cocoa_to_unix(ts):
    return float(ts) + COCOA_UNIX


def error_item(message):
    return {
        "title": "Sync Pad ran into a problem",
        "subtitle": message,
        "valid": False,
        "icon": {"path": ICON_SHARED},
    }


def connect_clipboard():
    uri = CLIPBOARD_DB.as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=1.0)


def local_rows():
    if not CLIPBOARD_DB.is_file():
        raise RuntimeError("Alfred clipboard history is not on this Mac.")
    connection = connect_clipboard()
    try:
        return connection.execute(
            "SELECT rowid, item, ts, app FROM clipboard "
            "WHERE dataType = 0 AND item IS NOT NULL "
            "ORDER BY ts DESC"
        ).fetchall()
    finally:
        connection.close()


def load_pad():
    path = pad_path()
    if not path.is_file():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError("Couldn't read the Sync Pad file.") from exc
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "sync-pad.json is unreadable. It was left in place."
        ) from exc
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise RuntimeError("sync-pad.json is unreadable. It was left in place.")
    clean = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        item_id = item.get("id")
        if not isinstance(text, str) or not isinstance(item_id, str):
            continue
        if not text.strip():
            continue
        clean.append(
            {
                "id": item_id.lower(),
                "text": text,
                "sha256": item.get("sha256") or digest(text),
                "shared_at": float(item.get("shared_at") or 0),
                "computer": item.get("computer") or "Mac",
                "app": item.get("app") or "",
            }
        )
    clean.sort(key=lambda item: item["shared_at"], reverse=True)
    newest = []
    seen = set()
    for item in clean:
        if item["sha256"] in seen:
            continue
        seen.add(item["sha256"])
        newest.append(item)
    return newest[:MAX_SHARED]


def save_pad(items):
    path = pad_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "items": items[:MAX_SHARED]}
    temporary = path.with_suffix(".json.tmp")
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, path)


def matches(query, *parts):
    if not query:
        return True
    folded = query.casefold()
    return any(folded in (part or "").casefold() for part in parts)


def history_item(rowid, text, when_unix, app):
    token = "h:%d:%s" % (rowid, digest(text))
    app_name = app or "Clipboard"
    return {
        "uid": "syncpad-" + digest(text),
        "title": display_title(text),
        "subtitle": "%s · %s · ↩ copy  ⌘↩ share" % (app_name, ago(when_unix)),
        "arg": token,
        "valid": True,
        "text": {"copy": text, "largetype": display_title(text)},
        "icon": {"path": ICON_LOCAL},
        "mods": {
            "cmd": {
                "subtitle": "Share this clip with your other Macs",
                "arg": token,
                "valid": True,
            },
            "alt": {
                "subtitle": "Only shared clips can be removed",
                "valid": False,
            },
        },
    }


def shared_item(entry):
    token = "s:" + entry["id"]
    where = "Sync Pad · %s" % entry["computer"]
    if entry.get("app"):
        where += " · %s" % entry["app"]
    return {
        "uid": "syncpad-s-" + entry["id"],
        "title": display_title(entry["text"]),
        "subtitle": "%s · %s · ↩ copy  ⌘↩ move to top  ⌥↩ remove" % (
            where,
            ago(entry["shared_at"]),
        ),
        "arg": token,
        "valid": True,
        "text": {"copy": entry["text"], "largetype": display_title(entry["text"])},
        "icon": {"path": ICON_SHARED},
        "mods": {
            "cmd": {
                "subtitle": "Move this clip to the top of Sync Pad",
                "arg": token,
                "valid": True,
            },
            "alt": {
                "subtitle": "Remove this clip from Sync Pad",
                "arg": token,
                "valid": True,
            },
        },
    }


def note(uid, title, subtitle, icon):
    return {
        "uid": uid,
        "title": title,
        "subtitle": subtitle,
        "valid": False,
        "icon": {"path": icon},
    }


def build_items(query):
    items = []
    shared_hashes = set()
    pad_error = False
    try:
        shared = load_pad()
    except RuntimeError as exc:
        items.append(error_item(str(exc)))
        shared = []
        pad_error = True

    # Saved snippets stay at the top. An empty `pad` shows them before any typing.
    saved = []
    for entry in shared:
        if matches(query, entry["text"], entry["computer"], entry.get("app") or ""):
            saved.append(entry)
            shared_hashes.add(entry["sha256"])
    items.extend(shared_item(entry) for entry in saved)

    if not query and not saved and not pad_error:
        items.append(
            note(
                "syncpad-empty",
                "No Sync Pad snippets yet",
                "⌘↩ a clipboard clip below to save it",
                ICON_SHARED,
            )
        )

    try:
        rows = local_rows()
    except (RuntimeError, sqlite3.Error) as exc:
        items.append(error_item(str(exc)))
        rows = []

    seen = set(shared_hashes)
    local_added = 0
    hidden = 0
    for rowid, text, ts, app in rows:
        if not isinstance(text, str) or not text.strip():
            continue
        if not matches(query, text, app or ""):
            continue
        item_digest = digest(text)
        if item_digest in seen:
            continue
        seen.add(item_digest)
        if not query and local_added >= RECENT_LOCAL:
            hidden += 1
            continue
        if query and len(items) >= MAX_RESULTS:
            hidden += 1
            continue
        if local_added == 0 and not query and saved:
            items.append(
                note(
                    "syncpad-clipboard",
                    "Clipboard",
                    "⌘↩ saves a clip to Sync Pad",
                    ICON_LOCAL,
                )
            )
        items.append(history_item(rowid, text, cocoa_to_unix(ts), app))
        local_added += 1

    clipboard_text = any(isinstance(row[1], str) and row[1].strip() for row in rows)
    if query and not saved and local_added == 0:
        items.append(
            note(
                "syncpad-none",
                "No matching clips",
                "Try a different search",
                ICON_LOCAL,
            )
        )
    elif not query and not clipboard_text:
        items.append(
            note(
                "syncpad-noclip",
                "No clipboard text yet",
                "Copy some text, then open pad again",
                ICON_LOCAL,
            )
        )
    elif hidden:
        items.append(
            note(
                "syncpad-more",
                "More clips match",
                "Type more to narrow the list",
                ICON_LOCAL,
            )
        )

    return {"skipknowledge": True, "items": items}


def parse_token(token):
    token = (token or "").strip()
    history = HISTORY_TOKEN.match(token)
    if history:
        return ("h", int(history.group(1)), history.group(2))
    shared = SHARED_TOKEN.match(token)
    if shared:
        return ("s", shared.group(1).lower())
    raise LookupError("That clip could not be read. Try again.")


def text_from_history(rowid, expected):
    connection = connect_clipboard()
    try:
        row = connection.execute(
            "SELECT item, app FROM clipboard WHERE rowid = ? AND dataType = 0",
            (rowid,),
        ).fetchone()
        if row and isinstance(row[0], str) and digest(row[0]) == expected:
            return row[0], row[1] or ""
        for text, app in connection.execute(
            "SELECT item, app FROM clipboard WHERE dataType = 0 ORDER BY ts DESC"
        ):
            if isinstance(text, str) and digest(text) == expected:
                return text, app or ""
    finally:
        connection.close()
    raise LookupError("That clip is no longer in clipboard history.")


def resolve(token):
    kind = parse_token(token)
    if kind[0] == "h":
        text, _app = text_from_history(kind[1], kind[2])
        return text
    with PadLock():
        for entry in load_pad():
            if entry["id"] == kind[1]:
                return entry["text"]
    raise LookupError("That clip is no longer on Sync Pad.")


def share(token):
    kind = parse_token(token)
    if kind[0] == "h":
        text, app = text_from_history(kind[1], kind[2])
    else:
        with PadLock():
            current = load_pad()
        match = next((entry for entry in current if entry["id"] == kind[1]), None)
        if match is None:
            raise LookupError("That clip is no longer on Sync Pad.")
        text = match["text"]
        app = match.get("app") or ""

    if not text.strip():
        raise LookupError("Empty clips are not shared.")

    item_digest = digest(text)
    now = time.time()
    with PadLock():
        items = load_pad()
        already = any(entry["sha256"] == item_digest for entry in items)
        kept = [entry for entry in items if entry["sha256"] != item_digest]
        previous = next((entry for entry in items if entry["sha256"] == item_digest), None)
        entry = {
            "id": previous["id"] if previous else str(uuid.uuid4()),
            "text": text,
            "sha256": item_digest,
            "shared_at": now,
            "computer": computer_name(),
            "app": app,
        }
        save_pad([entry] + kept)
    if already:
        return "Moved to the top of Sync Pad."
    return "Shared with your other Macs. Google Drive may take a moment."


def remove(token):
    kind = parse_token(token)
    if kind[0] != "s":
        raise LookupError("Only shared clips can be removed.")
    with PadLock():
        items = load_pad()
        kept = [entry for entry in items if entry["id"] != kind[1]]
        if len(kept) == len(items):
            raise LookupError("That clip is no longer on Sync Pad.")
        save_pad(kept)
    return "Removed from Sync Pad."


def emit_clipboard_text(text):
    # Checked against Alfred 5.8: Copy to Clipboard keeps stdout bytes, including newlines.
    sys.stdout.write(text)
    sys.stdout.flush()


def main(argv):
    configure_stdout()
    if len(argv) < 2:
        print("Sync Pad was started without a command.", file=sys.stderr)
        return 1
    command = argv[1]
    rest = argv[2:]
    try:
        if command == "list":
            payload = build_items(" ".join(rest).strip())
            json.dump(payload, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
            print("Sync Pad listed %d rows" % len(payload["items"]), file=sys.stderr)
            return 0
        if command == "copy":
            emit_clipboard_text(resolve(rest[0] if rest else ""))
            return 0
        if command == "share":
            print(share(rest[0] if rest else ""))
            return 0
        if command == "remove":
            print(remove(rest[0] if rest else ""))
            return 0
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        if command == "copy":
            return 1
        print(str(exc))
        return 0
    except Exception as exc:
        print("Sync Pad failed: %s" % exc, file=sys.stderr)
        if command == "list":
            json.dump({"items": [error_item(str(exc))]}, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
            return 0
        if command == "copy":
            return 1
        print("Sync Pad ran into a problem.")
        return 0
    print("Unknown Sync Pad command.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
