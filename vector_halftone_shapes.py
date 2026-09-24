#!/usr/bin/env python3
"""
vector_halftone.py

Converts an image into a true vector (SVG) grayscale halftone dot screen -
no perspective involved. For the perspective-aware version that places dots
directly into a photographed vanishing-point view, see
vector_halftone_perspective.py.

Usage:
    python vector_halftone.py <image> [options]

Required:
    image                   Source image to convert (any format OpenCV can read:
                            jpg, png, webp, etc.)

Grid / tone options:
    --spacing N             Grid spacing in pixels - the dot pitch. Smaller = finer
                            screen, more dots. (default: 20)
    --angle N               Screen angle in degrees, applied to the whole grid.
                            (default: 15)
    --invert                Flip the tone mapping: light areas get bigger dots
                            instead of dark areas. Off by default.
    --output-black N        Photoshop "Output Levels" black point, 0-255. Raises
                            the floor so the smallest dots never shrink to nothing.
                            (default: 0)
    --output-white N        Photoshop "Output Levels" white point, 0-255. Lowers
                            the ceiling so the largest dots never fully merge.
                            (default: 255)
    --radius-scale N        Flat multiplier on every dot's computed radius, for
                            taste - e.g. 1.2 to make everything 20% bigger.
                            (default: 1.0)
    --min-radius N          Dots smaller than this (in pixels) are skipped
                            entirely rather than drawn as a tiny speck.
                            (default: 0.15)
    --blur N                Radius (px) used to area-average the source image's
                            luminance before sampling each dot - this is what
                            keeps fine detail from aliasing/moire-ing against the
                            grid. Defaults to match --spacing; raise it for a
                            softer/smoothed tone map, lower it to track sharp
                            edges more closely.

Appearance:
    --color C               Dot fill color - any CSS color name or hex code, e.g.
                            "black", "#1a1a1a". (default: black)
    --background C          Background fill color, or "none" for a transparent
                            canvas instead of a solid rect. (default: white)

Shape (all built-in shapes are area-matched to the equivalent circle, so
switching shapes doesn't change the overall tonal balance):
    --shape S               circle | square | diamond | star | custom
                            (default: circle)
    --shape-rotation N      Rotation (degrees) applied to each individual shape.
                            Defaults to whatever --angle is. Has no visible effect
                            on --shape circle.
    --star-points N         Number of points, for --shape star. (default: 5)
    --star-inner-ratio N    Inner radius as a fraction of outer radius, for
                            --shape star - lower = spikier points. (default: 0.5)
    --shape-svg FILE        Path to a custom SVG file to use as the dot shape.
                            Required when --shape custom is set.
    --shape-svg-scale N     Size multiplier for --shape custom. Custom shapes are
                            NOT area-matched automatically (arbitrary geometry's
                            area isn't computed), so use this to calibrate how big
                            they look relative to the other shapes. (default: 1.0)

Output:
    --output FILE           Output SVG path. If omitted, a name is generated from
                            the input filename and the settings used, e.g.
                            "photo_halftone s20 a15 ob 0 ow 255.svg".

Examples:
    # Basic screen: 20px spacing, 15 degree angle, circles
    python vector_halftone.py photo.jpg --spacing 20 --angle 15

    # Finer screen, steeper angle, squares instead of circles
    python vector_halftone.py photo.jpg --spacing 12 --angle 45 --shape square

    # Diamonds, inverted (light areas get the big dots)
    python vector_halftone.py photo.jpg --spacing 18 --angle 15 --shape diamond --invert

    # 6-pointed stars with spiky points, no rotation on the grid
    python vector_halftone.py photo.jpg --spacing 24 --angle 0 --shape star \
        --star-points 6 --star-inner-ratio 0.35

    # Custom shape from your own SVG file, scaled up 30%
    python vector_halftone.py photo.jpg --spacing 24 --angle 15 --shape custom \
        --shape-svg leaf.svg --shape-svg-scale 1.3

    # Compress the tonal range so dots never fully vanish or fully merge
    python vector_halftone.py photo.jpg --spacing 20 --angle 15 \
        --output-black 30 --output-white 200

    # Navy dots on a transparent background, for placing over another layer
    python vector_halftone.py photo.jpg --spacing 20 --angle 15 \
        --color "#1a2b4c" --background none

    # Explicit output filename instead of the auto-generated one
    python vector_halftone.py photo.jpg --spacing 20 --angle 15 --output my_screen.svg

Output:
    An SVG the same pixel dimensions as the source image: a background
    rectangle (white by default) plus one shape per grid cell, sized by
    the local (area-averaged) luminance of the source image. Fully vector -
    open directly in Illustrator, or place in Photoshop.
"""

import sys
import os
import re
import argparse
import math
import numpy as np
import cv2


def fmt_num(v):
    """Format a number for use in a filename: '25.0' -> '25', '15.5' -> '15.5'."""
    if float(v).is_integer():
        return str(int(v))
    return str(v)


def build_grid(w, h, spacing, angle_deg):
    """Generate grid point coordinates, rotated by angle_deg, covering the
    full [0,w] x [0,h] canvas."""
    angle = math.radians(angle_deg)
    ux = np.array([math.cos(angle), math.sin(angle)])
    uy = np.array([-math.sin(angle), math.cos(angle)])
    center = np.array([w / 2.0, h / 2.0])

    diag = math.hypot(w, h)
    steps = int(math.ceil(diag / spacing)) + 2

    points = []
    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            p = center + i * spacing * ux + j * spacing * uy
            if 0 <= p[0] <= w and 0 <= p[1] <= h:
                points.append(p)
    return np.array(points)


# ---------------------------------------------------------------------------
# Shape generators. Each takes the dot's center (cx, cy), an "area radius" r
# (defined so that pi*r^2 == the dot's target area, same convention as the
# circle case), and a rotation in degrees. Returns one SVG element string.
# ---------------------------------------------------------------------------

def shape_circle(cx, cy, r, rotation):
    return f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:.3f}"/>'


def shape_square(cx, cy, r, rotation):
    # side^2 == pi*r^2  =>  side == r * sqrt(pi)
    side = r * math.sqrt(math.pi)
    x = cx - side / 2
    y = cy - side / 2
    return (f'<rect x="{x:.3f}" y="{y:.3f}" width="{side:.3f}" height="{side:.3f}" '
            f'transform="rotate({rotation:.3f} {cx:.3f} {cy:.3f})"/>')


def shape_diamond(cx, cy, r, rotation):
    # diamond (square rotated 45) with diagonal D: area = D^2/2 == pi*r^2
    D = r * math.sqrt(2 * math.pi)
    half = D / 2
    pts = f"{cx:.3f},{cy-half:.3f} {cx+half:.3f},{cy:.3f} {cx:.3f},{cy+half:.3f} {cx-half:.3f},{cy:.3f}"
    return f'<polygon points="{pts}" transform="rotate({rotation:.3f} {cx:.3f} {cy:.3f})"/>'


def shape_star(cx, cy, r, rotation, n=5, inner_ratio=0.5):
    # Area of an n-point star (2n vertices, outer R / inner R*inner_ratio):
    #   Area = n * R * (inner_ratio*R) * sin(pi/n)
    # Solve for R so Area == pi*r^2
    target_area = math.pi * r * r
    denom = n * inner_ratio * math.sin(math.pi / n)
    R = math.sqrt(target_area / denom) if denom > 1e-9 else r
    r_inner = R * inner_ratio

    pts = []
    for i in range(2 * n):
        rad = R if i % 2 == 0 else r_inner
        ang = math.pi / 2 + i * math.pi / n  # start pointing up
        px = cx + rad * math.cos(ang)
        py = cy - rad * math.sin(ang)
        pts.append(f"{px:.3f},{py:.3f}")
    pts_str = " ".join(pts)
    return f'<polygon points="{pts_str}" transform="rotate({rotation:.3f} {cx:.3f} {cy:.3f})"/>'


def shape_custom(cx, cy, r, rotation, shape_data, scale=1.0):
    # Custom shapes size linearly with r (not area-matched, since arbitrary
    # geometry area isn't known) - use --shape-svg-scale to calibrate.
    #
    # Illustrator's SVG importer does not reliably apply the viewBox-based
    # scaling that <use width height> is supposed to get from a <symbol> -
    # it renders the symbol at a fixed native size and clips it, instead of
    # scaling the artwork to fit (confirmed: renders correctly in Safari/
    # QuickLook, broken in Illustrator). To avoid depending on that
    # mechanism at all, we compute the scale/center transform ourselves and
    # inline a fresh copy of the shape's markup per dot, using plain
    # translate/rotate/scale - which every SVG renderer, including
    # Illustrator, handles identically.
    inner, vx, vy, vw, vh = shape_data
    D = 2 * r * scale
    s = min(D / vw, D / vh) if vw > 0 and vh > 0 else 1.0
    vcx, vcy = vx + vw / 2, vy + vh / 2
    transform = (f'translate({cx:.3f} {cy:.3f}) rotate({rotation:.3f}) '
                 f'scale({s:.5f}) translate({-vcx:.3f} {-vcy:.3f})')
    return f'<g transform="{transform}">{inner}</g>'


def load_custom_shape(svg_path):
    """Read an SVG file and return (inner_markup, vb_x, vb_y, vb_w, vb_h)."""
    with open(svg_path, "r") as f:
        text = f.read()

    m = re.search(r'<svg\b([^>]*)>(.*)</svg>', text, re.DOTALL | re.IGNORECASE)
    if not m:
        sys.exit(f"Could not parse SVG root element in: {svg_path}")
    attrs, inner = m.group(1), m.group(2)

    vb_match = re.search(r'viewBox\s*=\s*"([^"]+)"', attrs, re.IGNORECASE)
    if vb_match:
        vx, vy, vw, vh = [float(v) for v in re.split(r'[\s,]+', vb_match.group(1).strip())]
    else:
        w_match = re.search(r'\bwidth\s*=\s*"([\d.]+)', attrs)
        h_match = re.search(r'\bheight\s*=\s*"([\d.]+)', attrs)
        vx, vy = 0.0, 0.0
        vw = float(w_match.group(1)) if w_match else 100.0
        vh = float(h_match.group(1)) if h_match else 100.0

    return (inner.strip(), vx, vy, vw, vh)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Source image to convert")
    parser.add_argument("--output", default=None, help="Output SVG path (auto-named if omitted)")
    parser.add_argument("--spacing", type=float, default=20.0,
                         help="Grid spacing in pixels")
    parser.add_argument("--angle", type=float, default=15.0,
                         help="Screen angle in degrees")
    parser.add_argument("--invert", action="store_true",
                         help="Invert density mapping (light areas get bigger dots)")
    parser.add_argument("--output-black", type=float, default=0,
                         help="Photoshop-style Output Levels black point (0-255)")
    parser.add_argument("--output-white", type=float, default=255,
                         help="Photoshop-style Output Levels white point (0-255)")
    parser.add_argument("--radius-scale", type=float, default=1.0,
                         help="Multiplier on computed dot radius, for taste")
    parser.add_argument("--min-radius", type=float, default=0.15,
                         help="Skip drawing dots below this radius (pixels)")
    parser.add_argument("--color", default="black", help="Dot fill color")
    parser.add_argument("--background", default="white",
                         help="Background fill color, or 'none' for transparent")
    parser.add_argument("--blur", type=float, default=None,
                         help="Box-blur radius (px) used to area-average luminance per dot "
                              "before sampling. Defaults to --spacing (recommended: avoids "
                              "aliasing/moire compared to point-sampling).")
    parser.add_argument("--shape", choices=["circle", "square", "diamond", "star", "custom"],
                         default="circle", help="Dot shape")
    parser.add_argument("--shape-rotation", type=float, default=None,
                         help="Rotation (degrees) applied to each shape. Defaults to --angle "
                              "(ignored for --shape circle, which has no visible rotation).")
    parser.add_argument("--star-points", type=int, default=5, help="Number of star points")
    parser.add_argument("--star-inner-ratio", type=float, default=0.5,
                         help="Inner radius as a fraction of outer radius, for --shape star")
    parser.add_argument("--shape-svg", default=None,
                         help="Path to a custom SVG file to use as the dot shape "
                              "(required if --shape custom)")
    parser.add_argument("--shape-svg-scale", type=float, default=1.0,
                         help="Size multiplier for --shape custom (not area-matched "
                              "automatically, since arbitrary shapes' area isn't known - "
                              "use this to calibrate)")
    args = parser.parse_args()

    if args.shape == "custom" and not args.shape_svg:
        sys.exit("--shape custom requires --shape-svg <file.svg>")

    img = cv2.imread(args.image, cv2.IMREAD_UNCHANGED)
    if img is None:
        sys.exit(f"Could not read image: {args.image}")
    if img.ndim == 3:
        if img.shape[2] == 4:
            img = img[:, :, :3]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    h, w = gray.shape[:2]

    # Area-average the luminance so each dot represents the average tone of
    # its cell, not just a single point-sample (reduces moire/aliasing).
    blur_radius = args.blur if args.blur is not None else args.spacing
    k = max(1, int(round(blur_radius)))
    if k % 2 == 0:
        k += 1
    blurred = cv2.blur(gray, (k, k)) if k > 1 else gray

    points = build_grid(w, h, args.spacing, args.angle)
    if len(points) == 0:
        sys.exit("No grid points generated - check --spacing against the image size")

    xs = np.clip(points[:, 0].astype(int), 0, w - 1)
    ys = np.clip(points[:, 1].astype(int), 0, h - 1)
    raw = blurred[ys, xs].astype(np.float64)  # 0..255

    # Photoshop-style Output Levels remap
    ob = np.clip(args.output_black, 0, 255)
    ow = np.clip(args.output_white, 0, 255)
    remapped = ob + (raw / 255.0) * (ow - ob)

    lum = remapped / 255.0
    density = lum if args.invert else (1.0 - lum)

    # Area-proportional radius: dot area = spacing^2 * density_fraction
    radii = args.spacing * np.sqrt(np.clip(density, 0, 1) / math.pi) * args.radius_scale

    shape_rotation = args.shape_rotation if args.shape_rotation is not None else args.angle

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    ]

    shape_data = None
    if args.shape == "custom":
        shape_data = load_custom_shape(args.shape_svg)

    if args.background.lower() != "none":
        svg_parts.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="{args.background}"/>')
    svg_parts.append(f'<g fill="{args.color}">')

    drawn = 0
    for (x, y), r in zip(points, radii):
        if r < args.min_radius:
            continue
        if args.shape == "circle":
            svg_parts.append(shape_circle(x, y, r, shape_rotation))
        elif args.shape == "square":
            svg_parts.append(shape_square(x, y, r, shape_rotation))
        elif args.shape == "diamond":
            svg_parts.append(shape_diamond(x, y, r, shape_rotation))
        elif args.shape == "star":
            svg_parts.append(shape_star(x, y, r, shape_rotation, args.star_points, args.star_inner_ratio))
        elif args.shape == "custom":
            svg_parts.append(shape_custom(x, y, r, shape_rotation, shape_data, args.shape_svg_scale))
        drawn += 1

    svg_parts.append("</g></svg>")
    svg = "\n".join(svg_parts)

    base, _ = os.path.splitext(args.image)
    if args.output:
        out_path = args.output
    else:
        parts = [f"s{fmt_num(args.spacing)}", f"a{fmt_num(args.angle)}",
                 f"ob {fmt_num(args.output_black)}", f"ow {fmt_num(args.output_white)}"]
        if args.blur is not None:
            parts.append(f"bl {fmt_num(args.blur)}")
        if args.radius_scale != 1.0:
            parts.append(f"rs {fmt_num(args.radius_scale)}")
        if args.min_radius != 0.15:
            parts.append(f"mr {fmt_num(args.min_radius)}")
        if args.shape_rotation is not None:
            parts.append(f"sr {fmt_num(args.shape_rotation)}")
        if args.shape != "circle":
            parts.append(args.shape)
        if args.invert:
            parts.append("inv")
        out_path = f"{base}_halftone {' '.join(parts)}.svg"

    with open(out_path, "w") as f:
        f.write(svg)

    print(f"Grid points generated: {len(points)}")
    print(f"Dots drawn (above min-radius): {drawn}")
    print(f"Saved: {out_path}")
    print(f"Canvas: {w}x{h}, matches your source image exactly.")


if __name__ == "__main__":
    main()
