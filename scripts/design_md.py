#!/usr/bin/env python3
"""
DESIGN.md exporter + checker for the figma-design-tokens skill.

  design_md.py export <schema.json> [--answers answers.json] [-o DESIGN.md]
  design_md.py check  <DESIGN.md> --schema schema.json
  design_md.py export-css <schema.json> -o tokens.css [--check]

Turns the approved token schema (the same JSON the Figma plugin reads) into a
DESIGN.md that follows Google's open spec (github.com/google-labs-code/design.md,
"alpha"): YAML frontmatter holding the normative tokens, then markdown prose in
the spec's section order.

What it does and does NOT do:
  - The FRONTMATTER is deterministic: resolved semantic colors (Light, plus a
    non-spec `colors-dark` map), typography, rounded, spacing, components.
    Only roles that components/screens actually use are emitted - full
    50-900 primitive ramps are left out on purpose (a short, decisive file
    beats an exhaustive one).
  - The PROSE (overview, color intent/boundaries, don'ts, voice examples)
    comes ONLY from the answers file produced by the short interview. Anything
    not answered is left as a visible `TODO(interview)` marker. Nothing about
    the product, its audience or its rules is invented.

`check` runs stdlib-only consistency checks: every {reference} resolves,
section order / duplicate headings, hex and px values in prose that are not in
the tokens (the prose-vs-YAML drift the best-practice guides warn about),
leftover TODO markers, and a size estimate. For the official linter, see
SKILL.md (npx @google/design.md lint - ask before running it).
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from color_tools import check_contrast  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALIZATION_TEMPLATE = os.path.join(HERE, "..", "assets", "design-md-localization-he.md")

# Our role names -> the spec's recommended vocabulary where there is a clear 1:1.
# Anything not listed keeps its own name with "/" -> "-".
ROLE_MAP = {
    "background/default": "surface",
    "background/subtle": "surface-container",
    "background/raised": "surface-raised",
    "background/brand": "primary",
    "background/brand-hover": "primary-hover",
    "background/danger": "error",
    "text/default": "on-surface",
    "text/muted": "on-surface-muted",
    "text/on-brand": "on-primary",
    "text/on-danger": "on-error",
    "text/danger": "error-text",
    "border/default": "outline",
    "border/focus": "outline-focus",
}
WEIGHTS = {"Thin": 100, "Extra Light": 200, "ExtraLight": 200, "Light": 300, "Regular": 400,
           "Medium": 500, "Semi Bold": 600, "SemiBold": 600, "Bold": 700,
           "Extra Bold": 800, "ExtraBold": 800, "Black": 900}
GENERIC = {"Corben": "serif", "Georgia": "serif", "JetBrains Mono": "monospace"}
PROP_MAP = {"background": "backgroundColor", "text": "textColor", "border": "borderColor"}
STATE_SUFFIXES = ("hover", "active", "focus", "disabled")
SECTIONS = ["Overview", "Colors", "Typography", "Layout", "Elevation & Depth", "Shapes",
            "Components", "Do's and Don'ts"]


def q(v):
    return json.dumps(v, ensure_ascii=False)


def name_map(schema):
    """semantic role name -> spec color key. Spec vocabulary where mapped, otherwise the role
    without its group prefix (background/cta -> cta, text/on-cta -> on-cta, border/x -> outline-x).
    On a collision the later token falls back to its full flattened name."""
    used, nm = set(), {}
    for name in schema["semantics"]:
        group, _, rest = name.partition("/")
        cand = ROLE_MAP.get(name) or ({"background": rest, "text": rest, "border": "outline-" + rest}.get(group) or name.replace("/", "-"))
        # text coloured like a background role (text/brand next to background/brand) -> "<that role's key>-text"
        if group == "text" and name not in ROLE_MAP and not rest.startswith("on-") and ("background/" + rest) in schema["semantics"]:
            bg = "background/" + rest
            cand = (ROLE_MAP.get(bg) or rest) + "-text"
        if cand in used:
            cand = name.replace("/", "-")
        used.add(cand)
        nm[name] = cand
    return nm


def resolve(schema):
    """Return (light, dark, modes) dicts of spec-color-name -> hex, only for semantic roles."""
    P, S = schema["primitives"], schema["semantics"]
    modes = schema.get("modes") or ["Light"]
    nm = name_map(schema)
    out = {m: {} for m in modes}
    for name, d in S.items():
        a = d["aliasOf"] if isinstance(d, dict) else d
        for m in modes:
            target = a[m] if isinstance(a, dict) else a
            out[m][nm[name]] = P[target]
    return out, modes


def px(v):
    return f"{v:g}px" if isinstance(v, (int, float)) else str(v)


def build_tokens(schema, answers):
    colors_by_mode, modes = resolve(schema)
    tokens = {"colors": colors_by_mode[modes[0]], "colors-dark": None, "typography": {}, "rounded": {},
              "spacing": {}, "components": {}, "component_meta": {}}
    if len(modes) > 1:
        tokens["colors-dark"] = colors_by_mode[modes[1]]
    for name, t in schema.get("textStyles", {}).items():
        key = name.replace("heading/", "headline-").replace("/", "-")
        fam = t["family"]
        stack = f"{fam}, {GENERIC.get(fam, 'sans-serif')}"
        entry = {"fontFamily": stack, "fontSize": px(t["size"]),
                 "fontWeight": WEIGHTS.get(t["style"], 400), "lineHeight": px(t["lineHeight"])}
        if t.get("letterSpacing"):
            entry["letterSpacing"] = f"{t['letterSpacing']:g}em"
        tokens["typography"][key] = entry
    for name, v in schema.get("dimensions", {}).items():
        group, step = name.split("/", 1)
        if group == "radius":
            tokens["rounded"][step] = px(v)
        elif group == "space":
            tokens["spacing"][step] = px(v)
    # components: group "button/background/primary" -> button-primary { backgroundColor }
    comps = {}
    nm = name_map(schema)
    for name, target in schema.get("components", {}).items():
        parts = name.split("/")
        comp = parts[0]
        prop, variant = (parts[1], parts[2]) if len(parts) == 3 else (parts[1], "default")
        key = comp if variant == "default" else f"{comp}-{variant}"
        comps.setdefault(key, {"_comp": comp, "_variant": variant})[PROP_MAP.get(prop, prop)] = "{colors.%s}" % nm[target]
    for key, props in comps.items():  # state variants inherit missing props from their base variant
        base = key.rsplit("-", 1)[0] if key.rsplit("-", 1)[-1] in STATE_SUFFIXES else None
        if base and base in comps:
            for k, v in comps[base].items():
                props.setdefault(k, v)
    extras = answers.get("componentExtras", {})
    for key, props in comps.items():
        comp = props.pop("_comp")
        tokens["component_meta"][key] = (comp, props.pop("_variant"))
        merged = dict(extras.get(comp, {}))
        merged.update(extras.get(key, {}))
        for k, v in merged.items():
            props.setdefault(k, v)
        tokens["components"][key] = props
    return tokens


def frontmatter(tokens, schema, answers, dark_style="css"):
    L = ["---", "version: alpha", f"name: {q(answers.get('name') or schema.get('name') or 'Design System')}"]
    if answers.get("description"):
        L.append(f"description: {q(answers['description'])}")
    omitted = [g for g in ("typography", "rounded", "spacing") if not tokens[g]]
    if omitted:
        L.append("omitted: [" + ", ".join(omitted) + "]  # token groups intentionally not defined")
    L.append("colors:")
    L += [f"  {k}: {q(v)}" for k, v in tokens["colors"].items()]
    if tokens["colors-dark"] and dark_style == "frontmatter":
        L.append("colors-dark:  # non-spec extension: same keys as `colors`, values for dark mode")
        L += [f"  {k}: {q(v)}" for k, v in tokens["colors-dark"].items()]
    if tokens["typography"]:
        L.append("typography:")
        for k, t in tokens["typography"].items():
            L.append(f"  {k}:")
            L += [f"    {pk}: {q(pv) if isinstance(pv, str) else pv}" for pk, pv in t.items()]
    if tokens["rounded"]:
        L.append("rounded:")
        L += [f"  {k}: {q(v)}" for k, v in tokens["rounded"].items()]
    if tokens["spacing"]:
        L.append("spacing:")
        L += [f"  {q(k)}: {q(v)}" for k, v in tokens["spacing"].items()]
    if tokens["components"]:
        L.append("components:")
        for k, props in tokens["components"].items():
            if not [pk for pk in props if pk != "borderColor"]:
                continue
            L.append(f"  {k}:")
            L += [f"    {pk}: {q(pv)}" for pk, pv in props.items() if pk != "borderColor"]
    L.append("---")
    return "\n".join(L)


def contrast_summary(schema):
    """Tightest AA ratio among text/background pairs meant to sit together:
    text/on-X on background/X (and X-hover); every other text role on the surface backgrounds."""
    P, S = schema["primitives"], schema["semantics"]
    modes = schema.get("modes") or ["Light"]
    surfaces = [n for n in ("background/default", "background/subtle", "background/raised") if n in S]
    pairs = []
    for name in S:
        if not name.startswith("text/"):
            continue
        role = name[len("text/"):]
        if role.startswith("on-"):
            base = "background/" + role[3:]
            pairs += [(name, bg) for bg in S if bg == base or bg.startswith(base + "-")]
        else:
            pairs += [(name, bg) for bg in surfaces]
    worst = None
    for m in modes:
        def hexof(n):
            a = S[n]["aliasOf"] if isinstance(S[n], dict) else S[n]
            return P[a[m] if isinstance(a, dict) else a]
        for fg, bg in pairs:
            r = check_contrast(hexof(fg), hexof(bg))
            if worst is None or r["ratio"] < worst[0]:
                worst = (r["ratio"], fg, bg, m, r["passes"])
    return worst


PROPOSED_NOTE = "<!-- proposed by Claude (from the reference screenshots / tokens), pending designer review -->"


def section(title, body, proposed=False):
    note = f"\n\n{PROPOSED_NOTE}" if proposed else ""
    return f"## {title}\n\n{body.strip()}{note}\n"


def todo(what):
    return f"TODO(interview): {what}"


def bullets(items):
    return "\n".join(f"- {i}" for i in items)


def css_block(tokens):
    def blk(sel, d):
        return sel + " {\n" + "\n".join(f"  --color-{k}: {v};" for k, v in d.items()) + "\n}"
    out = [blk(":root", tokens["colors"])]
    if tokens["colors-dark"]:
        out.append(blk('[data-theme="dark"]', tokens["colors-dark"]))
    return "```css\n" + "\n".join(out) + "\n```"


# Baseline rules written into every DESIGN.md. Added 2026-10-12 after the
# "three screens" test (a clean session building from DESIGN.md alone drifted in
# exactly these places). Generic on purpose: no hex/px values, so `check` stays quiet.
BASELINE_RULES = [
    "Never apply `opacity` (or a translucent colour) to text that sits on a coloured surface. "
    "Use the `on-*` text token for that surface; contrast is only guaranteed for the token pair.",
    "Large display text (mastheads, page titles) uses the default text token at a size from the typography scale. "
    "Do not set it in the primary/brand colour or at an off-scale size unless a typography+colour token pair says so.",
    "Every interactive component gets a defined hover state, or explicitly has none. "
    "If the component tokens list no `-hover` variant, do not invent one.",
    "Use only radius, spacing and layout values that are defined in this file. If a needed value is not defined, "
    "do not invent one: use the nearest defined value, or stop and ask the designer.",
]
BASELINE_DARK_RULE = (
    "Switch themes by setting `data-theme=\"dark\"` on the root element (a visible toggle), using the generated CSS variables. "
    "Do not rely on `prefers-color-scheme` alone, and never hard-code a second set of colours."
)


def build_body(tokens, schema, answers, dark_style="css"):
    prop = set(answers.get("proposed", []))
    blocks = ["# " + (answers.get("name") or schema.get("name") or "Design System") + "\n"]
    blocks.append(section("Overview", answers.get("overview") or todo(
        "2-3 sentences: what the product does, who uses it, what the UI must help them do.")))
    ci = answers.get("colorIntent") or {}
    col = []
    if ci:
        col.append(bullets(f"**{k}**: {v}" for k, v in ci.items()))
    else:
        col.append(todo("one line per key role (primary, CTA, error...): what it is for, and what it must never be used for."))
    if tokens["colors-dark"] and dark_style == "frontmatter":
        col.append("Dark-mode values are in `colors-dark` (same keys). Use the semantic keys, never raw hex.")
    elif tokens["colors-dark"]:
        col.append("Use the semantic keys, never raw hex. All roles in both modes (generated from the same tokens; keep in sync):\n\n" + css_block(tokens))
    w = contrast_summary(schema)
    if w:
        verdict = "every pair meant to sit together passes" if w[4] else "AT LEAST ONE PAIR FAILS"
        col.append(f"Contrast, WCAG AA: {verdict}; the tightest is "
                   f"{w[1].replace('text/', '')} on {w[2].replace('background/', '')} at {w[0]}:1 ({w[3]}).")
    blocks.append(section("Colors", "\n\n".join(col)))
    blocks.append(section("Typography", answers.get("typographyNotes") or todo(
        "which level for what situation, and what each level is never used for."), "typographyNotes" in prop))
    blocks.append(section("Layout", answers.get("layout") or todo(
        "grid / spacing strategy: base unit, container widths, how dense the UI is."), "layout" in prop))
    blocks.append(section("Elevation & Depth", answers.get("elevation") or todo(
        "how hierarchy is shown: shadows (spread, blur, color) or borders / surface contrast for a flat style."), "elevation" in prop))
    blocks.append(section("Shapes", answers.get("shapes") or todo(
        "corner-radius language: which radius for which element, when pill/full is allowed."), "shapes" in prop))
    notes = answers.get("componentNotes")
    borders = [f"`{k}` border: `{p['borderColor'][len('{colors.'):-1]}`" for k, p in tokens["components"].items() if "borderColor" in p]
    comp_body = []
    if notes:
        comp_body.append(bullets(notes))
    if borders:
        comp_body.append("Borders (not expressible as component properties in the spec):\n" + bullets(borders))
    blocks.append(section("Components", "\n\n".join(comp_body) if comp_body else todo(
        "decision logic: when to use which component, one primary action per view, required states (hover, focus-visible, disabled, error)."), "componentNotes" in prop and bool(notes)))
    dd = []
    for label, items, prefix in (("Do", answers.get("dos"), "Do"), ("Don't", answers.get("donts"), "Don't")):
        if items:
            dd.append(bullets(f"{prefix} {i}" for i in items))
    base = list(BASELINE_RULES)
    if tokens["colors-dark"]:
        base.append(BASELINE_DARK_RULE)
    base_block = "Baseline rules (apply to every project; added by the skill):\n" + bullets(base)
    blocks.append(section("Do's and Don'ts", ("\n".join(dd) if dd else todo(
        "imperative rules with a concrete referent (a token, a component, a count). 'Do use button-primary for one action per view'.")) + "\n\n" + base_block))
    lang = (answers.get("language") or "").lower()
    if lang.startswith(("he", "ar")):
        with open(LOCALIZATION_TEMPLATE, encoding="utf-8") as f:
            blocks.append(f.read().strip() + "\n")
    ex = answers.get("examples")
    if ex:
        lines = []
        for e in ex:
            lines.append(f"- **{e['label']}**: " + " / ".join(f"{k.upper()}: {v}" for k, v in e.items() if k != "label"))
        blocks.append(section("Examples", "Copy in the system's voice. Calibrate tone with these; do not paste verbatim.\n\n" + "\n".join(lines), "examples" in prop))
    blocks.append("<!-- Generated by the figma-design-tokens skill (design_md.py) from the approved schema. "
                  "Full 50-900 primitive scales are omitted on purpose; they live in the schema / Figma. -->\n")
    return "\n".join(blocks)


def cmd_export(a):
    schema = json.load(open(a.schema, encoding="utf-8"))
    answers = json.load(open(a.answers, encoding="utf-8")) if a.answers else {}
    tokens = build_tokens(schema, answers)
    md = frontmatter(tokens, schema, answers, a.dark_style) + "\n\n" + build_body(tokens, schema, answers, a.dark_style)
    out = a.output or "DESIGN.md"
    open(out, "w", encoding="utf-8").write(md)
    todos = md.count("TODO(interview)")
    print(f"wrote {out}: {len(tokens['colors'])} colors" +
          (f" (+{len(tokens['colors-dark'])} dark)" if tokens["colors-dark"] else "") +
          f", {len(tokens['typography'])} type levels, {len(tokens['spacing'])} spacing, "
          f"{len(tokens['rounded'])} rounded, {len(tokens['components'])} component variants; "
          f"~{len(md)//4} tokens")
    if todos:
        print(f"{todos} section(s) still need interview answers (TODO(interview) markers left in the file)")
    if "primary" not in tokens["colors"]:
        print("WARN: no `primary` color - the official linter warns (missing-primary). Map a brand role to background/brand.")
    if tokens["colors-dark"] and a.dark_style == "frontmatter":
        print("note: `colors-dark` is a catalog convention; the official linter reports it as token-like-ignored and export tools skip it. Default (--dark-style css) puts dark values in a CSS block instead.")


def split_doc(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit("ERROR: no YAML frontmatter found")
    return m.group(1), m.group(2)


def cmd_check(a):
    text = open(a.design_md, encoding="utf-8").read()
    schema = json.load(open(a.schema, encoding="utf-8"))
    answers = json.load(open(a.answers, encoding="utf-8")) if a.answers else {}
    fm, body = split_doc(text)
    tokens = build_tokens(schema, answers)
    errors, warns = [], []
    # references
    for grp, key in re.findall(r"\{([a-z-]+)\.([\w-]+)\}", text):
        if key not in tokens.get(grp, {}):
            errors.append(f"broken reference {{{grp}.{key}}}")
    # headings
    heads = re.findall(r"^## (.+)$", body, re.M)
    dups = {h for h in heads if heads.count(h) > 1}
    for h in dups:
        errors.append(f"duplicate section heading '{h}' (the spec rejects the file)")
    known = [h for h in heads if h in SECTIONS]
    if known != sorted(known, key=SECTIONS.index):
        warns.append("sections are not in the spec order: " + " > ".join(SECTIONS))
    # prose vs tokens drift
    all_hex = {h.lower() for d in (tokens["colors"], tokens["colors-dark"] or {}) for h in d.values()}
    prose = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    for h in set(re.findall(r"#[0-9a-fA-F]{6}\b", prose)):
        if h.lower() not in all_hex:
            warns.append(f"prose mentions {h}, which is not a token value (drift between prose and YAML?)")
    px_vals = set()
    for t in tokens["typography"].values():
        px_vals |= {t["fontSize"], t["lineHeight"]}
    px_vals |= set(tokens["rounded"].values()) | set(tokens["spacing"].values())
    for n in set(re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:px|-pixel)\b", prose)):
        if f"{n}px" not in px_vals:
            warns.append(f"prose mentions {n}px, which is not a token value (drift between prose and YAML?)")
    m = re.search(r"```css\n(.*?)\n```", body, re.S)
    if m:
        light_css, _, dark_css = m.group(1).partition('[data-theme="dark"]')
        get = lambda t: dict(re.findall(r"--color-([\w-]+):\s*(#[0-9a-fA-F]{6})", t))
        for label, css, want in (("light", light_css, tokens["colors"]), ("dark", dark_css, tokens["colors-dark"] or {})):
            got = get(css)
            for k, v in want.items():
                if got.get(k, "").lower() != v.lower():
                    errors.append(f"CSS block ({label}) --color-{k} is {got.get(k)!r}, tokens say {v!r}")
            for k in got:
                if k not in want:
                    errors.append(f"CSS block ({label}) defines --color-{k}, which is not a token")
    todos = text.count("TODO(interview)")
    if todos:
        warns.append(f"{todos} TODO(interview) marker(s) left - sections not yet filled from the interview")
    if len(text) // 4 > 7000:
        warns.append(f"~{len(text)//4} tokens: longer than the ~7,000 community median; trim")
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"{len(errors)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errors else 0)


CSS_HEADER = ("/* GENERATED from the token schema by design_md.py export-css. Do not edit by hand:\n"
              "   change the schema and re-export. `export-css --check` fails when this file drifts.\n"
              "   tokens_lint.py reads this file as the allowed set of values. */\n")


def css_file(tokens):
    """Standalone tokens.css the app imports: one source for code, Figma and DESIGN.md."""
    root = [f"  --color-{k}: {v};" for k, v in tokens["colors"].items()]
    for k, t in tokens["typography"].items():
        root.append(f"  --type-{k}-family: {t['fontFamily']};")
        root.append(f"  --type-{k}-size: {t['fontSize']};")
        root.append(f"  --type-{k}-weight: {t['fontWeight']};")
        root.append(f"  --type-{k}-line-height: {t['lineHeight']};")
        if "letterSpacing" in t:
            root.append(f"  --type-{k}-letter-spacing: {t['letterSpacing']};")
    root += [f"  --space-{k}: {v};" for k, v in tokens["spacing"].items()]
    root += [f"  --radius-{k}: {v};" for k, v in tokens["rounded"].items()]
    out = CSS_HEADER + ":root {\n" + "\n".join(root) + "\n}\n"
    if tokens["colors-dark"]:
        out += '\n[data-theme="dark"] {\n' + "\n".join(
            f"  --color-{k}: {v};" for k, v in tokens["colors-dark"].items()) + "\n}\n"
    return out


def cmd_export_css(a):
    schema = json.load(open(a.schema, encoding="utf-8"))
    css = css_file(build_tokens(schema, {}))
    if a.check:
        cur = open(a.output, encoding="utf-8").read() if os.path.exists(a.output) else None
        if cur != css:
            print(f"DRIFT: {a.output} {'is missing' if cur is None else 'differs from the schema'}; re-run export-css")
            sys.exit(1)
        print(f"OK: {a.output} matches the schema")
        return
    open(a.output, "w", encoding="utf-8").write(css)
    print(f"wrote {a.output}: {css.count('--')} custom properties")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("schema")
    e.add_argument("--answers")
    e.add_argument("-o", "--output")
    e.add_argument("--dark-style", choices=["css", "frontmatter"], default="css",
                   help="css (default): dark values as a generated CSS block in the body; frontmatter: non-spec `colors-dark` map")
    c = sub.add_parser("check")
    c.add_argument("design_md")
    c.add_argument("--schema", required=True)
    c.add_argument("--answers")
    x = sub.add_parser("export-css")
    x.add_argument("schema")
    x.add_argument("-o", "--output", required=True)
    x.add_argument("--check", action="store_true", help="exit 1 if the file differs from what the schema generates")
    a = p.parse_args()
    {"export": cmd_export, "check": cmd_check, "export-css": cmd_export_css}[a.cmd](a)


if __name__ == "__main__":
    main()
