# CLAUDE.md: operating the AdCamp Video System

You DRIVE this engine through its scripts. Never hand-edit engine source to make one video work.
The skill `avs` sequences the work; these are the rules it relies on.

## Hard rules
1. A reel = `src/methodology/reels/<name>.config.ts` + one `<Reel .../>` line in `Root.tsx`
   (the generator writes both). Every reel is in the person's look: right after the first build,
   `scripts/make_style.py <name> <look> --in-place` (a starter look in styles/ or one of theirs; style.json is what
   the build reads, style.md the same in plain words; `scripts/my_styles.py`). `scripts/make_style.py <name> <look>`
   makes a second version in another look from the same cut. Studio, Minimal and Hype are the engine's base builds,
   never offered by name ("cards and panels" asks for Studio).
   A style built from someone else's reel copies the look, never their footage, words, music or name.
   The Picker (`scripts/picker.py`) saves styles/picks.json; `avs run my_styles.py save <name> --from-picks` turns it into a style.
2. Never render before the person has approved the draft in chat. The only exception is the install test
   (`avs smoke`), which approves its own sample clip.
   Run `scripts/approve_reel.py <name> --by "<their name>"` only after an explicit yes. Never infer
   approval. `avs reel --render` refuses without a current approval. Any later change to the
   config or the cut makes approval stale: show the new preview and ask again.
   The one exception is the review draft (`avs reel <video> <name> --draft`): half size, badged
   DRAFT, written to out/drafts/. It is for watching the edit before approving, never for posting,
   and it needs no approval.
3. The spoken script is the timeline. Cuts happen only between sentences, in a real pause. The
   captions show the script's words on the spoken timing. If the person ad-libbed, rewrite
   `script/<name>.txt` to what they actually said before building.
4. The person is always on screen. Nothing essential in the bottom 320px or right 120px
   (Instagram and TikTok buttons). One exception: `giant-number` covers the frame, face included, on purpose,
   for 12-45 frames on a list number they said. The engine caps it and keeps everything else off it.
   Lights Down (`lights-down`) dims the room behind them for one line: depth 0.35 to 0.7 (default 0.6), 30 to 150 frames,
   not in the first 45 frames, inside one take, not over words behind, a glass word, a card or a giant number, at most
   two, full-frame scenes only (and not while the picture glides back from a card). The engine enforces it.
5. On-screen words are the person's own. Write them from what they said, and never make up results,
   reviews or prices for them. Nothing is checked or blocked: they read it all on the storyboard.
6. Music and sound effects come only from AVS's own sounds, files the person supplied, or music they picked by
   listening from `scripts/find_music.py` (Openverse, CC0 / marked public domain / CC BY only). Every track is pinned
   on the reel it was chosen for (`avs run find_music.py --pick` or `--use`), with its license in `sounds/music/LICENSES.md`. A CC BY track's credit stays in the caption. Never take audio from
   anywhere else, never generate it, and never pick music for them.
7. Proof shots (panels and screenshot effects) are real, unedited captures the person supplied, with a truthful
   source line. Never stage, retouch or recreate one.
8. Caption and ad copy drafts are drafts. Nothing is posted, scheduled or spent from here.

## Build (the skill runs these)
1. `avs reel <video> <name> --face X,Y [--paid] [--unmirror] [--outdoor] --preview`
   - `--face`: the face center in 1080x1920 pixels, from a gridded still.
   - `--unmirror`: front-camera footage saved mirrored (text in the shot reads backwards).
   - `--outdoor`: street or noisy audio, or the cut fails with "no silence" at a take edge.
   - `--paid`: a Meta ad ("Click Learn More", ad copy draft) instead of an organic post. Every word in a paid ad
     stays inside Meta's ad safe zone (x 60-1020, y 250-1250) on its own: never move captions or drop effects for it.
2. Read `script/<name>-takes.md`: every stretch of audio is KEPT or DROPPED with a reason.
3. Fill every TODO in the config (cover title, panel copy), then re-run until the scene map says
   READY and you have LOOKED at `qa/<name>/preview/sheet.png`.
4. Show the person the draft (`--draft`, sent into the chat) with the storyboard published beside it, and wait for their go. Then `--render`, read the verify
   output, look at `qa/<name>/stills/sheet.png`, and hand over `out/<name>.mp4`.

## Troubleshooting
- `last_take` MISSING sentence: the script does not match what was said. Fix the script wording,
  or keep a specific take: `avs reel <video> <name> --keep-take N --preview` (numbers in `script/<name>-takes.md`).
- `last_take` "no silence" at a take edge: re-run with `--outdoor`.
- A mistake inside a kept take ("at 0:24 I fumbled") or a different take after the config was filled: back up the
  config, `avs reel <video> <name> --trim A-B --regen --preview` (one `--trim` per fumble, several in one run, or `--keep-take N`), then
  `scripts/retime_reel.py <name> --from <backup>`, then `--preview` again (the skill has the full steps).
- Face framed wrong: set `"faceX"` / `"faceY"` in the config to the corrected anchor and preview again. Never
  `--regen` a filled config (it discards every choice).
- Anything installed wrong: `avs doctor`.
