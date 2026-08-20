# Starting from a URL

Two ways to pull direction from a live site, and it's worth trying the cheaper one first:

1. **Fetch and inspect the page** (`WebFetch`, or the Browser pane tools if you need rendered/computed styles rather than raw markup). If you can get at actual CSS — custom properties, computed background/color/font-family values — that's exact data, not an inference, and worth preferring over a visual read whenever it's available (e.g. a site with visible CSS custom properties for its color palette tells you the *real* hex values directly).
2. **Fall back to visual inspection** (screenshot the rendered page via the Browser pane, then read it the same way as `references/from-screenshots.md`) when the site is heavily obfuscated/minified, uses a framework that inlines everything unhelpfully, or you just need the gestalt impression rather than exact values.

Either way, pull the same things a screenshot would give you — colors in use (background, primary/accent, text, semantic colors), typography character or exact font-family if visible in CSS, relative scale of headings vs. body — plus one thing a static screenshot can't: **check multiple pages/states if relevant** (homepage vs. a form/checkout page, light vs. dark if the site supports both) since a single URL sometimes only shows part of the system.

If pulling multiple pages, treat inconsistencies between them the same way as conflicting screenshots — surface it, don't silently pick one.

This only ever produces *reference material*, not a finished token set — still work through SKILL.md §2's direction-setting questions afterward (a competitor's site tells you nothing about whether *this* project needs dark mode, for instance).
