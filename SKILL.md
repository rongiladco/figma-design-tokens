---
name: figma-design-tokens
description: "Builds a color + typography design token system (primitive palette, semantic aliases, semantic text styles) and creates it as Figma Variables and Text Styles in a blank or existing Figma file. Use whenever someone wants to set up a design system, style guide, or token library in Figma — including phrasing like 'set up tokens in Figma', 'build a Figma design system from scratch', 'I have a blank Figma file and need colors + type styles', or 'turn this screenshot/site/Figma file into a token system'. Also trigger when the user shares screenshots, an existing Figma file, or a reference URL and wants a matching design system built from it, even if they never say the word 'tokens'."
---

# Figma Design Tokens

Turns a blank (or existing) Figma file into a working token system: a primitive color scale, semantic color aliases built on top of it, and semantic typography styles — created as real Figma Variables and Text Styles, not just documented. This is a prompt-only skill — everything below runs inside a Claude Code session (or any Claude Skills–compatible client), there's no deployed code.

**Scope, on purpose:** colors and typography only. Not spacing, radius, elevation/shadow, or component tokens. If a future run needs those, extend the schema deliberately rather than let this quietly grow into a general design-system builder.

## 0. Before anything else

1. If this project keeps its own running notes on skill gotchas (a `learnings.md` or similar), check it first — don't rediscover something already written down.
2. §7 (actually creating the tokens) doesn't strictly need an MCP at all — there's a self-contained Figma plugin bundled for exactly this (`references/figma-write.md` Path A), so don't treat a missing Figma MCP as blocking. It's still worth checking now (`ToolSearch` with query `"figma"`) since a *write-capable* MCP (Path B) lets you drive the creation yourself instead of handing the user a plugin to run — more convenient if one's available, not required if not.

## 1. Ask how they want to start

One question, and let them pick more than one if they've got a mix of references:

- **From scratch** — no reference at all, pure interview.
- **Screenshots** — one or more images of UI/branding they like.
- **An existing Figma file** — extract/harmonize from what's already there.
- **A URL** — a live site to pull visual direction from.

Whichever path (or combination) they pick, read only the matching reference file(s) before moving on — no need to load all four:

| Path | Read |
|---|---|
| Scratch | `references/from-scratch.md` |
| Screenshots | `references/from-screenshots.md` |
| Existing Figma file | `references/from-figma-file.md` |
| URL | `references/from-url.md` |

Each of these is mechanically different (reading pixels vs. querying Figma vs. fetching a page), but they all feed the same target: enough visual direction to move to §2.

## 2. Direction-setting follow-up questions

Regardless of path, a reference (or lack of one) only tells you *what exists* — it doesn't tell you what the system should optimize for. Ask, batched via `AskUserQuestion` where they're genuinely open decisions:

- What's this for — product UI, marketing site, both? (affects how much the type scale needs to flex across contexts)
- Any brand colors or fonts that are fixed and must be built around, vs. fully open?
- Does it need dark mode / theming, or just one mode for now? (determines whether color Variables need multiple modes set up from the start — much cheaper to decide now than to retrofit)
- Accessibility target for text contrast — WCAG AA (4.5:1 body text) is the sane default if they don't have a preference, but ask rather than assuming AAA or nothing.
- Any fixed font-licensing constraint (must be a Google Font / already-licensed family), or open to a recommendation?

If the project involves Hebrew or RTL content, apply your own house RTL/typography conventions if you have them (or ask). Font pairing, line-height, and letter-spacing defaults tuned for Latin type often need real adjustment for Hebrew — don't assume they carry over unchanged.

Don't over-ask: if the reference material already answers one of these clearly (e.g. a screenshot that's obviously dark-mode-only), confirm it rather than asking from scratch.

## 3. Build the token schema

Read `references/token-schema.md` for the exact structure (two-tier colors: primitives + semantic aliases; semantic typography styles) and default naming conventions.

For any primitive color scale derived from a base hex, use `scripts/color_tools.py generate-scale` rather than eyeballing tints/shades by hand — color math is exactly the kind of thing that's easy to get subtly wrong through reasoning alone and cheap to get right with a script. Use `scripts/color_tools.py check-contrast` to verify every semantic text/background pairing actually meets the accessibility target chosen in §2 *before* presenting the preview — catching a failing pairing after Figma creation is much more annoying to fix than before.

## 4. Build and show the preview

Build an HTML preview from `assets/preview-template.html` — color swatches for every primitive and semantic token (labeled with name + hex), live type specimens for every semantic text style (rendered at actual size/weight/line-height, not just described), and the full token-reference table at the bottom (every token, its value, and what it binds to for semantic/alias tokens) — the swatches are for judging how it looks, the table is what someone would actually reference while implementing.

Save it to the calling project's `Output/` folder (create one if it doesn't exist) and open it locally for review. **Don't publish this anywhere** (as a Claude Artifact, a hosted link, etc.) — a design-system preview is exactly the kind of draft that should stay private on disk until it's approved, not turn into a shareable link by default.

## 5. Iterate until approved

Show the preview, get feedback, adjust the schema (§3) and rebuild the preview (§4). Loop until the user explicitly approves — don't move to §6 on an ambiguous "looks fine" if they clearly haven't looked closely. This approval is the checkpoint that makes the Figma write in §7 a deliberate, reviewed action rather than an automated one touching a real file.

## 6. Confirm the target file

Ask for the Figma file URL or key, and whether it's the blank file they started from or an existing file with content already in it. If it's an existing file, this matters for §7 — there may already be Variables or Styles with colliding names.

## 7. Create the tokens in Figma

Read `references/figma-write.md` for the three ways to do this: **Path A**, the default — fill in the bundled plugin template (`assets/figma-plugin/`) with the approved schema and have the user import + run it once inside Figma (no MCP needed at all); **Path B** — a third-party write-capable Figma MCP, if one happens to be connected; or **Path C** — Figma's own official remote MCP (`use_figma`), which lets you drive the whole creation yourself in small verified steps, no user hands-on-Figma required, but comes with its own execution contract (return-based, no `closePlugin`/`notify`) and a mandatory skill resource gating it — re-check with `ToolSearch` for what's actually connected, most Figma MCPs people connect by default are read-only, don't assume. Whichever path: check the target file for existing Variable collections/Text Styles that would collide with the names you're about to create, ask the user how to resolve any collision (overwrite / rename / merge) rather than picking silently, then create the primitive Variables (with `scopes = []`), the semantic Variables aliased to them (with role-based `scopes`), and the Text Styles (with a real `style` name, not a numeric weight).

Don't fabricate a "created" result on any path — with Path A specifically, you can't see the outcome yourself, so ask the user to relay what the plugin reported before declaring success. With Path C, verify via a read-back before reporting, since scripts there run atomically and a mid-batch failure needs to surface honestly ("created 14 of 16...") rather than get rounded up.

## 8. Wrap up

Summarize what was created (counts of primitive/semantic color variables, text styles, which modes if any) and confirm it's live in the file. If this project keeps a running notes file for skill gotchas (see §0), add anything worth remembering — a naming choice that worked well, a Figma API quirk hit during creation, a question that should've been asked earlier. Don't skip this even on a smooth run; the quirks worth remembering are often small.
