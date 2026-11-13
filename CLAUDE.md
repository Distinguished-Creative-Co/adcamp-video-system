# CLAUDE.md: you are looking at AdCamp Video System (AVS)

AVS turns a phone video of the person talking, plus their script, into a finished vertical
video. This file tells you what to do when you open this folder.

## Not installed yet (no `runtime/base` in this folder)

1. This folder belongs at `~/AVS`. If it is somewhere else (Downloads, Desktop, a subfolder, or a
   `adcamp-video-system-windows-preview` folder from GitHub), move it there first (in PowerShell:
   `Move-Item "<this folder>" "$HOME\AVS"`), then work from `~/AVS`.
   Do not make a second copy by downloading or unzipping again.
2. Open `INSTALL.md` and follow it step by step. Tell the person what each step downloads and
   how big it is before it starts, and ask before anything that needs an account, a password or
   a choice from them. Never ask for an administrator: nothing here needs one, except Microsoft's free Visual C++
   runtime on a PC that lacks it, which the person installs themselves from the link the check prints.
   Every command goes through the launcher in this folder: `& "$HOME\AVS\avs.cmd" <command>` in PowerShell (written
   `avs <command>` below). The first step is `bootstrap.ps1`, which fetches AVS's own Python for it.
3. The install ends with `avs doctor` (all OK), `avs smoke` (one test video in the Clean Talk look),
   and their look (INSTALL.md 2b): every install ends with a default look. Do not call it done before all three.

## Installed (`runtime/.installed` exists, written when the install test passes)

`runtime/base` without `runtime/.installed`: run `avs doctor`. It ends with "All set" (its test video passed):
`avs flag installed`. Otherwise setup stopped partway: continue
`INSTALL.md` from step 1.

- Never move or rename this folder: its runtime records its paths.
- To make a video, the person puts their clip and script in `inbox/` and says "make a reel".
  The Claude Code skill `avs` runs the engine; its rules are in `engine/CLAUDE.md`.
- Something broken: `avs doctor` says what is missing and which step fixes it.
- Never change AVS's own scripts, tools, engine code or settings to get past a failure, not one number, and never offer
  to. Run the step once more, then stop and say what stopped. The skill's rules list the few files a request may change.
- New version: `avs update --latest` (from GitHub) or `avs update <path to a new zip>` keeps their reels, brand, music and styles.
  `avs update --check` says whether there is one (the skill runs it at the start of each chat).
- Installed from the Plugins panel (`runtime/.via-plugin` exists): the skill comes from the plugin, not ~/.claude/skills.
- Remove everything: `avs uninstall --yes`, only when the person asks for that.

`START-HERE.md` is the one-page guide written for the person. `CREDITS.md` lists what AVS is
built on and the licenses.
