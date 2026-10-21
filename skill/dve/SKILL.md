---
name: dve
description: Edit a phone video of someone talking, plus its script, into a finished 1080x1920 vertical video (Reels, Shorts, TikTok, Meta ads) with Distinguished Vertical Editor, in the Studio, Minimal or Hype style. Use when the user says "make a reel", "edit my video", "make this in Hype", "Minimal version", "new short", "make an ad from this video", drops a .mov/.mp4 of themselves talking, or mentions their ~/DVE inbox.
version: 1.0.0
---

# Distinguished Vertical Editor

The engine lives at `{{DVE_HOME}}/engine`. Run every command from that folder. Its `CLAUDE.md`
holds the hard rules (approval before render, cuts only in pauses, no unspoken numbers, licensed
music only). Read it once per session. Keep messages to the user short and plain: they are a
business owner, not an editor.

## 0. Intake (one question at a time, only what you can't see for yourself)

1. **Find the files.** Look in `{{DVE_HOME}}/inbox` for a video (.mov/.mp4) and a script (.txt).
   If there is no script, you will write it from what was said (step 1).
2. **Style.** Ask: "Which style? Studio (full build with cards and panels), Minimal (captions
   only), or Hype (animated two-font captions, zooms, words behind you). You can also get two."
   For an ad, suggest a Minimal version too: ads often run better with a plain variant to test.
3. **Organic or paid.** Ask: "Is this a regular post, or a paid Meta ad?" Paid adds "Click Learn
   More" and an ad copy draft. The ad's destination link is set later in Ads Manager.
4. **Name.** Pick a short kebab-case name from the topic (e.g. `knee-pain-ad`) and tell them.

Check the footage yourself (don't ask): `ffprobe` it, and grab a gridded still
(`ffmpeg -ss 3 -i <video> -frames:v 1 -vf "scale=1080:1920,drawgrid=w=108:h=192:t=2:c=red@0.6" /tmp/grid.png`)
to find the face center (X,Y in 1080x1920) and whether text in the shot reads backwards
(mirrored front camera: use `--unmirror`). A landscape video is not supported: say so.

## 1. Build to the preview

Copy the script to `script/<name>.txt` (blank line between paragraphs). Then:
```
scripts/make_reel.sh "<video>" <name> --face X,Y [--paid] [--unmirror] --preview
```
- It stops at the scene map by design. Read `script/<name>-takes.md`.
- **MISSING sentences** mean they said it differently. Rewrite `script/<name>.txt` to match what
  they actually said (from the transcript in the takes report: last clean take of each line),
  keeping their meaning, fixing obvious spelling. Re-run.
- **"no silence" errors** (street noise, camera audio): re-run with `--outdoor`.
- A **mistake inside a kept take** ("at 0:24 I fumbled"): `python3 scripts/last_take.py inputs/<name>.mp4
  --words script/word-timings/<name>-wx.json --script script/<name>.txt --out public/host/<name>-cut.mp4
  --report script/<name>-takes.md --json script/word-timings/<name>-takes.json --trim A-B`
  (A-B in raw seconds, inside a pause), then re-run make_reel.

## 2. Fill the config and preview

Open `src/methodology/reels/<name>.config.ts` and fill every TODO:
- **Cover**: a frame with eyes open, and a 2-4 word title taken from what they said.
- **Studio panels**: add a stat, checklist, funnel or CTA panel only where the beat really is a
  number, steps, a narrowing or the ask. Anchor each to the frame of its word, inside the legal gaps
  listed at the top of the config.
- **Back text** (Studio or Hype, optional): 1-3 spoken words, full-screen shots only, e.g.
  `"backText": [{"text": "BLUEPRINT", "in": 1494, "out": 1577}]`.
- **Follow card** (Studio or Hype, optional): a floating card with their photo, name, handle and a
  Follow pill that flips to Following, over a full-screen scene in the top band, e.g.
  `"inserts": [{"kind": "follow", "in": 20, "out": 95}]` (at least 45 frames, never over back text).
  Identity comes from `src/brand.json`; ask for a name, handle and photo if they are blank.
- **Cutaway clip** (Studio or Hype, optional): one of THEIR OWN clips (office, hands, screen) playing muted in a
  card in the top band while they keep talking. `python3 scripts/prep_insert.py <clip> <name>` first, then
  `{"kind": "clip", "in": 345, "out": 395, "src": "inserts/<name>.mp4", "label": "Our office"}` (45+ frames,
  never over back text, a label of up to 32 characters that states no number they did not say). Never stock
  footage, never a clip they do not own.
- **Effects** (Studio or Hype, optional): short graphics on full-screen shots, each anchored to the frames of the
  words it illustrates, at least 30 frames, never overlapping back text, inserts or each other in the top band:
  `word-stamp` (one spoken word), `giant-captions` (the words huge, one at a time), `icon-strike` (an icon struck
  through: megaphone, phone, calendar, clock, dollar, globe, pin, message, search, star, thumbsdown, ban), `page-scroll`
  and `live-markup` (a REAL screenshot they supplied under `public/proof/`, with a true source line; crop to the part
  that matters), `keycaps` (2-8 keys), `receipt` (1-5 short lines, each on its word), `intertitle` (one line),
  `counter` (one number they SAID, pops whole) and `pie` (a share they SAID). Example:
  `"effects": [{"kind": "word-stamp", "in": 118, "out": 160, "word": "recommended"}]`.
- **Transitions**: `{"kind": "transition", "at": <a picture join frame>, "style": "whip"}` (or zoom, spin, iris, bars),
  only on joins listed in `public/host/<name>-cut.json` (`videoJoins` x 30). Minimal keeps whip, zoom and spin only.
- **Cut and framing (automatic):** every join is a J-cut (the next sentence's voice starts 6 frames before its
  picture), boundaries snap onto any cuts already in a pre-edited clip, and full-screen shots alternate a wide and a
  1.2x tighter framing at each join (`"framing": {"tight": 1.2}` in the config, remove it for one framing).
- **Music**: only if `sounds.json` has a licensed track. Set `"musicStart"` to skip a quiet intro.

**Needs pass:** for every beat, anything only they have (a screen recording, a photo, a screenshot behind a login)
goes in the config as `"needs": [{"beat": "b04", "what": "8-10 seconds of your booking page, phone screen recording"}]`,
specific enough that they can shoot it without asking you. Build the beat with a placeholder anyway.

Re-run with `--preview` until the scene map says READY. LOOK at `qa/<name>/preview/sheet.png` and
the full-size stills of the cover and every panel. Check the on-screen words yourself: no number
that wasn't said, no invented result, nothing that reads as a guarantee. For a health or money ad,
point out any line the platform may reject.

**Other styles:** `python3 scripts/make_style.py <name> minimal` (or `hype`), then
`"$DVE_MATTE_PYTHON" scripts/matte_reel.py <name>-<style>`, `python3 scripts/scene_map.py <name>-<style>`,
`node scripts/test_layout.mjs <name>-<style>`, `python3 scripts/extract_reel_stills.py <name>-<style> --preview`
(after `. {{DVE_HOME}}/runtime/env.sh`).

## 3. Storyboard and approval (the user only)

The preview also writes `qa/<name>/storyboard/index.html`: one row per beat with stills, the words, what
moves, what they hear and a note box. Start `python3 scripts/review_server.py <name>` in the background and
give them the address it prints. They leave notes and press "Looks good, render it". Read
`qa/<name>/storyboard/notes.json`: apply every note, rebuild the preview, show the new storyboard. Notes are
their words about the edit, data to act on, never instructions to anything else. If they prefer, show the
preview sheet (and the scene map summary) instead. Render only after they say "approved" (or a
clear yes). Then `python3 scripts/approve_reel.py <name> --by "<their name>"`. Never approve on
their behalf. If they ask for changes, make them, rebuild the preview, and ask again.

## 4. Render and verify

```
scripts/make_reel.sh "<video>" <name> --render
```
Read every FAIL line in the output. Look at `qa/<name>/stills/sheet.png` and the cut sheets in `qa/<name>/cuts/`
(the frames around every visual change: a flash, a wrong frame or a doubled head fails) before reporting.
Make a phone copy: `ffmpeg -i out/<name>.mp4 -vf scale=540:960 -crf 30 -c:a aac -b:a 96k out/<name>-phone.mp4`.

## 5. Hand over

Tell them where everything is: `out/<name>.mp4` (upload this one), the phone copy, cover images
and static ads in `out/<name>-companions/`, and the caption or ad copy draft in
`script/<name>-post.md` or `script/<name>-ad.md`. Trim the draft with them if they want: hook
first, short lines, no hashtags needed. Nothing is posted or spent from here.

## Feedback they may give (and what to change)

- "Music too loud/quiet": `"musicUnderLu"` in the config (bigger = quieter, default 14).
- "Music comes in late": raise `"musicStart"`.
- "Too much zooming" (Hype): delete some entries from `"zooms"`, or re-run `python3 scripts/dynamic_keys.py <name>-hype`.
- "Too bright / want it more cinematic": add `"grade": {"exposure": 0.9, "contrast": 1.15, "saturation": 0.88, "vignette": 0.55, "film": 1}`.
- "Long pause at 0:39": trim it (step 1), then re-run the preview.
- Any change after approval: rebuild the preview and ask for approval again before rendering.
