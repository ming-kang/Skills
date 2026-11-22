// Shared text segmentation and font style vocabulary.
export const GRAPHEMES = new Intl.Segmenter('und', { granularity: 'grapheme' });
export const FONT_SLOTS = ['regular', 'bold', 'italic', 'boldItalic'];
export const FONT_STYLE_ITALIC = new Set(['italic', 'oblique']);
