# figma-design-tokens

A [Claude Skill](https://www.anthropic.com/news/skills) that turns a blank (or existing) Figma file into a real, working design token system — a primitive color scale, semantic color aliases on top of it, and semantic typography styles — created as actual Figma Variables and Text Styles, not just documented in a spec nobody applies.

Ask for a design system / style guide / token library in Figma — from scratch, from a screenshot, from an existing Figma file, or from a reference URL — and hand off content when it's ready; see [`SKILL.md`](SKILL.md) for the full behavior.

## What it does

- **Four ways in, one schema out.** Start from nothing (pure interview), a screenshot of UI you like, an existing Figma file to harmonize with, or a live URL to pull direction from — they all converge on the same intermediate schema before anything touches Figma.
- **Two-tier color model, not a flat palette.** A raw primitive scale per hue (generated in [OKLCH](https://bottosson.github.io/posts/oklab/) for perceptually-even steps, not naive HSL) plus semantic aliases that reference it — change a primitive later and every semantic alias pointing at it updates with it.
- **Contrast is checked, not assumed.** Every semantic text/background pairing is run through a real WCAG contrast calculation before the preview ships, against whatever accessibility target was set (AA by default).
- **A real HTML preview before anything is written** — live-rendered type specimens and color swatches, plus a full token-reference table, so there's a concrete approval step before touching a real file.
- **Three paths to actually create the tokens in Figma**, in order of how little setup they need: a self-contained Figma plugin that needs zero external tooling (works on any plan, no MCP required), a third-party write-capable Figma MCP if one's connected, or Figma's own official remote MCP for fully agent-driven creation. See [`references/figma-write.md`](references/figma-write.md) for the tradeoffs and exact mechanics of each — including two easy-to-miss Figma Variables API requirements (explicit `scopes`, and `{r,g,b,a}` with alpha) that this skill sets correctly by default.

## Install

Drop this repo's contents into `.claude/skills/figma-design-tokens/` in your project (or wherever your Claude Skills live). Claude Code (or any Claude Skills–compatible client) will pick it up automatically.

No dependencies beyond Python 3 standard library (`scripts/color_tools.py` — color math and contrast checking) and, if you use the default write path, nothing at all: it's a plain Figma plugin you import once.

## Repo layout

```
SKILL.md                        # the skill itself — what to do, and why
references/
  from-scratch.md               # interview flow when there's no reference material
  from-screenshots.md           # extracting direction from an image
  from-figma-file.md            # harmonizing with an existing Figma file
  from-url.md                   # pulling direction from a live site
  token-schema.md               # the exact color/typography schema and naming rules
  figma-write.md                # the three ways to actually create tokens in Figma
scripts/
  color_tools.py                # OKLCH-based scale generation + WCAG contrast checking
assets/
  preview-template.html         # the HTML preview template
  figma-plugin/                 # the self-contained Figma plugin (manifest.json + code.js)
evals/
  evals.json                    # behavioral eval prompts (skill-creator schema)
```

## License

MIT — see [LICENSE](LICENSE).
