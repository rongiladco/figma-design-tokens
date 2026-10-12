## Localization

Hebrew-first. The tokens above hold for both scripts when the font stack has Hebrew glyphs; these rules cover what tokens do not encode.

### RTL layout

- Set `<html lang="he" dir="rtl">` on every page. Screen readers use `lang` to pick the voice, layout uses `dir`.
- Use logical CSS only: `padding-inline-start`, `margin-inline-end`, `inset-inline-start`, `text-align: start`. Never `left`/`right`, `margin-left`, or `text-align: left`.
- Mirror asymmetric layouts through DOM order, not the CSS `order` property. A hero with image and text puts the image on the start side (right) in RTL.
- The primary action sits on the start side (right); secondary actions follow toward the end.
- Flip direction-aware icons (arrows, chevrons, breadcrumb separators, back/next). Do not flip logos, clocks, or media controls.
- Drawers slide in from the start side. Steppers and progress bars fill from start to end (right to left).
- Keyboard: for carousels and slides, "next" is ArrowLeft in RTL. Verify, do not assume the LTR convention.

### Hebrew typography

- Heading `letterSpacing` is for Latin runs. For Hebrew text set it to `0`: negative tracking crowds Hebrew letterforms.
- Hebrew needs more line-height than Latin at display sizes (descenders such as ק ץ ן collide). Use at least 1.15 for headlines.
- Keep `kern` and `calt` on; never set `font-feature-settings: normal` globally.
- Small text loses legibility faster in Hebrew. Reserve the smallest body level for captions and metadata.

### Mixed direction (BiDi)

- Wrap numbers, phone numbers, IDs, versions, file paths, and code inside Hebrew text in `<bdi>`.
- URLs, emails, and code stay LTR even on RTL pages (`direction: ltr`).
- Free-text inputs use `unicode-bidi: plaintext` so the typed direction follows the content.

### Hebrew copy and formats

- Quotes and acronyms use gershayim ״ (U+05F4), not ASCII `"`. Apostrophe-like marks use geresh ׳ (U+05F3).
- Dates `dd/mm/yyyy`, time 24-hour, week starts on Sunday, currency as `1,200 ₪` (symbol after the amount).
- Write `aria-label` text in Hebrew at build time; wrap Latin brand names in `<span lang="en">`.
- Required-field asterisk goes after the label. Error messages say how to fix the problem, not just that it failed.
