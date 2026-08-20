#!/usr/bin/env python3
"""
Color tools for the figma-design-tokens skill.

Two subcommands:
  generate-scale --base <hex> [--name <hue-name>]
      Derive a 50-900 tint/shade scale from one base color. Works in OKLCH
      (Bjorn Ottosson's perceptually-uniform space, same one Tailwind's own
      palettes are built in) rather than HSL, because HSL lightness isn't
      perceptually uniform across hues - "L=50%" yellow reads much lighter
      to the eye than "L=50%" blue, which makes an HSL-derived scale look
      subtly wrong in ways that are hard to put a finger on. Out-of-gamut
      results are fixed by reducing chroma at fixed lightness/hue (a CSS
      Color 4 style gamut map), not by clamping R/G/B independently, which
      would shift the hue instead of just desaturating it.
      Also prints WCAG contrast against pure white/black per step - quick
      reference only, not a substitute for checking the actual paired
      background a semantic alias will sit on (use check-contrast for that).

  check-contrast --fg <hex> --bg <hex> [--level AA|AAA] [--size normal|large]
      WCAG contrast ratio between two colors, pass/fail against a target.
      For non-text UI elements (borders, icons, focus rings - WCAG 1.4.11),
      use --size large: its 3:1 threshold is the same number 1.4.11 uses.

Stdlib only - no dependencies to install.
"""
import argparse
import json
import math
import sys

STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]

# Target OKLCH lightness per step (0-1), light to dark.
LIGHTNESS_CURVE = {
    50: 0.97, 100: 0.94, 200: 0.87, 300: 0.78, 400: 0.68,
    500: 0.58, 600: 0.48, 700: 0.38, 800: 0.29, 900: 0.21,
}

# Chroma multiplier per step, relative to the base color's own chroma -
# pulled back at the extremes so very light/dark steps don't come out
# neon or muddy (the same instinct as the old HSL saturation curve, just
# applied to a perceptually meaningful chroma value instead).
CHROMA_CURVE = {
    50: 0.35, 100: 0.45, 200: 0.65, 300: 0.82, 400: 0.94,
    500: 1.00, 600: 0.96, 700: 0.88, 800: 0.78, 900: 0.66,
}

LEVEL_THRESHOLDS = {
    ("AA", "normal"): 4.5,
    ("AA", "large"): 3.0,
    ("AAA", "normal"): 7.0,
    ("AAA", "large"): 4.5,
}


# ---------- hex <-> sRGB ----------

def hex_to_rgb(hex_color):
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"'{hex_color}' isn't a valid hex color")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


# ---------- WCAG relative luminance (kept separate from the OKLCH path -
# the WCAG formula's own spec text uses a 0.03928 linearization threshold,
# slightly different from the "true" sRGB EOTF threshold used below, and
# contrast-ratio math needs to match the spec exactly, not the physically
# precise transfer function ----------

def relative_luminance(rgb):
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a, hex_b):
    la = relative_luminance(hex_to_rgb(hex_a))
    lb = relative_luminance(hex_to_rgb(hex_b))
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


# ---------- sRGB <-> linear sRGB (true EOTF, for the OKLCH round-trip) ----------

def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = max(0.0, c)
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


# ---------- linear sRGB <-> OKLab (Bjorn Ottosson's matrices) ----------

def linear_rgb_to_oklab(r, g, b):
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (max(v, 0.0) ** (1 / 3) if v >= 0 else -((-v) ** (1 / 3)) for v in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, a, b2


def oklab_to_linear_rgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b2 = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return r, g, b2


def hex_to_oklch(hex_color):
    r, g, b = (srgb_to_linear(c / 255.0) for c in hex_to_rgb(hex_color))
    L, a, b2 = linear_rgb_to_oklab(r, g, b)
    C = math.hypot(a, b2)
    H = math.degrees(math.atan2(b2, a)) % 360
    return L, C, H


def _oklch_to_srgb_raw(L, C, H):
    hrad = math.radians(H)
    a, b = C * math.cos(hrad), C * math.sin(hrad)
    r, g, b2 = oklab_to_linear_rgb(L, a, b)
    return linear_to_srgb(r), linear_to_srgb(g), linear_to_srgb(b2)


def _in_gamut(rgb, eps=1e-4):
    return all(-eps <= c <= 1 + eps for c in rgb)


def oklch_to_hex(L, C, H):
    """OKLCH -> sRGB hex, gamut-mapped by reducing chroma at fixed L/H
    (binary search) rather than clamping each channel independently -
    clamping independently shifts the hue, chroma reduction doesn't."""
    rgb = _oklch_to_srgb_raw(L, C, H)
    if _in_gamut(rgb):
        return rgb_to_hex(tuple(c * 255 for c in rgb))

    lo, hi = 0.0, C
    for _ in range(24):  # plenty for float precision at 8-bit output
        mid = (lo + hi) / 2
        rgb = _oklch_to_srgb_raw(L, mid, H)
        if _in_gamut(rgb):
            lo = mid
        else:
            hi = mid
    rgb = _oklch_to_srgb_raw(L, lo, H)
    # final safety clamp for float noise right at the boundary
    rgb = tuple(min(1.0, max(0.0, c)) for c in rgb)
    return rgb_to_hex(tuple(c * 255 for c in rgb))


# ---------- scale generation ----------

def generate_scale(base_hex):
    _, base_c, base_h = hex_to_oklch(base_hex)
    scale = {}
    for step in STEPS:
        target_l = LIGHTNESS_CURVE[step]
        target_c = base_c * CHROMA_CURVE[step]
        hex_val = oklch_to_hex(target_l, target_c, base_h)
        scale[step] = {
            "hex": hex_val,
            "contrast_on_white": round(contrast_ratio(hex_val, "#ffffff"), 2),
            "contrast_on_black": round(contrast_ratio(hex_val, "#000000"), 2),
        }
    return scale


def check_contrast(fg_hex, bg_hex, level="AA", size="normal"):
    ratio = contrast_ratio(fg_hex, bg_hex)
    threshold = LEVEL_THRESHOLDS[(level.upper(), size.lower())]
    return {
        "foreground": fg_hex,
        "background": bg_hex,
        "ratio": round(ratio, 2),
        "level": level.upper(),
        "size": size.lower(),
        "threshold": threshold,
        "passes": ratio >= threshold,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_scale = sub.add_parser("generate-scale", help="Derive a 50-900 scale from one base hex color")
    p_scale.add_argument("--base", required=True, help="Base hex color, e.g. #3b82f6")
    p_scale.add_argument("--name", default=None, help="Hue name for labeling output keys, e.g. blue")

    p_contrast = sub.add_parser("check-contrast", help="WCAG contrast ratio between two hex colors")
    p_contrast.add_argument("--fg", required=True, help="Foreground (text) hex color")
    p_contrast.add_argument("--bg", required=True, help="Background hex color")
    p_contrast.add_argument("--level", default="AA", choices=["AA", "AAA"])
    p_contrast.add_argument("--size", default="normal", choices=["normal", "large"], help="'large' = 18pt+/14pt+bold, or non-text UI per WCAG 1.4.11")

    args = parser.parse_args()

    if args.command == "generate-scale":
        scale = generate_scale(args.base)
        name = args.name or "color"
        out = {f"{name}/{step}": data for step, data in scale.items()}
        print(json.dumps(out, indent=2))
    elif args.command == "check-contrast":
        result = check_contrast(args.fg, args.bg, args.level, args.size)
        print(json.dumps(result, indent=2))
        if not result["passes"]:
            sys.exit(1)


if __name__ == "__main__":
    main()
