# Starting from screenshots

Read the image(s) directly — Claude can inspect images natively, no OCR or extraction tooling needed. Pull out:

- **Colors in use** — background(s), primary/accent color, text colors, any semantic-looking colors (a red for errors, a green for success). Note approximate hex values, but say explicitly that these are *inferred approximations from a rendered image*, not exact source values — screen calibration, compression, and lighting in a photo all shift perceived color. Confirm the closest ones with the user rather than locking them in silently, especially the primary/brand color.
- **Typography character** — even without being able to identify the exact font family from a screenshot, describe what's visible: serif vs. sans, weight (light/regular/bold), whether headings are notably larger/tighter than body text, any distinctive letter-spacing. Propose a real, available font family (see the "font availability" note in `references/token-schema.md`) that matches this character rather than guessing at an exact match — screenshots very rarely let you identify a font precisely, and claiming otherwise would be more confident than the evidence supports.
- **Layout hints about scale** — if multiple text sizes are visible in the same shot, their *relative* proportions (this heading looks roughly 2× the body text) are more reliable to read off an image than absolute pixel sizes, which depend on the screenshot's original resolution/zoom.

If there are multiple screenshots and they disagree (different color schemes, inconsistent type), say so and ask the user which one is more representative, or whether they want a system that reconciles both — don't silently pick one.

Once you've got a proposed direction, move to SKILL.md §2 for the remaining direction-setting questions (dark mode, accessibility target, etc.) — a screenshot tells you *what it should look like*, not things like whether dark mode is needed.
