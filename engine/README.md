# Distinguished Vertical Editor (engine folder)

Phone video + script in, finished 1080x1920 vertical video out, in one of three styles.
You don't run anything here by hand: in Claude Code, say "make a reel from my inbox".

| Folder | What's in it |
|---|---|
| `inputs/` | your raw video, converted to 1080x1920 30fps |
| `script/` | your script, the take report, the scene map (the preview you approve), caption/ad drafts |
| `public/host/` | the cut (only your clean takes), its full-resolution twin, and the back-text cutouts |
| `public/inserts/` | your follow-card photo (`avatar.png`) and your cutaway clips (`scripts/prep_insert.py`) |
| `src/methodology/reels/` | one config per reel: scenes, captions, panels, style |
| `qa/<name>/` | preview stills and checks |
| `out/` | finished videos, phone copies, cover images and static ads |
| `sounds/` | DVE's own whoosh, land and click (`sfx/`, yours to use), and your licensed music (optional) |
| `samples/` | the sample clip and script the install test (`../tools/smoke_test.sh`) builds |

Look and feel: `src/brand.json` (accent color, sans font, serif font). Styles: `styles.json`.
Rules the engine follows: `CLAUDE.md`. Credits: `../CREDITS.md`.

## Pipeline
normalize -> transcribe -> keep the last clean take of each sentence (cuts only in pauses) ->
precise word alignment -> a full-resolution twin of the cut from the original recording (so
punch-ins and zooms stay sharp) -> seam check -> config -> scene map + preview (you approve) ->
render (silent picture) -> mix and master the voice (and music) to -14 LUFS -> verify ->
cover images and static ads.
