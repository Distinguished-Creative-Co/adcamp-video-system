# Music licenses

Only use music you are licensed to use in your videos (and in ads, if you run them).
Good free sources: Mixkit (mixkit.co, free license allows ads), YouTube Audio Library, Uppbeat.
Paid: Epidemic Sound, Artlist.

To add a track:
1. Put the file in this folder (mp3 or wav).
2. Add a row below: file, where it came from, the license, and the date you downloaded it.
3. Add its path to `music_beds` in `engine/sounds.json`, for example `"sounds/music/my-track.mp3"`.
4. Many tracks start quiet. Set `"musicStart": <seconds>` in a reel's config to skip the intro.

| File | Source | License | Downloaded |
|---|---|---|---|
