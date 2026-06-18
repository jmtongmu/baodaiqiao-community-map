#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a simple world file for image-space QGIS review.

The image is placed into a local pixel coordinate plane:
  x = image pixel x
  y = -image pixel y

This is not a geographic registration. It is only for reviewing OCR boxes on
top of the original image without distorting them into modern map coordinates.
"""

from __future__ import annotations

import argparse
from pathlib import Path


WORLD_EXTENSIONS = {
    ".png": ".pgw",
    ".jpg": ".jgw",
    ".jpeg": ".jgw",
    ".tif": ".tfw",
    ".tiff": ".tfw",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    suffix = WORLD_EXTENSIONS.get(args.image.suffix.lower(), ".wld")
    output = args.output or args.image.with_suffix(suffix)
    # Pixel size x, rotation y, rotation x, pixel size y, x center of UL pixel, y center of UL pixel.
    output.write_text("1\n0\n0\n-1\n0.5\n-0.5\n", encoding="ascii")
    print(output)


if __name__ == "__main__":
    main()
