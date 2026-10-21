# INSTALL.md: instructions for Claude Code

You are installing Distinguished Vertical Editor for the person you are talking to. Follow these steps in order.
Keep each update to the person short and plain: what the step does, how big the download is,
then run it. They may not be technical. Never use sudo. Nothing here needs a password.

## 0. Before you start

- Run all commands from `~/DVE`. If it doesn't exist yet and the person gave you the GitHub link, download it
  without git (a fresh Mac pops a developer-tools dialog the first time anything runs git):
  `mkdir -p ~/DVE && curl -fsSL https://github.com/Distinguished-Creative-Co/dve/archive/refs/heads/main.tar.gz | tar -xz -C ~/DVE --strip-components 1`
  (about 50 MB). Otherwise the folder came from a zip and may have landed somewhere else: Safari expands the
  zip into `~/Downloads/DVE` on its own, or the person may have unzipped it on the Desktop. If
  `runtime/` does not exist yet, move that folder to `~/DVE` (`mv ~/Downloads/DVE ~/DVE`) rather
  than unzipping a second copy. If only the zip exists: `ditto -x -k ~/Downloads/DVE-1.0.0.zip ~`
  (it creates `~/DVE`). A Google Drive download may show a "can't scan for viruses" page first:
  that is normal for a 50 MB file, click Download anyway.
- Tell the person: "This installs everything inside one folder, ~/DVE. About 3 GB of
  downloads, 20-40 minutes. You'll see permission prompts from Claude Code for each command.
  You can approve them one by one, or choose to allow commands in ~/DVE."
- Show them these terms in plain words and get a "yes" before installing:
  - **Remotion** (the video renderer) is free for individuals and companies of up to 3 people.
    A company with 4 or more employees needs a paid Remotion company license (remotion.pro).
  - **MediaPipe** (Google, cuts the person out for the "words behind you" effect) and its
    model are open source under Apache 2.0, downloaded during install.
  - Fonts come from Google Fonts (open licenses). Rendering needs an internet connection.
  - Full credits: `~/DVE/CREDITS.md`.

## 1. Run the steps

Run `./install.sh --step <name>` for each step below, one at a time. Before each, tell the person
the one-line purpose and size (from `./install.sh --list`). After each, confirm the OK line.
If a step FAILS, read the message, fix the cause if it's on this Mac (disk space, network), and
re-run the same step. Steps that are already done are skipped automatically.

1. `check` (no download). If disk space fails, tell them how much to free up and stop.
2. `node`
3. `ffmpeg`
4. `uv`
5. `python`
6. `venv` (the big one, ~1.3 GB, several minutes; on an Intel Mac say it uses the Intel library set)
7. `npm`
8. `models` (~1 GB)
9. `cutout` (~70 MB, the person-cutout library and its model)
10. `browser`
11. **brand**: ask the person two questions, one at a time:
    - "What's your brand color? Send a hex code like #F7C715, or say 'keep yellow'."
    - "Pick a font pair for your captions:" offer these four, default first:
      1. Hanken Grotesk + Playfair Display (clean and editorial, the default)
      2. Inter + Instrument Serif (minimal, airy)
      3. Montserrat + Fraunces (bold, warm)
      4. DM Sans + DM Serif Display (modern, friendly)
    - "For the follow card (a small card with your photo, name and a Follow button that some
      reels show): what name and handle should it show, and do you have a square photo of
      yourself? Send the file or say skip." Copy a sent photo to a path you can pass.
    Then run `./install.sh --step brand --accent '#RRGGBB' --sans <hanken|inter|montserrat|dmsans> --serif <playfair|instrument|fraunces|dmserif> --handle @theirhandle --name 'Their Name' --avatar /path/to/photo.jpg`
    (omit a flag to keep its default; the photo becomes engine/public/inserts/avatar.png).
12. `env`
13. `skill`
14. Run `tools/doctor.sh` and show the result.

## 2. First test video

Run the test so the person sees all three styles working on the included sample clip:

```
tools/smoke_test.sh
```

It builds the sample, renders Minimal, Hype and Studio (about 5-15 minutes total, longer on Intel),
and prints where the videos are. Open the folder for them (`open ~/DVE/engine/out`).
If it fails, show the last 20 lines of output and run `tools/doctor.sh`.

## 3. Hand off

Tell the person:
- "DVE is installed. To make a video: put your video and script in ~/DVE/inbox,
  open a NEW Claude Code session, and say: make a reel from my inbox."
- "Music is optional and must be music you're licensed to use. To add some, put the file in
  ~/DVE/engine/sounds/music, note its license in LICENSES.md there, and add its path to
  music_beds in ~/DVE/engine/sounds.json. Without music, videos have your voice plus DVE's own whoosh, land and click."
- "Stuck later? Set up Coach Chris, an AI version of me that answers from the DVE guide: open ~/DVE/coach/README.md."
- "To change your color, fonts, name or handle later, edit ~/DVE/engine/src/brand.json. Your follow-card photo is engine/public/inserts/avatar.png."
- "To remove everything: ~/DVE/tools/uninstall.sh"

## Notes for you (Claude)

- Uninstall: only run `tools/uninstall.sh --yes` after the person explicitly asks to remove
  DVE. It copies finished videos to ~/Desktop/DVE-videos first.
- Updating to a new version: `tools/update.sh --latest` (from GitHub) or `tools/update.sh ~/Downloads/DVE-<version>.zip`. It keeps the
  person's reels, brand.json, sounds.json and music, re-registers their reels, and refreshes the
  renderer packages and the skill.
