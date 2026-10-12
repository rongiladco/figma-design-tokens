# Exporting a DESIGN.md

For a designer who continues in code (Claude Code) instead of Figma. The same approved schema that feeds the Figma plugin also produces a `DESIGN.md` that follows Google's open spec ("alpha", github.com/google-labs-code/design.md): YAML frontmatter with the normative tokens + markdown prose in a fixed section order. Figma and DESIGN.md are two outputs of one schema, so they never drift apart.

## What makes one useful (from the guides read when this was built)

- **Constraint, not description.** A file that is only tokens underperforms. Every important token needs its *intent and boundary* ("CTA only, never a background, one per screen"); components need *decision logic* (when X instead of Y); the file ends with imperative Do's/Don'ts that reference a concrete token, component or count. "Buttons should feel modern" is useless; "use `button-primary` for exactly one action per view" is enforceable.
- **The model extracts the "what"; the designer owns the "why".** Generated reasoning is fabricated reasoning. So the frontmatter is generated, and the prose comes only from the interview below. Unanswered = visible `TODO(interview)`.
- **Decisive over complete.** ~30 unambiguous answers beat 300 vague mentions. Leave out full colour ramps no component uses (the exporter emits resolved semantic roles only), every weight permutation, long-tail components. Median community file is ~7,000 tokens; stay at or under.
- **Never state the same fact in YAML and prose** - they drift. Prose gives context for applying a token, it does not repeat its value. `design_md.py check` flags hex/px values in prose that are not tokens.
- **Test it.** After export, generate three screens in Claude Code with the file loaded, look for deviations, add the missing constraint, repeat.

## Mapping from the schema

| Schema | DESIGN.md |
|---|---|
| semantic color (resolved to hex, first mode) | `colors.<role>` - spec vocabulary where there is a clear 1:1 (`background/default`→`surface`, `background/brand`→`primary`, `text/default`→`on-surface`, `text/on-brand`→`on-primary`, `border/default`→`outline`, `background/danger`→`error`...), otherwise the role without its group prefix (`background/cta`→`cta`). Collisions fall back to the full name. |
| second mode (Dark) | **a generated CSS block in the Colors section** (`:root` + `[data-theme="dark"]`, `--color-<role>`), all roles in both modes. Default (`--dark-style css`). A `colors-dark` map in the frontmatter is available with `--dark-style frontmatter`, but the official linter reports it as `token-like-ignored` (not a spec key; export tools skip it), so it is not the default. `design_md.py check` verifies the CSS block matches the tokens (errors on any mismatch), so it cannot silently drift. |
| primitives (50-900 ramps) | not exported (only the resolved values of roles in use) |
| text styles | `typography.<name>` - `heading/*`→`headline-*`; Figma style name → numeric `fontWeight`; `lineHeight` kept in px; `letterSpacing` in em; font stack gets a generic fallback |
| `space/*`, `radius/*` | `spacing.<n>` (quoted keys), `rounded.<size>` |
| component tokens (`button/background/primary`) | per-variant objects `button-primary: {backgroundColor, textColor}`; state variants (`-hover`...) inherit missing props from their base; `componentExtras` in the answers file adds `rounded`/`padding`/`typography`. **Border colours are not emitted**: `borderColor` is not a spec component property (the linter warns), so border bindings are written as generated bullets in the Components prose ("`nav` border: `outline-brand`"). |

Naming: a text role coloured like a background role (`text/brand` next to `background/brand`) becomes `<that key>-text` (`primary-text`), so it is not confused with `primary`.

## Expected linter result

Run the official linter every time (see below): the self-check cannot see these. Findings seen so far and what they mean:

- `orphaned-tokens` - a colour no component references. Fix by adding a component token that uses it (e.g. `link`, `kicker`) when the component really exists; do not invent components just to silence it.
- Two warnings are **expected and accepted** when the schema has border/focus colours (`outline-brand`, `outline-focus`): the spec gives components no border property, so nothing can reference them. They stay in the frontmatter (one normative place) and in the CSS block.
- `declared-omission` (info) - `omitted: [rounded, spacing]` is emitted when those groups were not approved.

## The interview (short, free text, one message)

Ask these in chat, accept short answers, write them to `design-md-answers.json` next to the schema. Anything skipped stays a TODO.

1. **Product and audience** - 2-3 sentences: what it does, who uses it, what the UI must help them do. (`overview`, `description`; also the file `name`)
2. **Main action and colours** - what is the single primary action per screen, and for each key colour role: what it is for and what it must never be used for. (`colorIntent`, `componentNotes`)
3. **Never** - 3-5 things the UI must never do (second accent, gradients, colour-only errors...). (`donts`; matching `dos` as imperatives)
4. **States and components** - which components matter most and which states are required (hover, focus-visible, disabled, error). (`componentNotes`, `componentExtras`)
5. **Voice** - one line each for a hero headline, a CTA, an error message, in the product's language(s). (`examples`)

Optional prose keys when the designer has an opinion: `typographyNotes`, `layout`, `elevation`, `shapes`.

Answers file shape:
```json
{"name": "", "description": "", "language": "he", "overview": "",
 "colorIntent": {"primary": "...", "cta": "..."},
 "componentNotes": ["..."], "dos": ["..."], "donts": ["..."],
 "examples": [{"label": "Primary CTA", "he": "...", "en": "..."}],
 "componentExtras": {"button": {"rounded": "{rounded.md}", "typography": "{typography.button}"}}}
```
`language: "he"` (or `ar`) appends the Localization section from `assets/design-md-localization-he.md` (RTL layout, Hebrew typography overrides, BiDi, copy formats). It is generic best practice; a project's own conventions doc takes precedence if it differs.

## Baseline rules (always written)

`design_md.py export` appends a "Baseline rules" block to every file's Do's and Don'ts, on top of the interview answers. Added 2026-10-12 after the "three screens" test, where a clean session building from DESIGN.md alone drifted in exactly these places (rule 4 is the general guard behind the invented radius and layout values):

1. No `opacity` / translucent colour on text over a coloured surface; use the `on-*` token (contrast is only guaranteed for the token pair).
2. Large display text uses the default text token at an on-scale size, not the brand colour, unless a typography+colour pair says so.
3. Every interactive component has a defined hover state or explicitly none; do not invent one when no `-hover` variant exists.
4. Use only radius, spacing and layout values defined in the file; if a needed value is missing, use the nearest defined one or ask the designer. Never invent.
5. (Only when a dark mode exists) Switch themes with `data-theme="dark"` on the root and a visible toggle; never `prefers-color-scheme` alone, never a hard-coded second palette.

Rule 4 is written whether or not shapes/layout were answered; it is what stops an agent from filling a gap with its own numbers. The rules are generic on purpose (no hex/px values) so `check` stays quiet. Radius and layout values are NOT in the baseline: those are the designer's decisions (interview keys `shapes` / `layout`).

## Wiring it into Claude Code

The file only helps if the agent reads it. Place `DESIGN.md` at the project root and add one rule to that project's `CLAUDE.md`, e.g. "When working on UI, treat DESIGN.md at the project root as the source of truth for colors, typography, spacing and component patterns." Editing the project's `CLAUDE.md` is a Tier 2 change: propose the line, don't write it unasked.

## Official linter (ask first)

`npx --yes @google/design.md lint DESIGN.md` prints JSON (`findings` with `severity`/`rule`/`path`, plus a `summary`): broken references (error), and contrast, orphaned tokens, missing primary, section order, unrecognised keys (warnings); `diff` compares versions. It downloads and runs an npm package, so ask the user before running it (once per session is enough), and report its output as it is - don't paper over warnings.
