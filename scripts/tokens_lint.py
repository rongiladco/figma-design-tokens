#!/usr/bin/env python3
"""
tokens_lint.py: fail the build when app source hard-codes a value that belongs to a token.

  tokens_lint.py <app-root> [--config tokens-lint.json] [--write-baseline] [--max 30] [--lengths-all]

Why: a rules file (DESIGN.md, CLAUDE.md) is an instruction, and nothing fails when it is ignored.
This turns the rule into a check with an exit code. The allowed set is read from the token CSS
itself (a hand-written tokens.css, or the one `design_md.py export-css` generates), so the rule and
the check cannot drift apart.

Rules
  color    any hex / rgb() / hsl() / oklch() literal outside the token files. Message names the
           token that already holds that exact value, if there is one.
  length   (CSS only) a px/rem literal that equals a spacing/radius/size token's value, e.g. 16px
           when --space-4 is 16px. Other lengths (1px borders, one-off sizes) are NOT reported
           unless --lengths-all is given.

Config (JSON, default <app-root>/tokens-lint.json; paths relative to the app root)
  {
    "tokens":   ["src/styles/tokens.css"],         # required: the source of truth
    "src":      ["src"],                           # dirs/files to scan (default ["src"])
    "ignore":   ["src/styles/mock.css"],           # files exempt on purpose (say why in the README)
    "baseline": "product/tokens-lint.baseline.json"# optional: ratchet for code that already has violations
  }

Adopting on existing code: run with --write-baseline once. From then on only violations ABOVE the
baseline fail, so debt can shrink but not grow. Re-run --write-baseline after paying some down.

Escape hatches (use sparingly, explain in a comment): `tokens-lint-ignore` on the line,
or `tokens-lint-ignore-file` in the first 5 lines of a file.

Exit: 0 clean, 1 new violations, 2 config/usage error. Stdlib only.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

EXTS = {".css", ".scss", ".ts", ".tsx", ".js", ".jsx", ".html", ".vue", ".svelte"}
SKIP_DIRS = {"node_modules", "dist", "build", ".git", "out", ".next", "coverage"}

COLOR_RE = re.compile(
    r"(?:(?<=[\s'\"`:(,])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b)"
    r"|(?:\b(?:rgba?|hsla?|hwb|oklch|oklab|lab|lch)\()")
LEN_RE = re.compile(r"(?<![\w.#-])(\d*\.?\d+)(px|rem)\b")
TOKEN_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}]+)[;}]")
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b")
SIZE_TOKEN = re.compile(r"^--(?:space|radius|text|size|gutter|tap|content|page|gap|rounded|spacing)")


def norm_hex(h):
    h = h.lower()
    if len(h) == 4:
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def norm_len(num, unit):
    return f"{float(num):g}{unit}"


def strip_comments(text, css_like):
    """Blank out comments but keep newlines so line numbers stay right."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"/\*.*?\*/", blank, text, flags=re.S)
    if not css_like:
        text = re.sub(r"(?<![:\w\"'`])//[^\n]*", blank, text)
    return text


def load_tokens(root, files):
    colors, lengths = {}, {}
    for f in files:
        path = os.path.join(root, f)
        if not os.path.isfile(path):
            print(f"ERROR: token file not found: {f}")
            sys.exit(2)
        text = strip_comments(open(path, encoding="utf-8").read(), True)
        for name, val in TOKEN_RE.findall(text):
            val = val.strip()
            for h in HEX_RE.findall(val):
                if re.fullmatch(HEX_RE, val):
                    colors.setdefault(norm_hex(h), []).append(name)
            m = re.fullmatch(r"(\d*\.?\d+)(px|rem)", val)
            if m and SIZE_TOKEN.match(name):
                lengths.setdefault(norm_len(*m.groups()), []).append(name)
    return colors, lengths


def walk(root, targets):
    for t in targets:
        p = os.path.join(root, t)
        if os.path.isfile(p):
            yield p
            continue
        for d, dirs, files in os.walk(p):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for fn in sorted(files):
                if os.path.splitext(fn)[1] in EXTS:
                    yield os.path.join(d, fn)


def scan_file(path, rel, colors, lengths, lengths_all):
    raw = open(path, encoding="utf-8", errors="replace").read()
    if "tokens-lint-ignore-file" in "\n".join(raw.splitlines()[:5]):
        return []
    css_like = path.endswith((".css", ".scss"))
    clean = strip_comments(raw, css_like)
    out = []
    for i, (line, orig) in enumerate(zip(clean.splitlines(), raw.splitlines()), 1):
        if "tokens-lint-ignore" in orig:
            continue
        for m in COLOR_RE.finditer(line):
            v = m.group(0)
            if v.startswith("#"):
                names = colors.get(norm_hex(v))
                hint = f"use var({names[0]})" if names else "no token holds this value: add one or use the nearest"
                out.append((rel, i, "color", norm_hex(v), hint))
            else:
                out.append((rel, i, "color", v + "…)", "use a colour token (build translucent colours from a token)"))
        if css_like and not re.search(r"@(media|container|supports)", line) and not re.match(r"\s*--[\w-]+\s*:", line):
            for num, unit in LEN_RE.findall(line):
                v = norm_len(num, unit)
                names = lengths.get(v)
                if names:
                    out.append((rel, i, "length", v, f"use var({names[0]})" + (f" (or {names[1]})" if len(names) > 1 else "")))
                elif lengths_all and v not in ("0px", "1px", "2px"):
                    out.append((rel, i, "length", v, "no token holds this value"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--config")
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--max", type=int, default=30, help="max violation lines printed (default 30)")
    ap.add_argument("--lengths-all", action="store_true", help="also report px/rem values that no token holds")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    cfg_path = a.config or os.path.join(root, "tokens-lint.json")
    if not os.path.isfile(cfg_path):
        print(f"ERROR: no config at {cfg_path} (needs at least {{\"tokens\": [\"path/to/tokens.css\"]}})")
        sys.exit(2)
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    if not cfg.get("tokens"):
        print("ERROR: config needs a non-empty \"tokens\" list")
        sys.exit(2)
    colors, lengths = load_tokens(root, cfg["tokens"])
    token_abs = {os.path.abspath(os.path.join(root, t)) for t in cfg["tokens"]}
    ignore_abs = {os.path.abspath(os.path.join(root, t)) for t in cfg.get("ignore", [])}

    found = []
    for path in walk(root, cfg.get("src", ["src"])):
        ap_ = os.path.abspath(path)
        if ap_ in token_abs or ap_ in ignore_abs:
            continue
        found += scan_file(path, os.path.relpath(path, root), colors, lengths, a.lengths_all)

    counts = Counter((f, r, v) for f, _, r, v, _ in found)
    bl_path = os.path.join(root, cfg["baseline"]) if cfg.get("baseline") else None
    if a.write_baseline:
        if not bl_path:
            print('ERROR: set "baseline" in the config to use --write-baseline')
            sys.exit(2)
        os.makedirs(os.path.dirname(bl_path), exist_ok=True)
        json.dump({f"{f}|{r}|{v}": n for (f, r, v), n in sorted(counts.items())},
                  open(bl_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"baseline written: {sum(counts.values())} violations in {len({k[0] for k in counts})} files -> {cfg['baseline']}")
        return

    base = json.load(open(bl_path, encoding="utf-8")) if bl_path and os.path.isfile(bl_path) else {}
    over = {k for k, n in counts.items() if n > base.get(f"{k[0]}|{k[1]}|{k[2]}", 0)}
    new = [x for x in found if (x[0], x[2], x[3]) in over]
    baselined = sum(counts.values()) - len(new)
    stale = sum(1 for k, n in base.items() if tuple(k.split("|", 2)) not in counts)

    for f, ln, rule, val, hint in new[:a.max]:
        print(f"{f}:{ln}  {rule}  {val}  -> {hint}")
    if len(new) > a.max:
        print(f"... and {len(new) - a.max} more (raise --max)")
    tail = f" ({baselined} baselined" + (f", {stale} baseline entries now fixed: re-run --write-baseline to ratchet" if stale else "") + ")" if (baselined or stale) else ""
    if new:
        print(f"TOKENS LINT FAILED: {len(new)} new hard-coded value(s){tail}")
        sys.exit(1)
    print(f"TOKENS CLEAN{tail}")


if __name__ == "__main__":
    main()
