"""Generate the opaque maskable PWA icons from the canonical brand mark.

The maskable variant uses the install theme colour as its real background and
keeps the mark inside the circular safe area required by the manifest. The
desktop asset remains the single source of the mark; this script only derives
the web containers.
"""

from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "desktop" / "assets" / "icon.png"
TARGET = ROOT / "public" / "icons"
BACKGROUND = (0x0F, 0x17, 0x2A)
BACKGROUND_TOLERANCE = 12
SAFE_DIAMETER = 0.56


def _background_transparent(source: Image.Image) -> Image.Image:
    """Remove only the border-connected source background.

    Flood filling is intentional: the black checkmark inside the white bubble
    is part of the mark and must not be mistaken for the outer background.
    """

    image = source.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    background = pixels[0, 0][:3]
    seen = bytearray(width * height)
    queue = deque([(0, 0)])

    def matches(x: int, y: int) -> bool:
        red, green, blue, _ = pixels[x, y]
        return max(
            abs(red - background[0]),
            abs(green - background[1]),
            abs(blue - background[2]),
        ) <= BACKGROUND_TOLERANCE

    while queue:
        x, y = queue.popleft()
        index = y * width + x
        if seen[index] or not matches(x, y):
            continue
        seen[index] = 1
        pixels[x, y] = (*pixels[x, y][:3], 0)
        if x:
            queue.append((x - 1, y))
        if x + 1 < width:
            queue.append((x + 1, y))
        if y:
            queue.append((x, y - 1))
        if y + 1 < height:
            queue.append((x, y + 1))

    return image


def _mark(source: Image.Image) -> Image.Image:
    alpha = source.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError("canonical icon contains no visible mark")
    left, top, right, bottom = bbox
    padding = 2
    return source.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(source.width, right + padding),
            min(source.height, bottom + padding),
        )
    )


def _write(mark: Image.Image, size: int, path: Path) -> None:
    longest = max(mark.size)
    scaled = mark.resize(
        (round(mark.width * size * SAFE_DIAMETER / longest),
         round(mark.height * size * SAFE_DIAMETER / longest)),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGB", (size, size), BACKGROUND)
    x = (size - scaled.width) // 2
    y = (size - scaled.height) // 2
    canvas.paste(scaled, (x, y), scaled)
    canvas.save(path, format="PNG", optimize=True)


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    mark = _mark(_background_transparent(Image.open(SOURCE)))
    for size in (192, 512):
        _write(mark, size, TARGET / f"icon-maskable-{size}.png")
        print(f"icon-maskable-{size}.png: {size}x{size}")


if __name__ == "__main__":
    main()
