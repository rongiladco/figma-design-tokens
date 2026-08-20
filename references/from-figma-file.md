# Starting from an existing Figma file

Requires a connected Figma MCP with read access (see `references/figma-write.md` for the write-access caveat — a read-capable server doesn't necessarily also write). Confirm via `ToolSearch` with query `"figma"` before starting this path; if nothing's connected, tell the user this specific path is blocked until they connect one, and offer screenshots or a URL as an alternative way to reference the same file's content in the meantime (e.g. they export/screenshot a frame).

Once connected, inspect the file for:

- **Existing Variables and Styles** — if the file already has color Variables or text Styles defined, that's the starting point, not something to build over. Read what's there before proposing anything new. If it's partial (colors defined, no type styles, or vice versa) the job becomes filling the gap in a way that's consistent with what already exists, not designing from zero.
- **Colors and type actually used on canvas**, separate from what's formally tokenized — designers often apply raw hex values or font styles inconsistently before a token system exists. Sampling what's actually on the canvas (not just the Styles panel) surfaces the *real* palette in use, which is usually more useful than an incomplete or stale Styles panel.
- **Naming/organization already in place** — if there's an existing convention (even an inconsistent one), match its spirit in `references/token-schema.md`'s naming section rather than imposing an unrelated scheme that'll sit awkwardly next to what's there.

Flag explicitly, before moving to SKILL.md §2, whether you found:
- nothing formal (canvas has content, no tokens) → straightforward net-new build using this file's visual content as reference,
- a partial system → gap-filling,
- or a full existing system with different names than what you'd propose → ask whether to extend it as-is or replace/rename, since silently creating parallel tokens with different names is the collision scenario SKILL.md §6 warns about.
