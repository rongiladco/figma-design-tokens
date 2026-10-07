# Token schema

The intermediate representation every path (§1 in SKILL.md) converges on, before anything gets written to Figma. Keep it as plain JSON while you're iterating in §3–§5 — it's easier to edit and diff than reasoning about Figma's native structures directly, and it maps cleanly onto Variables + Text Styles when you get to §7.

## Colors — two tiers

**Primitives**: a raw scale per hue, never referenced directly by anything a designer applies to a layer. Default naming: `{hue}/{step}`, steps `50, 100, 200, ..., 900` (lightest to darkest — Tailwind-style, most people building products already have this mental model). Use `scripts/color_tools.py generate-scale` to derive a full scale from one base hex rather than hand-picking nine values.

```json
{
  "blue/50":  "#eff6ff",
  "blue/500": "#3b82f6",
  "blue/900": "#1e3a8a"
}
```

**Semantic aliases**: the names designers actually apply, each pointing at a primitive step. Default role set — treat as a starting proposal to confirm/edit with the user, not a fixed list:

```json
{
  "background/default":  { "aliasOf": "gray/50" },
  "background/subtle":   { "aliasOf": "gray/100" },
  "background/brand":    { "aliasOf": "blue/600" },
  "text/default":        { "aliasOf": "gray/900" },
  "text/muted":          { "aliasOf": "gray/500" },
  "text/on-brand":       { "aliasOf": "gray/50" },
  "text/danger":         { "aliasOf": "red/600" },
  "border/default":      { "aliasOf": "gray/200" },
  "border/focus":        { "aliasOf": "blue/500" }
}
```

The `{ "aliasOf": ... }` wrapper is the shape the plugin's `TOKENS` block reads (`code.js` does `def.aliasOf`), so keep it in the schema rather than rewrapping later. When the target differs per mode, `aliasOf` is an object keyed by mode name: `{ "aliasOf": { "Light": "gray/50", "Dark": "gray/900" } }`. Component tokens are the exception: single mode, so they stay a bare string naming a semantic token (`"button/background/default": "background/brand"`).

**No `color/` category prefix** — primitives and semantics already live in two separate Figma collections (see below), so a category segment isn't earning its keep the way it would if colors and other token types (spacing and radius, which are optional here and live in their own "Dimensions" collection) ever shared one flat namespace. `assets/figma-plugin/code.js`'s `scopesForSemantic()` matches on the bare role prefix (`background/`, `text/`, `border/`) — a name like `color/background/default` would silently miss every one of those checks and fall through to the generic `ALL_FILLS` default instead of the more precise scope. Keep names exactly as shown above; if a future version of this skill adds a category layer, `scopesForSemantic()` needs updating to match, not just the schema.

Every semantic pairing that's meant to sit text-on-background (`text/default` on `background/default`, `text/on-brand` on `background/brand`, etc.) must pass `scripts/color_tools.py check-contrast` against the accessibility target from §2 before the preview goes out. If a pairing fails, adjust which primitive step the alias points to (usually one step darker/lighter) rather than inventing an off-scale color just to pass — keeping every semantic alias pointing at a scale step is what makes the system maintainable later.

**Scopes, at write time (§7):** a Variable defaults to `ALL_SCOPES` in Figma, which clutters every color picker with tokens that were never meant to be applied directly — set it explicitly instead. Primitives get `scopes = []` (hidden entirely — nothing should ever pick one directly, per the "never referenced directly" rule above). Semantics get scoped to where their role actually applies: `background/*` → `["FRAME_FILL", "SHAPE_FILL"]`, `text/*` → `["TEXT_FILL"]`, `border/*` → `["STROKE_COLOR"]`. `assets/figma-plugin/code.js` already implements this mapping — extend it (don't bypass it) if a new role prefix is introduced.

**Two Figma collections, not one.** Primitives live in their own collection with a single mode — a primitive's value doesn't change meaning between light and dark, so giving it modes at all is the wrong model, even though Figma would technically allow it. Semantic aliases live in a *separate* collection that has one mode per theme (`Light`, `Dark`, ...) — Figma Variables support aliasing across collections natively, so a semantic Variable in the "Colors" collection can alias a primitive Variable in the "Primitives" collection without issue.

**Dark mode**, if requested in §2: `background/default` still exists once, as a single semantic Variable — what changes per mode is *which primitive it aliases*, not its name and not a duplicate variable. E.g. `background/default` aliases `gray/50` in the Light mode and `gray/900` in the Dark mode of the same Variable. Don't build parallel `background/default-dark` names, and don't give the *primitives* collection multiple modes just because the semantic layer has them.

**Interactive states — optional, ask rather than assume.** A system meant for product UI (per the §2 "what's this for" answer) usually needs more than one color per role: a button's `background/brand` isn't one static color, it's default/hover/active/disabled. A marketing site rarely needs this at all. If it's needed, derive states from the *same primitive scale* the semantic alias already points to, by stepping to an adjacent scale position rather than inventing a new color — e.g. if `background/brand` → `blue/600`, then `hover` → `blue/700` (one step darker) and `active` → `blue/800` (two steps darker) reads as the same color family getting more emphatic, which is what a hover/active state should feel like. Keep it to the states actually needed (hover/active is usually enough; add `disabled`/`focus` only if asked) rather than generating a full state matrix for every role by default — most roles (backgrounds, borders, muted text) never get interacted with and don't need states at all.

## Component tokens — optional third tier (ask, don't assume)

Source: zeroheight's three-tier model (global → alias → component). Here "global" = primitives and "alias" = semantics; the flow only goes downward — a component token references a semantic token, never holds a raw hex, and a primitive never knows which component uses it.

**Default: skip this tier.** It earns its place only when a component has design decisions specific enough to deserve their own name, or when the system needs a local override point (e.g. the button's hover color must change without touching every other `background/brand` consumer). A system for a marketing site, or an early-stage product UI, should stop at two tiers — adding component tokens before you know which decisions are really component-specific is the "created too early" mistake. Ask in §2 only when "product UI" is the answer to what the system is for.

When it's in scope: name them `{component}/{property}/{state}` (e.g. `button/background/default`, `button/background/hover`, `button/text/default`), each aliasing a **semantic** token (`background/brand`, a hover variant, `text/on-brand`). They live in a third Figma collection (default name "Components", single mode — the mode switching already happens in the semantic collection, and an alias resolves through it automatically). Only create tokens for components the user actually names; don't generate a component set speculatively.

## Don't over-tokenize

Every token is something someone has to name, document and govern. A value that appears once and has no reason to repeat (a one-off illustration color, a single decorative gradient stop) does **not** become a token — leave it as a local value in the file. Before adding any semantic or component token, ask whether a second consumer exists or is genuinely expected. Primitives are the exception: they're exhaustive by design (cover the range the design language could express, not just what's used today), and are hidden from pickers anyway.

## Dimensions — spacing and radius (optional, ask in §2)

Colors and typography stay the default scope. If the user wants spacing/radius too, add them as **flat global scales**, one `FLOAT` Variable per step, in a single-mode "Dimensions" collection — same reasoning as primitives having no modes. Don't invent an alias tier for them unless asked: zeroheight's own guidance is that radius in particular rarely needs a deep hierarchy, and a flat scale that components reference directly is fine. Shadow and motion remain out of scope (shadow is a composite value, motion needs code-side support).

```json
{
  "space/1": 4, "space/2": 8, "space/3": 12, "space/4": 16, "space/6": 24, "space/8": 32,
  "radius/none": 0, "radius/sm": 4, "radius/md": 8, "radius/lg": 16, "radius/full": 9999
}
```

Spacing steps should follow a consistent base unit (4 or 8px multiples). Scopes at write time: `space/*` → `["GAP"]` (Figma uses this scope for both gap and padding), `radius/*` → `["CORNER_RADIUS"]`. Unlike color primitives these are meant to be applied directly, so they're not hidden.

## Typography — semantic text styles

Each style bundles everything needed to apply it in one click: family, style, size, line-height, letter-spacing. **`style` is a string, not a number** — Figma identifies a font by `{family, style}` where `style` is the exact name Figma itself uses ("Regular", "Medium", "Semi Bold", "Bold", ...), not a CSS-style numeric weight. `assets/figma-plugin/code.js` passes this straight to `loadFontAsync({family, style})`, so a numeric value here would fail at write time with an unhelpful "unloaded font" error rather than a clear one. Default scale — again, a starting proposal:

```json
{
  "heading/xl":  { "family": "Inter", "style": "Bold",      "size": 40, "lineHeight": 48, "letterSpacing": -0.02 },
  "heading/lg":  { "family": "Inter", "style": "Bold",      "size": 32, "lineHeight": 40, "letterSpacing": -0.01 },
  "heading/md":  { "family": "Inter", "style": "Semi Bold", "size": 24, "lineHeight": 32, "letterSpacing": 0 },
  "heading/sm":  { "family": "Inter", "style": "Semi Bold", "size": 20, "lineHeight": 28, "letterSpacing": 0 },
  "body/lg":     { "family": "Inter", "style": "Regular",   "size": 18, "lineHeight": 28, "letterSpacing": 0 },
  "body/md":     { "family": "Inter", "style": "Regular",   "size": 16, "lineHeight": 24, "letterSpacing": 0 },
  "body/sm":     { "family": "Inter", "style": "Regular",   "size": 14, "lineHeight": 20, "letterSpacing": 0 },
  "caption":     { "family": "Inter", "style": "Regular",   "size": 12, "lineHeight": 16, "letterSpacing": 0.02 }
}
```

If it's more natural to think in numeric weights while designing (400/600/700...), that's fine for the conversation with the user — just translate to the real Figma style name before it lands in this schema, and **verify the `{family, style}` pair actually exists** (via `listAvailableFontsAsync()` when writing through `use_figma`, or by asking the user to confirm it's installed for Path A) rather than assuming a name like "Semi Bold" exists for every family — some fonts call it "SemiBold", "600", or don't have that weight at all.

`letterSpacing` is in **em** (a fraction of the font size, matching how type systems usually express it) — `-0.02` means "-0.02 × font size", not -0.02 pixels. Whatever writes the actual Figma Text Style needs to convert this to pixels at write time (`letterSpacing × size`).

Sizes step by a consistent ratio rather than arbitrary numbers — a modular scale (e.g. 1.125–1.25×, "major second" to "major third") applied to a base body size (usually 16px) keeps the hierarchy feeling designed rather than guessed. Line-height is typically 1.4–1.6× the size for body text and tighter (1.1–1.25×) for large headings, where too much leading looks broken. Letter-spacing is usually 0 except slightly negative on large headings (tighter, more confident) and slightly positive on all-caps/small text (more legible at small sizes).

Two font families max (one for headings, one for body — or the same family for both) unless the reference material clearly calls for more. Every family used must be something Figma can actually render — confirm in §2 whether it's a Google Font (safe default, always available) or a custom/licensed family the user's Figma team already has installed, since there's no way to verify font availability from outside Figma itself.

## Naming

**Semantic and component names describe a role, never a value.** `text/muted` survives dark mode; `text/grey` becomes actively misleading the moment dark mode resolves it to something light. So a semantic or component name must not contain a color word (`blue`, `grey`/`gray`, `red`, ...) or a theme word (`light`, `dark`). Color names belong to primitives only. Also never put a raw hex in a semantic/component definition ("flattening") — it must reference a primitive/semantic by name, otherwise the link between palette and usage is lost and several tokens end up holding the same value with no shared source. `scripts/validate_tokens.py` checks both before the preview goes out (see SKILL.md §3).

`{group}/{step-or-role}` with forward slashes — this is what makes Figma's Variables/Styles panel group things into a navigable tree instead of a flat list, and it's the exact convention `assets/figma-plugin/code.js` expects (see the no-`color/`-prefix note above — this isn't just a style preference, the scope-inference logic depends on it). Stick to this pattern for every name you create; don't mix in different separators (dashes, camelCase) partway through, since that breaks the grouping.
