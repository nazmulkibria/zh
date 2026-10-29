#!/usr/bin/env python3
"""
Zaheen's Cake — photo watermark + gallery builder.

Put your original cake photos in category folders:

    photos/birthday/   photos/custom/   photos/event/   photos/cupcakes/

then run (from the repo root):

    pip install pillow
    python tools/watermark.py

For every photo it will:
  * fix phone rotation (EXIF) and strip location/camera metadata
  * resize to web size (default 1600 px long side) + a 700 px thumbnail
  * stamp the "Zaheen's Cake / zhcakes.com" watermark
  * save to images/gallery/
  * rewrite js/gallery-data.js so the website shows the new photos
  * make images/og-cover.jpg (the preview image for Facebook/WhatsApp links)

File name tricks:
  chocolate-drip-cake.jpg        -> caption "Chocolate drip cake"
  unicorn-cake [hero].jpg        -> also shown in the big arched photo at the top
  family-cake [about].jpg        -> used as the round photo in the About section

Options:
  --style cake|corner|tile|both  watermark style (default: cake = big stamp across the
                             cake + faint pattern + corner signature)
  --opacity 0.0-1.0          watermark strength (default: 0.6)
  --text / --sub             watermark lines
  --max / --thumb            output sizes in px
  --force                    re-process photos that were already done
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError:
    sys.exit("Pillow is missing. Install it with:  pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / "photos"  # override with --src
OUT = ROOT / "images" / "gallery"
DATA_JS = ROOT / "js" / "gallery-data.js"
CATEGORIES = ["custom", "birthday", "event", "cupcakes"]  # add a "cupcakes" chip in index.html when you have cupcake photos
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".jfif"}

# Fonts tried in order (first one found wins). Drop any .ttf into tools/fonts/ to override.
FONT_CANDIDATES = [
    *sorted((ROOT / "tools" / "fonts").glob("*.ttf")),
    Path("C:/Windows/Fonts/georgiab.ttf"),
    Path("C:/Windows/Fonts/georgia.ttf"),
    Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf"),
    Path("/Library/Fonts/Georgia Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),
]
SUB_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
]


def load_font(candidates, size):
    for p in candidates:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                pass
    try:
        return ImageFont.load_default(size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def slugify(name):
    s = re.sub(r"\[[^\]]*\]", "", name).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "cake"


def caption_from(stem):
    s = re.sub(r"\[[^\]]*\]", "", stem)
    s = re.sub(r"[_\-]+", " ", s).strip()
    s = re.sub(r"\s+", " ", s)
    if not s or re.fullmatch(r"(img|dsc|pxl|photo|image|fb|received)?\s*[\d ]*", s, re.I):
        return ""
    return s[0].upper() + s[1:]


def text_size(draw, text, font):
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return r - l, b - t, l, t


def corner_mark(img, text, sub, opacity):
    """Two-line signature in the bottom-right with a soft shadow so it reads on light or dark cakes."""
    w, h = img.size
    base = min(w, h)
    f_main = load_font(FONT_CANDIDATES, max(16, int(base * 0.060)))
    f_sub = load_font(SUB_FONT_CANDIDATES, max(11, int(base * 0.028)))

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    mw, mh, ml, mt = text_size(d, text, f_main)
    sw, sh, sl, st = text_size(d, sub, f_sub)
    pad = int(base * 0.035)
    gap = int(base * 0.010)
    x_main = w - pad - mw - ml
    y_sub = h - pad - sh - st
    y_main = y_sub - gap - mh
    x_sub = w - pad - sw - sl

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    a_sh = int(210 * opacity)
    off = max(1, base // 400)
    sd.text((x_main + off, y_main + off), text, font=f_main, fill=(40, 20, 15, a_sh))
    sd.text((x_sub + off, y_sub + off), sub, font=f_sub, fill=(40, 20, 15, a_sh))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(1.5, base / 450)))

    a = int(255 * opacity)
    d.text((x_main, y_main), text, font=f_main, fill=(255, 255, 255, a))
    d.text((x_sub, y_sub), sub, font=f_sub, fill=(255, 255, 255, int(a * 0.9)))
    return Image.alpha_composite(Image.alpha_composite(img, shadow), layer)


def tile_mark(img, text, opacity):
    """Faint diagonal repeated text across the whole photo — harder to crop out."""
    w, h = img.size
    f = load_font(FONT_CANDIDATES, max(14, int(min(w, h) * 0.045)))
    diag = int((w * w + h * h) ** 0.5)
    tile = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    tw, th, _, _ = text_size(d, text, f)
    step_x, step_y = tw + int(tw * 0.8), th * 5
    a = int(255 * opacity * 0.22)
    for row, yy in enumerate(range(0, diag, step_y)):
        off = (row % 2) * step_x // 2
        for xx in range(-step_x, diag, step_x):
            d.text((xx + off, yy), text, font=f, fill=(255, 255, 255, a))
    tile = tile.rotate(28, resample=Image.BICUBIC)
    left, top = (diag - w) // 2, (diag - h) // 2
    return Image.alpha_composite(img, tile.crop((left, top, left + w, top + h)))


def center_mark(img, text, phone, opacity):
    """Large, angled name + phone stamped across the middle of the photo, i.e. over the cake.
    Semi-transparent white with a soft dark edge, so it reads on white icing and dark chocolate
    alike but still lets the cake show through. Cropping it out would destroy the photo."""
    w, h = img.size
    base = min(w, h)
    big = text.upper()
    # size the main line to ~78% of the short side
    size = max(18, int(base * 0.13))
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    for _ in range(12):
        f_main = load_font(FONT_CANDIDATES, size)
        if text_size(probe, big, f_main)[0] <= base * 0.78:
            break
        size = int(size * 0.9)
    f_sub = load_font(SUB_FONT_CANDIDATES, max(12, int(size * 0.42)))

    mw, mh, ml, mt = text_size(probe, big, f_main)
    sw, sh, sl, st = text_size(probe, phone, f_sub)
    gap = int(size * 0.25)
    bw, bh = max(mw, sw) + size, mh + gap + sh + size
    block = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(block)
    a = int(255 * opacity * 0.62)
    stroke = max(1, size // 22)
    xm, ym = (bw - mw) // 2 - ml, size // 2 - mt
    xs, ys = (bw - sw) // 2 - sl, size // 2 + mh + gap - st
    edge = (40, 20, 15, int(a * 0.45))
    d.text((xm, ym), big, font=f_main, fill=(255, 255, 255, a), stroke_width=stroke, stroke_fill=edge)
    d.text((xs, ys), phone, font=f_sub, fill=(255, 255, 255, a), stroke_width=max(1, stroke // 2), stroke_fill=edge)
    block = block.rotate(18, resample=Image.BICUBIC, expand=True)

    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cx, cy = w // 2, int(h * 0.56)  # cakes usually sit slightly below the middle of the frame
    layer.alpha_composite(block, (max(0, cx - block.width // 2), max(0, cy - block.height // 2)))
    return Image.alpha_composite(img, layer)


def fit(img, max_side):
    img = img.copy()
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    return img


def process(src, cat, args):
    stem = src.stem
    slug = f"{cat}-{slugify(stem)}"
    big = OUT / f"{slug}.jpg"
    small = OUT / f"{slug}-thumb.jpg"

    if args.force or not big.exists() or big.stat().st_mtime < src.stat().st_mtime:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert("RGBA")
            im = fit(im, args.max)
            if args.style in ("tile", "both", "cake"):
                im = tile_mark(im, args.text, args.opacity)
            if args.style == "cake":
                im = center_mark(im, args.text, args.phone, args.opacity)
            if args.style in ("corner", "both", "cake"):
                im = corner_mark(im, args.text, args.sub, args.opacity)
            im = im.convert("RGB")
            im.save(big, "JPEG", quality=84, optimize=True, progressive=True)
            th = fit(im, args.thumb)  # thumbnail made from the watermarked image
            th.save(small, "JPEG", quality=80, optimize=True, progressive=True)
        print(f"  ✓ {src.name}  ->  {big.relative_to(ROOT)}")
    else:
        print(f"  · {src.name} (up to date)")

    with Image.open(small) as t:
        tw, th_ = t.size
    entry = {
        "src": f"images/gallery/{big.name}",
        "thumb": f"images/gallery/{small.name}",
        "w": tw, "h": th_,
        "cat": cat,
        "title": caption_from(stem),
    }
    low = stem.lower()
    if "[hero]" in low:
        entry["featured"] = True
    if "[about]" in low:
        entry["about"] = True
    return entry


def make_og(entries):
    pick = next((e for e in entries if e.get("featured")), entries[0] if entries else None)
    if not pick:
        return
    with Image.open(ROOT / pick["src"]) as im:
        og = ImageOps.fit(im.convert("RGB"), (1200, 630), Image.LANCZOS, centering=(0.5, 0.45))
        og.save(ROOT / "images" / "og-cover.jpg", "JPEG", quality=85, optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--style", choices=["cake", "corner", "tile", "both"], default="cake")
    ap.add_argument("--opacity", type=float, default=0.6)
    ap.add_argument("--text", default="Zaheen's Cake")
    ap.add_argument("--phone", default="01670-236621")
    ap.add_argument("--sub", default="zhcakes.com  |  01670-236621")
    ap.add_argument("--max", type=int, default=1600)
    ap.add_argument("--thumb", type=int, default=700)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--src", help="photos folder (default: photos/)")
    args = ap.parse_args()
    global PHOTOS
    if args.src:
        PHOTOS = Path(args.src).resolve()

    # Files dropped loose in photos/ named "zh__<category>__<name>.jpg" are sorted into their folder.
    for p in sorted(PHOTOS.glob("zh__*__*")):
        m = re.match(r"zh__([a-z]+)__(.+)$", p.name)
        if p.is_file() and m and m.group(1) in CATEGORIES:
            (PHOTOS / m.group(1)).mkdir(exist_ok=True)
            p.rename(PHOTOS / m.group(1) / m.group(2))
            print(f"  sorted {p.name} -> {m.group(1)}/")

    OUT.mkdir(parents=True, exist_ok=True)
    entries, seen = [], set()
    for cat in CATEGORIES:
        folder = PHOTOS / cat
        if not folder.is_dir():
            continue
        files = sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTS)
        if files:
            print(f"{cat}:")
        for f in files:
            try:
                e = process(f, cat, args)
                entries.append(e)
                seen.add(Path(e["src"]).name)
                seen.add(Path(e["thumb"]).name)
            except Exception as ex:  # keep going if one photo is broken
                print(f"  ✗ {f.name}: {ex}")

    if not entries:
        sys.exit("No photos found. Put cake photos into photos/birthday, photos/custom, "
                 "photos/event or photos/cupcakes and run again.")

    # remove outputs whose original photo was deleted
    for old in OUT.glob("*.jpg"):
        if old.name not in seen:
            old.unlink()

    # gallery order: hero photos first, then alternate categories so the grid looks mixed
    buckets = {c: [e for e in entries if e["cat"] == c and not e.get("featured")] for c in CATEGORIES}
    ordered = [e for e in entries if e.get("featured")]
    while any(buckets.values()):
        for c in CATEGORIES:
            if buckets[c]:
                ordered.append(buckets[c].pop(0))
    entries = ordered

    DATA_JS.write_text(
        "/* Generated by tools/watermark.py — do not edit by hand, re-run the script instead. */\n"
        "window.ZH_GALLERY = " + json.dumps(entries, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    make_og(entries)
    print(f"\nDone: {len(entries)} photos. Updated {DATA_JS.relative_to(ROOT)} and images/og-cover.jpg")


if __name__ == "__main__":
    main()
