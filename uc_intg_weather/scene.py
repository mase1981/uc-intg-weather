"""
Dynamic weather scene renderer.

Draws a 480x420 JPEG "weather card" for the media player artwork: a sky that
follows the time of day, the sun or moon (with its real phase) moving along an
arc between sunrise and sunset, weather layers (clouds, rain, snow, hail, fog,
lightning) and the temperature. The Remote only supports static JPG/PNG artwork
(core-api: entity_media_player.md, "Media images"), so the scene is redrawn
whenever its inputs change instead of being animated.

:copyright: (c) 2025 by Meir Miyara.
:license: MPL-2.0, see LICENSE for more details.
"""

from __future__ import annotations

import io
import math
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Remote 3 media player artwork box (remote-ui deviceclass/*.qml): full page width
# (480) by width - 60, filled with PreserveAspectCrop + AlignTop. A square image
# loses its bottom, so render at the box ratio. The Remote Two box is square and
# crops the sides instead: keep text and the strip inside SAFE_X of each edge.
WIDTH = 480
HEIGHT = 420
SAFE_X = 40
JPEG_QUALITY = 85

_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_FONT_REGULAR = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
_FONT_BOLD = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")

# Known new moon (2000-01-06 18:14 UTC) and synodic month length in days.
_NEW_MOON_REF = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
_SYNODIC_MONTH = 29.530588853

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

# Text size steps. "normal" keeps the original layout; larger steps enlarge the
# text and drop lower-priority detail so everything stays readable in the box.
TEXT_NORMAL = "normal"
TEXT_LARGE = "large"
TEXT_XLARGE = "xlarge"
TEXT_SIZES = (TEXT_NORMAL, TEXT_LARGE, TEXT_XLARGE)

# Forecast card slots shown per text size: (hourly, daily).
CARD_SLOTS = {TEXT_NORMAL: (6, 5), TEXT_LARGE: (4, 4), TEXT_XLARGE: (3, 3)}


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# ----------------------------------------------------------------------
# Scene description
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Condition:
    """Visual layers derived from an Open-Meteo weather code."""

    clouds: float = 0.0  # 0 = none, 1 = full cover
    dark_clouds: bool = False
    rain: int = 0  # number of rain streaks
    freezing: bool = False
    snow: int = 0  # number of snowflakes
    hail: int = 0  # number of hail stones
    fog: bool = False
    lightning: bool = False
    overcast: bool = False  # hides sun/moon and greys the sky


def condition_for_code(code: int) -> Condition:
    """Map an Open-Meteo WMO weather code to scene layers."""
    if code in (0,):
        return Condition()
    if code == 1:
        return Condition(clouds=0.25)
    if code == 2:
        return Condition(clouds=0.55)
    if code == 3:
        return Condition(clouds=1.1, overcast=True)
    if code in (45, 48):
        return Condition(clouds=0.6, fog=True, overcast=True)
    if code in (51, 53, 55):
        return Condition(clouds=1.0, rain=35 + (code - 51) * 10, overcast=True)
    if code in (56, 57):
        return Condition(clouds=1.0, rain=45, freezing=True, overcast=True)
    if code in (61, 80):
        return Condition(clouds=1.0, rain=60, overcast=True)
    if code in (63, 81):
        return Condition(clouds=1.2, dark_clouds=True, rain=100, overcast=True)
    if code in (65, 82):
        return Condition(clouds=1.4, dark_clouds=True, rain=150, overcast=True)
    if code in (66, 67):
        return Condition(clouds=1.2, dark_clouds=True, rain=90, freezing=True, overcast=True)
    if code in (71, 85):
        return Condition(clouds=1.0, snow=45, overcast=True)
    if code in (73, 86):
        return Condition(clouds=1.1, snow=80, overcast=True)
    if code in (75, 77):
        return Condition(clouds=1.3, snow=120, overcast=True)
    if code in (87, 88):
        return Condition(clouds=1.3, dark_clouds=True, rain=50, hail=40, overcast=True)
    if code == 95:
        return Condition(clouds=1.6, dark_clouds=True, rain=130, lightning=True, overcast=True)
    if code in (96, 99):
        return Condition(
            clouds=1.6, dark_clouds=True, rain=110, hail=35, lightning=True, overcast=True
        )
    return Condition(clouds=0.8)


@dataclass(frozen=True)
class SceneSpec:
    """Everything needed to draw one card. Equal specs produce equal images."""

    weather_code: int
    is_day: bool
    temperature: str  # already formatted, e.g. "18°"
    description: str
    subtitle: str
    sky_position: float | None = None  # 0..1 along the day (or night) arc
    golden: bool = False  # near sunrise / sunset
    moon_phase: float = 0.5  # 0 = new, 0.5 = full
    southern: bool = False  # mirror the moon for the southern hemisphere
    strip_temps: tuple[float, ...] = field(default_factory=tuple)
    strip_pops: tuple[int, ...] = field(default_factory=tuple)
    strip_label: str = ""
    info_line: str = ""  # small extra line, e.g. feels like / wind / UV
    wind: float = 0.0  # 0 = calm, 1 = very windy (streaks and slanted rain)
    twilight: bool = False  # blue hour just after sunset / before sunrise
    text_size: str = TEXT_NORMAL


# ----------------------------------------------------------------------
# Astronomy helpers
# ----------------------------------------------------------------------
def moon_phase(when: datetime) -> float:
    """Return the moon phase in [0, 1): 0 = new moon, 0.5 = full moon."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    days = (when - _NEW_MOON_REF).total_seconds() / 86400.0
    return (days / _SYNODIC_MONTH) % 1.0


# ----------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------
_SKY_DAY = ((38, 108, 210), (140, 196, 246))
_SKY_GOLDEN = ((72, 62, 142), (250, 152, 82))
_SKY_NIGHT = ((8, 12, 35), (30, 40, 86))
_SKY_TWILIGHT = ((22, 28, 78), (118, 84, 150))
_SKY_OVERCAST_DAY = ((96, 106, 122), (162, 170, 180))
_SKY_OVERCAST_NIGHT = ((18, 20, 30), (48, 52, 66))
_SKY_STORM = ((30, 25, 50), (76, 70, 96))


def _lerp(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _sky(spec: SceneSpec, cond: Condition) -> Image.Image:
    if cond.lightning:
        top, bottom = _SKY_STORM
    elif not spec.is_day:
        if cond.overcast:
            top, bottom = _SKY_OVERCAST_NIGHT
        else:
            top, bottom = _SKY_TWILIGHT if spec.twilight else _SKY_NIGHT
    elif spec.golden and not cond.overcast:
        top, bottom = _SKY_GOLDEN
    elif cond.overcast:
        top, bottom = _SKY_OVERCAST_DAY
        if cond.dark_clouds:
            top, bottom = _lerp(top, (0, 0, 0), 0.25), _lerp(bottom, (0, 0, 0), 0.25)
    else:
        top, bottom = _SKY_DAY

    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        draw.line([(0, y), (WIDTH, y)], fill=_lerp(top, bottom, y / HEIGHT))
    return img.convert("RGBA")


def _glow(img: Image.Image, xy: tuple[float, float], radius: float, color, blur: float) -> None:
    layer = Image.new("RGBA", img.size, color[:3] + (0,))
    ImageDraw.Draw(layer).ellipse(
        [xy[0] - radius, xy[1] - radius, xy[0] + radius, xy[1] + radius], fill=color
    )
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def _arc_point(position: float) -> tuple[float, float]:
    x = SAFE_X + 20 + position * (WIDTH - 2 * (SAFE_X + 20))
    y = 200 - math.sin(position * math.pi) * 135
    return x, y


def _sun(img: Image.Image, position: float) -> None:
    x, y = _arc_point(position)
    _glow(img, (x, y), 62, (255, 220, 120, 120), 26)
    _glow(img, (x, y), 30, (255, 241, 182, 255), 3)


def _moon(img: Image.Image, position: float, phase: float, southern: bool) -> None:
    x, y = _arc_point(position)
    radius = 26
    _glow(img, (x, y), 42, (200, 210, 255, 70), 16)

    # Shadowed disc, then the lit part row by row (terminator is an ellipse).
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(60, 66, 90, 140))
    k = math.cos(2 * math.pi * phase)
    waxing = phase < 0.5
    if southern:
        waxing = not waxing
    for dy in range(-radius, radius + 1):
        half = math.sqrt(max(0.0, radius * radius - dy * dy))
        if waxing:
            left, right = k * half, half
        else:
            left, right = -half, -k * half
        if right - left > 0.5:
            draw.line([(x + left, y + dy), (x + right, y + dy)], fill=(242, 242, 226, 255))
    img.alpha_composite(layer)


def _stars(img: Image.Image, rnd: random.Random, count: int) -> None:
    draw = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rnd.randrange(WIDTH), rnd.randrange(230)
        draw.point((x, y), fill=(255, 255, 255, rnd.randrange(90, 255)))


def _clouds(img: Image.Image, rnd: random.Random, density: float, dark: bool) -> None:
    base = (88, 90, 104) if dark else (244, 246, 252)
    layer = Image.new("RGBA", img.size, base + (0,))
    draw = ImageDraw.Draw(layer)
    alpha = int(150 * min(1.0, density))
    for _ in range(max(1, int(6 * density))):
        cx, cy = rnd.randrange(-40, WIDTH + 40), rnd.randrange(35, 210)
        for _ in range(5):
            w, h = rnd.randrange(60, 130), rnd.randrange(35, 65)
            ox, oy = rnd.randrange(-55, 55), rnd.randrange(-14, 14)
            draw.ellipse([cx + ox - w, cy + oy - h, cx + ox + w, cy + oy + h], fill=base + (alpha,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(13)))


def _rain(img: Image.Image, rnd: random.Random, count: int, freezing: bool, wind: float) -> None:
    color = (210, 235, 255, 170) if freezing else (190, 215, 255, 150)
    slant = 5 + 12 * wind
    draw = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rnd.randrange(WIDTH), rnd.randrange(HEIGHT)
        draw.line([(x, y), (x - slant, y + 16)], fill=color, width=2)


def _wind(img: Image.Image, rnd: random.Random, strength: float) -> None:
    layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(int(4 + 10 * strength)):
        x, y = rnd.randrange(-80, WIDTH), rnd.randrange(30, 230)
        length = rnd.randrange(60, 160)
        bend = rnd.randrange(-8, 8)
        draw.line(
            [(x, y), (x + length * 0.6, y + bend), (x + length, y + bend // 2)],
            fill=(255, 255, 255, int(70 + 80 * strength)), width=2, joint="curve",
        )
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1)))


def _snow(img: Image.Image, rnd: random.Random, count: int) -> None:
    draw = ImageDraw.Draw(img)
    for _ in range(count):
        r = rnd.choice((2, 2, 3, 4))
        x, y = rnd.randrange(WIDTH), rnd.randrange(HEIGHT)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 220))


def _hail(img: Image.Image, rnd: random.Random, count: int) -> None:
    draw = ImageDraw.Draw(img)
    for _ in range(count):
        r = rnd.choice((3, 4, 5))
        x, y = rnd.randrange(WIDTH), rnd.randrange(HEIGHT)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(230, 240, 255, 235), outline=(160, 180, 210, 255))


def _fog(img: Image.Image) -> None:
    layer = Image.new("RGBA", img.size, (235, 235, 240, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(110, 270, 30):
        draw.rectangle([0, y, WIDTH, y + 12], fill=(235, 235, 240, 110))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(7)))


def _lightning(img: Image.Image, rnd: random.Random) -> None:
    x = rnd.randrange(170, 300)
    points = [(x, 95), (x - 28, 170), (x - 2, 170), (x - 40, 255)]
    draw = ImageDraw.Draw(img)
    for width, alpha in ((13, 60), (6, 140), (3, 255)):
        draw.line(points, fill=(255, 250, 200, alpha), width=width, joint="curve")


def _text(img: Image.Image, spec: SceneSpec) -> None:
    if spec.text_size != TEXT_NORMAL:
        _text_large(img, spec)
        return

    shade = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    for y in range(215, HEIGHT):
        shade_draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, int(175 * (y - 215) / (HEIGHT - 215))))
    img.alpha_composite(shade)

    draw = ImageDraw.Draw(img)
    text_width = WIDTH - 2 * SAFE_X
    draw.text((SAFE_X - 2, 232), spec.temperature, font=_font(_FONT_BOLD, 80), fill="white")
    draw.text(
        (SAFE_X, 322), _fit(spec.description, _FONT_BOLD, 24, text_width), font=_font(_FONT_BOLD, 24), fill="white"
    )
    draw.text(
        (SAFE_X, 356), _fit(spec.subtitle, _FONT_REGULAR, 17, text_width), font=_font(_FONT_REGULAR, 17),
        fill=(222, 226, 236),
    )
    if spec.info_line:
        draw.text(
            (SAFE_X, 383), _fit(spec.info_line, _FONT_REGULAR, 15, text_width),
            font=_font(_FONT_REGULAR, 15), fill=(196, 204, 218),
        )


# Large text: (temperature, description, subtitle) font sizes; laid out bottom-up.
_LARGE_TEXT = {TEXT_LARGE: (104, 31, 21), TEXT_XLARGE: (126, 36, 24)}
_BOTTOM_MARGIN = 16


def _text_height(font: ImageFont.FreeTypeFont, text: str = "Hg°") -> tuple[int, int]:
    """Return (top offset, height) of the drawn glyphs for vertical layout."""
    left, top, right, bottom = font.getbbox(text)
    return top, bottom - top


def _text_large(img: Image.Image, spec: SceneSpec) -> None:
    """Large / extra large layout: stack subtitle, description, temperature upwards."""
    temp_size, desc_size, sub_size = _LARGE_TEXT[spec.text_size]
    text_width = WIDTH - 2 * SAFE_X
    temp_font = _font(_FONT_BOLD, temp_size)
    desc_font = _font(_FONT_BOLD, desc_size)
    sub_font = _font(_FONT_REGULAR, sub_size)

    sub_top, sub_h = _text_height(sub_font)
    desc_top, desc_h = _text_height(desc_font)
    temp_top, temp_h = _text_height(temp_font, spec.temperature or "0°")

    sub_y = HEIGHT - _BOTTOM_MARGIN - sub_h
    desc_y = sub_y - 10 - desc_h
    temp_y = desc_y - 14 - temp_h

    shade_start = max(0, temp_y - 30)
    shade = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shade_draw = ImageDraw.Draw(shade)
    for y in range(shade_start, HEIGHT):
        shade_draw.line(
            [(0, y), (WIDTH, y)], fill=(0, 0, 0, int(190 * (y - shade_start) / (HEIGHT - shade_start)))
        )
    img.alpha_composite(shade)

    draw = ImageDraw.Draw(img)
    draw.text((SAFE_X - 3, temp_y - temp_top), spec.temperature, font=temp_font, fill="white")
    draw.text(
        (SAFE_X, desc_y - desc_top), _fit(spec.description, _FONT_BOLD, desc_size, text_width),
        font=desc_font, fill="white",
    )
    draw.text(
        (SAFE_X, sub_y - sub_top), _fit(spec.subtitle, _FONT_REGULAR, sub_size, text_width),
        font=sub_font, fill=(226, 230, 240),
    )

    # The 6-hour strip only stays if it fits beside the temperature.
    if spec.text_size == TEXT_LARGE and len(spec.strip_temps) >= 2:
        temp_right = SAFE_X + temp_font.getlength(spec.temperature)
        x1 = WIDTH - SAFE_X - 4
        x0 = max(x1 - 150, temp_right + 24)
        if x1 - x0 >= 110:
            _draw_strip(img, spec, x0, x1, temp_y, desc_y - 12)


def _fit(text: str, font_path: str, size: int, max_width: int) -> str:
    font = _font(font_path, size)
    if font.getlength(text) <= max_width:
        return text
    while text and font.getlength(text + "…") > max_width:
        text = text[:-1]
    return text.rstrip() + "…"


def _draw_strip(img: Image.Image, spec: SceneSpec, x0: float, x1: float, top: float, bottom: float) -> None:
    """Strip for the large layout, fitted into the given box."""
    temps, pops = spec.strip_temps, spec.strip_pops
    draw = ImageDraw.Draw(img)
    label_font = _font(_FONT_REGULAR, 15)
    line_top = top + 22
    bar_bottom = bottom
    line_h = max(20.0, (bar_bottom - line_top) * 0.45)
    lo, hi = min(temps), max(temps)
    step = (x1 - x0) / (len(temps) - 1)
    points = [
        (x0 + i * step, line_top + line_h - (t - lo) / max(1.0, hi - lo) * line_h) for i, t in enumerate(temps)
    ]
    bar_max = max(10.0, bar_bottom - (line_top + line_h) - 10)
    for i, pop in enumerate(pops[: len(temps)]):
        height = max(2.0, pop / 100 * bar_max)
        x = x0 + i * step
        draw.rectangle([x - 6, bar_bottom - height, x + 6, bar_bottom], fill=(120, 180, 255, 210))
    draw.line(points, fill=(255, 210, 120), width=4, joint="curve")
    for px, py in points:
        draw.ellipse([px - 4.5, py - 4.5, px + 4.5, py + 4.5], fill="white")
    if spec.strip_label:
        draw.text((x1 - label_font.getlength(spec.strip_label), top), spec.strip_label, font=label_font, fill=(215, 220, 230))


def _strip(img: Image.Image, spec: SceneSpec) -> None:
    if spec.text_size != TEXT_NORMAL:
        return  # drawn by _text_large when it fits
    temps, pops = spec.strip_temps, spec.strip_pops
    if len(temps) < 2:
        return
    draw = ImageDraw.Draw(img)
    x1 = WIDTH - SAFE_X - 4
    x0, y0 = x1 - 150, 250
    lo, hi = min(temps), max(temps)
    step = (x1 - x0) / (len(temps) - 1)
    points = [
        (x0 + i * step, y0 + 42 - (t - lo) / max(1.0, hi - lo) * 42) for i, t in enumerate(temps)
    ]
    for i, pop in enumerate(pops[: len(temps)]):
        height = max(2.0, pop / 100 * 30)
        x = x0 + i * step
        draw.rectangle([x - 5, 320 - height, x + 5, 320], fill=(120, 180, 255, 210))
    draw.line(points, fill=(255, 210, 120), width=3, joint="curve")
    for px, py in points:
        draw.ellipse([px - 3.5, py - 3.5, px + 3.5, py + 3.5], fill="white")
    if spec.strip_label:
        font = _font(_FONT_REGULAR, 13)
        draw.text((x1 - font.getlength(spec.strip_label), 226), spec.strip_label, font=font, fill=(205, 210, 220))


def render(spec: SceneSpec) -> bytes:
    """Render a scene and return JPEG bytes."""
    cond = condition_for_code(spec.weather_code)
    # Stable layout per condition so redraws only change what actually moved.
    rnd = random.Random(f"{spec.weather_code}-{int(spec.is_day)}")

    img = _sky(spec, cond)

    if not spec.is_day and not cond.overcast:
        _stars(img, rnd, 30 if spec.twilight else 70)

    if spec.sky_position is not None and not cond.overcast:
        if spec.is_day:
            _sun(img, spec.sky_position)
        else:
            _moon(img, spec.sky_position, spec.moon_phase, spec.southern)

    if cond.clouds:
        _clouds(img, rnd, cond.clouds, cond.dark_clouds or not spec.is_day)
    if cond.fog:
        _fog(img)
    if spec.wind >= 0.25:
        _wind(img, rnd, spec.wind)
    if cond.lightning:
        _lightning(img, rnd)
    if cond.rain:
        _rain(img, rnd, cond.rain, cond.freezing, spec.wind)
    if cond.hail:
        _hail(img, rnd, cond.hail)
    if cond.snow:
        _snow(img, rnd, cond.snow)

    _text(img, spec)
    _strip(img, spec)

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()


# ----------------------------------------------------------------------
# Forecast overview cards (several slots on one image)
# ----------------------------------------------------------------------
# The Remote UI keeps decoded artwork for at most 12 media players
# (remote-ui src/ui/mediaImageProvider.h, m_maxEntries = 12) and evicts the
# least recently updated one, leaving that tile blank. One card per forecast
# range instead of one image per slot keeps the weather footprint small.
_ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
_icon_cache: dict[tuple[str, int], Image.Image] = {}


@dataclass(frozen=True)
class ForecastSlot:
    """One column of a forecast card."""

    label: str  # "6 PM" / "Sat"
    icon: str  # icon file name from the icons folder
    primary: str  # "18°", or the high for a day
    precipitation: int  # chance in percent
    secondary: str = ""  # the low for a day, drawn under the primary value


@dataclass(frozen=True)
class ForecastCardSpec:
    """A row of forecast slots drawn over the current sky."""

    title: str
    subtitle: str
    slots: tuple[ForecastSlot, ...]
    selected: int = 0
    weather_code: int = 0  # sky background follows the current conditions
    is_day: bool = True
    golden: bool = False
    twilight: bool = False
    text_size: str = TEXT_NORMAL


# Card font sizes: title, subtitle, slot label, icon, primary, secondary, rain %.
_CARD_SIZES = {
    TEXT_NORMAL: (26, 16, 17, 64, 22, 17, 14),
    TEXT_LARGE: (30, 19, 23, 78, 31, 23, 18),
    TEXT_XLARGE: (34, 21, 27, 92, 38, 27, 21),
}


def _icon(name: str, size: int) -> Image.Image | None:
    key = (name, size)
    if key not in _icon_cache:
        path = os.path.join(_ICON_DIR, name)
        if not os.path.exists(path):
            path = os.path.join(_ICON_DIR, "cloud.png")
        try:
            with Image.open(path) as src:
                _icon_cache[key] = src.convert("RGBA").resize((size, size), Image.LANCZOS)
        except OSError:
            return None
    return _icon_cache[key]


def render_forecast_card(spec: ForecastCardSpec) -> bytes:
    """Render a forecast overview card and return JPEG bytes."""
    background = SceneSpec(
        weather_code=spec.weather_code,
        is_day=spec.is_day,
        temperature="",
        description="",
        subtitle="",
        golden=spec.golden,
        twilight=spec.twilight,
    )
    img = _sky(background, condition_for_code(spec.weather_code))

    # Darken for contrast so every slot stays readable on any sky.
    shade = Image.new("RGBA", img.size, (0, 0, 0, 110))
    img.alpha_composite(shade)

    title_size, subtitle_size, label_size, icon_max, primary_max, secondary_size, pop_size = _CARD_SIZES.get(
        spec.text_size, _CARD_SIZES[TEXT_NORMAL]
    )
    draw = ImageDraw.Draw(img)
    text_width = WIDTH - 2 * SAFE_X
    title_font = _font(_FONT_BOLD, title_size)
    subtitle_font = _font(_FONT_REGULAR, subtitle_size)
    title_y = 28
    subtitle_y = 62 if spec.text_size == TEXT_NORMAL else title_y + _text_height(title_font)[1] + 10
    draw.text((SAFE_X, title_y), _fit(spec.title, _FONT_BOLD, title_size, text_width), font=title_font, fill="white")
    draw.text(
        (SAFE_X, subtitle_y), _fit(spec.subtitle, _FONT_REGULAR, subtitle_size, text_width),
        font=subtitle_font, fill=(214, 220, 232),
    )

    count = max(1, len(spec.slots))
    column = text_width / count
    top = max(108, subtitle_y + _text_height(subtitle_font)[1] + 24)
    bottom = 392
    icon_size = int(min(icon_max, column - 10))
    label_font = _font(_FONT_BOLD, label_size)
    secondary_font = _font(_FONT_REGULAR, secondary_size)
    pop_font = _font(_FONT_REGULAR, pop_size)
    has_secondary = any(slot.secondary for slot in spec.slots)

    # Vertical layout from the top of the slot down; the rain bar takes what is left.
    label_y = top + 14
    icon_y = label_y + _text_height(label_font)[1] + 14
    primary_y = icon_y + icon_size + (6 if has_secondary else 14)
    primary_h = _text_height(_font(_FONT_BOLD, primary_max))[1]
    secondary_y = primary_y + primary_h + 8
    values_bottom = secondary_y + (_text_height(secondary_font)[1] if has_secondary else -8)
    pop_h = _text_height(pop_font, "0%")[1]
    bar_top = values_bottom + 16
    bar_bottom = bottom - pop_h - 22
    bar_half = 9
    pop_y = bottom - pop_h - 14
    if spec.text_size == TEXT_NORMAL:
        # Keep the original 3.5.0 layout exactly.
        icon_y = top + 50
        primary_y = top + (122 if has_secondary else 132)
        secondary_y = primary_y + 28
        bar_top, bar_bottom = top + 180, top + 240
        bar_half = 7
        pop_y = bar_bottom + 8

    for index, slot in enumerate(spec.slots):
        x0 = SAFE_X + index * column
        center = x0 + column / 2

        if index == spec.selected:
            panel = Image.new("RGBA", img.size, (255, 255, 255, 0))
            ImageDraw.Draw(panel).rounded_rectangle(
                [x0 + 3, top, x0 + column - 3, bottom], radius=14, fill=(255, 255, 255, 46),
                outline=(255, 255, 255, 150), width=2,
            )
            img.alpha_composite(panel)
            draw = ImageDraw.Draw(img)

        label = _fit(slot.label, _FONT_BOLD, label_size, int(column - 6))
        draw.text((center - label_font.getlength(label) / 2, label_y), label, font=label_font, fill="white")

        icon = _icon(slot.icon, icon_size)
        if icon is not None:
            img.alpha_composite(icon, (int(center - icon_size / 2), int(icon_y)))
            draw = ImageDraw.Draw(img)

        # Shrink rather than truncate so every value stays complete.
        primary_size = primary_max
        while primary_size > 12 and _font(_FONT_BOLD, primary_size).getlength(slot.primary) > column - 6:
            primary_size -= 1
        primary_font = _font(_FONT_BOLD, primary_size)
        shrink = 0 if spec.text_size == TEXT_NORMAL else (primary_max - primary_size) // 2
        draw.text(
            (center - primary_font.getlength(slot.primary) / 2, primary_y + shrink),
            slot.primary, font=primary_font, fill="white",
        )
        if slot.secondary:
            draw.text(
                (center - secondary_font.getlength(slot.secondary) / 2, secondary_y), slot.secondary,
                font=secondary_font, fill=(196, 206, 222),
            )

        # Rain chance: small bar plus percentage.
        if bar_bottom - bar_top >= 36:
            bar_height = max(2.0, (bar_bottom - bar_top) * max(0, min(100, slot.precipitation)) / 100)
            bars = Image.new("RGBA", img.size, (255, 255, 255, 0))
            bars_draw = ImageDraw.Draw(bars)
            bars_draw.rounded_rectangle(
                [center - bar_half, bar_top, center + bar_half, bar_bottom], radius=4, fill=(255, 255, 255, 45)
            )
            bars_draw.rounded_rectangle(
                [center - bar_half, bar_bottom - bar_height, center + bar_half, bar_bottom], radius=4,
                fill=(120, 180, 255, 235),
            )
            img.alpha_composite(bars)
            draw = ImageDraw.Draw(img)
        pop = f"{slot.precipitation}%"
        draw.text((center - pop_font.getlength(pop) / 2, pop_y), pop, font=pop_font, fill=(196, 214, 240))

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()
