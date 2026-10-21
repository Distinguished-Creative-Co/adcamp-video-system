# CLAUDE.md: operating the Distinguished Vertical Editor

You DRIVE this engine through its scripts. Never hand-edit engine source to make one video work.
The skill `dve` sequences the work; these are the rules it relies on.

## Hard rules
1. A reel = `src/methodology/reels/<name>.config.ts` + one `<Reel .../>` line in `Root.tsx`
   (the generator writes both). Styles: Studio is the base build, `scripts/make_style.py <base>
   <minimal|hype>` makes a variant from the same cut.
2. Never render before the person has approved the preview (scene map + preview sheet) in chat.
   Run `scripts/approve_reel.py <name> --by "<their name>"` only after an explicit yes. Never infer
   approval. `make_reel.sh --render` refuses without a current approval. Any later change to the
   config or the cut makes approval stale: show the new preview and ask again.
3. The spoken script is the timeline. Cuts happen only between sentences, in a real pause. The
   captions show the script's words on the spoken timing. If the person ad-libbed, rewrite
   `script/<name>.txt` to what they actually said before building.
4. The person is always on screen. Nothing essential in the bottom 320px or right 120px
   (Instagram and TikTok buttons).
5. On-screen copy is the person's claim, in public. No number on screen that was not said aloud
   (the scene map enforces it). Never invent results, reviews, prices or guarantees. If a line
   could get a health or finance ad rejected or mislead a viewer, say so before they post it.
6. Music and sound effects come only from files the person supplied and listed in `sounds.json`,
   with a license noted in `sounds/music/LICENSES.md`. Never download, generate or borrow audio.
7. Proof shots (Studio panels) are real, unedited captures the person supplied, with a truthful
   source line. Never stage, retouch or recreate one.
8. Caption and ad copy drafts are drafts. Nothing is posted, scheduled or spent from here.

## Build (the skill runs these)
1. `scripts/make_reel.sh <video> <name> --face X,Y [--paid] [--unmirror] [--outdoor] --preview`
   - `--face`: the face center in 1080x1920 pixels, from a gridded still.
   - `--unmirror`: front-camera footage saved mirrored (text in the shot reads backwards).
   - `--outdoor`: street or noisy audio, or the cut fails with "no silence" at a take edge.
   - `--paid`: a Meta ad ("Click Learn More", ad copy draft) instead of an organic post.
2. Read `script/<name>-takes.md`: every stretch of audio is KEPT or DROPPED with a reason.
3. Fill every TODO in the config (cover title, panel copy), then re-run until the scene map says
   READY and you have LOOKED at `qa/<name>/preview/sheet.png`.
4. Show the person the preview sheet and wait for approval. Then `--render`, read the verify
   output, look at `qa/<name>/stills/sheet.png`, and hand over `out/<name>.mp4`.

## Troubleshooting
- `last_take` MISSING sentence: the script does not match what was said. Fix the script wording,
  or keep a specific take with `--keep-take N` (numbers in `script/<name>-takes.md`).
- `last_take` "no silence" at a take edge: re-run with `--outdoor`.
- A mistake inside a kept take ("at 0:24 I fumbled"): `python3 scripts/last_take.py ... --trim A-B`
  (raw seconds), then re-align and `scripts/retime_reel.py` (see the skill).
- Face framed wrong: re-run with a corrected `--face X,Y --regen` (regen discards config edits).
- Anything installed wrong: `~/DVE/tools/doctor.sh`.
