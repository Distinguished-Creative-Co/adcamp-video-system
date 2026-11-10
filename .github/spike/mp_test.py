import sys
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import ImageSegmenter, ImageSegmenterOptions
model, img = sys.argv[1], sys.argv[2]
for mode in ('full path with a space', 'bytes'):
    try:
        base = BaseOptions(model_asset_path=model) if mode.startswith('full') else BaseOptions(model_asset_buffer=open(model, 'rb').read())
        with ImageSegmenter.create_from_options(ImageSegmenterOptions(base_options=base, output_category_mask=True)) as seg:
            m = seg.segment(mp.Image.create_from_file(img)).category_mask.numpy_view()
            print('%s: ok %s, person pixels %.0f%%' % (mode, m.shape, 100.0 * (m > 0).mean()))
    except Exception as e:
        print('%s: FAILED %r' % (mode, e))
