# Writing tokens to Figma

This is the step the rest of the skill builds up to, and the one most likely to fail quietly if you're not careful — so verify capability before promising results, and never report tokens as "created" without a confirmed write.

There are three ways to actually do this. None require an Enterprise plan — the thing that's plan-gated is Figma's **REST API** write access to Variables, and none of the paths below go through the REST API for the write itself.

## Path A — a self-contained plugin (default; needs nothing external)

`assets/figma-plugin/` is a template Figma plugin (`manifest.json` + `code.js`) that creates everything through the Plugin API directly — `figma.variables.createVariableCollection()`, `figma.variables.createVariable()`, `figma.createTextStyle()` — running inside Figma itself. No MCP, no personal access token, no websocket bridge, no plan requirement, because the Plugin API isn't gated the way the REST API is.

1. Copy `assets/figma-plugin/` to a working location (e.g. the calling project's `Output/` folder) and fill in the `TOKENS` block in `code.js` (clearly marked between `=== TOKENS ===` and `=== END TOKENS ===`) with the approved schema from §3 of SKILL.md — primitives (flat name → hex), semantics (name → `{ aliasOf: "gray/50" }`, or `{ aliasOf: { Light: ..., Dark: ... } }` if the target differs per mode), optionally `components` (name → semantic token name) and `dimensions` (name → number), and text styles (family/style/size/lineHeight/letterSpacing). The script already handles the primitives-collection-vs-semantic-collection split and per-mode aliasing described in `references/token-schema.md` — you're populating data, not writing plugin logic.
2. Tell the user to import it once: Figma Desktop → Plugins → Development → Import plugin from manifest → point at the `manifest.json` you just filled in.
3. Tell them to run it (Plugins → Development → Design Token Creator) inside the target file. It reports what it created/skipped in a toast when it finishes (`figma.closePlugin(summary)`), and logs any skipped collisions to the console.
4. **You can't see the result yourself** — the plugin runs in the user's Figma session, not through a tool call you make. Ask them to relay the summary (or a screenshot of the new Variables/Text Styles panel) so you can confirm counts before reporting success, per §4 below. Don't report "created" on the strength of "the user said they clicked Run."
5. If the token schema changes after a review round, overwrite `code.js`'s `TOKENS` block and have them re-run — re-running is safe, since the script skips anything that already exists by name rather than duplicating it.

This is the right default because it has zero setup cost beyond one plugin import, and it works regardless of what's connected to this session. The tradeoff is that it's not something *you* can drive end-to-end without the user's hands-on participation each run.

## Path B — a write-capable Figma MCP (optional, more automated)

If a write-capable Figma MCP is already connected, you can drive the whole thing yourself without the user touching Figma directly. Don't assume based on the name alone — run `ToolSearch` with query `"figma"` and read what's actually there:

**A server exposing only `get_*` tools (design context, metadata, variable defs, screenshot, motion context) is Figma's official Dev Mode MCP Server — read-only, by design, built for design-to-code workflows.** This is the one people connect by default, and it cannot create or modify Variables or Styles no matter how the request is phrased. It's still genuinely useful for `references/from-figma-file.md` (reading an existing file), just not for this step — fall back to Path A or check for Path C below.

For real write access via a *third-party* MCP, a known-working option is [`southleft/figma-console-mcp`](https://github.com/southleft/figma-console-mcp) paired with its **Desktop Bridge plugin**: a companion plugin imported into Figma Desktop (Plugins → Development → Import plugin from manifest → the manifest at `~/.figma-console-mcp/plugin/manifest.json`, then run it once), which opens a local WebSocket (ports 9223–9232) that the MCP server talks to. That bridge is what unlocks real `CREATE_VARIABLE` / `UPDATE_VARIABLE`-style calls through the same Plugin API Path A's generated plugin uses — same underlying mechanism, just remote-controlled instead of a one-shot script.

Once a write-capable server is confirmed, map the operations in "Create in this order" below onto whatever tool names it actually exposes — don't assume they match the names used here.

## Path C — Figma's own official remote MCP (preferred over Path B when available)

Figma ships an official MCP server with a **write-to-canvas** capability (currently free, in beta) — connect it at `https://mcp.figma.com/mcp` (HTTP transport; in Claude Code, `claude mcp add --transport http figma-remote https://mcp.figma.com/mcp -s user`, then complete the OAuth login via `/mcp` in a session, since connecting and authenticating both require a session restart to take effect). Once connected, the write tool is `use_figma` — it executes Plugin API JS you write inline, and it is **gated behind a mandatory skill resource** (`skillNames: "resource:figma-use"`) exactly like the read-only server's `get_design_context` gates on design-to-code guidance — read that skill's full rules before writing any script for it, don't rely on the summary below.

**Its execution contract is a genuinely different shape than Path A's plugin, not just a different transport** — don't reuse `code.js` verbatim against it:

- Return results via a plain `return` statement. No `figma.closePlugin()`, no wrapping IIFE, no `figma.notify()` (it throws). `console.log` isn't visible to you afterward — anything worth knowing must come back through the return value.
- Every Promise must be awaited; the canonical text-edit recipe (`loadFontAsync` → await → mutate → `return`) applies to `createTextStyle()` just as much as to text nodes.
- `figma.currentPage` resets on every call and can be changed at most once per script — irrelevant for pure Variable/Style creation (those aren't page-scoped), but relevant if a future version of this skill adds a visible specimen frame.
- **Work in small, verified steps — capped around ~10 "logical operations" per call.** For a typical system (say 30 primitives across a few hues, 12–15 semantics, 6–10 text styles), don't attempt it in one script. A workable split:
  1. Create both collections (with modes).
  2. Primitives in batches of ~10 (multiple `use_figma` calls) — each returns the created Variable IDs.
  3. A read-only lookup confirming the primitives exist and collecting their IDs, since semantics need those IDs to alias against — don't assume the IDs from step 2's return are still valid without this check if any time or other calls passed in between.
  4. Semantics in batches of ~10, each `VARIABLE_ALIAS` pointing at an ID from step 3.
  5. Component tokens and dimensions, if approved (same batching, aliasing to semantic IDs looked up as in step 3).
  6. Text styles (usually fits in one call, under the cap).
  7. Final validation — `get_metadata` and/or a screenshot of the Variables/Text Styles panel.
- **This ~10-operation batching is specific to `use_figma` being called repeatedly by you, the agent** — it does not apply to Path A, which runs as one continuous plugin execution inside Figma with no equivalent mid-run validation checkpoint. Don't "fix" Path A's `code.js` to match this batching; they're different execution models on purpose.

**Status in this skill: confirmed working end-to-end**, not just documented. Verified by creating a real COLOR Variable via `mcp__figma-remote__use_figma` (with explicit `{r,g,b,a}` and `scopes`, exactly as specified above), then reading it back in a *separate* `use_figma` call via `getVariableByIdAsync` to confirm it actually persisted rather than trusting the first call's return value alone. Both the `{r,g,b,a}` shape and explicit `scopes` worked cleanly with no error — the tool name may still vary by how the user's specific MCP connection was set up (this one was added as `figma-remote`), so re-confirm the exact name via `ToolSearch` rather than hardcoding `mcp__figma-remote__use_figma`.

## Check for collisions before creating anything

List existing Variable collections and Text Styles in the target file. For every name you're about to create (from the approved token schema), check whether it already exists. **Default toward reusing/extending what's already there rather than replacing it** — a Variable that already exists may be referenced by frames elsewhere in the file that the user isn't thinking about right now, and silently overwriting it can break those without anyone noticing until later. If a genuine collision needs resolving, ask the user specifically (overwrite this one / rename the new one / merge) rather than picking a default — and treat "overwrite" as something that needs its own explicit yes per colliding token, not a blanket policy applied to the whole batch. (Path A's plugin already enforces "skip on collision" as its own default; a deliberate overwrite there means the user removes the existing Variable/Style in Figma first, or you adjust the name in the approved schema.)

## Create in this order

Order matters because semantic Variables need the primitives to exist first, and Text Styles are independent of the color work:

1. **Variable collections** — "Primitives" (single mode) and a semantic collection (one mode per theme if dark mode is in scope); plus, only if approved, a single-mode "Components" collection and a single-mode "Dimensions" collection. See `references/token-schema.md` for why these are separate collections, not one.
2. **Primitive color Variables** — one per `color/{hue}/{step}` entry from the approved schema, mode-invariant, `scopes = []` (hidden from pickers — see `references/token-schema.md`).
3. **Semantic color Variables** — one per `color/{role}/{variant}` entry, each **aliased to** the matching primitive Variable (not given a hard-coded hex value directly), with the alias target set per mode if it differs between Light/Dark, and `scopes` set per role (`background/*` / `text/*` / `border/*`, see `references/token-schema.md`). This is what makes the system actually maintainable — changing a primitive later cascades to every semantic alias pointing at it.
4. **Component tokens** (if approved) — one COLOR Variable per entry in the "Components" collection, each aliased to a **semantic** Variable (never a primitive, never a hex). Scope by role segment in the name (`background` → fills, `text` → `TEXT_FILL`, `border` → `STROKE_COLOR`).
5. **Dimensions** (if approved) — one FLOAT Variable per step in "Dimensions": `space/*` → scope `["GAP"]`, `radius/*` → `["CORNER_RADIUS"]`. Not hidden from pickers (they're meant to be applied directly).
6. **Text Styles** — one per semantic typography entry, with family/style/size/line-height/letter-spacing set as specified (letter-spacing converted from em to px: `letterSpacing × size`; `style` must be a real Figma style name for that family, not a numeric weight — see `references/token-schema.md`).

Optional finishing touch, not required for the skill's core scope: if the token system is meant to hand off to developers, `setVariableCodeSyntax` links a Variable to how it should appear in code (e.g. `var(--color-background-brand)`) — worth doing if asked, not worth adding by default since it's dev-handoff polish rather than a design-system requirement.

## Verify, don't just assume success

After creation, confirm what was actually created before reporting success to the user — read it back via MCP if that's the path taken, or ask the user to relay the plugin's summary/screenshot if Path A was used. A partial failure midway through (a name collision, a font not installed in Figma) should surface as "created 14 of 16, these two failed because X" — not get rounded up to "done."
