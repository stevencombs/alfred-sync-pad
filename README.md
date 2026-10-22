# Sync Pad for Alfred

Share clipboard text with your other Macs. Sync Pad is its own workflow. Alfred Clipboard History stays on `clip`.

The keyword is `pad`. Saved snippets are listed first, newest at the top. This Mac's clipboard history follows them. Return copies the highlighted clip and makes it the newest clipboard item.

| | |
|---|---|
| Keyword | `pad` |
| Bundle ID | `com.retrocombs.syncpad` |
| Alfred | 5, with the Powerpack |
| Version | 1.0 |
| Source | https://github.com/stevencombs/alfred-sync-pad |

On the Macs that already sync Alfred preferences through Google Drive, the workflow is already installed. This repository is the source copy: the script, the icon, the Alfred package, and these instructions.

The shared text is not in this repository. It lives in `sync-pad.json` next to your synced Alfred preferences.

## Requirements

- macOS with Alfred 5 and the Powerpack. Script Filters are a Powerpack feature.
- `/usr/bin/python3`. macOS provides this with the Xcode Command Line Tools. Check with `python3 --version`. If the command is missing, install the tools with `xcode-select --install`.
- Alfred's preferences sync, if you want a clip saved on one Mac to show up on the others. Sync is already pointed at `~/Google Drive (Home)/Computers/Mac/MacSyncing/Alfred` on this setup.

## Repository layout

```text
alfred-sync-pad/
├── README.md
├── Sync.Pad.alfredworkflow          ← double-click to install
├── scripts/
│   ├── install.sh                   ← copy workflow/ into Alfred
│   ├── export-from-alfred.sh        ← copy Alfred's copy back here
│   └── package.sh                   ← rebuild the .alfredworkflow
└── workflow/
    ├── info.plist                   ← keyword, objects, configuration
    ├── sync_pad.py                  ← clipboard list and the scratch pad
    └── icon.png
```

`Sync.Pad.alfredworkflow` is a zip of `info.plist`, `sync_pad.py`, and `icon.png`. Alfred imports that zip. The README stays in the repository and is not part of the package.

## Where the files live

There are two copies, on purpose.

| Copy | Path | What it is for |
|---|---|---|
| Running workflow | Alfred's synced preferences, folder `user.workflow.B8E4C1D2-3F47-4A96-8C05-1D2E3F4A5B6C` | What Alfred runs. Google Drive syncs this folder to your other Macs. |
| Source | `~/Google Drive (Home)/GitHub Repos/stevencombs/alfred-sync-pad` | This git repository. `~/src/github.com/stevencombs/alfred-sync-pad` is a shortcut to the same folder after `repos-sync`. |
| Scratch pad | `~/Google Drive (Home)/Computers/Mac/MacSyncing/Alfred/sync-pad.json` | The last 30 shared clips. Created the first time you share. Plain text. |

The running folder on this Mac is:

```text
~/Google Drive (Home)/Computers/Mac/MacSyncing/Alfred/Alfred.alfredpreferences/workflows/user.workflow.B8E4C1D2-3F47-4A96-8C05-1D2E3F4A5B6C
```

Editing the workflow in Alfred Preferences changes the running copy. Editing `workflow/` in this repository changes the source. [Keep the repo and Alfred in step](#keep-the-repo-and-alfred-in-step) explains how to copy either way.

## Install

### Already installed

If Alfred preferences are syncing through Google Drive, open Alfred and type `pad`. The workflow is there. You only need the steps below to reinstall it, or to install it on a Mac that does not use that sync folder.

### Double-click the package

1. Download [Sync.Pad.alfredworkflow](https://github.com/stevencombs/alfred-sync-pad/raw/main/Sync.Pad.alfredworkflow), or use the copy in a clone of this repository.
2. Double-click it. Alfred asks to import the workflow.
3. If Alfred says a workflow with bundle ID `com.retrocombs.syncpad` is already installed, replace it.

Importing can give the workflow a new folder name inside `workflows/`. The keyword, bundle ID, and behavior stay the same. `scripts/install.sh` keeps the original folder name, which matters if you want the synced copy to stay one workflow instead of a second copy.

### Install from a clone

```bash
git clone https://github.com/stevencombs/alfred-sync-pad.git
cd alfred-sync-pad
./scripts/install.sh
```

On this Mac the checkout already lives in Google Drive:

```bash
cd "$HOME/Google Drive (Home)/GitHub Repos/stevencombs/alfred-sync-pad"
./scripts/install.sh
```

`install.sh` copies `info.plist`, `sync_pad.py`, and `icon.png` into the synced workflow folder and tells Alfred to reload bundle ID `com.retrocombs.syncpad`.

## Use it

1. Copy some text.
2. Open Alfred and type `pad`.
3. The newest Sync Pad snippets are the first rows. A Clipboard row follows, then this Mac's recent clipboard text.
4. Highlight a clipboard row and press ⌘Return to save it.
5. On another Mac, type `pad` and press Return on that snippet.

| Key | What it does |
|---|---|
| Return | Copies the clip and makes it the newest clipboard item. Paste with ⌘V. |
| ⌘Return | Saves a clipboard clip to Sync Pad, or moves a saved snippet to the top. |
| ⌥Return | Removes a saved snippet. Clipboard rows cannot be removed this way. |

The pad keeps 30 snippets. Sharing the same text again moves that snippet to the top instead of adding a second copy.

Type after `pad` to narrow the list. `pad budget` finds that word in a saved snippet or in clipboard history.

Google Drive has to finish syncing `sync-pad.json` before the other Mac can see a new snippet. Text only. Images and files stay on the Mac where you copied them.

Share only text you are willing to keep in Google Drive. `sync-pad.json` is plain text.

## Keep the repo and Alfred in step

### You edited the repository

```bash
cd "$HOME/Google Drive (Home)/GitHub Repos/stevencombs/alfred-sync-pad"
./scripts/package.sh
./scripts/install.sh
git add -A
git status
git commit -m "Describe the change"
git push
```

`package.sh` writes `Sync.Pad.alfredworkflow` next to this README. Commit that file when you change `workflow/`, so the downloadable package matches the source.

### You edited the workflow inside Alfred

```bash
cd "$HOME/Google Drive (Home)/GitHub Repos/stevencombs/alfred-sync-pad"
./scripts/export-from-alfred.sh
git diff
```

`export-from-alfred.sh` copies `info.plist`, `sync_pad.py`, and `icon.png` from the installed workflow into `workflow/`, then rebuilds the package.

Do not commit `sync-pad.json`. That file is your shared clips, and it is gitignored.

## Other Macs

**Alfred preferences sync** carries the installed workflow. After Google Drive finishes syncing `Computers/Mac/MacSyncing/Alfred`, the other Mac's Alfred sees **Sync Pad**. Type `pad`.

**This git repository** is stored with the other checkouts:

```text
~/Google Drive (Home)/GitHub Repos/stevencombs/alfred-sync-pad
```

It is listed in `~/.local/share/repos/github.txt`. On another Mac, wait until Drive has finished syncing `GitHub Repos`, update dotfiles with `dpull`, then run `repos-sync`. That creates:

```text
~/src/github.com/stevencombs/alfred-sync-pad
```

Do not commit this repository from two Macs while Drive is still syncing the `.git` folder.

## Troubleshooting

**`pad` shows nothing.**

Alfred Preferences → Workflows → Sync Pad. Confirm the workflow is enabled. Confirm the keyword is `pad`. Powerpack has to be active.

**A snippet saved on the other Mac is missing.**

Wait for Google Drive to finish `sync-pad.json`. The file sits next to `Alfred.alfredpreferences`, not inside the workflow folder. Open `pad` again after the file is on this Mac.

**Return did not paste into the document.**

Return only copies. Click the document and press ⌘V.

**`/usr/bin/python3` is missing.**

Install the Xcode Command Line Tools (`xcode-select --install`). The Script Filter calls `/usr/bin/python3` directly.

## Uninstall

1. Alfred Preferences → Workflows → Sync Pad → right-click → Remove.
2. Delete `sync-pad.json` next to `Alfred.alfredpreferences` if you also want the shared clips gone.

To drop the git checkout as well, delete `stevencombs/alfred-sync-pad` from `~/.local/share/repos/github.txt` (and from the chezmoi source of that file), run `repos-sync`, and delete the Google Drive checkout when you are sure you want it gone. The GitHub repository stays until you delete it on GitHub.
