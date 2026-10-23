# Credits

Distinguished Vertical Editor (DVE) was built by Chris Serra for AdCamp members, on the shoulders of these people and projects.

## Methods and code

- **AI Video Editor by Ryan Musselman** (skool.com/aice). Much of how DVE works was learned from his course:
  cutting only in silence, word-level alignment, rendering the picture silent and mixing the narration straight
  from the cut, mastered to -14 LUFS, the seam check, the cover frame, the completion rule for panels, the
  charcoal stage and the glow look. DVE's code for all of it was written from scratch. If you want to go deeper
  on AI video editing, his course is where this started.
- **Shortify by Claude Code Club** (claudecodeclub.ai, free resource). Proof shots, the post kit,
  the hook-holds rule, punch captions, the ducked music bed and light "paper" chapters.
- **Chris Serra**: the vertical engine itself, the last-take selector, the three styles (Studio,
  Minimal, Hype), paid ad mode, the companion pack, back text, the film grade, outdoor cutting.

## Software (downloaded by the installer, each under its own license)

| What | Used for | License |
|---|---|---|
| Remotion | renders the video | Remotion License: free for individuals and companies up to 3 people, company license otherwise (remotion.pro) |
| WhisperX | word-level timing | BSD-2-Clause |
| faster-whisper / CTranslate2 | speech to text | MIT |
| PyTorch, torchaudio | runs the speech models | BSD-style |
| wav2vec2 (via torchaudio) | word alignment model | MIT (fairseq) |
| MediaPipe (Google) and its selfie segmentation model | cuts you out for "words behind you" | Apache-2.0 |
| FFmpeg (static build by Martin Riedl) | video and audio processing | LGPL/GPL |
| Node.js | runs the renderer | MIT |
| uv | installs Python privately | MIT / Apache-2.0 |
| Hanken Grotesk, Inter, Montserrat, DM Sans, Poppins, Playfair Display, Instrument Serif, DM Serif Display, Fraunces | caption fonts (Google Fonts) | SIL Open Font License 1.1 |

Sound effects: `engine/sounds/sfx/` (whoosh, land, click) are synthesized from scratch by `engine/scripts/make_sounds.py`.
No samples or recordings. Use them anywhere.

Ideas, not code: the storyboard with notes, the needs pass, and lining a sound's loudest moment up on its event were
learned from Reel Kit by Justyn Berkovits (MIT, justyn.ai). DVE's versions were written from scratch.

Music is never included. Add only music you are licensed to use (see `engine/sounds/music/LICENSES.md`).
