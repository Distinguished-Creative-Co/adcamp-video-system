# AdCamp Video System for Windows (preview)

> **AVS for Windows is a preview.**
>
> What's been checked: a test computer running Windows installs AVS from nothing and makes the test video, and that
> check runs again every time AVS changes.
>
> What hasn't been checked yet: a person using it in the Claude app on a home or office PC. You may be one of the first.
>
> What it takes: about an hour, more on a slower PC, and about 12 GB of free space. The first minute checks your PC. If
> your PC isn't a fit, AVS says so right then and downloads nothing.
>
> If a step fails: AVS stops and tells you which step. It changes no Windows settings. Say "make an AVS report" and
> post the report in the AdCamp member group. Say "uninstall AVS" and it's gone.
>
> Have a Mac? AVS for Mac is the finished version.

Turn a phone video of you talking into a finished, captioned vertical video for Reels, Shorts, TikTok
and Meta ads. A script helps AVS cut cleaner, but it's optional.

- **Your look, set once:** every video comes out in it. Start from one of four looks (Clean Talk, Big Energy, Soft
  Story, Show and Tell), all full frame in your own fonts and brand color, and tweak it in plain words.
- **Your own styles:** send links to reels you love and AVS rebuilds that look on your videos. Or open the
  Picker and choose by watching: 8 caption styles, 20 effects, 6 transitions and 4 font pairs, each playing on a
  sample video.
- **Music by vibe (optional):** say "calm and warm" or "upbeat" and pick from a few free tracks listed on Openverse
  as CC0, CC BY or public domain, licenses that allow business use, ads included. The license details come from
  whoever uploaded each track, and AVS doesn't verify them. Almost all ask for a credit, and the line goes into your
  caption for you. Keep it wherever you post that video. In a paid ad it's a long line with two links at the end of
  your text. AVS saves where each track came from so you can check it, and any platform can still flag music.
- **Same as last time:** every video starts on a setup page filled in from your last one, so a video like it is one
  press of Start.
- **Carousels:** turn a video or a topic into a carousel in your look. You approve the words first.

The cutting, transcribing and rendering all happen on your own PC. Claude, inside Claude Code, reads your transcript
and preview stills to build the edit, and shows you drafts in the chat. Rendering and the storyboard page need an
internet connection for the fonts, which load from Google Fonts. Your style board, video setup page, storyboard, Picker
and carousel slides open as private pages in your Claude account, beside the chat, so their frames go to Claude the way
your chat does. Only you can see them. Say "keep it on my PC" and Claude uses pages in your browser instead. Once a
day, at the start of a chat, AVS checks GitHub for a newer version: it only reads the version number, and nothing about
you or your videos is sent.

## What you need

- A Windows PC: Windows 11, or Windows 10 version 1809 or newer, with an Intel or AMD chip, and about 12 GB free.
  16 GB of memory is recommended. With 8 GB it works, but videos take longer, and that hasn't been tested yet.
  PCs with an ARM chip (like a Snapdragon laptop) aren't supported.
- Microsoft's free Visual C++ runtime. Most PCs already have it. If yours doesn't, AVS stops at the first check and
  gives you Microsoft's link. Installing it may ask for the PC's admin password (on a work PC, ask whoever looks after it).
- The Claude desktop app for Windows, and a Claude plan that includes Claude Code. Everything else installs for you.
- One license note: Remotion (the part that draws the video) is free for individuals and for companies with up to
  3 employees. A company with 4 or more employees needs a paid Remotion company license (remotion.pro).
- A video filmed vertically, with a pause between sentences. If you make a mistake, say "reset, reset" and start
  the sentence again. AVS keeps your last clean take.

## Install (about an hour, mostly downloads and a test video)

Neither way below needs git or any developer tools, and AVS itself never asks for an administrator. Claude asks your OK
before it runs each step: allow it each time.

Easiest: in the Claude desktop app, open the **Code** tab, start a new chat and paste this. It looks technical, but
you don't need to understand it, just paste it:

```
Install AdCamp Video System for Windows for me from https://github.com/Distinguished-Creative-Co/adcamp-video-system/archive/refs/heads/windows-preview.zip into the AVS folder in my home folder (download it with curl.exe and unpack it with tar.exe, not with git), then open AVS\INSTALL.md and follow it step by step. Tell me what each step downloads and how big it is before it starts, and ask me before anything that needs an account, a password, or a choice from me.
```

Or from the Plugins panel:

1. In the **Code** tab, click the **+** next to the message box, then **Plugins**, then **Browse plugins**.
2. Click **Add**, then **Add marketplace**, then **Add from a repository**. Paste this link exactly as it is and click
   **Sync**:

```
https://raw.githubusercontent.com/Distinguished-Creative-Co/adcamp-video-system/windows-preview/marketplace.json
```

3. Install **AdCamp Video System for Windows (Preview)** from the list in **Browse plugins**.
4. Start a new chat and say:

```
Set up AVS
```

Claude checks your PC first, then walks you through everything, shows you your name in four font pairs so you can
pick, makes a test video, helps you set your look, then gets you straight into your first video.

## Making a video, once installed

1. Get your video onto your PC. From an iPhone: open icloud.com/photos on the PC and download it, or plug the phone in
   with its cable. From an Android: photos.google.com, or the cable. If you filmed it as a few clips, bring them all.
2. Tell Claude "open my AVS inbox" and drop the video in. Add your script as a text file, or paste it into the chat.
3. In a chat (a new one right after installing or updating), say:

```
Make a reel from the video in my inbox.
```

Your setup opens beside the chat, filled in from last time: your captions, up to four effects (each one playing so
you can see it), a color for your footage, and a box for your script. Press Start. Then Claude plays a quick draft in
the chat and opens your storyboard beside it, every part of the video with a Comment button.
Comment on anything you'd change, or tell Claude in the chat. When it looks right, say "render it" and it makes the
finished video. Nothing is ever posted for you.

## Stuck?

Say "make an AVS report" and post the report from your Desktop in the AdCamp member group. It has no videos and no
personal details. Or set up **Coach Chris**, an AI version of Chris that answers from the AVS guide, in about two
minutes: tell Claude "show me the Coach Chris setup steps".
