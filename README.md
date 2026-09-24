# Vector Halftone Shapes

Converts an image into a true **vector** (SVG) halftone dot screen — not a
rasterized filter. Every dot is a real, editable SVG shape (`circle`,
`square`, `diamond`, `star`, or any custom SVG you provide), sized by the
local, area-averaged luminance of the source image.

## Features

- Adjustable grid **spacing** and screen **angle**
- Five dot shapes — `circle`, `square`, `diamond`, `star`, or `custom`
  (your own SVG file), all area-matched so switching shapes doesn't change
  the overall tonal balance
- Photoshop-style **Output Levels** clamping (`--output-black` /
  `--output-white`), to cap how small or large dots can get
- Adjustable blur radius for tone sampling, radius scaling, minimum dot
  size, custom colors, transparent backgrounds
- Fully vector output — open directly in Illustrator, or place in
  Photoshop
- Auto-generated, descriptive output filenames based on whichever
  settings you actually used

## Requirements

```bash
pip install opencv-python numpy
```

## Usage

```bash
python vector_halftone_shapes.py <image> [options]
```

### Grid / tone options

| Flag | Description | Default |
|---|---|---|
| `--spacing N` | Grid spacing in pixels (the dot pitch) | `20` |
| `--angle N` | Screen angle in degrees | `15` |
| `--invert` | Light areas get bigger dots instead of dark areas | off |
| `--output-black N` | Output Levels black point, 0–255 | `0` |
| `--output-white N` | Output Levels white point, 0–255 | `255` |
| `--radius-scale N` | Flat multiplier on every dot's radius | `1.0` |
| `--min-radius N` | Skip drawing dots smaller than this (px) | `0.15` |
| `--blur N` | Area-averaging radius (px) for tone sampling | matches `--spacing` |

### Appearance

| Flag | Description | Default |
|---|---|---|
| `--color C` | Dot fill color (name or hex) | `black` |
| `--background C` | Background fill color, or `none` for transparent | `white` |

### Shape

| Flag | Description | Default |
|---|---|---|
| `--shape S` | `circle` \| `square` \| `diamond` \| `star` \| `custom` | `circle` |
| `--shape-rotation N` | Rotation (degrees) applied to each shape | matches `--angle` |
| `--star-points N` | Number of points, for `--shape star` | `5` |
| `--star-inner-ratio N` | Inner/outer radius ratio, for `--shape star` | `0.5` |
| `--shape-svg FILE` | Custom SVG file to use as the dot shape (required for `--shape custom`) | — |
| `--shape-svg-scale N` | Size multiplier for `--shape custom` | `1.0` |

### Output

| Flag | Description |
|---|---|
| `--output FILE` | Output SVG path (auto-named from settings if omitted) |

## Examples

```bash
# Basic screen: 20px spacing, 15 degree angle, circles
python vector_halftone_shapes.py photo.jpg --spacing 20 --angle 15

# Finer screen, steeper angle, squares instead of circles
python vector_halftone_shapes.py photo.jpg --spacing 12 --angle 45 --shape square

# Diamonds, inverted (light areas get the big dots)
python vector_halftone_shapes.py photo.jpg --spacing 18 --angle 15 --shape diamond --invert

# 6-pointed stars with spiky points, no rotation on the grid
python vector_halftone_shapes.py photo.jpg --spacing 24 --angle 0 --shape star \
    --star-points 6 --star-inner-ratio 0.35

# Custom shape from your own SVG file, scaled up 30%
python vector_halftone_shapes.py photo.jpg --spacing 24 --angle 15 --shape custom \
    --shape-svg leaf.svg --shape-svg-scale 1.3

# Compress the tonal range so dots never fully vanish or fully merge
python vector_halftone_shapes.py photo.jpg --spacing 20 --angle 15 \
    --output-black 30 --output-white 200
```

## Output filenames

Output files are auto-named from whichever settings you actually
specified, e.g.:

```
marilyn_halftone s20 a15 ob 0 ow 255 diamond.svg
```

Only non-default values appear in the name, so a plain run stays short.
Pass `--output <path>` to override entirely.

## Gallery

<!--
  One block per example. Copy/paste this block for each new example,
  point the <img> src at the SVG's path in the repo, and put the exact
  command used as the caption underneath.
-->

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 star.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --shape star --star-points 5 --star-inner-ratio 0.4</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 star inv.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --shape star --star-points 5 --star-inner-ratio 0.4 --invert</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 min-radius 4.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 square.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --shape square</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 diamond.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --shape diamond</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 custom rot 15.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --shape custom --shape-svg dollar.svg</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 mr 4 custom scale 2.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --shape custom --shape-svg dollar.svg --shape-svg-scale 2</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 custom rot 0.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --shape custom --shape-svg dollar.svg --shape-rotation 0</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 colored.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --color '#f75dff' --background '#62ff77'</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 100 ow 255.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --output-black 100</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 155.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --min-radius 4 --output-white 155</code>
</p>

<p align="center">
  <img src="examples/marilyn_halftone s20 a15 ob 0 ow 255 bl 100.svg" width="800"><br>
  <code>python vector_halftone_shapes.py marilyn.png --spacing 20 --angle 15 --blur 100</code>
</p>

## Notes

- **Illustrator + `--shape custom`:** each dot inlines a full copy of your
  shape's path (rather than a shared `<symbol>`/`<use>` reference). This
  makes for a larger file, but Illustrator's SVG importer doesn't
  reliably apply the viewBox-based scaling `<use>` needs from a
  `<symbol>` — it can render every instance at a fixed, cropped size
  instead of scaling correctly. Inlining sidesteps that entirely.

## License

GNU GENERAL PUBLIC LICENSE
