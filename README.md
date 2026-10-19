# figma-design-tokens

A [Claude Skill](https://www.anthropic.com/news/skills) that turns a blank (or existing) Figma file into a real, working design token system — a primitive color scale, semantic color aliases on top of it, and semantic typography styles — created as actual Figma Variables and Text Styles, not just documented in a spec nobody applies.

Ask for a design system / style guide / token library in Figma — from scratch, from a screenshot, from an existing Figma file, or from a reference URL — and hand off content when it's ready; see [`SKILL.md`](SKILL.md) for the full behavior.

## What it does

- **Four ways in, one schema out.** Start from nothing (pure interview), a screenshot of UI you like, an existing Figma file to harmonize with, or a live URL to pull direction from — they all converge on the same intermediate schema before anything touches Figma.
- **Two-tier color model, not a flat palette.** A raw primitive scale per hue (generated in [OKLCH](https://bottosson.github.io/posts/oklab/) for perceptually-even steps, not naive HSL) plus semantic aliases that reference it — change a primitive later and every semantic alias pointing at it updates with it.
- **Optional third tier and extra scales.** Component tokens (aliasing the semantic layer, e.g. `button/background/default`) and flat spacing/radius scales are available when asked; the default stays colors + typography so the system doesn't get over-tokenized. The three-tier model follows [zeroheight's guide to token hierarchy](https://zeroheight.com/learn/how-design-tokens-work-types-structure-and-hierarchy/).
- **Schema is validated, not just eyeballed.** `scripts/validate_tokens.py` flags role names that carry a color or light/dark word, raw hex values inside semantic tokens, and alias targets that don't exist.
- **A code path too: `DESIGN.md`.** For designers who continue in code with Claude Code instead of (or as well as) Figma, the same approved schema exports to a [`DESIGN.md`](https://github.com/google-labs-code/design.md) (Google's open spec, alpha): a short interview supplies the "why" (intent and boundaries per colour, never-rules, states, voice), and `scripts/design_md.py` writes the file, then `check`s it for broken references, prose that drifts from the tokens, and unanswered `TODO(interview)` markers. Every file also gets a few always-on baseline rules learned from a real test (no `opacity` on text over coloured surfaces, no invented hover states, no invented radius/spacing/layout values, theme switching via `data-theme`). See [`references/design-md.md`](references/design-md.md).
- **Contrast is checked, not assumed.** Every semantic text/background pairing is run through a real WCAG contrast calculation before the preview ships, against whatever accessibility target was set (AA by default).
- **Rules that fail the build, not just instructions.** `design_md.py export-css` writes one `tokens.css` from the schema (with `--check` to catch drift), and `scripts/tokens_lint.py` scans app source and exits 1 on a new hard-coded colour or a px/rem value a token already holds, naming the token to use. Existing code can adopt it through a baseline ratchet. See SKILL.md §7c.
- **A real HTML preview before anything is written** — live-rendered type specimens and color swatches, a component gallery (each variant rendered as a usage example), a Light/Dark toggle, and a full token-reference table, so there's a concrete approval step before touching a real file. `scripts/build_preview.py` builds it from the template.
- **Three paths to actually create the tokens in Figma**, in order of how little setup they need: a self-contained Figma plugin that needs zero external tooling (works on any plan, no MCP required), a third-party write-capable Figma MCP if one's connected, or Figma's own official remote MCP for fully agent-driven creation. See [`references/figma-write.md`](references/figma-write.md) for the tradeoffs and exact mechanics of each — including two easy-to-miss Figma Variables API requirements (explicit `scopes`, and `{r,g,b,a}` with alpha) that this skill sets correctly by default.

## Install

Drop this repo's contents into `.claude/skills/figma-design-tokens/` in your project (or wherever your Claude Skills live). Claude Code (or any Claude Skills–compatible client) will pick it up automatically.

No dependencies beyond Python 3 standard library (`scripts/color_tools.py` — color math and contrast checking; `scripts/validate_tokens.py` — schema checks; `scripts/design_md.py` and `scripts/build_preview.py` — the DESIGN.md export/check and the preview builder) and, if you use the default write path, nothing at all: it's a plain Figma plugin you import once.

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
  design-md.md                  # the DESIGN.md route: principles, schema mapping, interview, linter
scripts/
  color_tools.py                # OKLCH-based scale generation + WCAG contrast checking
  validate_tokens.py            # schema checks: role-based names, no raw hex in aliases, valid targets
  design_md.py                  # export the schema to DESIGN.md, and check it (broken refs, prose drift, TODOs); export-css writes tokens.css
  tokens_lint.py                # fail on hard-coded colours/lengths in app source that a token already holds
  build_preview.py              # fills the preview template from a schema
assets/
  preview-template.html         # the HTML preview template
  design-md-localization-he.md  # generic RTL/Hebrew section appended to DESIGN.md when language is he/ar
  figma-plugin/                 # the self-contained Figma plugin (manifest.json + code.js)
evals/
  evals.json                    # behavioral eval prompts (skill-creator schema)
```

## License

MIT — see [LICENSE](LICENSE).
