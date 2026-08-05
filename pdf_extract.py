"""PDF image extraction backend (PyMuPDF-based). No UI dependencies."""
# ImgSnips
# Copyright (C) 2026 Andrew Howard
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import io
import hashlib
import pymupdf
from PIL import Image, ImageChops

# Cached thumbnails are generated once at this size and only ever downscaled
# for display from there; it must cover the UI's largest selectable icon
# size (main.py's MAX_THUMB_SIZE) so the icon-size slider has real pixels to
# scale up to instead of upscaling a smaller cached copy.
THUMB_CACHE_SIZE = 280


def canonical_png_path(img_dir, obj_num):
    return os.path.join(img_dir, f"image-{obj_num:04d}.png")


def _explicit_mask_xref(doc, xref):
    """Some PDFs reference a hard /Mask (stencil mask) instead of a soft
    /SMask. /Mask can also be inline color-key masking (an array of
    integers, not an image reference) -- only follow it when it's actually
    an indirect object reference."""
    kind, value = doc.xref_get_key(xref, 'Mask')
    if kind == 'xref':
        return int(value.split()[0])
    return None


def enumerate_images(doc):
    """One entry per distinct image object (not per page reference -- the
    same image xref can be reused across many pages, e.g. repeated cover
    art or logos), each carrying its real mask xref read straight from the
    PDF. Guessing image/mask pairs from extraction order and matching pixel
    size is unreliable: documents that reuse identical dimensions for
    repeated cover art, logos, or color swatches can silently pair an image
    with an unrelated mask."""
    seen = {}
    for page_num in range(doc.page_count):
        for img in doc[page_num].get_images(full=True):
            xref, smask, width, height = img[0], img[1], img[2], img[3]
            if xref in seen:
                continue
            mask_xref = smask or _explicit_mask_xref(doc, xref)
            seen[xref] = {
                'page': page_num + 1,
                'obj_num': xref,
                'width': width,
                'height': height,
                'mask_xref': mask_xref or None,
            }
    return list(seen.values())


def _open_raw_image(doc, xref):
    """Decode an image object to a PIL image, handling CMYK JPEGs written by
    Adobe tools (InDesign, Photoshop) that render as color negatives of
    themselves: Adobe's CMYK JPEG encoder stores channel values inverted (a
    legacy Photoshop convention marked by the APP14 'Adobe' segment), and
    neither libjpeg nor MuPDF's own decoder correct for it automatically."""
    data = doc.extract_image(xref)['image']
    im = Image.open(io.BytesIO(data))
    im.load()
    if im.mode == 'CMYK' and im.info.get('adobe'):
        im = Image.eval(im, lambda x: 255 - x)
    return im


def extract_and_normalize(doc, outdir, img):
    """Decode one image object -- merging its mask into an alpha channel and
    trimming the transparent border if it has one -- straight to a
    canonical RGBA PNG on disk. Returns the output path."""
    obj_num = img['obj_num']
    out_path = canonical_png_path(outdir, obj_num)
    im = _open_raw_image(doc, obj_num).convert('RGBA')
    mask_xref = img['mask_xref']
    if mask_xref:
        mask_im = _open_raw_image(doc, mask_xref).convert('L')
        if mask_im.size != im.size:
            resample = getattr(Image, 'Resampling', Image).LANCZOS
            mask_im = mask_im.resize(im.size, resample)
        r, g, b, _ = im.split()
        im = Image.merge('RGBA', (r, g, b, mask_im))
        bbox = im.split()[-1].getbbox()
        if bbox:
            im = im.crop(bbox)
    im.save(out_path)
    return out_path


def trim_whitespace(im):
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        alpha = im.convert('RGBA').split()[-1]
        bbox = alpha.getbbox()
        return im.crop(bbox) if bbox else im
    bg = im.getpixel((0, 0))
    if isinstance(bg, int):
        bg = (bg,)
    bg_img = Image.new(im.mode, im.size, bg)
    diff = ImageChops.difference(im, bg_img)
    bbox = diff.getbbox()
    return im.crop(bbox) if bbox else im


def hash_image_file(path):
    hasher = hashlib.sha1()
    with open(path, 'rb') as f:
        while True:
            buf = f.read(8192)
            if not buf:
                break
            hasher.update(buf)
    return hasher.hexdigest()


def ahash_image(img, hash_size=8):
    img = img.convert('L')
    resample = getattr(Image, 'Resampling', Image).LANCZOS
    img = img.resize((hash_size, hash_size), resample)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    return ''.join('1' if p > avg else '0' for p in pixels)


def hamming_distance(a, b):
    return sum(x != y for x, y in zip(a, b))


def extract_images(pdf_path, outdir):
    """Full pipeline: enumerate embedded image objects -> decode + merge
    masks straight to canonical PNGs -> thumbnails -> exact + perceptual
    dedup. Returns a list of image dicts:
    {filename, meta, orig_path, thumb_path, save_name}."""
    doc = pymupdf.open(pdf_path)
    try:
        images = enumerate_images(doc)
        if not images:
            return []

        img_files = []
        for img in images:
            obj_num = img['obj_num']
            try:
                orig_path = extract_and_normalize(doc, outdir, img)
            except Exception as e:
                # One image object in a shape/colorspace we can't decode
                # shouldn't take down every other image in the file with it.
                print(f"[WARN] Skipping image object {obj_num}, could not decode: {e}")
                continue
            img_files.append({
                'filename': os.path.basename(orig_path),
                'meta': {k: img[k] for k in ('page', 'obj_num', 'width', 'height')},
                'orig_path': orig_path,
                'thumb_path': os.path.join(outdir, f"thumb-{obj_num:04d}.png"),
                'save_name': None,
            })
    finally:
        doc.close()

    if not img_files:
        return []

    # Exact-duplicate removal (identical bytes).
    seen_hashes = set()
    unique = []
    for img in img_files:
        try:
            h = hash_image_file(img['orig_path'])
        except Exception:
            continue
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique.append(img)
    img_files = unique
    if not img_files:
        return []

    # Thumbnails (trimmed + capped to THUMB_CACHE_SIZE).
    for img in img_files:
        orig_path = img['orig_path']
        thumb_path = img['thumb_path']
        if os.path.exists(thumb_path):
            continue
        try:
            with Image.open(orig_path) as im:
                im_trimmed = trim_whitespace(im)
                im_trimmed.thumbnail((THUMB_CACHE_SIZE, THUMB_CACHE_SIZE))
                im_trimmed.save(thumb_path, 'PNG')
        except Exception as e:
            print(f"[WARN] Failed to generate thumbnail for {orig_path}: {e}")

    # Perceptual dedup: group visually-similar images, keep the largest of each group.
    hash_area_img = []
    for img in img_files:
        thumb_path = img['thumb_path']
        if not os.path.exists(thumb_path):
            continue
        try:
            with Image.open(thumb_path) as thumb_img:
                h = ahash_image(thumb_img)
        except Exception as e:
            print(f"[WARN] Could not perceptual-hash {thumb_path}: {e}")
            continue
        try:
            with Image.open(img['orig_path']) as orig_img:
                area = orig_img.width * orig_img.height
        except Exception:
            area = 0
        hash_area_img.append((h, area, img))

    threshold = 5
    kept = []
    used = set()
    for i, (h1, area1, img1) in enumerate(hash_area_img):
        if i in used:
            continue
        group = [(area1, img1, i)]
        for j in range(i + 1, len(hash_area_img)):
            if j in used:
                continue
            h2, area2, img2 = hash_area_img[j]
            if hamming_distance(h1, h2) <= threshold:
                group.append((area2, img2, j))
                used.add(j)
        group.sort(key=lambda x: x[0], reverse=True)
        kept.append(group[0][1])
        used.add(i)

    return kept


def make_extract_dir(base_tmpdir=None):
    """Create/clear a fresh extraction directory."""
    import tempfile
    import shutil
    if base_tmpdir and os.path.exists(base_tmpdir):
        shutil.rmtree(base_tmpdir)
    return tempfile.mkdtemp(prefix='imgsnips_')
