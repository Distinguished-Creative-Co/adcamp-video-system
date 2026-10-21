# DVE Guide: everything Coach Chris knows

Distinguished Vertical Editor (DVE) by Chris Serra, built for AdCamp members. Cite sections by name, like (Guide: Fixes).

## What DVE is

DVE turns a phone video of you talking, plus your script, into a finished, captioned vertical video for Reels, Shorts, TikTok and Meta ads. It runs inside Claude Code on your own Mac: the cutting, transcribing and rendering all happen on your computer. Claude Code reads your transcript and preview stills to build the edit, and rendering needs an internet connection for the fonts.

- Mac only, Apple chip or Intel, macOS 12 or newer, about 12 GB free.
- Claude Code is the only account you need. Everything else installs for you, free.
- Model: Chris runs it on Opus 5.5 and recommends it. Sonnet works but takes longer. Fable isn't needed and uses up your limits fast.

## Install

1. Open Claude Code in your home folder (the Code tab in the Claude desktop app is easiest) and paste this, exactly:

```
Install Distinguished Vertical Editor for me from https://github.com/Distinguished-Creative-Co/dve into ~/DVE, then open ~/DVE/INSTALL.md and follow it step by step. Tell me what each step downloads and how big it is before it starts, and ask me before anything that needs an account, a password, or a choice from me.
```

2. Have the zip instead (`DVE-1.0.0.zip`, from a link Chris shared)? Put it in Downloads and say: "Install Distinguished Vertical Editor from ~/Downloads/DVE-1.0.0.zip into ~/DVE, then follow ~/DVE/INSTALL.md". A Google Drive link may show a "can't scan for viruses" page first: that's normal for a 50 MB file, click Download anyway.
3. Before installing, Claude shows you the terms and waits for your yes. The one that matters: **Remotion** (the video renderer) is free for individuals and companies of up to 3 people. A company with 4 or more employees needs a paid Remotion company license (remotion.pro).
4. Claude runs each step, says what it downloads and how big it is, and asks for your choices: your brand color, a font pair, and the name, handle and photo for your follow card. Expect a permission prompt from Claude Code for each command. You can approve them one by one, or allow commands in `~/DVE`.
5. It ends by making a test video from the included sample in all three styles (about 5 to 15 minutes, longer on Intel). Open them with `open ~/DVE/engine/out`.

Timing: 20 to 40 minutes the first time, about 3 GB of downloads. Longer on an Intel Mac.

The first time you open Claude Code from a terminal it asks for a color theme, a sign-in and to trust the folder. That's normal. The Code tab in the desktop app skips those screens.

## Making a video

1. Put your video (.mov or .mp4) and your script (.txt) in `~/DVE/inbox`.
2. Open a NEW Claude Code session and say: "Make a reel from the video and script in my inbox."
3. Claude asks which style (Studio, Minimal or Hype) and whether it's a regular post or a paid Meta ad.
4. It cuts your takes, builds a preview, and shows you the storyboard. Nothing renders until you say approved.
5. After the render you get, in `~/DVE/engine/out`: the video (upload this one), a phone copy, and cover images and static ads in the `<name>-companions` folder. The caption draft is `~/DVE/engine/script/<name>-post.md`, or `<name>-ad.md` for a paid ad. Nothing is ever posted for you.

No script? It still works: Claude writes the script from what you said. With a script it's better, because the script is the map for where to cut and what the captions say.

## The three styles

- **Studio**: the full build. Glass cards, a stat or proof panel, words behind you, a call-to-action card. Best for teaching, or an ad with a number or proof to show.
- **Minimal**: bold captions only, nothing else on screen. Good for everyday posts and as a plain second version of an ad to test.
- **Hype**: two-font animated captions, zoom punches, big words behind you. Energetic everyday posting.

You can ask for two styles from the same take. Mixing styles across your posts keeps your feed from looking the same every day. Words behind you, the follow card and your own clips appear in Studio and Hype. Minimal drops them on purpose.

## The preview and the storyboard

Before anything renders, Claude shows you a storyboard page: one row per beat (b01, b02...) with stills, the words you say there, what moves on screen, what you hear, and a box for a note.

- Leave a note on any beat you want changed, like "b03: hold the stat a second longer" or "b05: no words behind me here". Press Save notes.
- When it all looks right, press "Looks good, render it", then tell Claude approved.
- "What I need from you" at the top lists anything only you can provide, like a screen recording of your booking page, each one specific enough to shoot without asking. Placeholders fill in until you send it.

## Filming (Chris's rules)

DVE's own rules: film vertical, pause between sentences, and say "reset, reset" after a mistake. The rest is how Chris films.

- Film vertical on your phone. The phone you have is the right camera.
- Look into the lens, not at the screen or yourself.
- Light in front of you, a window is perfect. Never a bright light or window behind you, and avoid standing right under a ceiling light.
- Frame from mid-chest up with a little space above your head.
- Say the whole script, through the ending, in one session.
- Pause a beat between sentences. DVE only cuts in pauses, so the breaths you leave are its room to work.
- Made a mistake? Stop, say "reset, reset", and start that whole sentence again. DVE keeps your last clean take of each line.
- Reading lines fed to you or from a teleprompter? Slow down. Rushing to beat the flubs makes more of them.
- Dated claims stay dated. If something happened last week, say "last week", not "today".

## What goes on screen (and what never does)

- Every word on screen is your claim, in public. DVE refuses to put a number on screen that you didn't say out loud.
- Never invented results, reviews, prices or guarantees.
- Proof panels use real screenshots you supply, with a true source line. Never staged or edited.
- For health or money ads, Claude will flag lines Meta may reject before you post.

## Extras

- **Words behind you**: one to three of your own spoken words, huge, behind your head on a full-screen shot.
- **Follow card**: a card with your photo, name, handle and a Follow button that taps to Following. Set them during install, or later in `~/DVE/engine/src/brand.json` (photo at `engine/public/inserts/avatar.png`).
- **Your own clips**: a short clip of your office, your hands or your screen playing in a card above you while you keep talking. Your own footage only, never stock or someone else's.
- **Effects** (Studio and Hype): short graphics tied to the words you say, like a word stamped on screen, your words huge one at a time, an icon struck through ("no ads"), your website scrolling, a circle drawn on a screenshot, keys typing out SITE, a receipt printing a short list, a title card, one big number, or a pie. Ask for one by name on a storyboard note, like "b03: stamp the word recommended". Numbers and words on screen must be ones you said.
- **Transitions**: a whip, zoom or spin on the camera, or an iris or bars wipe, at the moment the picture cuts. Minimal keeps the camera ones.
- **Smoother cuts (automatic)**: at every cut the next sentence starts a beat before its picture, and full-screen shots switch between a wide and a slightly tighter framing so cuts feel like a camera change. Already trimmed your clip in CapCut or Edits? DVE lines its cuts up with yours so nothing flashes.
- **Sounds**: DVE comes with its own whoosh, land, click, impact, pop, ding and riser. They were made from scratch for DVE (no samples or recordings), so there's no license to worry about. They play on scene changes, panels, words behind you, cards and the call to action, all under your voice. To turn one off, ask Claude to set it to null in `~/DVE/engine/sounds.json`.
- **Music**: optional, and only music you're licensed to use, with a license that covers ads if you'll run it in one (Mixkit's does). Good sources: Mixkit, YouTube Audio Library, Uppbeat, Epidemic Sound, Artlist. Put the file in `~/DVE/engine/sounds/music`, note its license in `LICENSES.md` there, and add it to `music_beds` in `~/DVE/engine/sounds.json`. Claude never downloads or picks music for you. Many tracks start quiet: Claude can skip the intro so the music is there from the first second.
- **Your look**: color and fonts live in `~/DVE/engine/src/brand.json`. Sans fonts: hanken, inter, montserrat, dmsans, poppins. Serif fonts (Hype key words): playfair, instrument, dmserif, fraunces. Any change means a new preview and a new approval before the next render.

## Common requests after a render

- "Music too loud" or "too quiet": Claude changes the level for that reel.
- "Music comes in late": Claude skips further into the track.
- "Too much zooming" (Hype): Claude removes some zooms.
- "Too bright, make it more cinematic": Claude adds a grade to your footage.
- "There's a long pause at 0:39": Claude trims it, then shows you the preview again.
- Any change after you approve means a new preview and a new approval. That's on purpose.

## Updates

Tell Claude Code: "Run ~/DVE/tools/update.sh --latest". It downloads the newest version from GitHub (about 50 MB). Installed from a zip and have a newer zip? "Run ~/DVE/tools/update.sh ~/Downloads/DVE-<version>.zip" works too. It keeps your reels, brand, sounds settings and music, then refreshes the renderer packages, the cutout library and the skill, so it needs internet and a few minutes. Start a new Claude Code session afterwards.

## Fixes

Start most install problems the same way: tell Claude Code "run ~/DVE/tools/doctor.sh and fix what it says is missing". Each missing line names the install step that fixes it.

- **The doctor says all OK but videos won't render**: the doctor doesn't check the renderer's browser. Ask Claude to run `./install.sh --step browser` in `~/DVE`.
- **The install stopped partway**: run the doctor, then let Claude re-run the step it names. Steps that already finished are skipped.
- **"only N GB free. DVE needs about 12 GB"**: free up space (empty the Trash, move large files), then run the install again.
- **The DVE folder ended up in the wrong place** (Safari expanded the zip into Downloads, or you unzipped it on the Desktop): before the install finishes, Claude moves that folder to `~/DVE` instead of unzipping a second copy. After the install, never move or rename `~/DVE`.
- **"Pick a repository" or GitHub questions**: you're in the cloud version of Claude Code. Start a new session in the Claude desktop app's Code tab instead, which works with your Mac's files.
- **The test video failed**: ask Claude to run `~/DVE/tools/smoke_test.sh` again and show you the last 20 lines, then run the doctor.
- **Claude doesn't know what "make a reel" means**: start a NEW session. If it still doesn't, run the doctor: the skill line should say OK.
- **It seems stuck with no output**: Claude Code may be waiting on a permission prompt. Look for it in the window.
- **A sentence is missing from the cut**: you said it differently from the script. Claude updates the script to what you said and re-runs.
- **It kept the wrong take**: tell Claude which one you want. It can keep a specific take by its number from the takes report.
- **"No silence" at a take edge**: usually street or room noise between your sentences. Claude re-runs it in the mode for noisy audio.
- **You fumbled inside a take it kept**: tell Claude the time ("at 0:24 I tripped over a word") and it trims that bit, inside a pause.
- **Your face is cut off or off-center**: tell Claude. It re-frames from a still, which resets the config, so any copy changes get re-applied after.
- **Text in your shot reads backwards**: the front camera saved it mirrored. Claude flips it.
- **Landscape video**: not supported. Film vertical.
- **The render refuses to start**: something changed after you approved. Look at the new preview and approve again.
- **The render fails partway**: rendering needs internet for the fonts. Check your connection and try again.
- **Can't find your finished videos**: they're in `~/DVE/engine/out`. Tell Claude "open my DVE out folder".
- **Still stuck after two fixes**: post in the AdCamp community with the error text or a screenshot.

## Removing DVE

Tell Claude: "Uninstall DVE." It asks you to type REMOVE to confirm. It copies your finished videos (everything in `~/DVE/engine/out`) to `~/Desktop/DVE-videos`, then deletes the whole `~/DVE` folder and the DVE skill. That includes your inbox, so save any original footage or scripts you want to keep somewhere else first.
