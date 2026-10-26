import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { Slide, type Identity, type SlideData, type SlideLook } from '../components/slides/Slide';

/**
 * A carousel: frame i is slide i (scripts/carousel.py renders the frames as PNGs in one pass). The document
 * comes in as input props from <carousel folder>/carousel.json; pictures resolve against that folder.
 */
export type CarouselDoc = { title: string; slug: string; size?: '4:5' | '1:1'; look?: SlideLook; who?: Identity; slides: SlideData[]; caption?: string };
export const CAROUSEL_SIZE = { '4:5': [1080, 1350], '1:1': [1080, 1080] } as const;

export const Carousel: React.FC<{ doc: CarouselDoc | null }> = ({ doc }) => {
  const frame = useCurrentFrame();
  if (!doc) return null;
  const [w, h] = CAROUSEL_SIZE[doc.size ?? '4:5'];
  const i = Math.min(frame, doc.slides.length - 1);
  return (
    <AbsoluteFill>
      <Slide data={doc.slides[i]} look={doc.look} who={doc.who} w={w} h={h} page={[i + 1, doc.slides.length]} />
    </AbsoluteFill>
  );
};
