"""
EAS Station - Emergency Alert System
Copyright (c) 2025-2026 Timothy Kramer (KR8MER)

This file is part of EAS Station.

EAS Station is dual-licensed software:
- GNU Affero General Public License v3 (AGPL-3.0) for open-source use
- Commercial License for proprietary use

You should have received a copy of both licenses with this software.
For more information, see LICENSE and LICENSE-COMMERCIAL files.

IMPORTANT: This software cannot be rebranded or have attribution removed.
See NOTICE file for complete terms.

Repository: https://github.com/KR8MER/eas-station
"""

from __future__ import annotations

"""Social media image export for alert details.

Generates a Facebook-ready 1200×630 PNG for a given CAP alert containing:
- A stormy-sky header with procedural lightning bolts (same visual
  language as the site's lightning theme), the event name, and severity
- Static OpenStreetMap tile background with the alert polygon drawn on top
- Storm threat badges (tornado, wind, hail) when present
- NWS headline, affected areas, description, and safety instructions —
  the priority sections for a share card, sized to fill the available
  space rather than being clipped at an arbitrary line count
- County coverage and storm-motion summary when space remains
- Alert header and footer with timing info

Operator-only fields (VTAC strings, issuing-office block) are
intentionally omitted — they're technical noise for social sharing and
previously crowded out the readable copy.

The map tile layer is fetched live from OpenStreetMap.  If tiles are
unavailable (network timeout, offline environment, …) the map area is
replaced with a plain dark background; all data cards are unaffected.

Usage::

    from app_utils.image_export import generate_alert_image
    png_bytes = generate_alert_image(alert, coverage_data, ipaws_data, location_settings)
"""

import io
import json
import math
import random
import re
from typing import Any, Dict, List, Optional, Tuple

import requests as _http
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ─── Canvas dimensions (Facebook recommended: 1200×630) ────────────────────
FB_WIDTH    = 1200
FB_HEIGHT   = 630
HEADER_H    = 90
FOOTER_H    = 50
BODY_H      = FB_HEIGHT - HEADER_H - FOOTER_H   # 490
MAP_W       = 582
MAP_H       = BODY_H                             # 490
INFO_X      = MAP_W + 8                          # 590
INFO_W      = FB_WIDTH - INFO_X - 8             # 594
TILE_SIZE   = 256

# ─── Colour palette ─────────────────────────────────────────────────────────
_BG         = (22,  27,  38)
_PANEL      = (30,  36,  51)
_CARD       = (38,  45,  63)
_STRIP      = (14,  18,  30)
_DIVIDER    = (55,  65,  88)
_TEXT       = (230, 235, 245)
_TEXT_SEC   = (155, 165, 190)
_TEXT_MUT   = ( 95, 108, 132)
WHITE       = (255, 255, 255)

_SEVERITY: Dict[str, Tuple[int, int, int]] = {
    'extreme':  (220,  53,  69),
    'severe':   (253, 126,  20),
    'moderate': (255, 193,   7),
    'minor':    ( 13, 110, 253),
    'unknown':  (108, 117, 125),
}
_THREAT_CLR: Dict[str, Tuple[int, int, int]] = {
    'observed': (220,  53,  69),
    'radar':    (255, 193,   7),
    'possible': (253, 126,  20),
    'none':     ( 80,  95, 120),
}


# ─── Font loading ────────────────────────────────────────────────────────────
def _load_fonts() -> Dict[str, ImageFont.FreeTypeFont]:
    """Return a dict of sized fonts; falls back to Pillow built-in."""
    _reg = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    ]
    _bold = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
    ]

    def _load(paths: List[str], size: int) -> ImageFont.FreeTypeFont:
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except (IOError, OSError):
                pass
        return ImageFont.load_default(size=size)

    return {
        'title':  _load(_bold, 30),
        'head':   _load(_bold, 18),
        'bold':   _load(_bold, 15),
        'normal': _load(_reg,  14),
        'small':  _load(_reg,  12),
        'tiny':   _load(_reg,  11),
        'label':  _load(_bold, 11),
        'threat': _load(_bold, 15),
        'mono':   _load(_reg,  11),
    }


# ─── Colour helpers ──────────────────────────────────────────────────────────
def _darken(c: Tuple[int, int, int], f: float) -> Tuple[int, int, int]:
    return tuple(max(0, int(v * (1.0 - f))) for v in c)  # type: ignore[return-value]


def _pct_bar_color(pct: float) -> Tuple[int, int, int]:
    if pct >= 95:  return (40, 167,  69)
    if pct >= 75:  return (255, 193,   7)
    if pct >= 50:  return ( 13, 110, 253)
    return (108, 117, 125)


# ─── Text measurement helpers ────────────────────────────────────────────────
def _tw(font: ImageFont.FreeTypeFont, text: str) -> int:
    bb = font.getbbox(text)
    return bb[2] - bb[0]


def _th(font: ImageFont.FreeTypeFont, text: str) -> int:
    bb = font.getbbox(text)
    return bb[3] - bb[1]


def _truncate(font: ImageFont.FreeTypeFont, text: str, max_w: int) -> str:
    """Truncate *text* with an ellipsis to fit within *max_w* pixels."""
    if _tw(font, text) <= max_w:
        return text
    ellipsis = '…'
    while len(text) > 0 and _tw(font, text + ellipsis) > max_w:
        text = text[:-1]
    return text + ellipsis


# ─── Lightning bolt renderer (matches the site's lightning theme) ───────────
# Ported from static/js/core/lightning.js so social-share images carry the
# same stormy-sky visual identity as the web UI.

def _lb_trunk(rng: random.Random, start_x: float, start_y: float,
              end_y: float, segments: int, drift: float) -> List[Tuple[float, float]]:
    """Jagged descending trunk with uneven step length — real bolts aren't even zigzags."""
    pts: List[Tuple[float, float]] = [(start_x, start_y)]
    x, y = start_x, start_y
    avg_step = (end_y - start_y) / max(1, segments)
    for _ in range(1, segments):
        step = avg_step * rng.uniform(0.55, 1.45)
        y = min(end_y, y + step)
        x += rng.uniform(-drift, drift)
        pts.append((x, y))
    pts.append((x + rng.uniform(-drift, drift), end_y))
    return pts


def _lb_branches(rng: random.Random, parent: List[Tuple[float, float]],
                 spawn_chance: float, depth: int, base_width: float,
                 side_hint: int) -> List[Dict[str, Any]]:
    """Branches fork from interior trunk vertices and may recurse."""
    out: List[Dict[str, Any]] = []
    if depth <= 0:
        return out
    for i in range(1, len(parent) - 1):
        if rng.random() >= spawn_chance:
            continue
        ox, oy = parent[i]
        direction = side_hint * (1 if rng.random() < 0.75 else -1)
        length = rng.uniform(40, 140)
        segs = rng.randint(3, 7)
        step = length / segs
        angle = rng.uniform(0.55, 1.25)
        branch: List[Tuple[float, float]] = [(ox, oy)]
        cx, cy = ox, oy
        for _ in range(segs):
            lateral = math.sin(angle + rng.uniform(-0.35, 0.35)) * step * direction
            descent = math.cos(angle) * step * 0.65 + rng.uniform(-step * 0.15, step * 0.35)
            cx += lateral
            cy += descent
            branch.append((cx, cy))
        out.append({'points': branch, 'width': base_width})
        if depth > 1 and rng.random() < spawn_chance * 0.6:
            out.extend(_lb_branches(rng, branch, spawn_chance * 0.5,
                                    depth - 1, base_width * 0.55, direction))
    return out


def _lb_render_polyline(draw: ImageDraw.ImageDraw,
                        points: List[Tuple[float, float]],
                        base_width: float, taper: float,
                        color: Tuple[int, int, int, int]) -> None:
    """Draw a tapered polyline — width shrinks toward the tip for a bolt-like feel."""
    total = len(points) - 1
    if total <= 0:
        return
    for i in range(total):
        t = i / total
        w = max(1, int(round(base_width * ((1 - t) ** taper))))
        p1 = (int(points[i][0]),     int(points[i][1]))
        p2 = (int(points[i + 1][0]), int(points[i + 1][1]))
        draw.line([p1, p2], fill=color, width=w)


def _draw_lightning_bolts(target: Image.Image, region: Tuple[int, int, int, int],
                          *, count: int = 2, seed: int = 0,
                          intensity: float = 1.0) -> None:
    """Composite glowing lightning bolts onto *target* within *region* (x, y, w, h).

    Bolts are rendered once as geometry, then drawn three times with
    shrinking widths and increasing opacity: a wide blurred halo, a
    medium-width glow, and a crisp white core.  This stack mimics the
    CSS drop-shadow layers used by the web UI's lightning.js so the
    share image carries the same visual identity.
    """
    x0, y0, rw, rh = region
    if rw <= 0 or rh <= 0:
        return

    rng = random.Random(seed)

    # ── Geometry pass: build trunks + branches once, reuse for each layer ──
    bolts: List[Dict[str, Any]] = []
    # Extend virtual height so the trunk develops a natural zigzag rhythm
    # even when the physical region is short (e.g. the 90-px header).  We
    # draw into the full virtual range, then clip by the region when
    # compositing.
    vh = max(rh, 260)
    for _ in range(count):
        start_x  = rng.uniform(rw * 0.08, rw * 0.92)
        start_y  = rng.uniform(-vh * 0.20, -vh * 0.05)
        end_y    = vh + rng.uniform(-vh * 0.10, vh * 0.05)
        segments = rng.randint(12, 18)
        # Drift is per-step, proportional to segment length — this keeps
        # the bolt predominantly vertical instead of ping-ponging sideways.
        step_h   = (end_y - start_y) / segments
        drift    = step_h * rng.uniform(0.35, 0.75)
        side     = 1 if start_x < rw / 2 else -1

        trunk    = _lb_trunk(rng, start_x, start_y, end_y, segments, drift)
        branches = _lb_branches(rng, trunk, 0.38, 2, 1.6, side)
        bolts.append({'trunk': trunk, 'branches': branches})

    # Render geometry to three layers at different widths/opacities.
    def _stamp(width_trunk: float, width_branch: float,
               taper_t: float, taper_b: float, alpha: int) -> Image.Image:
        layer = Image.new('RGBA', (rw, vh), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        color = (255, 255, 255, min(255, max(0, int(alpha * intensity))))
        for bolt in bolts:
            _lb_render_polyline(ld, bolt['trunk'], width_trunk, taper_t, color)
            for b in bolt['branches']:
                _lb_render_polyline(ld, b['points'],
                                    max(1.0, b['width'] * width_branch),
                                    taper_b, color)
        return layer

    halo = _stamp(width_trunk=14, width_branch=7, taper_t=1.0, taper_b=1.3, alpha=110)
    glow = _stamp(width_trunk=7,  width_branch=4, taper_t=1.1, taper_b=1.4, alpha=170)
    core = _stamp(width_trunk=3,  width_branch=1, taper_t=1.3, taper_b=1.6, alpha=245)

    halo = halo.filter(ImageFilter.GaussianBlur(radius=10))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=3))

    # Composite onto target, clipping to the physical region height.
    def _paste(layer: Image.Image) -> None:
        cropped = layer.crop((0, 0, rw, rh))
        if target.mode != 'RGBA':
            base = target.convert('RGBA')
            base.alpha_composite(cropped, dest=(x0, y0))
            target.paste(base.convert('RGB'))
        else:
            target.alpha_composite(cropped, dest=(x0, y0))

    _paste(halo)
    _paste(glow)
    _paste(core)


# ─── OSM tile helpers ────────────────────────────────────────────────────────
def _lon_to_tx(lon: float, z: int) -> float:
    return (lon + 180.0) / 360.0 * (2 ** z)


def _lat_to_ty(lat: float, z: int) -> float:
    lat_r = math.radians(lat)
    return (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * (2 ** z)


def _geojson_bbox(geom: Dict) -> Optional[Tuple[float, float, float, float]]:
    """Return (min_lon, min_lat, max_lon, max_lat) from a GeoJSON geometry."""
    gtype = geom.get('type', '')
    coords = geom.get('coordinates', [])
    lons: List[float] = []
    lats: List[float] = []

    def _collect(ring: List) -> None:
        for pt in ring:
            lons.append(float(pt[0]))
            lats.append(float(pt[1]))

    if gtype == 'Polygon':
        for ring in coords:
            _collect(ring)
    elif gtype == 'MultiPolygon':
        for poly in coords:
            for ring in poly:
                _collect(ring)
    elif gtype == 'Point' and coords:
        lons.append(float(coords[0]))
        lats.append(float(coords[1]))
    else:
        return None

    if not lons:
        return None
    return (min(lons), min(lats), max(lons), max(lats))


def _geojson_centroid(geom: Dict) -> Optional[Tuple[float, float]]:
    """Return (lon, lat) bounding-box centre of a GeoJSON geometry."""
    bbox = _geojson_bbox(geom)
    if bbox is None:
        return None
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _best_zoom(min_lon: float, min_lat: float, max_lon: float, max_lat: float,
               map_w: int, map_h: int) -> int:
    """Highest OSM zoom where bbox comfortably fits inside the map dimensions."""
    for z in range(15, 3, -1):
        tx1 = _lon_to_tx(min_lon, z)
        tx2 = _lon_to_tx(max_lon, z)
        ty1 = _lat_to_ty(max_lat, z)   # higher lat → lower tile-y
        ty2 = _lat_to_ty(min_lat, z)
        span_w = (tx2 - tx1) * TILE_SIZE
        span_h = (ty2 - ty1) * TILE_SIZE
        if span_w <= map_w * 0.60 and span_h <= map_h * 0.60:
            return z
    return 7


def _fetch_tile(tx: int, ty: int, z: int) -> Optional[Image.Image]:
    url = f'https://tile.openstreetmap.org/{z}/{tx}/{ty}.png'
    try:
        r = _http.get(
            url, timeout=4,
            headers={'User-Agent': 'EASStation/1.0 (+https://github.com/KR8MER/eas-station)'},
        )
        if r.status_code == 200:
            return Image.open(io.BytesIO(r.content)).convert('RGB')
    except Exception:
        pass
    return None


def _draw_storm_track(od: ImageDraw.ImageDraw, storm: Dict,
                      z: int, tx_min: int, ty_min: int) -> None:
    """Draw the storm motion track line and directional arrowhead on *od*."""
    track      = storm.get('track', [])
    toward_deg = storm.get('toward_deg')

    pts: List[Tuple[int, int]] = []
    for point in track:
        try:
            lat, lon = float(point[0]), float(point[1])
            px = int((_lon_to_tx(lon, z) - tx_min) * TILE_SIZE)
            py = int((_lat_to_ty(lat, z) - ty_min) * TILE_SIZE)
            pts.append((px, py))
        except (TypeError, IndexError, ValueError):
            continue

    if not pts:
        return

    _TRACK   = (255, 230,   0)   # bright yellow
    _SHADOW  = (  0,   0,   0)   # black drop-shadow for contrast

    # Track line (shadow then yellow)
    if len(pts) >= 2:
        od.line(pts, fill=_SHADOW, width=5)
        od.line(pts, fill=_TRACK,  width=3)

    # Waypoint circles (larger circle at newest / last point)
    for i, (px, py) in enumerate(pts):
        r = 5 if i == len(pts) - 1 else 3
        od.ellipse((px - r - 1, py - r - 1, px + r + 1, py + r + 1), fill=_SHADOW)
        od.ellipse((px - r,     py - r,     px + r,     py + r),     fill=_TRACK)

    # Arrowhead at the newest track point pointing in the direction of travel
    if toward_deg is not None:
        last_x, last_y = pts[-1]
        ang = math.radians(toward_deg)
        dx  =  math.sin(ang)          # eastward screen component
        dy  = -math.cos(ang)          # screen y grows downward → negate

        arrow_len = 24
        wing_len  = 11
        wing_ang  = 0.45   # ~26°

        tip_x = last_x + int(dx * arrow_len)
        tip_y = last_y + int(dy * arrow_len)

        def _wing(sign: int) -> Tuple[int, int]:
            wx = tip_x - int((dx * math.cos(sign * wing_ang)
                              - dy * math.sin(sign * wing_ang)) * wing_len)
            wy = tip_y - int((dy * math.cos(sign * wing_ang)
                              + dx * math.sin(sign * wing_ang)) * wing_len)
            return (wx, wy)

        lw = _wing(+1)
        rw = _wing(-1)

        # Shadow
        so = 2
        od.polygon([(tip_x + so, tip_y + so), (lw[0] + so, lw[1] + so),
                    (rw[0] + so, rw[1] + so)], fill=_SHADOW)
        # Arrow fill
        od.polygon([(tip_x, tip_y), lw, rw], fill=_TRACK)


def _render_map(geom: Dict, severity: str,
                storm_motion: Optional[Dict] = None,
                boundary_features: Optional[List[Dict]] = None) -> Image.Image:
    """Return a MAP_W×MAP_H RGB map image with the alert polygon overlaid."""
    fallback = Image.new('RGB', (MAP_W, MAP_H), (35, 42, 62))
    fd = ImageDraw.Draw(fallback)
    msg = 'Map not available'
    fonts = _load_fonts()
    fd.text(((MAP_W - _tw(fonts['small'], msg)) // 2, MAP_H // 2 - 8),
            msg, font=fonts['small'], fill=_TEXT_MUT)

    bbox = _geojson_bbox(geom)
    if bbox is None:
        return fallback

    min_lon, min_lat, max_lon, max_lat = bbox
    lon_pad = max(max_lon - min_lon, 0.005) * 0.30
    lat_pad = max(max_lat - min_lat, 0.005) * 0.30
    min_lon -= lon_pad; max_lon += lon_pad
    min_lat -= lat_pad; max_lat += lat_pad

    z = _best_zoom(min_lon, min_lat, max_lon, max_lat, MAP_W, MAP_H)

    tx_min = max(0,        int(math.floor(_lon_to_tx(min_lon, z))) - 1)
    tx_max = min(2**z - 1, int(math.ceil( _lon_to_tx(max_lon, z))) + 1)
    ty_min = max(0,        int(math.floor(_lat_to_ty(max_lat, z))) - 1)
    ty_max = min(2**z - 1, int(math.ceil( _lat_to_ty(min_lat, z))) + 1)

    n_tiles = (tx_max - tx_min + 1) * (ty_max - ty_min + 1)
    if n_tiles > 30:
        return fallback

    canvas_w = (tx_max - tx_min + 1) * TILE_SIZE
    canvas_h = (ty_max - ty_min + 1) * TILE_SIZE
    canvas = Image.new('RGB', (canvas_w, canvas_h), (200, 200, 200))

    for ty in range(ty_min, ty_max + 1):
        for tx in range(tx_min, tx_max + 1):
            tile = _fetch_tile(tx, ty, z)
            if tile:
                canvas.paste(tile, ((tx - tx_min) * TILE_SIZE, (ty - ty_min) * TILE_SIZE))

    # Build polygon pixel-coordinate lists
    alr_clr = _SEVERITY.get(severity.lower(), _SEVERITY['unknown'])

    def _to_px(ring: List) -> List[Tuple[int, int]]:
        pts = []
        for pt in ring:
            px = int((_lon_to_tx(float(pt[0]), z) - tx_min) * TILE_SIZE)
            py = int((_lat_to_ty(float(pt[1]), z) - ty_min) * TILE_SIZE)
            pts.append((px, py))
        return pts

    gtype = geom.get('type', '')
    raw_coords = geom.get('coordinates', [])
    rings: List[List] = []
    if gtype == 'Polygon':
        rings = raw_coords
    elif gtype == 'MultiPolygon':
        rings = [r for poly in raw_coords for r in poly]

    # Semi-transparent fill via RGBA overlay
    overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    ov = ImageDraw.Draw(overlay)
    for ring in rings:
        pts = _to_px(ring)
        if len(pts) >= 3:
            ov.polygon(pts, fill=(*alr_clr, 65))

    canvas = Image.alpha_composite(canvas.convert('RGBA'), overlay).convert('RGB')

    # Solid outline on top
    od = ImageDraw.Draw(canvas)
    for ring in rings:
        pts = _to_px(ring)
        if len(pts) >= 2:
            od.line(pts + [pts[0]], fill=alr_clr, width=3)

    # Storm motion track + arrowhead
    if storm_motion:
        _draw_storm_track(od, storm_motion, z, tx_min, ty_min)

    # ── Boundary overlays ─────────────────────────────────────────────────────
    # Draw county boundaries thicker/brighter; other service boundaries thinner.
    for feat in (boundary_features or []):
        bgeom   = feat.get('geometry', {})
        btype   = feat.get('type', '').lower()
        bgt     = bgeom.get('type', '')
        bcoords = bgeom.get('coordinates', [])
        brings: List[List] = []
        if bgt == 'Polygon':
            brings = bcoords
        elif bgt == 'MultiPolygon':
            brings = [r for poly in bcoords for r in poly]

        is_county = (btype == 'county')
        lw = 2 if is_county else 1
        line_clr = (255, 255, 255) if is_county else (210, 220, 235)

        for ring in brings:
            bpts = _to_px(ring)
            if len(bpts) >= 2:
                closed = bpts + [bpts[0]]
                od.line(closed, fill=(0, 0, 0),   width=lw + 2)   # shadow
                od.line(closed, fill=line_clr,     width=lw)        # outline

    # Crop to MAP_W × MAP_H centred on the padded bbox
    cx = int((_lon_to_tx((min_lon + max_lon) / 2, z) - tx_min) * TILE_SIZE)
    cy = int((_lat_to_ty((min_lat + max_lat) / 2, z) - ty_min) * TILE_SIZE)

    x1 = max(0, cx - MAP_W // 2)
    y1 = max(0, cy - MAP_H // 2)
    x2 = min(canvas_w, x1 + MAP_W)
    y2 = min(canvas_h, y1 + MAP_H)

    if x2 - x1 < MAP_W:
        x1 = max(0, x2 - MAP_W)
    if y2 - y1 < MAP_H:
        y1 = max(0, y2 - MAP_H)

    cropped = canvas.crop((x1, y1, x2, y2))
    if cropped.size != (MAP_W, MAP_H):
        cropped = cropped.resize((MAP_W, MAP_H), Image.LANCZOS)

    # ── Post-crop: boundary name labels ───────────────────────────────────────
    cd       = ImageDraw.Draw(cropped)
    lbl_font = fonts['small']

    # Gather labels — county boundaries get the name shown; other types get a
    # shorter label only when no county is present (avoids clutter).
    has_county_feat = any(f.get('type', '').lower() == 'county'
                          for f in (boundary_features or []))
    seen_labels: set = set()

    for feat in (boundary_features or []):
        name  = (feat.get('name') or '').strip()
        btype = feat.get('type', '').lower()
        if not name or name in seen_labels:
            continue
        if has_county_feat and btype != 'county':
            continue   # skip non-county when county data is available
        cent = _geojson_centroid(feat.get('geometry', {}))
        if cent is None:
            continue
        clon, clat = cent
        lx = int((_lon_to_tx(clon, z) - tx_min) * TILE_SIZE) - x1
        ly = int((_lat_to_ty(clat, z) - ty_min) * TILE_SIZE) - y1
        lw_ = _tw(lbl_font, name)
        lh_ = _th(lbl_font, name)
        # Only render if centroid falls inside the viewport with some margin
        if lw_ // 2 + 4 <= lx <= MAP_W - lw_ // 2 - 4 and lh_ + 4 <= ly <= MAP_H - 4:
            tx0, ty0 = lx - lw_ // 2, ly - lh_ // 2
            # Pill background for readability
            pad = 3
            cd.rounded_rectangle(
                (tx0 - pad, ty0 - pad, tx0 + lw_ + pad, ty0 + lh_ + pad),
                radius=3, fill=(0, 0, 0),
            )
            cd.text((tx0, ty0), name, font=lbl_font, fill=(255, 255, 255))
            seen_labels.add(name)

    # ── OSM attribution (required by tile usage policy) ───────────────────────
    attr     = '\u00a9 OpenStreetMap contributors'
    attr_fnt = fonts['tiny']
    aw, ah   = _tw(attr_fnt, attr), _th(attr_fnt, attr)
    ax, ay   = MAP_W - aw - 5, MAP_H - ah - 5
    cd.rectangle((ax - 2, ay - 1, MAP_W - 3, MAP_H - 3), fill=(0, 0, 0))
    cd.text((ax, ay), attr, font=attr_fnt, fill=(200, 200, 200))

    return cropped


# ─── Drawing helpers ─────────────────────────────────────────────────────────
def _section_header(draw: ImageDraw.ImageDraw, fonts: Dict,
                    alr_clr: Tuple, ix: int, iy: int, iw: int, title: str) -> int:
    """Draw a coloured section header; return y after it."""
    h = 20
    draw.rectangle((ix, iy, ix + iw, iy + h), fill=_darken(alr_clr, 0.25))
    draw.text((ix + 7, iy + (h - _th(fonts['label'], title)) // 2),
              title, font=fonts['label'], fill=WHITE)
    return iy + h + 2


def _card_row(draw: ImageDraw.ImageDraw, ix: int, iy: int, iw: int, h: int) -> None:
    """Fill a single card-row background."""
    draw.rectangle((ix, iy, ix + iw, iy + h - 1), fill=_CARD)


def _draw_header_gradient(img: Image.Image, alr_clr: Tuple[int, int, int]) -> None:
    """Paint a top→bottom gradient across the header for a stormy-cloud look."""
    top = _darken(alr_clr, 0.55)
    bot = alr_clr
    d = ImageDraw.Draw(img)
    for y in range(HEADER_H):
        t = y / max(1, HEADER_H - 1)
        r = int(top[0] * (1 - t) + bot[0] * t)
        g = int(top[1] * (1 - t) + bot[1] * t)
        b = int(top[2] * (1 - t) + bot[2] * t)
        d.line([(0, y), (FB_WIDTH, y)], fill=(r, g, b))


# ─── Main public function ─────────────────────────────────────────────────────
def generate_alert_image(
    alert: Any,
    coverage_data: Dict[str, Any],
    ipaws_data: Optional[Dict[str, Any]],
    location_settings: Optional[Dict[str, Any]],
) -> bytes:
    """Generate a 1200×630 Facebook-ready PNG for *alert*.

    Args:
        alert:             CAPAlert model instance.
        coverage_data:     Dict returned by calculate_coverage_percentages().
        ipaws_data:        Dict returned by _extract_alert_display_data(), may be None.
        location_settings: Dict from get_location_settings(), may be None.

    Returns:
        Raw PNG bytes.
    """
    fonts = _load_fonts()

    severity    = (getattr(alert, 'severity', '') or '').lower()
    alr_clr     = _SEVERITY.get(severity, _SEVERITY['unknown'])
    event_name  = (getattr(alert, 'event', '') or 'Alert').upper()
    county_name = (location_settings or {}).get('county_name', 'County') or 'County'

    # Stable per-alert seed so each alert's bolt pattern is reproducible.
    alert_seed = hash((getattr(alert, 'id', 0) or 0, event_name)) & 0xFFFFFFFF

    # ── Base canvas ──────────────────────────────────────────────────────────
    img  = Image.new('RGB', (FB_WIDTH, FB_HEIGHT), _BG)
    draw = ImageDraw.Draw(img)

    # ── Header bar (stormy sky with lightning) ────────────────────────────────
    # Vertical gradient from darkened-severity → severity so the header reads
    # as an illuminated storm cloud rather than a flat colour block.
    _draw_header_gradient(img, alr_clr)
    # Glowing lightning bolts behind the title — matches the site's lightning
    # theme so the share card feels like a still frame from the UI.
    _draw_lightning_bolts(img, (0, 0, FB_WIDTH, HEADER_H),
                          count=3, seed=alert_seed, intensity=1.0)
    # Soft scrim under the text for legibility after the flash.
    scrim = Image.new('RGBA', (FB_WIDTH, HEADER_H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    sd.rectangle((0, 0, 560, HEADER_H), fill=(0, 0, 0, 70))
    base = img.convert('RGBA')
    base.alpha_composite(scrim)
    img.paste(base.convert('RGB'))
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, HEADER_H - 2, FB_WIDTH, HEADER_H), fill=_darken(alr_clr, 0.45))

    # Event name (left)
    draw.text((16, 10), event_name, font=fonts['title'], fill=WHITE)

    # Status sub-line
    sub_parts = []
    for attr, label in [('status', 'Status'), ('severity', 'Severity'),
                        ('urgency', 'Urgency'), ('certainty', 'Certainty')]:
        val = getattr(alert, attr, '') or ''
        if val:
            sub_parts.append(f'{label}: {val}')
    sub_text = '  |  '.join(sub_parts)
    draw.text((18, 52), sub_text, font=fonts['small'], fill=(*WHITE, 200))  # type: ignore[arg-type]

    # Branding (top-right)
    brand = 'EAS STATION'
    draw.text((FB_WIDTH - _tw(fonts['head'], brand) - 16, 10),
              brand, font=fonts['head'], fill=WHITE)

    # Sent time (right, lower)
    try:
        from app_core.eas_storage import format_local_datetime
        if getattr(alert, 'sent', None):
            sent_str = format_local_datetime(alert.sent, include_utc=False)
            draw.text((FB_WIDTH - _tw(fonts['small'], sent_str) - 16, 55),
                      sent_str, font=fonts['small'], fill=(*WHITE, 180))  # type: ignore[arg-type]
    except Exception:
        pass

    # ── Map (left side) ──────────────────────────────────────────────────────
    storm_motion = (ipaws_data or {}).get('storm_motion')
    map_img: Optional[Image.Image] = None
    try:
        from app_core.extensions import db
        from app_core.models import CAPAlert as _CA, Boundary as _Bdy, Intersection as _Isect
        from sqlalchemy import func as _func
        alert_id = getattr(alert, 'id', None)
        if alert_id is not None:
            geom_json = (
                db.session.query(_func.ST_AsGeoJSON(_CA.geom))
                .filter(_CA.id == alert_id)
                .scalar()
            )
            # Query intersecting boundary geometries for county outlines + labels
            boundary_features: List[Dict[str, Any]] = []
            try:
                rows = (
                    db.session.query(
                        _Bdy.name,
                        _Bdy.type,
                        _func.ST_AsGeoJSON(_Bdy.geom).label('geom_json'),
                    )
                    .join(_Isect, _Isect.boundary_id == _Bdy.id)
                    .filter(_Isect.cap_alert_id == alert_id)
                    .all()
                )
                for row in rows:
                    if row.geom_json:
                        boundary_features.append({
                            'name':     row.name or '',
                            'type':     (row.type or '').lower(),
                            'geometry': json.loads(row.geom_json),
                        })
            except Exception:
                pass
            if geom_json:
                map_img = _render_map(json.loads(geom_json), severity,
                                      storm_motion=storm_motion,
                                      boundary_features=boundary_features)
    except Exception:
        pass

    if map_img is None:
        map_img = Image.new('RGB', (MAP_W, MAP_H), (34, 42, 60))
        md = ImageDraw.Draw(map_img)
        lbl = 'Map not available'
        md.text(((MAP_W - _tw(fonts['small'], lbl)) // 2, MAP_H // 2 - 8),
                lbl, font=fonts['small'], fill=_TEXT_MUT)

    img.paste(map_img, (0, HEADER_H))

    # Thin vertical separator
    draw.line([(MAP_W, HEADER_H), (MAP_W, FB_HEIGHT - FOOTER_H)],
              fill=_darken(alr_clr, 0.20), width=3)

    # ── Info panel (right side) ───────────────────────────────────────────────
    ix  = INFO_X
    iw  = INFO_W
    iy  = HEADER_H + 8
    bot = FB_HEIGHT - FOOTER_H - 6

    # Priority order for a share card: storm threats (when dangerous), the
    # headline, WHO is affected, WHAT is happening, WHAT to do.  Coverage /
    # storm motion come last so they only consume space the copy doesn't
    # need.  VTAC codes and the issuing-office block are intentionally
    # omitted — they're operator data, not share-worthy info, and were the
    # main reason long descriptions were being clipped.
    iy = _draw_threats(draw, fonts, alr_clr, ix, iy, iw, bot, ipaws_data)
    iy = _draw_nws_headline(draw, fonts, alr_clr, ix, iy, iw, bot, alert, ipaws_data)
    iy = _draw_areas(draw, fonts, alr_clr, ix, iy, iw, bot, alert)
    iy = _draw_description(draw, fonts, alr_clr, ix, iy, iw, bot, alert)
    iy = _draw_instruction(draw, fonts, alr_clr, ix, iy, iw, bot, alert)
    iy = _draw_coverage(draw, fonts, alr_clr, ix, iy, iw, bot, coverage_data, county_name)
    iy = _draw_compass_section(draw, fonts, alr_clr, ix, iy, iw, bot, ipaws_data)

    # ── Footer ────────────────────────────────────────────────────────────────
    fy = FB_HEIGHT - FOOTER_H
    draw.rectangle((0, fy, FB_WIDTH, FB_HEIGHT), fill=_STRIP)
    draw.line([(0, fy), (FB_WIDTH, fy)], fill=_DIVIDER, width=1)

    timing: List[str] = []
    try:
        from app_core.eas_storage import format_local_datetime
        if getattr(alert, 'sent', None):
            timing.append(f"Issued: {format_local_datetime(alert.sent, include_utc=False)}")
        if getattr(alert, 'expires', None):
            timing.append(f"Expires: {format_local_datetime(alert.expires, include_utc=False)}")
    except Exception:
        pass

    if timing:
        t_str = '   |   '.join(timing)
        ty_pos = fy + (FOOTER_H - _th(fonts['small'], t_str)) // 2
        draw.text((12, ty_pos), t_str, font=fonts['small'], fill=_TEXT_SEC)

    credit = 'EAS Station  •  Emergency Alert System'
    cy_pos = fy + (FOOTER_H - _th(fonts['small'], credit)) // 2
    draw.text((FB_WIDTH - _tw(fonts['small'], credit) - 12, cy_pos),
              credit, font=fonts['small'], fill=_TEXT_MUT)

    # ── Serialise ────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


# ─── Threat-card icon helpers ─────────────────────────────────────────────────
def _icon_wind(draw: ImageDraw.ImageDraw, cx: int, cy: int,
               color: Tuple[int, int, int]) -> None:
    """Three descending-width pill bars representing wind gusts."""
    bars    = [(32, 0), (25, 0), (18, 0)]  # (width, x-offset)
    bar_h   = 6
    spacing = 5
    total_h = len(bars) * bar_h + (len(bars) - 1) * spacing
    y0 = cy - total_h // 2
    for i, (w, xo) in enumerate(bars):
        y = y0 + i * (bar_h + spacing)
        x0 = cx - w // 2 + xo
        draw.rounded_rectangle((x0, y, x0 + w, y + bar_h), radius=3, fill=color)


def _icon_hail(draw: ImageDraw.ImageDraw, cx: int, cy: int,
               color: Tuple[int, int, int]) -> None:
    """Simple cloud arc with hailstone circles beneath it."""
    r = 12
    # Cloud top: semicircle arc
    draw.arc((cx - r, cy - r - 4, cx + r, cy + r - 4),
             start=180, end=360, fill=color, width=3)
    # Cloud base: horizontal line connecting the arc ends
    draw.line([(cx - r, cy + r - 5), (cx + r, cy + r - 5)], fill=color, width=3)
    # Hailstones (2 rows of dots)
    for dx, dy in [(-8, 9), (0, 9), (8, 9), (-4, 16), (4, 16)]:
        rr = 3
        draw.ellipse((cx + dx - rr, cy + dy - rr, cx + dx + rr, cy + dy + rr),
                     fill=color)


def _icon_tornado(draw: ImageDraw.ImageDraw, cx: int, cy: int,
                  color: Tuple[int, int, int]) -> None:
    """Tapering funnel (wide at top, narrowing to a point)."""
    widths  = [30, 22, 15, 9, 4]
    bar_h   = 5
    spacing = 4
    total_h = len(widths) * bar_h + (len(widths) - 1) * spacing
    y0 = cy - total_h // 2
    for i, w in enumerate(widths):
        y = y0 + i * (bar_h + spacing)
        x0 = cx - w // 2
        draw.rounded_rectangle((x0, y, x0 + w, y + bar_h), radius=2, fill=color)
    # Narrow tail below the funnel
    tail_y = y0 + total_h
    draw.line([(cx, tail_y), (cx, tail_y + 6)], fill=color, width=2)


_ICON_FN = {
    'wind':    _icon_wind,
    'hail':    _icon_hail,
    'tornado': _icon_tornado,
}


# ─── Info-panel section drawers ───────────────────────────────────────────────
def _draw_threats(draw: ImageDraw.ImageDraw, fonts: Dict, alr_clr: Tuple,
                  ix: int, iy: int, iw: int, bot: int,
                  ipaws_data: Optional[Dict]) -> int:
    """Draw graphical threat cards — one card per active hazard."""
    threat_data = (ipaws_data or {}).get('threat_data', {})
    if not threat_data:
        return iy

    # Collect present threats in display order
    active = [(k, threat_data[k]) for k in ('tornado', 'wind', 'hail')
              if threat_data.get(k)]
    if not active:
        return iy

    n       = len(active)
    gap     = 5
    card_w  = (iw - gap * (n - 1)) // n
    card_h  = 108
    # Reserve space for the section header (22px) + card height before
    # committing to drawing anything, so we never leave an orphan header.
    if iy + 22 + card_h > bot:
        return iy

    iy = _section_header(draw, fonts, alr_clr, ix, iy, iw, 'STORM THREATS')

    for i, (key, t) in enumerate(active):
        cx   = ix + i * (card_w + gap)
        cy   = iy
        ce_x = cx + card_w // 2   # card horizontal centre

        level   = t.get('level', 'none')
        lvl_clr = _THREAT_CLR.get(level, _THREAT_CLR['none'])

        # Card background: slight colour tint based on threat level
        bg = tuple(int(lvl_clr[j] * 0.18 + _CARD[j] * 0.82) for j in range(3))

        draw.rounded_rectangle((cx, cy, cx + card_w, cy + card_h),
                               radius=7, fill=bg,
                               outline=lvl_clr, width=1)

        # ── Icon (top section) ──────────────────────────────────────────────
        icon_fn = _ICON_FN.get(key)
        if icon_fn:
            icon_fn(draw, ce_x, cy + 28, lvl_clr)

        # ── Primary value (large number or short label) ─────────────────────
        if key == 'wind':
            val = t.get('gust', '')
            unit = t.get('gust_unit', 'MPH')
        elif key == 'hail':
            size = t.get('size', '')
            val  = f'{size}"' if size else ''
            unit = t.get('descriptor', '')
        else:  # tornado
            val  = t.get('display', '')
            unit = ''

        vfont = fonts['head']   # 18 pt bold
        vw    = _tw(vfont, val)
        draw.text((ce_x - vw // 2, cy + 52), val, font=vfont, fill=_TEXT)

        # ── Unit / descriptor ───────────────────────────────────────────────
        if unit:
            uw = _tw(fonts['tiny'], unit)
            draw.text((ce_x - uw // 2, cy + 73), unit,
                      font=fonts['tiny'], fill=_TEXT_SEC)

        # ── Threat level (coloured) ─────────────────────────────────────────
        disp = t.get('display', '') if key != 'tornado' else ''
        if disp and key in ('wind', 'hail'):
            dw = _tw(fonts['tiny'], disp)
            draw.text((ce_x - dw // 2, cy + 84), disp,
                      font=fonts['tiny'], fill=lvl_clr)

        # ── Category label at bottom ────────────────────────────────────────
        cat = key.upper()
        cw  = _tw(fonts['label'], cat)
        draw.text((ce_x - cw // 2, cy + 95), cat,
                  font=fonts['label'], fill=_TEXT_MUT)

    return iy + card_h + 6


def _draw_coverage(draw: ImageDraw.ImageDraw, fonts: Dict, alr_clr: Tuple,
                   ix: int, iy: int, iw: int, bot: int,
                   coverage_data: Dict, county_name: str) -> int:
    if not coverage_data:
        return iy

    # Reserve section-header (22) + at least one row of content before
    # drawing anything — otherwise we'd leave an orphan "COVERAGE" title.
    if iy + 22 + 22 > bot:
        return iy

    iy = _section_header(draw, fonts, alr_clr, ix, iy, iw, 'COVERAGE')

    county = coverage_data.get('county', {})
    if county:
        pct   = float(county.get('coverage_percentage', 0))
        est   = county.get('is_estimated', False)
        row_h = 32
        if iy + row_h <= bot:
            _card_row(draw, ix, iy, iw, row_h)

            # Percentage label
            tag  = ' (est.)' if est else ''
            lbl  = f'{pct:.1f}%{tag} of {county_name}'
            lbl  = _truncate(fonts['small'], lbl, iw - 16)
            draw.text((ix + 8, iy + 4), lbl, font=fonts['small'], fill=_TEXT)

            # Progress bar
            bar_x, bar_y = ix + 8, iy + 21
            bar_w, bar_h = iw - 16, 6
            draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
                                   radius=3, fill=(55, 65, 88))
            fill_w = max(4, int(bar_w * min(pct, 100) / 100))
            draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_w, bar_y + bar_h),
                                   radius=3, fill=_pct_bar_color(pct))
            iy += row_h + 3

    # Service counts row
    svc_parts: List[str] = []
    for stype, sdata in sorted(coverage_data.items()):
        if stype == 'county':
            continue
        affected = int(sdata.get('affected_boundaries', 0) or 0)
        total    = int(sdata.get('total_boundaries',    0) or 0)
        if total > 0:
            svc_parts.append(f'{stype.title()}: {affected}/{total}')

    if svc_parts and iy + 22 <= bot:
        _card_row(draw, ix, iy, iw, 22)
        svc_text = _truncate(fonts['tiny'], '  ·  '.join(svc_parts), iw - 14)
        draw.text((ix + 7, iy + (22 - _th(fonts['tiny'], svc_text)) // 2),
                  svc_text, font=fonts['tiny'], fill=_TEXT_SEC)
        iy += 24

    return iy + 6


def _draw_areas(draw: ImageDraw.ImageDraw, fonts: Dict, alr_clr: Tuple,
                ix: int, iy: int, iw: int, bot: int, alert: Any) -> int:
    area_desc = (getattr(alert, 'area_desc', '') or '').strip()
    if not area_desc or iy + 30 > bot:
        return iy

    iy = _section_header(draw, fonts, alr_clr, ix, iy, iw, 'AFFECTED AREAS')

    # Split on semicolons, clean up, display up to ~3 rows
    segments = [s.strip() for s in area_desc.split(';') if s.strip()]
    font = fonts['small']
    row_h = 21

    # Try to fit all segments on as few rows as possible
    current_line = ''
    for seg in segments:
        candidate = f'{current_line}; {seg}' if current_line else seg
        if _tw(font, candidate) <= iw - 14:
            current_line = candidate
        else:
            if current_line and iy + row_h <= bot:
                _card_row(draw, ix, iy, iw, row_h)
                draw.text((ix + 7, iy + (row_h - _th(font, current_line)) // 2),
                          current_line, font=font, fill=_TEXT)
                iy += row_h + 1
            current_line = seg

    if current_line and iy + row_h <= bot:
        _card_row(draw, ix, iy, iw, row_h)
        line = _truncate(font, current_line, iw - 14)
        draw.text((ix + 7, iy + (row_h - _th(font, line)) // 2),
                  line, font=font, fill=_TEXT)
        iy += row_h + 1

    return iy + 4


def _draw_compass_section(draw: ImageDraw.ImageDraw, fonts: Dict, alr_clr: Tuple,
                          ix: int, iy: int, iw: int, bot: int,
                          ipaws_data: Optional[Dict]) -> int:
    """Draw a circular compass rose with the storm motion arrow + speed/direction text."""
    storm = (ipaws_data or {}).get('storm_motion', {})
    if not storm:
        return iy

    toward_deg    = storm.get('toward_deg')
    direction_deg = storm.get('direction_deg')
    compass_toward = storm.get('compass_toward', '')
    compass_from   = storm.get('compass_from', storm.get('compass', ''))
    speed_mph      = storm.get('speed_mph', '')
    speed_kt       = storm.get('speed_kt', '')

    if toward_deg is None and not compass_toward and not speed_mph:
        return iy

    section_h = 88
    if iy + 22 + section_h + 6 > bot:
        return iy

    iy = _section_header(draw, fonts, alr_clr, ix, iy, iw, 'STORM MOTION')
    draw.rectangle((ix, iy, ix + iw, iy + section_h), fill=_CARD)

    # ── Compass rose ──────────────────────────────────────────────────────────
    r   = 30                   # ring radius
    ccx = ix + r + 16          # compass centre-x
    ccy = iy + section_h // 2  # compass centre-y

    ring_clr = _TEXT_MUT
    draw.ellipse((ccx - r, ccy - r, ccx + r, ccy + r), outline=ring_clr, width=2)

    # Cardinal ticks + labels
    for deg, lbl in [(0, 'N'), (90, 'E'), (180, 'S'), (270, 'W')]:
        ang = math.radians(deg)
        sx  =  math.sin(ang)
        sy  = -math.cos(ang)   # screen y grows downward
        # Tick mark
        draw.line([
            (ccx + int(sx * (r - 6)), ccy + int(sy * (r - 6))),
            (ccx + int(sx * r),       ccy + int(sy * r)),
        ], fill=ring_clr, width=2)
        # Label just outside the ring
        lx = ccx + int(sx * (r + 9))
        ly = ccy + int(sy * (r + 9))
        draw.text((lx - _tw(fonts['tiny'], lbl) // 2,
                   ly - _th(fonts['tiny'], lbl) // 2),
                  lbl, font=fonts['tiny'], fill=ring_clr)

    # Intermediate ticks (45°)
    for deg in [45, 135, 225, 315]:
        ang = math.radians(deg)
        sx, sy = math.sin(ang), -math.cos(ang)
        draw.line([
            (ccx + int(sx * (r - 4)), ccy + int(sy * (r - 4))),
            (ccx + int(sx * r),       ccy + int(sy * r)),
        ], fill=ring_clr, width=1)

    # Directional arrow
    if toward_deg is not None:
        ang = math.radians(toward_deg)
        dx  =  math.sin(ang)
        dy  = -math.cos(ang)

        tip_x = ccx + int(dx * (r - 7))
        tip_y = ccy + int(dy * (r - 7))
        tail_x = ccx - int(dx * int(r * 0.38))
        tail_y = ccy - int(dy * int(r * 0.38))

        draw.line([(tail_x, tail_y), (tip_x, tip_y)], fill=alr_clr, width=3)

        w_ang = 0.45
        hw    = 7
        lw_x = tip_x - int((dx * math.cos( w_ang) - dy * math.sin( w_ang)) * hw)
        lw_y = tip_y - int((dy * math.cos( w_ang) + dx * math.sin( w_ang)) * hw)
        rw_x = tip_x - int((dx * math.cos(-w_ang) - dy * math.sin(-w_ang)) * hw)
        rw_y = tip_y - int((dy * math.cos(-w_ang) + dx * math.sin(-w_ang)) * hw)
        draw.polygon([(tip_x, tip_y), (lw_x, lw_y), (rw_x, rw_y)], fill=alr_clr)

    # Centre dot
    draw.ellipse((ccx - 3, ccy - 3, ccx + 3, ccy + 3), fill=ring_clr)

    # ── Text block to the right of the compass ────────────────────────────────
    tx   = ccx + r + 18
    tw_  = iw - (tx - ix) - 8
    ty   = iy + 10
    lh   = 17

    if compass_toward:
        hstr = f'Heading {compass_toward}'
        if toward_deg is not None:
            hstr += f' ({int(toward_deg)}\u00b0)'
        draw.text((tx, ty), hstr, font=fonts['bold'], fill=_TEXT)
        ty += lh + 2

    if compass_from:
        fstr = f'From {compass_from}'
        if direction_deg is not None:
            fstr += f' ({int(direction_deg)}\u00b0)'
        draw.text((tx, ty), fstr, font=fonts['small'], fill=_TEXT_SEC)
        ty += lh

    if speed_mph:
        sstr = f'{speed_mph} MPH'
        if speed_kt:
            sstr += f'  ({speed_kt} kt)'
        draw.text((tx, ty), sstr, font=fonts['bold'], fill=_TEXT)
        ty += lh + 2

    # Storm position (newest track point)
    track = storm.get('track', [])
    if track:
        try:
            lat, lon = float(track[-1][0]), float(track[-1][1])
            pstr = f'Position: {lat:.2f}, {lon:.2f}'
            draw.text((tx, ty), _truncate(fonts['tiny'], pstr, tw_),
                      font=fonts['tiny'], fill=_TEXT_MUT)
        except (TypeError, IndexError, ValueError):
            pass

    return iy + section_h + 6


def _draw_nws_headline(draw: ImageDraw.ImageDraw, fonts: Dict, alr_clr: Tuple,
                       ix: int, iy: int, iw: int, bot: int,
                       alert: Any, ipaws_data: Optional[Dict]) -> int:
    """Render the NWS operational headline (ALL-CAPS quote block).

    Falls back to alert.headline when nws_headline is absent.
    The alert.description is intentionally omitted — it's too long to
    truncate meaningfully in a social-media image.
    """
    nws_head = (ipaws_data or {}).get('nws_headline', '').strip()
    pub_head = (getattr(alert, 'headline', '') or '').strip()
    text     = nws_head or pub_head

    if not text or iy + 30 > bot:
        return iy

    iy = _section_header(draw, fonts, alr_clr, ix, iy, iw, 'HEADLINE')

    # Word-wrap (leave 10 px for the quote bar on the left)
    font  = fonts['small']
    max_w = iw - 18
    words = text.split()
    lines: List[str] = []
    line  = ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if _tw(font, candidate) <= max_w:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)

    row_h = 19
    for ltext in lines:
        if iy + row_h > bot:
            break
        _card_row(draw, ix, iy, iw, row_h)
        # Coloured quote bar on the left edge
        draw.rectangle((ix, iy, ix + 3, iy + row_h), fill=alr_clr)
        draw.text((ix + 10, iy + (row_h - _th(font, ltext)) // 2),
                  ltext, font=font, fill=_TEXT)
        iy += row_h + 1

    return iy + 4


def _wrap_text(font: ImageFont.FreeTypeFont, text: str,
               max_w: int, max_lines: int = 8) -> List[str]:
    """Word-wrap *text* into lines that fit within *max_w* pixels."""
    words = text.split()
    lines: List[str] = []
    line = ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if _tw(font, candidate) <= max_w:
            line = candidate
        else:
            if line:
                lines.append(line)
                if len(lines) >= max_lines:
                    # Truncate the last line with ellipsis
                    lines[-1] = _truncate(font, lines[-1], max_w)
                    return lines
            line = word
    if line:
        if len(lines) >= max_lines:
            lines[-1] = _truncate(font, lines[-1] + ' ' + line, max_w)
        else:
            lines.append(line)
    return lines


def _draw_description(draw: ImageDraw.ImageDraw, fonts: Dict, alr_clr: Tuple,
                      ix: int, iy: int, iw: int, bot: int,
                      alert: Any) -> int:
    """Render the alert description text (word-wrapped, space-limited)."""
    desc = (getattr(alert, 'description', '') or '').strip()
    if not desc or iy + 30 > bot:
        return iy

    # Clean up NWS description formatting: collapse multiple whitespace,
    # strip leading asterisks/bullets, normalise newlines to spaces.
    desc = re.sub(r'\s*\n\s*', ' ', desc)
    desc = re.sub(r'\s{2,}', ' ', desc)
    desc = re.sub(r'^\*\s*', '', desc)
    desc = desc.strip()

    if not desc:
        return iy

    font = fonts['small']
    row_h = 18
    # Reserve the 22px section header + at least one row before committing.
    if iy + 22 + row_h > bot:
        return iy

    iy = _section_header(draw, fonts, alr_clr, ix, iy, iw, 'DESCRIPTION')

    max_w = iw - 14
    # Fill all remaining vertical space rather than capping at an arbitrary
    # line count — long descriptions previously ended mid-sentence because
    # the cap was 6 lines regardless of how much room was left.
    avail_lines = max(1, (bot - iy) // (row_h + 1))
    lines = _wrap_text(font, desc, max_w, max_lines=avail_lines)

    for ltext in lines:
        if iy + row_h > bot:
            break
        _card_row(draw, ix, iy, iw, row_h)
        draw.text((ix + 7, iy + (row_h - _th(font, ltext)) // 2),
                  ltext, font=font, fill=_TEXT)
        iy += row_h + 1

    return iy + 4


def _draw_instruction(draw: ImageDraw.ImageDraw, fonts: Dict, alr_clr: Tuple,
                      ix: int, iy: int, iw: int, bot: int,
                      alert: Any) -> int:
    """Render safety/action instructions with a caution-coloured accent."""
    instr = (getattr(alert, 'instruction', '') or '').strip()
    if not instr or iy + 30 > bot:
        return iy

    instr = re.sub(r'\s*\n\s*', ' ', instr)
    instr = re.sub(r'\s{2,}', ' ', instr)
    instr = instr.strip()

    if not instr:
        return iy

    font = fonts['small']
    row_h = 18
    if iy + 22 + row_h > bot:
        return iy

    iy = _section_header(draw, fonts, alr_clr, ix, iy, iw, 'INSTRUCTIONS')

    max_w = iw - 18  # leave room for accent bar
    # Fill remaining vertical space instead of capping at 4 lines.
    avail_lines = max(1, (bot - iy) // (row_h + 1))
    lines = _wrap_text(font, instr, max_w, max_lines=avail_lines)

    _INSTR_ACCENT = (255, 193, 7)  # warning-yellow accent bar

    for ltext in lines:
        if iy + row_h > bot:
            break
        _card_row(draw, ix, iy, iw, row_h)
        # Yellow accent bar on the left edge
        draw.rectangle((ix, iy, ix + 3, iy + row_h), fill=_INSTR_ACCENT)
        draw.text((ix + 10, iy + (row_h - _th(font, ltext)) // 2),
                  ltext, font=font, fill=_TEXT)
        iy += row_h + 1

    return iy + 4


__all__ = ['generate_alert_image']
