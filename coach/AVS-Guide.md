# AVS Guide: everything Coach Chris knows

AdCamp Video System (AVS) by Chris Serra, built for AdCamp members. Cite sections by name, like (Guide: Fixes).

## What AVS is

AVS turns a phone video of you talking (plus your script, if you have one) into a finished, captioned vertical video for Reels, Shorts, TikTok and Meta ads. It runs inside Claude Code on your own Mac: the cutting, transcribing and rendering all happen on your computer. Claude Code reads your transcript and preview stills to build the edit, and rendering and the storyboard page need an internet connection for the fonts, which load from Google Fonts. Your style board, video setup page, storyboard, Picker and carousel slides open as private pages in your Claude account, beside the chat, so their frames go to Claude the way your chat does. Only you can see them. Say "keep it on my Mac" and Claude uses pages in your browser instead.

- Mac only, Apple chip or Intel (Intel is supported but not yet tested on a real Intel Mac), macOS 12 or newer, about 12 GB free.
- You need a Claude plan that includes Claude Code. Everything else installs for you.
- Remotion (the part that draws the video) is free for individuals and for companies with up to 3 employees. A company with 4 or more employees needs a paid Remotion company license (remotion.pro).
- Use the strongest Claude model your plan allows. Smaller models work but take longer and need more nudging.

## Install

1. Easiest: in the Claude desktop app's Code tab, click the **+** next to the message box, then **Plugins**, **Browse plugins**, **Add**, **Add marketplace**, **Add from a repository**. Paste `https://github.com/Distinguished-Creative-Co/adcamp-video-system`, click **Sync**, install **AdCamp Video System**, start a new chat and say "Set up AVS". Or start a new chat in the Code tab and paste this, exactly:

```
Install AdCamp Video System for me from https://github.com/Distinguished-Creative-Co/adcamp-video-system into ~/AVS (download it as a tar.gz with curl, not with git), then open ~/AVS/INSTALL.md and follow it step by step. Tell me what each step downloads and how big it is before it starts, and ask me before anything that needs an account, a password, or a choice from me.
```

2. If you have the zip instead (`AVS-2.0.0.zip`, from a link Chris shared), put it in Downloads and say: "Install AdCamp Video System from ~/Downloads/AVS-2.0.0.zip into ~/AVS, then follow ~/AVS/INSTALL.md". A Google Drive link may show a "can't scan for viruses" page first: that's normal for a 50 MB file, click Download anyway.
3. Before installing, Claude shows you the terms and waits for your yes. The one that matters: **Remotion** (the video renderer) is free for individuals and for companies with up to 3 employees. A company with 4 or more employees needs a paid Remotion company license (remotion.pro).
4. Claude runs each step, says what it downloads and how big it is, and asks for your choices: your brand color, a font pair, and the name, handle and photo for your follow card. Expect a permission prompt from Claude Code for each command. You can approve them one by one, or choose the option that allows them for the AVS folder so it stops asking.
5. It makes a test video from the included sample in Clean Talk, one of the four starter looks (10 to 15 minutes, longer on Intel), and plays it in the chat.
6. Then it sets your look, every time, so you never have to pick one per video: send links to reels you love, open the Picker, or pick one of the four starter looks. Then drop in your first video and say "make a reel".

Timing: 20 to 40 minutes the first time, about 3 GB of downloads, then the test video adds 10 to 15 minutes. Longer on an Intel Mac.

The first time you open Claude Code from a terminal it asks for a color theme, a sign-in and to trust the folder. That's normal. The Code tab in the desktop app skips those screens.

## Making a video

1. Get your video onto your Mac (AirDrop from your phone is easiest), tell Claude "open my AVS inbox" and drop it in. Add your script as a text file, or paste it into the chat. If you filmed it as a few clips, put them all in. AVS puts them in the order you recorded them, and clips filmed more than 10 minutes apart become separate videos.
2. In a chat, say: "Make a reel from the video in my inbox." (Right after installing or updating, start a new chat first.)
3. Your setup opens beside the chat: pick your captions (8 styles, each playing), up to four effects (21 of them, each playing, grouped by what they're for, two to four works best), a color for your footage (Natural, Bright and Clean, Warm, Cool, Soft Film, Moody or Cinematic, each shown on a frame of your own video), paste your script if you have one, and choose regular post or paid ad and a music vibe. It's filled in from last time, so a video like your last one is one press of Start. Say "make it in Big Energy" to use another look for this one. Claude only asks before cutting when something needs you, like a word it wasn't sure it heard right.
4. It cuts your takes, plays a quick draft of the whole video right in the chat (half size, marked DRAFT, about a minute to make), and opens your storyboard beside the chat. Comment on any part you'd change, or give notes in plain words or by time, like "at 0:12, cut tighter". It makes the changes, updates the storyboard and plays a fresh draft. The real video renders only after you say "render it". It takes a few minutes, longer for a long video or on an Intel Mac. Want a change after that? Comment again, and the new version lands next to the first.
5. The finished video plays in the chat too. In `~/AVS/engine/out` you get: the video (upload this one), a phone copy, and, when the video has a cover title, cover images and static ads in the `<name>-companions` folder. Claude pastes your caption draft into the chat at the end, ready to trim and copy. Nothing is ever posted for you.

No script? It still works: Claude writes the script from what you said. With a script it's better, because the script is the map for where to cut and what the captions say.

## Your look

Every video comes out in your look. You set it once at install on your style board, a page beside the chat with your fonts, your colors and the looks playing. Comment on it to change anything, any time ("show me my style", "open the picker", or send reel links). Four starter looks come with AVS, full frame with you in the middle, in your own fonts and brand color:

- **Clean Talk**: one word at a time, low and clean, a hook title over your head at the start. The everyday look.
- **Big Energy**: bold one-or-two-word captions, zoom punches, big words behind you. Fast and loud.
- **Soft Story**: words that step down softly, the key word in your second font, gentle moves. For stories and trust.
- **Show and Tell**: clear captions on a dark strip, with graphics for the numbers, lists and screenshots you mention. For teaching and ads (in an ad, "Click Learn More" stands in for the comment keyword).

Want one a little different? Say so ("calmer captions", "white words with my color on the key ones", "less movement") and Claude saves your own version of it. Or build a look from reels you love (Your own styles, below). You can also ask for a second version of any video in another look, which is handy for testing two versions of an ad.

## The Picker

If you're not sure what you want, tell Claude "open the picker". A page opens beside the chat with every starter look, caption look, effect, transition and font pair. Hover over a card, or press its play button, to watch it on a sample video. Your own saved styles are listed too, without a preview. Click a card to pick it.

- **A starter look:** one pick sets everything (Clean Talk, Big Energy, Soft Story, Show and Tell, or a style you saved).
- **Mix your own:** pick a caption look (Lines, Punch, Two-Font, One Word, Big Word, Pill, Editorial, Steps), any effects and any transitions.
- Press **Save my pick**, then go back to Claude. A mix gets a name and becomes one of your styles (and your default, if you don't have one yet). Claude only uses a picked effect where it fits what you're saying, and tells you when one didn't fit.
- Picking a starter look makes it your default for new videos.
- **Your fonts** (optional, under either way): four font pairs playing on the sample. The plain words are your main font, the slanted key word is your second font. Your pick is used in every video, card and carousel.
- To keep an effect to one part of your videos, turn on "Choose where in your video each effect may go", tick the effect, then press Start, Middle or End on it. Start means your opening line or two, End means your closing.
- The page is a private page in your Claude account, and your saved pick is kept with it. Change your picks any time: "open the picker" again. (Said "keep it on my Mac"? Then it opens in your browser instead.)

## Your own styles

If you love how someone else's reels are edited, send Claude the links (Instagram, TikTok, YouTube Shorts and most others) or the video files, and say "make me a style like these". You can mix: the captions from one, the cards from another. Or describe the look in your own words.

- Claude studies each reel start to finish, asks what you want from each one, then rebuilds that look on YOUR video: the type, colors, where the words sit, how they move, the pace. It shows you the result next to the example, with a plain list of what matches and what it couldn't match.
- Give notes until it's right, then it's saved under the name you pick. After that, drop your video in and say "make it in <name>". It becomes your default if you don't have one yet.
- Some posts only show to people who are logged in. Claude asks before using your browser's login for that one download. Your login is not stored. Instagram and TikTok don't officially allow downloading posts and sometimes block it. Using your browser's login can make your Mac ask for your Mac password: that's macOS, and you can say no and drop the file in instead. AVS only keeps the copy on your Mac to study the look and never posts it. If a download is blocked, or you'd rather not, save the video yourself and drop the file in.
- What's copied is the look, never the other creator's footage, music, words, logo or name. Fonts come from open-licensed ones: Claude tells you which face stands in for theirs.
- What AVS can't do (yet): copy another creator's music, speed ramps, 3D, or stock and meme images. It says so instead of faking it.
- Manage them anytime: "what styles do I have", "make Soft Story my default", "rename it", "get rid of that style" (it's hidden, not deleted). The four starter looks stay as they are.

## Carousels

Say "make a carousel about <topic>" or "turn my last reel into a carousel". Claude writes the words for every slide and the post caption first, in your voice (from a reel, from what you actually said), and shows them to you as a list. Nothing is designed until you say yes.

Then it designs the slides in your style's type and color with your handle and photo, and opens them beside the chat to swipe like the real post. Comment on any slide to change it. The slides land in `~/AVS/engine/carousels/<name>/slides`. Say "redo slide 3" or "make it square" to change things. Nothing is ever posted for you.

The same slide design works inside your videos as a card: the page fills the frame for a key point, you move into a small window in the corner, and each item ticks as you say it.

## The draft and the storyboard

Before the real render, Claude plays you a draft in the chat: the whole video at half size with sound, a red "DRAFT, not for posting" tag at the top. Never post the draft. It's there so you judge the edit in motion before you approve. In a terminal instead of the desktop app, Claude opens it for you.

With the draft, Claude opens your storyboard beside the chat: one row per part of the video (Part 01, Part 02...) with stills, the words you say there, what moves on screen and what you hear.

- Press Comment on this part on anything you want changed, like "hold the stat a second longer" or "no words behind me here", and send it to Claude. Claude makes the change, updates the storyboard and answers in the comment.
- When it all looks right, say "render it" in the chat.
- "What I need from you" at the top lists anything only you can provide, like a screen recording of your booking page, each one specific enough to shoot without asking. Placeholders fill in until you send it.

## Filming (Chris's rules)

AVS's own rules: film vertical, pause between sentences, and say "reset, reset" after a mistake. The rest is how Chris films.

- Film vertical on your phone. The phone you have is the right camera.
- Look into the lens, not at the screen or yourself.
- Light in front of you, a window is perfect. Never a bright light or window behind you, and avoid standing right under a ceiling light.
- Frame from mid-chest up with a little space above your head.
- Say the whole script, through the ending, in one session.
- Pause a beat between sentences. AVS only cuts in pauses, so the breaths you leave are its room to work.
- If you make a mistake, stop, say "reset, reset", and start that whole sentence again. AVS keeps your last clean take of each line.
- If you're reading lines fed to you or from a teleprompter, slow down. Rushing to beat the flubs makes more of them.
- Dated claims stay dated. If something happened last week, say "last week", not "today".

## What goes on screen

- Every word on screen is yours, in public. Read them all on the storyboard before you say render it.
- Claude writes from what you said. It never makes up results, reviews or prices for you.
- Proof panels use real screenshots you supply, with a true source line. Cropped to the part that matters, never altered.

## Extras

- **Words behind you**: one to three of your own spoken words, huge, behind your head on a full-screen shot.
- **Follow card**: a card with your photo, name, handle and a Follow button that taps to Following. Set them during install. To change them later, tell Claude (drag a new photo into the chat box).
- **Your own clips**: a short clip of your office, your hands or your screen playing in a card above you while you keep talking. Your own footage only, never stock or someone else's.
- **Effects** (21 on your start page, in the same groups): short graphics tied to the words you say. Pick up to four on the start page, or ask for one by name in a storyboard comment ("stamp the word recommended").
  - For your words: Word Stamp, Giant Words, Snap Zoom (a quick snap in on your most important word), Glass Word (a frosted word behind you), Quote Card (what someone said, in quotes), Title Card, Arrow Note (a handwritten arrow pointing at something), Icon Strike ("no ads")
  - For numbers: Big Number, Pie
  - For lists and steps: Giant Number (the 1, 2, 3 of your list slams in huge and covers you for about half a second), List Tracker (a header that counts through your list), Receipt (a short list printing), Note Wall (paper notes with your words)
  - For the open and the ask: Cover Story (your opening as a magazine cover), Pinned Line (one line held at the top, like "Comment SITE"), Keycaps (keys typing out your keyword), Comment Box (your keyword typed into a comment, then a heart)
  - For your screenshots (drop the screenshot in your inbox with the video, or Claude asks for it): Page Scroll (your website scrolling), Live Markup (a circle drawn on it), Highlighter (a line highlighted)
- **Transitions** (6), all at the moment the picture cuts: a warm Flash, Whip, Zoom and Spin (camera moves), and Iris and Bars (wipes). Each look uses its own.
- **Smoother cuts (automatic)**: at every cut the next sentence starts a beat before its picture, and full-screen shots switch between a wide and a slightly tighter framing so cuts feel like a camera change. Already trimmed your clip in CapCut or Edits? AVS lines its cuts up with yours so nothing flashes.
- **Sounds**: AVS comes with its own whoosh, land, click, impact, pop, ding and riser. They were made from scratch for AVS (no samples or recordings), so there's no license to worry about. They play on scene changes, panels, words behind you, cards and the call to action, all under your voice. To turn one off, tell Claude which ("no pops").
- **Music**: optional. Tell Claude a vibe ("calm and warm", "upbeat") and it finds a few free tracks from Openverse whose license allows business use, ads included (CC0, CC BY, or marked public domain by the uploader). The license details come from Openverse and the person who uploaded the track, so AVS keeps the source link for you to check, and any platform can still flag music in a video or an ad. You hear a 20-second snippet of each in the chat and pick one, or say no music. Almost all tracks ask for a credit, so Claude adds one Music line to the end of your caption with the track, the artist, its source and its license. Keep that line everywhere you post that video, ads and other versions too. In a paid ad it sits at the end of your primary text and is fairly long, with two links, so leave room for it. Already have a track you're licensed to use? Drag it into the chat box, tell Claude where it's from, and it sets it up. Claude skips a quiet intro so the music starts where the track gets going.
- **Your look**: tell Claude to change your color or fonts any time ("make my color green"), or pick fonts by watching them in the Picker. A very dark color (navy, black, deep purple) shows as a lighter shade of itself in the words and graphics over your video, photos and dark slides, so they stay readable. Light slides keep it exactly. Plain fonts: Hanken Grotesk, Inter, Montserrat, DM Sans, Poppins. Second fonts, for key words in some looks: Playfair, Instrument Serif, DM Serif, Fraunces. Want dollar amounts like $200 in green? Say "make the money green" and Claude saves it in your own look, so every video after has it. Any change means a new preview and a new approval before the next render.

## Common requests after a render

- "Music too loud" or "too quiet": Claude changes the level for that reel.
- "Music comes in late": Claude skips further into the track.
- "Too much zooming": Claude removes some zooms.
- "Too bright", "more cinematic", "moodier": Claude switches the color look (Natural, Bright and Clean, Warm, Cool, Soft Film, Moody, Cinematic), and the next start page opens on it.
- "There's a long pause at 0:39": Claude trims it, then shows you the preview again.
- "I don't like the opening" (or any part): Claude makes two or three different versions of just that part, plays them in the chat, and puts in the one you pick.
- Any change after you approve means a new preview and a new approval. That's on purpose.

## Updates

Once a day, at the start of a chat, AVS checks GitHub for a newer version (it only reads the version number, nothing about you or your videos is sent). When there's a new one, Claude tells you and asks if you want it. Say yes. You can also say "update AVS" any time, or tell Claude Code: "Run ~/AVS/tools/update.sh --latest". It downloads the newest version from GitHub (about 50 MB). Installed from a zip and have a newer zip? "Run ~/AVS/tools/update.sh ~/Downloads/AVS-<version>.zip" works too. It keeps your reels, brand, sound settings, music and saved styles, then refreshes the renderer packages, the cutout library and the skill, so it needs internet and a few minutes. Start a new chat afterwards.

## Fixes

Start most install problems the same way: tell Claude Code "run ~/AVS/tools/doctor.sh and fix what it says is missing". Each missing line names the install step that fixes it.

- **The doctor says all OK but videos won't render**: the doctor doesn't check the renderer's browser. Ask Claude to run `~/AVS/install.sh --step browser`.
- **The install stopped partway**: run the doctor, then let Claude re-run the step it names. Steps that already finished are skipped.
- **"only N GB free. AVS needs about 12 GB"**: free up space (empty the Trash, move large files), then run the install again.
- **The AVS folder ended up in the wrong place** (Safari expanded the zip into Downloads, or you unzipped it on the Desktop): before the install finishes, Claude moves that folder to `~/AVS` instead of unzipping a second copy. After the install, never move or rename `~/AVS`.
- **"Pick a repository" or GitHub questions**: you're in the cloud version of Claude Code. Start a new session in the Claude desktop app's Code tab, and when it asks where to work, pick a folder on your Mac (your home folder is fine), not a cloud environment.
- **The test video failed**: ask Claude to run `~/AVS/tools/smoke_test.sh` again and show you the last 20 lines, then run the doctor.
- **You installed the plugin but nothing happens**: start a new chat. A plugin never shows up in a chat that was already open. Still nothing: you may be in a cloud session (see "Pick a repository" above).
- **Claude doesn't know what "make a reel" means**: start a new chat. If it still doesn't, run the doctor: the skill line should say OK.
- **It seems stuck with no output**: Claude Code may be waiting on a permission prompt. Look for it in the window.
- **A sentence is missing from the cut**: you said it differently from the script. Claude updates the script to what you said and re-runs.
- **It kept the wrong take**: tell Claude which one you want, in your own words ("use the first time I said the opening line"). Claude finds that take and re-cuts.
- **"No silence" at a take edge**: usually street or room noise between your sentences. Claude re-runs it in the mode for noisy audio.
- **You fumbled inside a take it kept**: tell Claude the time ("at 0:24 I tripped over a word") and it trims that bit, inside a pause.
- **Your face is cut off or off-center**: tell Claude. It re-frames from a still and keeps everything else in the edit.
- **Text in your shot reads backwards**: the front camera saved it mirrored. Claude flips it.
- **Landscape video**: not supported. Film vertical.
- **The render refuses to start**: something changed after you approved. Look at the new preview and approve again.
- **The render fails partway**: rendering needs internet for the fonts. Check your connection and try again.
- **The draft didn't play in the chat**: you're in a terminal, not the Claude desktop app. Claude opens it for you there. Use the Code tab next time to watch it in the chat.
- **Can't find your finished videos**: they're in `~/AVS/engine/out`. Tell Claude "open my AVS out folder".
- **A page beside the chat is blank or closed**: tell Claude "open my storyboard again" (or "open my setup page", "show me my style"). Rather have it in your browser? Say "keep it on my Mac".
- **No Comment button on a part**: tell Claude in the chat instead, like "part 3, hold it longer". It works the same.
- **You commented and nothing happened**: press Send to Claude on the comment, or tell Claude in the chat "I left comments on the storyboard".
- **Still stuck after two fixes**: post in the AdCamp community with the error text or a screenshot.

## Removing AVS

Tell Claude: "Uninstall AVS." It asks you to type REMOVE to confirm. It copies your finished videos, caption drafts, carousel slides and carousel captions to `~/Desktop/AVS-videos`, then deletes the whole `~/AVS` folder and the AVS skill (the instructions that teach Claude to use AVS). That includes your inbox, your saved looks and any music you added, so ask Claude to copy out any footage, scripts or music you want to keep first. If you installed it from the Plugins panel, remove AdCamp Video System there too (Plugins, Manage plugins), or Claude will offer to set it up again. Your pages beside the chat (storyboards, your style board) stay in your Claude account until you delete them, and Claude offers to delete them for you.
