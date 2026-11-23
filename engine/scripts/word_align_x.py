#!/usr/bin/env python3
"""Per-word timings for a media file -> script/word-timings/<stem>-wx.json.

    "$AVS_PYTHON" scripts/word_align_x.py <media> [--model NAME] [--fast | --full]

Modes (CPU, int8 everywhere):
  --fast    faster-whisper transcription only (model base). Words keep their punctuation,
            which the take selector (last_take.py) reads for sentence ends.
  default   whisperX: transcribe (model small), then forced alignment for tight word edges.
  --full    faster-whisper transcribes with the voice-activity filter OFF (no stretch of
            speech can be dropped), then whisperX only aligns those segments.

Output: a JSON list of {"word", "start", "end"}, times rounded to 3 decimals.

A file with more than one audio track (a raw iPhone clip with spatial audio) is read through
a temporary WAV of the track normalize_source.audio_stream() picks. Left alone, faster-whisper
opens the first track and whisperX's ffmpeg the one with the most channels, both the
spatial-audio track ffmpeg cannot decode.
"""
import json
import os
import subprocess
import sys
import tempfile

# everything stays on this Mac: pyannote (inside whisperX) sends usage pings by default, Hugging Face may too
os.environ.setdefault('PYANNOTE_METRICS_ENABLED', '0')
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')

DEVICE = 'cpu'
COMPUTE = 'int8'
SETUP_HINT = ('the speech environment is not set up (faster-whisper / whisperX missing). '
              'Run ~/AVS/tools/doctor.sh')


def _need(module):
    try:
        return __import__(module)
    except ImportError:
        sys.exit('word_align_x: %s' % SETUP_HINT)


def speech_input(media):
    """(path to transcribe, temp folder to remove or None). A file with one decodable audio track is read as is.
    With several (an iPhone spatial-audio clip), the picked track goes to a 16 kHz mono WAV, what both speech
    libraries resample to anyway, so the words keep their times."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import normalize_source
    info = normalize_source.probe(media)
    auds = [s['index'] for s in info['streams'] if s.get('codec_type') == 'audio']
    pick = normalize_source.audio_stream(media, info)
    if pick is None:
        sys.exit('word_align_x: no audio track in %s that can be decoded (the transcript needs speech)' % media)
    if auds == [pick]:
        return media, None
    tmp = tempfile.mkdtemp(prefix='avs-speech-')
    wav = os.path.join(tmp, 'speech.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', media, '-map', '0:%d' % pick, '-vn',
                    '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', wav], check=True)
    return wav, tmp


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

    speech, tmp = speech_input(media)
    try:
        if '--fast' in argv:
            raw = words_fast(speech, model or 'base')
            label = 'faster-whisper transcribe (punctuated, for the cut)'
        elif '--full' in argv:
            raw = words_full(speech, model or 'small')
            label = 'whisperX forced alignment'
        else:
            raw = words_whisperx(speech, model or 'small')
            label = 'whisperX forced alignment'
    finally:
        if tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    rows = [{'word': w.strip(), 'start': round(float(s), 3), 'end': round(float(e), 3)} for w, s, e in raw]
    stem = os.path.splitext(os.path.basename(media))[0]
    out_dir = os.path.join('script', 'word-timings')
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, '%s-wx.json' % stem)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('wrote %s, %d words (%s)' % (out, len(rows), label))


if __name__ == '__main__':
    if '--help' in sys.argv[1:] or sys.argv[1:2] == ['-h']:   # --help: the usage, nothing else
        print((__doc__ or '').strip() or 'usage: python3 scripts/%s' % os.path.basename(__file__))
        sys.exit(0)
    main()
    # the speech libraries can crash while tearing down their thread pools; the file is
    # already on disk, so leave without running interpreter shutdown
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
