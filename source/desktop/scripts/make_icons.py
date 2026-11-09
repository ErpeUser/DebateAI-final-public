"""Regenerate platform containers from the committed Backchannel mark.

``desktop/assets/icon.png`` is the canonical generated brand asset.  This
script only derives the Windows and macOS containers; it deliberately does
not redraw or restyle the mark.
"""

from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "assets"

def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    source_path = ASSETS / "icon.png"
    with Image.open(source_path) as source:
        mark = source.convert("RGB")
        mark.load()

    mark.resize((256, 256), Image.Resampling.LANCZOS).save(
        ASSETS / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)],
    )
    mark.resize((1024, 1024), Image.Resampling.LANCZOS).save(ASSETS / "icon.icns")

    for name in ("icon.png", "icon.ico", "icon.icns"):
        with Image.open(ASSETS / name) as check:
            check.load()
            print(f"{name}: {check.format} {check.size}")


if __name__ == "__main__":
    main()
