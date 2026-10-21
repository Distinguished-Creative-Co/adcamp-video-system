# Distinguished Vertical Editor

Turn a phone video of you talking plus your script into a finished, captioned vertical video
(Reels, Shorts, TikTok, Meta ads) in one of three styles:

- **Studio**: the full build. Glass cards, a stat or proof panel, words behind you, a call-to-action card.
- **Minimal**: bold captions only. Nothing else on screen.
- **Hype**: two-font animated captions, zoom punches, big words behind you.

It runs on your own Mac (Apple Silicon or Intel), inside Claude Code. Your videos never leave your computer.

## Install (about 20-40 minutes, mostly downloads)

1. Open Claude Code (the Code tab in the Claude desktop app is easiest).
2. Paste this, exactly:

```
Install Distinguished Vertical Editor for me from https://github.com/Distinguished-Creative-Co/dve into ~/DVE, then open ~/DVE/INSTALL.md and follow it step by step. Tell me what each step downloads and how big it is before it starts, and ask me before anything that needs an account, a password, or a choice from me.
```

Have the zip instead (`DVE-1.0.0.zip`)? Put it in Downloads and say "Install Distinguished Vertical Editor from ~/Downloads/DVE-1.0.0.zip into ~/DVE, then follow ~/DVE/INSTALL.md".

The first time you start Claude Code from a terminal, it asks you to pick a color theme, sign in
to your Claude account, and trust the folder before it reads your message. That's normal. Using
the Code tab in the Claude desktop app skips those screens.

That's it. Claude walks you through everything, asks you to pick your brand color and fonts,
and finishes with a test video in all three styles.

## Making a video, once installed

Put your video and your script in `~/DVE/inbox`, open a new Claude Code session, and say:

```
Make a reel from the video and script in my inbox.
```

Claude asks which style (Studio, Minimal or Hype) and whether it's an organic post or a paid ad,
shows you a storyboard to leave notes on and approve, then renders it.

## Stuck?

Set up **Coach Chris**, an AI version of Chris that answers from the DVE guide, in about two minutes:
see `coach/README.md`.

## What you need

- A Mac with macOS 12 or newer and about 12 GB free.
- Claude Code (the only account you need). Everything else is free and installed for you.
- A video filmed vertically, with a pause between sentences. Say "reset, reset" after a mistake
  and start the sentence again: the engine keeps your last clean take.
