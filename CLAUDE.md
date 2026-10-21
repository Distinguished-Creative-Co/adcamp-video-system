# CLAUDE.md: you are looking at Distinguished Vertical Editor (DVE)

DVE turns a phone video of the person talking, plus their script, into a finished vertical
video. This file tells you what to do when you open this folder.

## Not installed yet (no `runtime/env.sh` in this folder)

1. This folder belongs at `~/DVE`. If it is somewhere else (Downloads, Desktop, a subfolder, or a
   `dve-main` folder from GitHub), move it there first: `mv "<this folder>" ~/DVE`, then work from `~/DVE`.
   Do not make a second copy by downloading or unzipping again.
2. Open `INSTALL.md` and follow it step by step. Tell the person what each step downloads and
   how big it is before it starts, and ask before anything that needs an account, a password or
   a choice from them. Never use sudo. Nothing here needs a password.
3. The install ends with `tools/doctor.sh` (all OK) and `tools/smoke_test.sh` (three sample
   videos). Do not call it done before both pass.

## Installed (`runtime/env.sh` exists)

- Never move or rename this folder: `runtime/env.sh` records its paths.
- To make a video, the person puts their clip and script in `inbox/` and says "make a reel".
  The Claude Code skill `dve` runs the engine; its rules are in `engine/CLAUDE.md`.
- Something broken: `tools/doctor.sh` says what is missing and which step fixes it.
- New version: `tools/update.sh --latest` (from GitHub) or `tools/update.sh <path to a new zip>` keeps their reels, brand and music.
- Remove everything: `tools/uninstall.sh --yes`, only when the person asks for that.

`START-HERE.md` is the one-page guide written for the person. `CREDITS.md` lists what DVE is
built on and the licenses.
