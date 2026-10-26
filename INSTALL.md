# INSTALL.md: instructions for Claude Code

You are installing AdCamp Video System for the person you are talking to. Follow these steps in order.
Keep each update to the person short and plain: what the step does, how big the download is,
then run it. They may not be technical. Never use sudo. Nothing here needs a password.

## 0. Before you start

- Installed from the Plugins panel? The skill's quiet check already ran `tools/plugin_setup.sh`, which
  copied AVS into `~/AVS`. Skip the next bullet (the download) and go on from "Tell the person".
- Run all commands from `~/AVS`. If it doesn't exist yet and the person gave you the GitHub link, download it
  without git (a fresh Mac pops a developer-tools dialog the first time anything runs git):
  `mkdir -p ~/AVS && curl -fsSL https://github.com/Distinguished-Creative-Co/adcamp-video-system/archive/refs/heads/main.tar.gz | tar -xz -C ~/AVS --strip-components 1`
  (about 50 MB). Otherwise the folder came from a zip and may have landed somewhere else: Safari expands the
  zip into `~/Downloads/AVS` on its own, or the person may have unzipped it on the Desktop. If
  `runtime/` does not exist yet, move that folder to `~/AVS` (`mv ~/Downloads/AVS ~/AVS`) rather
  than unzipping a second copy. If only the zip exists: `ditto -x -k ~/Downloads/AVS-2.0.0.zip ~`
  (it creates `~/AVS`). A Google Drive download may show a "can't scan for viruses" page first:
  that is normal for a 50 MB file, click Download anyway.
- Tell the person: "Welcome to AVS. Setup takes up to an hour, mostly downloads and a test video. I'll ask you a
  few things along the way." Then, on its own line: "Claude Code asks your permission before each step. I'll say
  what each one does first, so say yes when it matches."
- Show them these terms in plain words and get a "yes" before installing:
  - **Remotion** (the video renderer) is free for individuals and companies with up to 3 employees.
    A company with 4 or more employees needs a paid Remotion company license (remotion.pro).
    Ask first: "How many employees does your business have?" 4 or more: tell them they need that
    company license before using AVS for the business, point them to remotion.pro for the price, and let them
    decide before you go on.
  - **MediaPipe** (Google, cuts the person out for the "words behind you" effect) and its
    model are open source under Apache 2.0, downloaded during install.
  - Fonts come from Google Fonts (open licenses). Rendering needs an internet connection.
  - The full credits are in AVS's credits file: offer to open it for them.

## 1. Run the steps

Run `~/AVS/install.sh --step <name>` for each step below, one at a time (always this full path). Before each, tell the person
its purpose and size in plain words, like "Downloading the speech tools, about 1.3 GB" (the sizes are in
`~/AVS/install.sh --list`, but never read its folder names out). After each, confirm the OK line.

Long steps: venv, npm, models, cutout, browser and the test video each take minutes. Run them in the background
(or with the longest timeout) and check back, so a time limit never cuts one off midway. A cut-off step is safe to
run again.
If a step FAILS, read the message, fix the cause if it's on this Mac (disk space, network), and
re-run the same step. Every step is safe to re-run, and finished ones go quickly.

1. `check` (no download). If disk space fails, tell them how much to free up and stop.
2. `node`
3. `ffmpeg`
4. `uv`
5. `python`
6. `venv` (the big one, ~1.3 GB, several minutes. On an Intel Mac say it takes a bit longer on their Mac)
7. `npm`
8. `models` (~1 GB)
9. `cutout` (~70 MB, the person-cutout library and its model)
10. `ytdlp` (~37 MB, brings in reels they like so AVS can build a style from them. When a download fails, it updates
    itself from its official releases and tries again, so it keeps working when Instagram or TikTok change)
11. `browser`
12. **brand**: these questions, one at a time. Picking up a stopped setup: skip the name, handle and photo questions
    when `engine/src/brand.json` already has a name, handle or avatar (confirm them in one line). Always ask the color
    and show the font sheet: the file starts with default color and fonts, so those prove nothing.
    - "First, the name you post under?"
    - "And your handle, like @yourpractice? (Or say skip.)"
    - "If you have a square photo of yourself for your follow card, drag it into the chat box. Or say skip."
      A dropped photo arrives with a file path: pass that. No path (or they emailed it): ask them to drop it into
      their AVS inbox (`open ~/AVS/inbox`) and use it from there.
    - "What's your brand color? Name it, or drag your logo into the chat and I'll match it. Or say 'keep yellow'."
    - The fonts, shown, not named. First run `~/AVS/install.sh --step env` (it writes the paths the sheet needs, and
      the env step below then has nothing left to do), then
      `cd ~/AVS/engine && . ~/AVS/runtime/env.sh && python3 scripts/font_sheet.py "Their Name" --accent '#RRGGBB'`
      (the npm and browser steps above make this work), put `~/AVS/engine/out/font-sheet.png` into the chat
      (SendUserFile in the desktop app, else `open` it), and ask "Which font pair do you like, 1 to 4?"
      1 = hanken + playfair, 2 = inter + instrument, 3 = montserrat + fraunces, 4 = dmsans + dmserif.
      (Poppins is also available as the main font if they ask for it by name.) Fonts set here: when they open the
      Picker later, they can leave its "Your fonts" row alone.
    Then run `~/AVS/install.sh --step brand --accent '#RRGGBB' --sans <hanken|inter|montserrat|dmsans> --serif <playfair|instrument|fraunces|dmserif> --handle @theirhandle --name 'Their Name' --avatar /path/to/photo.jpg`
    (omit a flag to keep its default. The photo becomes engine/public/inserts/avatar.png). When it prints "a dark
    color", tell them in one line: "Your color is dark, so words over your video and photos use a lighter shade of it to
    stay readable. Light slides keep it exactly."
13. `env` (`~/AVS/install.sh --step env`, like every step: always with the full path)
14. `skill` (from the Plugins panel it just confirms the plugin provides the skill). If it says it moved an older video
    skill to the Trash, tell them in one line: AVS replaces it, the old skill is in their Trash if they want it back, and their videos are untouched.
15. Run `~/AVS/tools/doctor.sh`. All OK: say "Everything's installed." Anything else: fix what it names, then tell them in
    one plain sentence what was missing and that it's sorted.

## 2. First test video

Run the test. It proves the install and shows them AVS's everyday look on a real reel:

```
~/AVS/tools/smoke_test.sh
```

It cuts the included sample, puts it in the Clean Talk look and renders it, then checks the tools (10 to 15 minutes,
longer on an Intel Mac). Run it in the background and check back. When it passes, make a phone copy
(`. ~/AVS/runtime/env.sh && ffmpeg -y -i ~/AVS/engine/out/sample.mp4 -vf scale=540:960 -crf 30 -c:a aac -b:a 96k ~/AVS/engine/out/sample-phone.mp4`),
put it in the chat (SendUserFile, display render, else `open` it) and say: "Here's a test video, in Clean Talk, one of
four starter looks. Next, yours." (A dark brand color: the words show in a lighter shade of it, as you told them at the brand step.)
If it fails, read the last 20 lines and run `~/AVS/tools/doctor.sh` yourself, fix what you can, and tell them in one plain
sentence what happened and what you're doing about it.

## 2b. Their look (always, before the hand-off)

Follow "Their look" and "Pages beside the chat" in the AVS skill (if it isn't loaded in this chat, read
`~/AVS/skills/avs/SKILL.md`). In short:
- `python3 scripts/style_board.py`, publish `qa/style-board/pane.html` beside the chat (capabilities `{"comments": {"composer_only": true}}`, icon "palette";
  in a terminal without the pane, `open qa/style-board/index.html`), and say the look line.
- A look they name becomes the default (`my_styles.py default <slug>`). A comment on the board (a tweak, a color, the
  type) changes it, and the board is rebuilt and republished until they say it's right.
- The Picker or links to reels they love: "The Picker" and "Styles from reels they like" in the skill. Saved, either
  becomes the default.
- No preference: Clean Talk becomes the default, said as "I'll start you on Clean Talk. Change it any time."
There is no skip: every install ends with a default look, so "make a reel" never asks which style.
Each command runs in a fresh shell, so start every one with `cd ~/AVS/engine && . ~/AVS/runtime/env.sh && `.

## 3. Their first video, then hand off

Say: "Got a video of you talking? Drop it in your AVS inbox and say make a reel. Or do it later." (`open ~/AVS/inbox`
when they want the folder.) A video already in the inbox: go straight to the AVS skill's intake, in this chat when
the skill is loaded (the plugin install), else ask them to start a new chat and say "make a reel from my inbox".

When they're done for now, say this, and nothing more unless they ask:
"You're all set. Any time: drop a video in your AVS inbox and say make a reel. Want to know what else it can do?"
On a yes, one line each: music by vibe ("tell me a vibe, like calm and warm, and you pick from a few free tracks"),
styles from reels they love ("send me links"), the Picker ("open the picker"), changing color, fonts, name or photo
("just tell me"), Coach Chris for help ("show me the Coach Chris setup steps"), and "Uninstall AVS" to remove it.

## Notes for you (Claude)

- Music by vibe: "Music" in the AVS skill (`scripts/find_music.py`, Openverse, CC0, CC BY and marked public domain
  only). They always choose by listening. A CC BY track's credit line goes into their caption draft by itself, and it
  stays wherever they post that video.
- Music they send: ask where it's from and whether its license covers ads if they run ads. Copy it into
  `engine/sounds/music/`, write the file, source and license in `engine/sounds/music/LICENSES.md`, and put it on the
  video with `python3 scripts/find_music.py --use sounds/music/<file> --reel <name>` once the first build has made
  that video's config (it also skips a quiet intro).
  If its license asks for a credit, add `--credit "<the line it asks for>"` to that command, so every caption draft
  for that video carries it. Never pull music from anywhere
  else, and never generate it.
- Brand changes later ("make my color green", a new photo): run `~/AVS/install.sh --step brand` with only the flags that change (`--accent '#RRGGBB'`, `--sans`, `--serif`, `--handle`, `--name`, `--avatar <photo path>`). The rest stay as they are, and a photo gets cropped square and set on the follow card and carousels. Then the next preview shows it.

- Uninstall: only run `~/AVS/tools/uninstall.sh --yes` after the person explicitly asks to remove
  AVS. It copies finished videos and carousel slides to ~/Desktop/AVS-videos first.
- Updating to a new version: `~/AVS/tools/update.sh --latest` (from GitHub) or `~/AVS/tools/update.sh ~/Downloads/AVS-<version>.zip`. It keeps the
  person's reels, brand.json, sounds.json, music and styles, re-registers their reels, and refreshes the
  renderer packages and the skill (and the plugin, when AVS came from the Plugins panel). The skill checks
  for a new version once a day with `~/AVS/tools/update.sh --check` and offers it in the chat.
