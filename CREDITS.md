# Credits

AdCamp Video System (AVS) was built by Chris Serra for AdCamp members. These people and projects made it possible.

## Methods and code

- **AI Video Editor by Ryan Musselman** (skool.com/aice). Much of how AVS works was learned from his course: cutting
  only in the pauses, timing every word, keeping the voice clean and even, checking every cut, and how the cards and the
  stage look. AVS's code for all of it was written from scratch. If you want to go deeper on AI video editing, his
  course is where this started.
- **Shortify by Claude Code Club** (claudecodeclub.ai, a free guide and video). Ideas for proof shots, the post kit,
  holding the hook on screen, punch captions, music that dips under your voice, and the light paper backgrounds.
  AVS's versions were written in its own code.
- **Chris Serra**: the vertical engine itself, the last-take selector, the base builds and the four starter
  looks (Clean Talk, Big Energy, Soft Story, Show and Tell), paid ad mode, the companion pack, words behind you, the film grade, cutting outdoor footage, and in 2.0 saved
  styles built from reels you like, the Picker, the eight caption styles, carousels and cards, beat versions
  and joining clips.

## Software (downloaded by the installer, each under its own license)

| What | Used for | License |
|---|---|---|
| Remotion | renders the video | Remotion License: free for individuals and companies with up to 3 employees, company license otherwise (remotion.pro) |
| WhisperX | word-level timing | BSD-2-Clause |
| faster-whisper / CTranslate2 | speech to text | MIT |
| PyTorch, torchaudio | runs the speech models | BSD-style |
| wav2vec2 (via torchaudio) | word alignment model | MIT (fairseq) |
| Whisper speech models, base and small (Systran's faster-whisper conversions of OpenAI Whisper) | speech to text | MIT |
| Voice activity model (pyannote segmentation, bundled with WhisperX, its usage reporting turned off) | finds where you're speaking | MIT |
| MediaPipe (Google) and its selfie segmentation model | cuts you out for "words behind you" | Apache-2.0 |
| FFmpeg (static build by Martin Riedl, downloaded by the installer, not shipped in AVS) | video and audio processing | GPL (this build includes x264) |
| Node.js | runs the renderer | MIT |
| Lucide icons (lucide-react) | the icons in Icon Strike | ISC |
| uv | installs Python privately | MIT / Apache-2.0 |
| yt-dlp | brings in reels you like, to study their look. When a download fails, it updates itself from its official GitHub releases and tries again, so it keeps working when sites change | Unlicense source. The macOS app the installer downloads bundles GPLv3+ code, so that download is GPLv3+ |
| Chrome Headless Shell (Google, from Chromium) | draws every frame of your video | BSD-style (Chromium) |
| The renderer's other packages (React and the libraries Remotion depends on, installed by npm) | building the video | each under its own license, listed in `engine/node_modules` |
| Hanken Grotesk, Inter, Montserrat, DM Sans, Poppins, Playfair Display, Instrument Serif, DM Serif Display, Fraunces, Anton, Bebas Neue, Oswald, Archivo, Inter Tight, Barlow Condensed, Caveat | caption, card, note and carousel fonts (Google Fonts) | SIL Open Font License 1.1 |

Sound effects: `engine/sounds/sfx/` (whoosh, land, click, impact, pop, ding, riser) are synthesized from scratch by `engine/scripts/make_sounds.py`.
No samples or recordings. Use them anywhere.

Ideas, not code: the storyboard with notes, the needs pass, and lining a sound's loudest moment up on its event were
learned from Reel Kit by Justyn Berkovits (MIT, justyn.ai). AVS's versions were written from scratch.

The Picker's preview clips are AVS rendering its own sample video. The screenshot effects show a capture of AVS's
own GitHub page.

Music is never included in AVS. When you ask for music by vibe, AVS searches Openverse (openverse.org, a free
library of openly licensed media) for tracks licensed CC0 or CC BY, or marked public domain by the uploader. CC0 and CC BY allow commercial use, ads
included. Almost every track found this way is CC BY and needs the credit line.
You choose each one. The license details come from Openverse and the track's uploader, not from AVS, so each kept
track is recorded in `engine/sounds/music/LICENSES.md` with its creator, source link and license for you to check.
A CC BY track's credit line is added to your caption draft: keep it wherever you post that video. Platforms can
still flag music in any video or ad. You can also add music you hold a license for.
