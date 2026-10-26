# AdCamp Video System

Turn a phone video of you talking into a finished, captioned vertical video for Reels, Shorts, TikTok
and Meta ads. A script helps AVS cut cleaner, but it's optional.

- **Your look, set once:** every video comes out in it. Start from one of four looks (Clean Talk, Big Energy, Soft
  Story, Show and Tell), all full frame in your own fonts and brand color, and tweak it in plain words.
- **Your own styles:** send links to reels you love and AVS rebuilds that look on your videos. Or open the
  Picker and choose by watching: 8 caption styles, 21 effects, 6 transitions and 4 font pairs, each playing on a
  sample video.
- **Music by vibe (optional):** say "calm and warm" or "upbeat" and pick from a few free tracks listed on Openverse
  as CC0, CC BY or public domain, licenses that allow business use, ads included. The license details come from
  whoever uploaded each track, and AVS doesn't verify them. Almost all ask for a credit, and the line goes into your caption for you. Keep
  it wherever you post that video. In a paid ad it's a long line with two links at the end of your text. AVS saves
  where each track came from so you can check it, and any platform can still flag music.
- **Same as last time:** every video starts on a setup page filled in from your last one, so a video like it is one press of Start.
- **Carousels:** turn a video or a topic into a carousel in your look. You approve the words first.

The cutting, transcribing and rendering all happen on your own Mac (Apple chip, or Intel, which is supported but not yet tested on a real Intel Mac). Claude, inside
Claude Code, reads your transcript and preview stills to build the edit, and shows you drafts in the chat. Rendering and the storyboard page need an internet connection for the fonts, which load from Google Fonts. Your style board, video setup page, storyboard, Picker and carousel slides open as private pages in your Claude account, beside the chat, so their frames go to Claude the way your chat does. Only you can see them. Say "keep it on my Mac" and Claude uses pages in your browser instead. Once a day, at the start of a chat, AVS checks GitHub for a newer version: it only reads the version number, and nothing about you or your videos is sent.

## What you need

- A Mac with macOS 12 or newer and about 12 GB free.
- A Claude plan that includes Claude Code. Everything else installs for you.
- One license note: Remotion (the part that draws the video) is free for individuals and for companies with up to
  3 employees. A company with 4 or more employees needs a paid Remotion company license (remotion.pro).
- A video filmed vertically, with a pause between sentences. If you make a mistake, say "reset, reset" and start
  the sentence again. AVS keeps your last clean take.

## Install (20 to 40 minutes, mostly downloads, then a test video of 10 to 15 minutes)

Easiest, in the Claude desktop app:

1. Open the **Code** tab. Click the **+** next to the message box, then **Plugins**, then **Browse plugins**.
2. Click **Add**, then **Add marketplace**, then **Add from a repository**. Paste this link and click **Sync**:

```
https://github.com/Distinguished-Creative-Co/adcamp-video-system
```

3. Install **AdCamp Video System** from the list.
4. Start a new chat and say:

```
Set up AVS
```

Or start a new chat in the Code tab and paste this instead:

```
Install AdCamp Video System for me from https://github.com/Distinguished-Creative-Co/adcamp-video-system into ~/AVS (download it as a tar.gz with curl, not with git), then open ~/AVS/INSTALL.md and follow it step by step. Tell me what each step downloads and how big it is before it starts, and ask me before anything that needs an account, a password, or a choice from me.
```

If you have the zip instead (`AVS-2.0.0.zip`), put it in Downloads and say "Install AdCamp Video System from
~/Downloads/AVS-2.0.0.zip into ~/AVS, then follow ~/AVS/INSTALL.md".

Claude walks you through everything, shows you your name in four font pairs so you can pick, makes a test video,
helps you set your look, then gets you straight into your first video.

## Making a video, once installed

1. Get your video onto your Mac (AirDrop from your phone is easiest). If you filmed it as a few clips, send them all.
2. Tell Claude "open my AVS inbox" and drop the video in. Add your script as a text file, or paste it into the chat.
3. In a chat (a new one right after installing or updating), say:

```
Make a reel from the video in my inbox.
```

Your setup opens beside the chat, filled in from last time: your captions, up to four effects (each one playing so
you can see it), a color for your footage, and a box for your script. Press Start. Then Claude plays a quick draft in the chat and opens your
storyboard beside it, every part of the video with a Comment button.
Comment on anything you'd change, or tell Claude in the chat. When it looks right, say "render it" and it makes the
finished video. Nothing is ever posted for you.

## Stuck?

Set up **Coach Chris**, an AI version of Chris that answers from the AVS guide, in about two minutes. Tell Claude
"show me the Coach Chris setup steps".
