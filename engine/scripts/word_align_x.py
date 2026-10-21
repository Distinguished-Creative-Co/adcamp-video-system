#!/usr/bin/env python3
"""Per-word timings for a media file -> script/word-timings/<stem>-wx.json.

    "$DVE_PYTHON" scripts/word_align_x.py <media> [--model NAME] [--fast | --full]

Modes (CPU, int8 everywhere):
  --fast    faster-whisper transcription only (model base). Words keep their punctuation,
            which the take selector (last_take.py) reads for sentence ends.
  default   whisperX: transcribe (model small), then forced alignment for tight word edges.
  --full    faster-whisper transcribes with the voice-activity filter OFF (no stretch of
            speech can be dropped), then whisperX only aligns those segments.

Output: a JSON list of {"word", "start", "end"}, times rounded to 3 decimals.
"""
import json
import os
import sys

DEVICE = 'cpu'
COMPUTE = 'int8'
SETUP_HINT = ('the speech environment is not set up (faster-whisper / whisperX missing). '
              'Run ~/DVE/tools/doctor.sh')


def _need(module):
    try:
        return __import__(module)
    except ImportError:
        sys.exit('word_align_x: %s' % SETUP_HINT)


def words_fast(path, model):
    fw = _need('faster_whisper')
    segments, _info = fw.WhisperModel(model, device=DEVICE, compute_type=COMPUTE).transcribe(
        path, word_timestamps=True)
    out = []
    for seg in segments:
        for w in (seg.words or []):
            out.append((w.word, w.start, w.end))
    return out


def _aligned_words(whisperx, audio, transcript):
    model, meta = whisperx.load_align_model(language_code=transcript['language'], device=DEVICE)
    res = whisperx.align(transcript['segments'], model, meta, audio, DEVICE, return_char_alignments=False)
    out = []
    for seg in res['segments']:
        for w in seg.get('words', []):
            if w.get('start') is not None and w.get('end') is not None:
                out.append((w['word'], w['start'], w['end']))
    return out


def words_whisperx(path, model):
    whisperx = _need('whisperx')
    audio = whisperx.load_audio(path)
    transcript = whisperx.load_model(model, DEVICE, compute_type=COMPUTE).transcribe(audio, batch_size=16)
    return _aligned_words(whisperx, audio, transcript)


def words_full(path, model):
    fw = _need('faster_whisper')
    whisperx = _need('whisperx')
    segments, info = fw.WhisperModel(model, device=DEVICE, compute_type=COMPUTE).transcribe(path, vad_filter=False)
    transcript = {'language': info.language,
                  'segments': [{'start': s.start, 'end': s.end, 'text': s.text} for s in segments]}
    return _aligned_words(whisperx, whisperx.load_audio(path), transcript)


def main():
    argv = sys.argv[1:]
    pos = [a for a in argv if not a.startswith('--')]
    model = None
    if '--model' in argv:
        i = argv.index('--model')
        if i + 1 >= len(argv):
            sys.exit('usage: word_align_x.py <media> [--model NAME] [--fast | --full]')
        model = argv[i + 1]
        pos = [a for a in pos if a != model]
    if not pos:
        sys.exit('usage: word_align_x.py <media> [--model NAME] [--fast | --full]')
    media = pos[0]

    if '--fast' in argv:
        raw = words_fast(media, model or 'base')
        label = 'faster-whisper transcribe (punctuated, for the cut)'
    elif '--full' in argv:
        raw = words_full(media, model or 'small')
        label = 'whisperX forced alignment'
    else:
        raw = words_whisperx(media, model or 'small')
        label = 'whisperX forced alignment'

    rows = [{'word': w.strip(), 'start': round(float(s), 3), 'end': round(float(e), 3)} for w, s, e in raw]
    stem = os.path.splitext(os.path.basename(media))[0]
    out_dir = os.path.join('script', 'word-timings')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, '%s-wx.json' % stem)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('wrote %s — %d words (%s)' % (out, len(rows), label))


if __name__ == '__main__':
    main()
    # the speech libraries can crash while tearing down their thread pools; the file is
    # already on disk, so leave without running interpreter shutdown
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
