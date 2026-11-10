import torch
from faster_whisper import WhisperModel
for m in ('base', 'small'):
    WhisperModel(m, device='cpu', compute_type='int8'); print('  speech model', m, 'ready')
import whisperx
whisperx.load_align_model(language_code='en', device='cpu'); print('  word-alignment model ready')
whisperx.load_model('base', 'cpu', compute_type='int8'); print('  voice-activity model ready')
