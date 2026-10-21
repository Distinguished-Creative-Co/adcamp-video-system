# inserts/

Pictures the floating cards use. The follow card wants a square photo of you here, named in
`src/brand.json` as `"avatar": "inserts/avatar.png"` (400x400 or larger, PNG or JPG). No photo:
the card shows your initials instead.

Cutaway clips live here too: `python3 scripts/prep_insert.py <your clip> <name>` writes `inserts/<name>.mp4`
(muted, 16:9, up to 20 seconds). Your own footage only: your office, your hands, your screen.
Never stock video and never someone else's clip.
