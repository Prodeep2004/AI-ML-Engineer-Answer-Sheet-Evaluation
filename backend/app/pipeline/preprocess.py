"""Load PDFs/images -> cleaned, deskewed, size-capped JPEG pages."""
import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageOps

MAX_SIDE = 2000  # plenty for handwriting; keeps uploads small and fast
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class PageImage:
    page_no: int
    jpeg: bytes
    sha: str
    skew_deg: float


def _load(name: str, data: bytes) -> list[np.ndarray]:
    """Return RGB arrays, one per page."""
    if name.lower().endswith(".pdf"):
        doc = pymupdf.open(stream=data, filetype="pdf")
        out = []
        for p in doc:
            pix = p.get_pixmap(dpi=200)
            out.append(np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[..., :3].copy())
        return out
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")  # honour phone rotation
    return [np.array(img)]


def _estimate_skew(gray: np.ndarray) -> float:
    """Projection-profile deskew: the angle whose row-sum profile is sharpest wins (text lines align)."""
    small = cv2.resize(gray, None, fx=600 / max(gray.shape), fy=600 / max(gray.shape))
    ink = cv2.adaptiveThreshold(small, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 15)
    h, w = ink.shape
    best, best_score = 0.0, -1.0
    for angle in np.arange(-6, 6.01, 0.5):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        rows = cv2.warpAffine(ink, m, (w, h)).sum(axis=1).astype(np.float64)
        score = float(np.var(rows))
        if score > best_score:
            best, best_score = float(angle), score
    return best


def _clean(rgb: np.ndarray) -> tuple[np.ndarray, float]:
    h, w = rgb.shape[:2]
    scale = min(1.0, MAX_SIDE / max(h, w))
    if scale < 1:
        rgb = cv2.resize(rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    angle = _estimate_skew(gray)
    if abs(angle) >= 0.5:
        hh, ww = gray.shape
        m = cv2.getRotationMatrix2D((ww / 2, hh / 2), angle, 1.0)
        gray = cv2.warpAffine(gray, m, (ww, hh), flags=cv2.INTER_CUBIC, borderValue=255)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)  # lift faint ink on grey paper
    return gray, angle


def prepare(files: list[tuple[str, bytes]]) -> list[PageImage]:
    """files: (filename, bytes) in page order."""
    pages: list[PageImage] = []
    for name, data in files:
        for rgb in _load(name, data):
            gray, angle = _clean(rgb)
            ok, buf = cv2.imencode(".jpg", gray, [cv2.IMWRITE_JPEG_QUALITY, 88])
            jpeg = buf.tobytes()
            pages.append(PageImage(len(pages) + 1, jpeg, hashlib.sha256(jpeg).hexdigest(), angle))
    return pages


def files_from_paths(paths: list[Path]) -> list[tuple[str, bytes]]:
    """Expand folders, keep natural page order (page2 before page10)."""
    import re

    expanded: list[Path] = []
    for p in paths:
        if p.is_dir():
            expanded += [f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXT | {".pdf"}]
        else:
            expanded.append(p)
    natural = lambda f: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", f.name)]
    return [(f.name, f.read_bytes()) for f in sorted(expanded, key=natural)]
