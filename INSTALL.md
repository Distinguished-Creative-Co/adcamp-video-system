# INSTALL.md: instructions for Claude Code (Windows preview)

You are installing AdCamp Video System for the person you are talking to, on a Windows PC. Follow these steps in
order. Keep each update to the person short and plain: what the step does, how big the download is, then run it. They
may not be technical. Never ask for an administrator, never install other software, never change a Windows setting,
and never change AVS's own files to get a step through.
The one exception the person handles themselves: Microsoft's free Visual C++ runtime, when the PC check says it's
missing.

Every command goes through the launcher in the AVS folder. In PowerShell: `& "$HOME\AVS\avs.cmd" <command>`, written
below as `avs <command>`. In Git Bash: `"$HOME/AVS/avs.cmd" <command>`. It sets its own environment on every call, so
there is no prefix and no `cd`. Never put text with a double quote in it on a command line (Windows PowerShell 5.1
splits it): write it to a file in your scratchpad and pass `@file=<that file>` to `avs run`.

## 0. Before you start

- Installed from the Plugins panel? The skill's quiet check already ran the plugin's `bootstrap.ps1 -FromPlugin`, which
  copied AVS into `~/AVS` and fetched its own Python. Skip the next two bullets and go on from "Tell the person".
- No `~/AVS` yet and the person gave you the link: download it without git, one command at a time:
  `curl.exe -fL -o "$HOME\Downloads\avs-windows.zip" https://github.com/Distinguished-Creative-Co/adcamp-video-system/archive/refs/heads/windows-preview.zip`
  (about 60 MB), then `New-Item -ItemType Directory -Force "$HOME\AVS-unpack" | Out-Null`, then
  `tar.exe -xf "$HOME\Downloads\avs-windows.zip" -C "$HOME\AVS-unpack"`, then
  `Move-Item "$HOME\AVS-unpack\adcamp-video-system-windows-preview" "$HOME\AVS"`, then
  `Remove-Item "$HOME\AVS-unpack"` (it's empty now). The zip stays in Downloads.
  An AVS folder somewhere else (Downloads, the Desktop) with no `runtime` folder in it: move it to `~/AVS` with
  `Move-Item` rather than downloading a second copy.
- The lines to say to the person come from "What the member hears" in the AVS skill. If the skill isn't loaded in this
  chat (they pasted the install line), read that section of `~/AVS/skills/avs/SKILL.md` now.
- Then the bootstrap, which checks the chip and fetches uv and AVS's own Python (about 50 MB):
  `powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\AVS\bootstrap.ps1"`. It stops on an ARM PC, or one
  with under 8 GB of memory, with one plain line: say that line from the AVS skill and stop.
- Tell the person the Windows welcome from the AVS skill ("Welcome to AVS. On Windows this is a preview: ...") and wait
  for their go. Then, on its own line: "Claude Code asks your permission before each step. I'll say what each one does
  first, so say yes when it matches."
- Show them these terms in plain words and get a "yes" before installing:
  - **Remotion** (the video renderer) is free for individuals and companies with up to 3 employees.
    A company with 4 or more employees needs a paid Remotion company license (remotion.pro).
    Ask first: "How many employees does your business have?" 4 or more: tell them they need that
    company license before using AVS for the business, point them to remotion.pro for the price, and let them
    decide before you go on.
  - **MediaPipe** (Google, cuts the person out for the "words behind you" effect) and its
    model are open source under Apache 2.0, downloaded during install.
  - Fonts come from Google Fonts (open licenses). Rendering needs an internet connection.
  - The full credits are in AVS's credits file: offer to open it for them (`avs open ../CREDITS.md`).

## 1. Run the steps

Run `avs install --step <name>` for each step below, one at a time, in this order: the cheap checks come first, so a
problem shows in minutes, not after an hour. Before each, tell the person its purpose and size in plain words, like
"Downloading the speech tools, about 1.8 GB" (the sizes are in `avs install --list`, but never read its folder names
out). After each, confirm its OK line.

Long steps: npm, browser, venv, models, cutout and the test video each take minutes. Run them in the background (or
with the longest timeout) and check back, so a time limit never cuts one off midway. A cut-off step is safe to run
again.
If a step FAILS: read the message. Its cause on this PC (disk space, the network): fix it and run the same step again.
A second failure of the same step: stop, run `avs report`, and say the step-failed line from the AVS skill. Every step
is safe to re-run, and finished ones go quickly.

1. `avs install --step check` (no download): the chip, Windows version, disk, memory and Microsoft's Visual C++ runtime. A stop: say its
   line from the AVS skill (an ARM chip, under 8 GB of memory, not enough space, the runtime with the link it printed)
   and stop there. Its memory note (8 to 15 GB): say once that videos will take longer.
2. `avs install --step uv`
3. `avs install --step python`
4. `avs install --step node`
5. `avs install --step ffmpeg`
6. `avs install --step npm`
7. `avs install --step browser`
8. `avs install --step still` (one test image from the renderer, before the big downloads. A failure here is worth a report right away)
9. `avs install --step venv` (the big one, about 1.8 GB, several minutes)
10. `avs install --step models` (about 1 GB)
11. `avs install --step cutout` (about 200 MB, the person-cutout library and its model)
12. `avs install --step ytdlp` (brings in reels they like so AVS can build a style from them. It's optional: if it fails twice, or their
    antivirus removes it, say the antivirus line below and carry on without it)
13. **brand**: these questions, one at a time. Picking up a stopped setup: skip the name, handle and photo questions
    when `engine/src/brand.json` already has a name, handle or avatar (confirm them in one line). Always ask the color
    and show the font sheet: the file starts with default color and fonts, so those prove nothing.
    - "First, the name you post under?"
    - "And your handle, like @yourpractice? (Or say skip.)"
    - "If you have a square photo of yourself for your follow card, drag it into the chat box. Or say skip."
      A dropped photo arrives with a file path: pass that. No path (or they emailed it): ask them to drop it into
      their AVS inbox (`avs open inbox`) and use it from there. An iPhone photo (HEIC) can't be read on a PC: ask for a
      JPG or PNG instead.
    - "What's your brand color? Name it, or drag your logo into the chat and I'll match it. Or say 'keep yellow'."
    - The fonts, shown, not named. First run `avs install --step env`, then
      `avs run font_sheet.py "Their Name" --accent '#RRGGBB'` (a name with a double quote in it: write it to a file and
      pass `@file=<that file>` in its place), put `~/AVS/engine/out/font-sheet.png` into the chat (SendUserFile in the
      desktop app, else `avs open out/font-sheet.png`), and ask "Which font pair do you like, 1 to 4?"
      1 = hanken + playfair, 2 = inter + instrument, 3 = montserrat + fraunces, 4 = dmsans + dmserif.
      (Poppins is also available as the main font if they ask for it by name.) Fonts set here: when they open the
      Picker later, they can leave its "Your fonts" row alone.
    Then run `avs install --step brand --accent '#RRGGBB' --sans <hanken|inter|montserrat|dmsans> --serif <playfair|instrument|fraunces|dmserif> --handle '@theirhandle' --name "Their Name" --avatar "<photo path>"`
    (the handle in single quotes, since PowerShell reads a bare @ as something else. Omit a flag to keep its default.
    The photo becomes engine/public/inserts/avatar.png). When it prints "a dark color", tell them in one line: "Your
    color is dark, so words over your video and photos use a lighter shade of it to stay readable. Light slides keep it
    exactly."
14. `avs install --step env`
15. `avs install --step skill` (from the Plugins panel it just confirms the plugin provides the skill).
16. Run `avs doctor`. All OK (its test video row says NOT YET until section 2): say "Everything's installed." Anything else: fix what it names, then tell them in
    one plain sentence what was missing and that it's sorted.

Their antivirus removed a tool (a step that just passed now fails with a missing file, or the antivirus says so): "Your
antivirus removed one of the tools AVS downloaded. That happens with new tools sometimes. Want me to leave it out? It's
only for building a look from a reel link, and everything else works without it." Never ask them to turn the
antivirus off.

## 2. First test video

Run the test. It proves the install and shows them AVS's everyday look on a real reel:

```
avs smoke
```

It cuts the included sample, puts it in the Clean Talk look and renders it, then checks the tools. On a PC that often
takes 20 to 40 minutes. Tell the person first: "Last setup step: a test video. On a PC it often takes 20 to 40 minutes.
Nothing is stuck, I'll tell you when it's ready." Run it in the background and check back. When it passes, make a phone
copy (`avs phone-copy out/sample.mp4`), put it in the chat (SendUserFile, display render, else
`avs open out/sample-phone.mp4`) and say: "Here's a test video, in Clean Talk, one of four starter looks. Next, yours."
(A dark brand color: the words show in a lighter shade of it, as you told them at the brand step.)
If it fails, read the last 20 lines (all of it is kept in `runtime/logs/test-video.log`, and `avs doctor` shows
the result) and run `avs doctor` yourself, fix what you can without changing AVS's own files and run it once more. Out of
memory: the skill's out-of-memory line, then stop. A test video row that says NO RESULT
means a run started and hasn't ended: if it is still running, wait for it. Start it again only once nothing is running. A second
failure: run `avs report` and say the test-failed line from the AVS skill.

## 2b. Their look (always, before the hand-off)

Follow "Their look" and "Pages beside the chat" in the AVS skill (if it isn't loaded in this chat, read
`~/AVS/skills/avs/SKILL.md`). In short:
- `avs run style_board.py`, publish `qa/style-board/pane.html` beside the chat (capabilities
  `{"comments": {"composer_only": true}}`, icon "palette". Without the pane: `avs open qa/style-board/index.html`),
  and say the look line.
- A look they name becomes the default (`avs run my_styles.py default <slug>`). A comment on the board (a tweak, a
  color, the type) changes it, and the board is rebuilt and republished until they say it's right.
- The Picker or links to reels they love: "The Picker" and "Styles from reels they like" in the skill. Saved, either
  becomes the default.
- No preference: Clean Talk becomes the default, said as "I'll start you on Clean Talk. Change it any time."
There is no skip: every install ends with a default look, so "make a reel" never asks which style.

## 3. Their first video, then hand off

Say: "Got a video of you talking? Drop it in your AVS inbox and say make a reel. Or do it later." (`avs open inbox`
when they want the folder.) Not sure how to get a video from their phone to the PC: the phone-video line in the AVS
skill. A video already in the inbox: go straight to the AVS skill's intake, in this chat when the skill is loaded (the
plugin install), else ask them to start a new chat and say "make a reel from my inbox".

When they're done for now, say this, and nothing more unless they ask:
"You're all set. Any time: drop a video in your AVS inbox and say make a reel. Want to know what else it can do?"
On a yes, one line each: music by vibe ("tell me a vibe, like calm and warm, and you pick from a few free tracks"),
styles from reels they love ("send me links"), the Picker ("open the picker"), changing color, fonts, name or photo
("just tell me"), Coach Chris for help ("show me the Coach Chris setup steps"), and "Uninstall AVS" to remove it.

## Notes for you (Claude)

- Music by vibe: "Music" in the AVS skill (`avs run find_music.py`, Openverse, CC0, CC BY and marked public domain
  only). They always choose by listening. A CC BY track's credit line goes into their caption draft by itself, and it
  stays wherever they post that video.
- Music they send: ask where it's from and whether its license covers ads if they run ads. Copy it into
  `engine/sounds/music/` (Read and Write tools, or `Copy-Item`), write the file, source and license in
  `engine/sounds/music/LICENSES.md`, and put it on the video with `avs run find_music.py --use sounds/music/<file>
  --reel <name>` once the first build has made that video's config (it also skips a quiet intro).
  If its license asks for a credit, write the line to a file and add `--credit @file=<that file>`, so every caption
  draft for that video carries it. Never pull music from anywhere else, and never generate it.
- Brand changes later ("make my color green", a new photo): `avs install --step brand` with only the flags that change
  (`--accent '#RRGGBB'`, `--sans`, `--serif`, `--handle '@...'`, `--name "..."`, `--avatar "<photo path>"`). The rest
  stay as they are. Then the next preview shows it.
- Uninstall: only run `avs uninstall --yes` after the person explicitly asks to remove AVS. It copies finished videos
  and carousel slides to an AVS-videos folder on their Desktop first, then the AVS folder goes a few seconds later.
- Updating: `avs update --latest` (the Windows preview, from GitHub). It keeps the person's reels, brand.json,
  sounds.json, music and styles, re-registers their reels, and refreshes the renderer packages and the skill. The
  skill checks for a new version once a day with `avs update --check` and offers it in the chat.
