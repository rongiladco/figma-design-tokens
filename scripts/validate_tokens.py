#!/usr/bin/env python3
"""
Schema validator for the figma-design-tokens skill.

  validate_tokens.py <schema.json>

Run it on the approved schema (the intermediate JSON from SKILL.md §3) before
building the preview. Exits 1 if there are errors; warnings don't fail it.

Expected shape (same as the TOKENS block in assets/figma-plugin/code.js):
  {
    "modes": ["Light", "Dark"],                         # optional
    "primitives": {"blue/500": "#3b82f6", ...},
    "semantics":  {"background/brand": "blue/600"
                   | {"aliasOf": "blue/600" | {"Light": "blue/600", "Dark": "blue/400"}}},
    "components": {"button/background/default": "background/brand", ...},   # optional
    "dimensions": {"space/4": 16, "radius/md": 8}                            # optional
  }

Checks (from zeroheight's token-hierarchy guidance):
  - semantic aliases point at an existing primitive (not a raw hex, "flattening")
  - component tokens point at an existing semantic token (or, with a warning, a primitive)
  - semantic/component names are role-based: no color words, no light/dark words
  - names use "/" grouping consistently (no spaces, dashes-as-separators, camelCase)
  - every mode in "modes" has an alias target for each multi-mode semantic
  - dimension tokens are numbers (warn on non-numeric / negative)

Stdlib only.
"""
import json
import re
import sys

COLOR_WORDS = {
    "blue", "red", "green", "grey", "gray", "yellow", "orange", "purple",
    "pink", "teal", "cyan", "indigo", "violet", "brown", "black", "white",
    "navy", "lime", "amber", "emerald", "rose", "slate", "zinc", "stone",
}
THEME_WORDS = {"light", "dark"}
HEX_RE = re.compile(r"^#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$")


def targets(defn):
    """Yield (mode_or_None, target_name) for a semantic/component definition."""
    alias = defn.get("aliasOf") if isinstance(defn, dict) else defn
    if isinstance(alias, dict):
        for mode, t in alias.items():
            yield mode, t
    else:
        yield None, alias


def words(name):
    return set(re.split(r"[/\-_]", name.lower()))


def validate(schema):
    errors, warnings = [], []
    prims = schema.get("primitives", {})
    sems = schema.get("semantics", {})
    comps = schema.get("components", {})
    dims = schema.get("dimensions", {})
    modes = schema.get("modes") or []

    for tier, tokens in (("primitive", prims), ("semantic", sems), ("component", comps), ("dimension", dims)):
        for name in tokens:
            if not NAME_RE.match(name):
                warnings.append(f"{tier} '{name}': name should be lowercase segments joined by '/' (dashes within a segment are fine) - mixed separators break Figma's grouping")

    for name, defn in sems.items():
        w = words(name)
        for bad in sorted(w & COLOR_WORDS):
            errors.append(f"semantic '{name}': contains color word '{bad}' - name the role, not the value (color names belong to primitives)")
        for bad in sorted(w & THEME_WORDS):
            errors.append(f"semantic '{name}': contains theme word '{bad}' - theme is a mode, not part of the name")
        seen_modes = set()
        for mode, t in targets(defn):
            if not isinstance(t, str) or not t:
                errors.append(f"semantic '{name}'{f' [{mode}]' if mode else ''}: missing alias target")
                continue
            if HEX_RE.match(t):
                errors.append(f"semantic '{name}': holds raw value '{t}' instead of a primitive name (flattening)")
            elif t not in prims:
                errors.append(f"semantic '{name}'{f' [{mode}]' if mode else ''}: target primitive '{t}' does not exist")
            if mode:
                seen_modes.add(mode)
        if seen_modes and modes:
            missing = [m for m in modes if m not in seen_modes]
            if missing:
                errors.append(f"semantic '{name}': no alias target for mode(s) {', '.join(missing)}")

    for name, defn in comps.items():
        w = words(name)
        for bad in sorted(w & COLOR_WORDS):
            errors.append(f"component '{name}': contains color word '{bad}' - name the role, not the value")
        for bad in sorted(w & THEME_WORDS):
            errors.append(f"component '{name}': contains theme word '{bad}' - theme is a mode, not part of the name")
        for mode, t in targets(defn):
            if not isinstance(t, str) or not t:
                errors.append(f"component '{name}': missing alias target")
            elif HEX_RE.match(t):
                errors.append(f"component '{name}': holds raw value '{t}' instead of referencing a semantic token (flattening)")
            elif t in sems:
                pass
            elif t in prims:
                warnings.append(f"component '{name}': references primitive '{t}' directly - skips the semantic tier, prefer a semantic token")
            else:
                errors.append(f"component '{name}': target '{t}' does not exist")

    for name, v in dims.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            errors.append(f"dimension '{name}': value must be a number, got {v!r}")
        elif v < 0:
            warnings.append(f"dimension '{name}': negative value {v}")

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    with open(sys.argv[1]) as f:
        schema = json.load(f)
    errors, warnings = validate(schema)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
