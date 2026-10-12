#!/usr/bin/env python3
"""
Build the HTML preview (SKILL.md section 4) from the approved schema.

  build_preview.py <schema.json> -o preview.html [--title "..."] [--lang he|en]

Fills assets/preview-template.html: primitive swatches, semantic swatches
(they follow the fixed Light/Dark toggle; both modes are listed in the text),
type specimens, component tokens rendered as realistic examples with the
tokens each one uses, spacing/radius, and the full token table. Stdlib only.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from design_md import build_tokens, name_map, WEIGHTS  # noqa: E402

TEMPLATE = os.path.join(HERE, "..", "assets", "preview-template.html")
SAMPLES = {
    "he": {"heading": "השוואת מחירים חכמה", "button": "לקבלת הצעה", "body": "משווים מחירים במקום אחד, כדי שתשלמו פחות.",
           "caption": "המחירים כוללים מע״מ", "label": "קטגוריה", "cta": "לקבלת הצעה", "input": "אימייל",
           "title": "כותרת ראשית בולטת לידיעה", "text": "שורת תיאור קצרה שמסבירה במה עוסקת הכתבה.", "byline": "שם הכתב · לפני 12 דקות",
           "badge": "שידור ישיר", "more": "עוד", "tag": ["כלכלה", "טכנולוגיה", "בריאות"], "nav": ["ראשי", "חדשות", "כלכלה", "ספורט", "תרבות"],
           "alert": "מבזק: עדכון חשוב שנוסף זה עתה", "section": "כתבות נוספות", "kicker": "חדשות", "link": "לכתבה המלאה"},
    "en": {"heading": "Design is how it works", "button": "Get a quote", "body": "The quick brown fox jumps over the lazy dog, then reads the spec.",
           "caption": "Prices include VAT", "label": "CATEGORY", "cta": "Get a quote", "input": "Email",
           "title": "A strong headline for the story", "text": "A short description line that explains what the article is about.", "byline": "Reporter name · 12 min ago",
           "badge": "LIVE", "more": "More", "tag": ["Economy", "Tech", "Health"], "nav": ["Home", "News", "Economy", "Sport", "Culture"],
           "alert": "Breaking: an important update just came in", "section": "More stories", "kicker": "News", "link": "Read the full story"},
}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;")


def swatch(name, hexv):
    return (f'<div class="swatch"><div class="swatch-color" style="background:{hexv}"></div><div class="swatch-label">'
            f'<div class="swatch-name">{name}</div><div class="swatch-hex">{hexv}</div></div></div>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("schema")
    ap.add_argument("-o", "--output", default="preview.html")
    ap.add_argument("--title", default="Token system preview")
    ap.add_argument("--lang", default="en", choices=["he", "en"])
    a = ap.parse_args()
    schema = json.load(open(a.schema, encoding="utf-8"))
    P, S = schema["primitives"], schema["semantics"]
    C, D, TS = schema.get("components", {}), schema.get("dimensions", {}), schema.get("textStyles", {})
    modes = schema.get("modes") or ["Light"]
    tokens = build_tokens(schema, {})
    nm = name_map(schema)
    smp = SAMPLES[a.lang]
    rtl = ' dir="rtl"' if a.lang == "he" else ""
    h = open(TEMPLATE, encoding="utf-8").read()

    # primitives
    groups = {}
    for k, v in P.items():
        groups.setdefault(k.split("/")[0], []).append((k, v))
    prim = "".join(f"<h3>{g}</h3><div class=\"swatch-grid\">" + "".join(swatch(k, v) for k, v in it) + "</div>" for g, it in groups.items())

    # semantic swatches: the colour follows the fixed Light/Dark toggle; both modes are listed in the text
    def alias(d, m):
        x = d["aliasOf"] if isinstance(d, dict) else d
        return x[m] if isinstance(x, dict) else x
    sem = '<div class="swatch-grid">'
    for k, d in S.items():
        l, dk = alias(d, modes[0]), alias(d, modes[-1])
        sem += (f'<div class="swatch"><div class="swatch-color" style="background:var(--c-{nm[k]})"></div>'
                f'<div class="swatch-label"><div class="swatch-name">{k}</div>'
                f'<div class="swatch-hex">{modes[0][0]} {l} · {P[l]}<br>{modes[-1][0]} {dk} · {P[dk]}</div></div></div>')
    sem += "</div>"

    # type specimens
    typ = ""
    for k, t in TS.items():
        sample = smp.get(k.split("/")[0], smp["body"])
        w = WEIGHTS.get(t["style"], 400)
        typ += (f'<div class="type-specimen"><div class="type-specimen-sample"{rtl} style="font-family:\'{t["family"]}\',sans-serif;'
                f'font-size:{t["size"]}px;line-height:{t["lineHeight"]}px;font-weight:{w};letter-spacing:{t.get("letterSpacing", 0)}em">{sample}</div>'
                f'<div class="type-specimen-meta">{k}<br>{t["family"]} {t["style"]} · {t["size"]}/{t["lineHeight"]}</div></div>')

    # component gallery: each variant rendered as a realistic example, followed by the tokens it uses
    font_of = lambda prefix: next((t for k, t in TS.items() if k.startswith(prefix)), None)
    def tstyle(prefix, extra=""):
        t = font_of(prefix)
        if not t:
            return extra
        return (f"font-family:'{t['family']}',sans-serif;font-size:{t['size']}px;line-height:{t['lineHeight']}px;"
                f"font-weight:{WEIGHTS.get(t['style'], 400)};") + extra
    ref = lambda r: "var(--c-" + re.match(r"\{colors\.([\w-]+)\}", r).group(1) + ")"
    dflt_fg = "var(--c-on-surface)" if "on-surface" in tokens["colors"] else "inherit"
    dflt_bg = "var(--c-surface)" if "surface" in tokens["colors"] else "transparent"

    def example(key, comp, props):
        bg, fg, bd = props.get("backgroundColor"), props.get("textColor"), props.get("borderColor")
        fill = f"background:{ref(bg)};" if bg else ""
        ink = f"color:{ref(fg)};" if fg else f"color:{dflt_fg};"
        base = comp.lower()
        if base in ("pill", "button", "btn", "cta") or base.endswith("button"):
            rad = "999px" if base == "pill" else "6px"
            return f'<button type="button" style="{fill}{ink}border:0;border-radius:{rad};padding:8px 20px;cursor:pointer;{tstyle("button", "font-weight:700;")}">{smp["more"] if base == "pill" else smp["cta"]}</button>'
        if base == "badge":
            return f'<span style="{fill}{ink}display:inline-block;padding:4px 14px;{tstyle("label", "font-weight:700;")}">{smp["badge"]}</span>'
        if base in ("news-card", "card", "tile"):
            br = f"border:1px solid {ref(bd)};" if bd else ""
            return (f'<div style="{fill}{ink}{br}display:flex;gap:12px;align-items:stretch;min-height:96px;max-width:360px">'
                    f'<div style="flex:1;padding:12px 14px"><div style="{tstyle("heading/md", "font-weight:700;")}font-size:18px;line-height:24px">{smp["title"]}</div>'
                    f'<div style="{tstyle("body/sm")}margin-top:4px">{smp["text"]}</div>'
                    f'<div style="{tstyle("caption")}margin-top:6px;opacity:.85">{smp["byline"]}</div></div>'
                    f'<div style="width:96px;background:rgba(128,128,128,.35);flex:none"></div></div>')
        if base in ("section-header", "header", "section"):
            return f'<div style="{fill}{ink}padding:8px 14px;min-width:260px;{tstyle("heading/sm", "font-weight:700;")}">{smp["section"]}</div>'
        if base in ("tag", "chip"):
            return "".join(f'<span style="{fill}{ink}display:inline-block;padding:3px 10px;border-radius:4px;margin-inline-end:6px;{tstyle("caption")}">{t}</span>' for t in smp["tag"])
        if base in ("breaking-item", "alert", "notice"):
            return f'<div style="{fill}{ink}padding:10px 14px;border-radius:12px;min-width:260px;{tstyle("body/sm", "font-weight:600;")}">{smp["alert"]}</div>'
        if base in ("kicker", "eyebrow"):
            return f'<span style="{ink}{tstyle("caption", "font-weight:700;")}">{smp["kicker"]}</span>'
        if base == "link":
            return f'<a href="#" onclick="return false" style="{ink}text-decoration:underline;{tstyle("body/md")}">{smp["link"]}</a>'
        if base == "nav":
            color = ref(bd) if bd else "currentColor"
            return (f'<nav style="display:flex;gap:20px;padding:0 4px 8px;border-bottom:2px solid {color};{tstyle("label")}">' +
                    "".join(f"<span>{n}</span>" for n in smp["nav"]) + "</nav>")
        if base == "input":
            br = f"border:2px solid {ref(bd)};" if bd else "border:2px solid transparent;"
            return f'<input placeholder="{smp["input"]}" style="{fill or "background:" + dflt_bg + ";"}{ink}{br}border-radius:6px;padding:8px 12px;min-width:220px;font:inherit">'
        br = f"border:2px solid {ref(bd)};" if bd else ""
        return f'<div style="{fill}{ink}{br}padding:12px 16px;min-width:200px">{key}</div>'

    comp = ""
    if tokens["components"]:
        comp += ('<style>.cmp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}'
                 '.cmp-cell{border:1px solid var(--card-border);border-radius:10px;overflow:hidden;background:var(--card-bg)}'
                 f'.cmp-stage{{padding:20px;background:{dflt_bg};color:{dflt_fg};min-height:96px;display:flex;align-items:center;flex-wrap:wrap}}'
                 '.cmp-meta{padding:10px 14px;font-size:12px;border-top:1px solid var(--card-border);font-family:ui-monospace,monospace}'
                 '.cmp-meta b{display:block;margin-bottom:4px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:13px}'
                 '.cmp-meta span{color:var(--muted-fg);display:block}</style>')
        comp += "<p style=\"color:var(--muted-fg);font-size:13px\">Each variant rendered with its component tokens (follows the Light/Dark toggle). Shapes in these examples are illustrative: radius is not a token unless spacing/radius was approved.</p>"
        comp += f'<div class="cmp-grid"{rtl}>'
        for key, props in tokens["components"].items():
            cname, variant = tokens["component_meta"][key]
            caption = "".join(f"<span>{pk} → {pv}</span>" for pk, pv in props.items())
            comp += f'<div class="cmp-cell"><div class="cmp-stage">{example(key, cname, props)}</div><div class="cmp-meta"><b>{key}</b>{caption}</div></div>'
        comp += "</div>"

    # dimensions
    dim = ""
    sp = {k: v for k, v in D.items() if k.startswith("space/")}
    rd = {k: v for k, v in D.items() if k.startswith("radius/")}
    if sp:
        dim += '<div style="display:flex;flex-wrap:wrap;gap:24px;align-items:flex-end;margin-bottom:24px">' + "".join(
            f'<div style="text-align:center;font-size:12px;font-family:ui-monospace,monospace"><div style="width:{v}px;height:{v}px;background:var(--page-fg);opacity:.8;margin:0 auto 6px"></div>{k.split("/")[1]}<br>{v}px</div>' for k, v in sp.items()) + "</div>"
    if rd:
        dim += '<div style="display:flex;flex-wrap:wrap;gap:24px">' + "".join(
            f'<div style="text-align:center;font-size:12px;font-family:ui-monospace,monospace"><div style="width:72px;height:72px;border:2px solid var(--page-fg);border-radius:{v}px;margin:0 auto 6px"></div>{k.split("/")[1]}<br>{v}px</div>' for k, v in rd.items()) + "</div>"

    # CSS variables per mode (drive semantic swatches + component examples through the Light/Dark toggle)
    def varblock(mode_vals):
        return ";".join(f"--c-{k}:{v}" for k, v in mode_vals.items())
    css = f":root{{{varblock(tokens['colors'])}}}"
    if tokens["colors-dark"]:
        css += f'[data-theme="dark"]{{{varblock(tokens["colors-dark"])}}}'
    token_vars = f"<style>{css}</style>"

    # full table
    rows = []
    for k, v in P.items():
        rows.append((k, f'<span class="swatch-chip" style="background:{v}"></span>{v}', "primitive"))
    for k, d in S.items():
        l, dk = alias(d, modes[0]), alias(d, modes[-1])
        rows.append((k, f'<span class="swatch-chip" style="background:{P[l]}"></span>{l} / <span class="swatch-chip" style="background:{P[dk]}"></span>{dk}', f"semantic · {modes[0]} / {modes[-1]}"))
    for k, v in C.items():
        rows.append((k, v, "component → semantic"))
    for k, v in D.items():
        rows.append((k, f"{v}px", "dimension (FLOAT)"))
    for k, t in TS.items():
        rows.append((k, f'{t["family"]} {t["style"]} {t["size"]}/{t["lineHeight"]}', "text style"))
    tr = "".join(f'<tr><td class="token-name">{esc(a_)}</td><td class="token-value">{b}</td><td>{c}</td></tr>' for a_, b, c in rows)

    fams = sorted({t["family"] for t in TS.values()})
    link = "".join(f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={f.replace(" ", "+")}:wght@300;400;500;600;700;800;900&display=swap">' for f in fams)
    h = h.replace("<!--TITLE-->", esc(a.title)).replace("<!--GOOGLE_FONT_LINK-->", link)
    for token, val in (("<!--COLOR_PRIMITIVES-->", prim), ("<!--SEMANTIC_COLORS-->", sem), ("<!--TYPE_SPECIMENS-->", typ),
                       ("<!--COMPONENT_TOKENS-->", comp), ("<!--DIMENSIONS-->", dim), ("<!--TOKEN_VARS-->", token_vars), ("<!--TOKEN_TABLE_ROWS-->", tr)):
        h = h.replace(token, val)
    h = re.sub(r"<!-- OPTIONAL:.*?-->\n?", "", h, flags=re.S)
    open(a.output, "w", encoding="utf-8").write(h)
    print(f"wrote {a.output}: {len(P)} primitives, {len(S)} semantics, {len(tokens['components'])} component variants, {len(TS)} text styles")


if __name__ == "__main__":
    main()
