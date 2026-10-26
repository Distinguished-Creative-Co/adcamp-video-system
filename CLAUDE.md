# CLAUDE.md: you are looking at AdCamp Video System (AVS)

AVS turns a phone video of the person talking, plus their script, into a finished vertical
video. This file tells you what to do when you open this folder.

## Not installed yet (no `runtime/env.sh` in this folder)

1. This folder belongs at `~/AVS`. If it is somewhere else (Downloads, Desktop, a subfolder, or a
   `adcamp-video-system-main` folder from GitHub), move it there first: `mv "<this folder>" ~/AVS`, then work from `~/AVS`.
   Do not make a second copy by downloading or unzipping again.
2. Open `INSTALL.md` and follow it step by step. Tell the person what each step downloads and
   how big it is before it starts, and ask before anything that needs an account, a password or
   a choice from them. Never use sudo. Nothing here needs a password.
3. The install ends with `tools/doctor.sh` (all OK), `tools/smoke_test.sh` (one test video in the Clean Talk look),
   and their look (INSTALL.md 2b): every install ends with a default look. Do not call it done before all three.

## Installed (`runtime/.installed` exists, written when the install test passes)

`runtime/env.sh` without `runtime/.installed`: run `tools/doctor.sh`. All OK and `engine/out/sample.mp4` exists (an
older install whose test video rendered): `touch runtime/.installed`. Otherwise setup stopped partway: continue
`INSTALL.md` from step 1.

- Never move or rename this folder: `runtime/env.sh` records its paths.
- To make a video, the person puts their clip and script in `inbox/` and says "make a reel".
  The Claude Code skill `avs` runs the engine; its rules are in `engine/CLAUDE.md`.
- Something broken: `tools/doctor.sh` says what is missing and which step fixes it.
- New version: `tools/update.sh --latest` (from GitHub) or `tools/update.sh <path to a new zip>` keeps their reels, brand, music and styles.
  `tools/update.sh --check` says whether there is one (the skill runs it at the start of each chat).
- Installed from the Plugins panel (`runtime/.via-plugin` exists): the skill comes from the plugin, not ~/.claude/skills.
- Remove everything: `tools/uninstall.sh --yes`, only when the person asks for that.

`START-HERE.md` is the one-page guide written for the person. `CREDITS.md` lists what AVS is
built on and the licenses.
