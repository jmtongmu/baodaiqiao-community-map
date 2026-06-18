#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run RapidOCR on a historical map and keep results in image coordinates.

The output is intentionally image-space OCR data. It preserves the layout of
the source map and does not attempt to georeference text into modern map
coordinates.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR


CJK_RE = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
SOURCE_TERM_RE = re.compile(
    r"[街巷坊弄路橋桥河湖港堤塘門门城府署局倉仓营營兵寺廟庙院觀观山"
    r"井巷市橋桥池園园巖岩]"
)
PUNCT_RE = re.compile(r"[\s·•,.;:!?，。；：！？、|/\\_\-—~`'\"“”‘’()\[\]{}<>《》]+")
PLACE_SUFFIX_CHARS = set("街巷坊弄路橋桥河湖港堤塘門门城府署局倉仓营營兵寺廟庙院觀观山")


@dataclass(frozen=True)
class Variant:
    name: str
    image: np.ndarray
    scale: float
    tile_size: int
    overlap: int
    source_path: Path | None


def read_image_any(path: Path) -> np.ndarray:
    data = np.frombuffer(path.read_bytes(), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"cannot read image: {path}")
    return image


def write_image_any(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(path.suffix or ".png", image)
    if not ok:
        raise RuntimeError(f"cannot encode image: {path}")
    path.write_bytes(encoded.tobytes())


def clean_text(text: str) -> str:
    text = text.strip()
    text = PUNCT_RE.sub("", text)
    return text


def cjk_count(text: str) -> int:
    return len(CJK_RE.findall(text))


def has_source_term(text: str) -> bool:
    return bool(SOURCE_TERM_RE.search(text))


def normalize_reading_order(text: str) -> tuple[str, str]:
    """Return a human-readable label while preserving raw OCR elsewhere.

    Many labels on the source map are physically printed right-to-left or in a
    direction that OCR reads in reverse. A common signal is a place-type suffix
    appearing as the first character: 巷坊井百 should be read as 百井坊巷.
    """

    if len(text) >= 2 and text[0] in PLACE_SUFFIX_CHARS and text[-1] not in PLACE_SUFFIX_CHARS:
        return text[::-1], "reverse_suffix_first"
    return text, "as_detected"


def infer_category(text: str) -> str:
    if re.search(r"[街巷坊弄路橋桥]", text):
        return "ocr_街巷道路"
    if re.search(r"[河湖港堤塘池井]", text):
        return "ocr_水系"
    if re.search(r"[門门城府署局倉仓营營兵]", text):
        return "ocr_城防官署"
    if re.search(r"[寺廟庙院觀观]", text):
        return "ocr_寺观"
    if re.search(r"[山巖岩]", text):
        return "ocr_山体"
    return "ocr_文字"


def box_to_bbox(points: list[list[float]]) -> list[float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def bbox_area(bbox: list[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def bbox_iou(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    denom = bbox_area(a) + bbox_area(b) - inter
    return inter / denom if denom else 0.0


def center_distance(a: list[float], b: list[float]) -> float:
    acx = (a[0] + a[2]) / 2.0
    acy = (a[1] + a[3]) / 2.0
    bcx = (b[0] + b[2]) / 2.0
    bcy = (b[1] + b[3]) / 2.0
    return math.hypot(acx - bcx, acy - bcy)


def orientation_for_quad(points: list[list[float]]) -> str:
    top = math.hypot(points[1][0] - points[0][0], points[1][1] - points[0][1])
    right = math.hypot(points[2][0] - points[1][0], points[2][1] - points[1][1])
    angle = math.degrees(math.atan2(points[1][1] - points[0][1], points[1][0] - points[0][0]))
    abs_angle = abs(((angle + 90) % 180) - 90)
    if right > top * 1.35:
        return "vertical"
    if abs_angle > 15:
        return "diagonal"
    return "horizontal"


def build_preprocessed_variants(
    map_id: str,
    image: np.ndarray,
    preprocess_dir: Path,
    names: list[str],
) -> list[Variant]:
    variants: list[Variant] = []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def add_variant(name: str, out: np.ndarray, scale: float, tile_size: int, overlap: int) -> None:
        path = preprocess_dir / f"{map_id}_{name}.png"
        write_image_any(path, out)
        variants.append(
            Variant(
                name=name,
                image=cv2.cvtColor(out, cv2.COLOR_GRAY2BGR) if len(out.shape) == 2 else out,
                scale=scale,
                tile_size=tile_size,
                overlap=overlap,
                source_path=path,
            )
        )

    if "original" in names:
        variants.append(
            Variant(
                name="original",
                image=image,
                scale=1.0,
                tile_size=900,
                overlap=150,
                source_path=None,
            )
        )

    scale = 3
    if "gray3x_sharp" in names:
        gray3 = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        blur = cv2.GaussianBlur(gray3, (0, 0), 1.0)
        sharp = cv2.addWeighted(gray3, 1.7, blur, -0.7, 0)
        add_variant("gray3x_sharp", sharp, float(scale), 1400, 220)

    if "adaptive3x" in names:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        clahe3 = cv2.resize(clahe, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        clahe3 = cv2.GaussianBlur(clahe3, (3, 3), 0)
        adaptive = cv2.adaptiveThreshold(
            clahe3,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            41,
            13,
        )
        add_variant("adaptive3x", adaptive, float(scale), 1400, 220)

    if "darkmask3x" in names:
        mask = cv2.inRange(gray, 0, 165)
        mask = cv2.medianBlur(mask, 3)
        mask3 = cv2.resize(255 - mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        add_variant("darkmask3x", mask3, float(scale), 1400, 220)

    return variants


def tile_offsets(width: int, height: int, tile_size: int, overlap: int) -> list[tuple[int, int, int, int]]:
    if width <= tile_size and height <= tile_size:
        return [(0, 0, width, height)]
    stride = max(1, tile_size - overlap)

    def starts(length: int) -> list[int]:
        values = list(range(0, max(1, length - tile_size + 1), stride))
        last = max(0, length - tile_size)
        if values[-1] != last:
            values.append(last)
        return values

    offsets = []
    for y in starts(height):
        for x in starts(width):
            offsets.append((x, y, min(width, x + tile_size), min(height, y + tile_size)))
    return offsets


def result_to_candidate(
    *,
    map_id: str,
    source_image: Path,
    image_width: int,
    image_height: int,
    variant: Variant,
    pass_name: str,
    item: list[Any],
    tile_x: int,
    tile_y: int,
    index: int,
    min_conf: float,
) -> dict[str, Any] | None:
    if len(item) < 3:
        return None
    raw_points, raw_text, raw_conf = item[:3]
    detected_text = clean_text(str(raw_text or ""))
    if not detected_text:
        return None
    text, reading_rule = normalize_reading_order(detected_text)
    try:
        confidence = float(raw_conf)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < min_conf:
        return None
    if not CJK_RE.search(text):
        return None
    # Keep short labels only when they contain map-place semantics.
    if cjk_count(text) < 2 and not has_source_term(text):
        return None

    points: list[list[float]] = []
    for point in raw_points:
        x = (float(point[0]) + tile_x) / variant.scale
        y = (float(point[1]) + tile_y) / variant.scale
        x = max(0.0, min(float(image_width), x))
        y = max(0.0, min(float(image_height), y))
        points.append([round(x, 2), round(y, 2)])
    bbox = box_to_bbox(points)
    area = bbox_area(bbox)
    if area < 20 or area > image_width * image_height * 0.08:
        return None
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    if width < 3 or height < 3:
        return None

    term_bonus = 0.08 if has_source_term(text) or has_source_term(detected_text) else 0.0
    length_bonus = min(cjk_count(text), 6) * 0.01
    tile_bonus = 0.03 if pass_name == "tile" else 0.0
    quality = confidence + term_bonus + length_bonus + tile_bonus
    return {
        "ocr_id": f"{map_id}_rapidocr_raw_{index:05d}",
        "text": text,
        "ocr_text_raw_order": detected_text,
        "reading_rule": reading_rule,
        "raw_text": str(raw_text or ""),
        "bbox_pixel": [round(v, 2) for v in bbox],
        "quad_pixel": points,
        "confidence": round(confidence, 6),
        "quality": round(quality, 6),
        "orientation": orientation_for_quad(points),
        "category": infer_category(text),
        "source_map": source_image.name,
        "source_stage": f"rapidocr_{variant.name}_{pass_name}",
        "engine": "rapidocr-onnxruntime",
        "ocr_variant": variant.name,
        "ocr_pass": pass_name,
        "scale": variant.scale,
        "tile_x": round(tile_x / variant.scale, 2),
        "tile_y": round(tile_y / variant.scale, 2),
        "text_len": cjk_count(text),
        "reference_logic": "原图像素坐标；未做现代地图锚定",
        "notes": "",
    }


def run_ocr_variant(
    ocr: RapidOCR,
    *,
    map_id: str,
    source_image: Path,
    image_width: int,
    image_height: int,
    variant: Variant,
    include_full: bool,
    include_tiles: bool,
    min_conf: float,
    start_index: int,
) -> tuple[list[dict[str, Any]], int]:
    candidates: list[dict[str, Any]] = []
    index = start_index

    def consume(pass_name: str, image: np.ndarray, tile_x: int, tile_y: int) -> None:
        nonlocal index
        result, _ = ocr(image)
        if not result:
            return
        for item in result:
            index += 1
            candidate = result_to_candidate(
                map_id=map_id,
                source_image=source_image,
                image_width=image_width,
                image_height=image_height,
                variant=variant,
                pass_name=pass_name,
                item=item,
                tile_x=tile_x,
                tile_y=tile_y,
                index=index,
                min_conf=min_conf,
            )
            if candidate:
                candidates.append(candidate)

    if include_full:
        consume("full", variant.image, 0, 0)

    if include_tiles:
        height, width = variant.image.shape[:2]
        offsets = tile_offsets(width, height, variant.tile_size, variant.overlap)
        for tile_index, (x1, y1, x2, y2) in enumerate(offsets, start=1):
            tile = variant.image[y1:y2, x1:x2]
            consume("tile", tile, x1, y1)
            if tile_index % 5 == 0:
                print(f"  {variant.name}: processed {tile_index}/{len(offsets)} tiles", flush=True)

    return candidates, index


def same_place(a: dict[str, Any], b: dict[str, Any], iou_threshold: float) -> bool:
    bbox_a = a["bbox_pixel"]
    bbox_b = b["bbox_pixel"]
    iou = bbox_iou(bbox_a, bbox_b)
    if iou >= iou_threshold:
        return True
    if iou > 0.25 and (a["text"] == b["text"] or has_source_term(a["text"]) == has_source_term(b["text"])):
        return True
    diag = math.sqrt(max(bbox_area(bbox_a), bbox_area(bbox_b)))
    if diag > 0 and center_distance(bbox_a, bbox_b) < max(8.0, diag * 0.18):
        aw = bbox_a[2] - bbox_a[0]
        ah = bbox_a[3] - bbox_a[1]
        bw = bbox_b[2] - bbox_b[0]
        bh = bbox_b[3] - bbox_b[1]
        if abs(aw - bw) <= max(12.0, 0.45 * max(aw, bw)) and abs(ah - bh) <= max(12.0, 0.45 * max(ah, bh)):
            return True
    return False


def dedupe_candidates(candidates: list[dict[str, Any]], iou_threshold: float) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: item["quality"], reverse=True):
        duplicate = None
        for existing in kept:
            if same_place(candidate, existing, iou_threshold):
                duplicate = existing
                break
        if duplicate is None:
            kept.append(candidate)
            continue
        alternatives = duplicate.setdefault("alternatives", [])
        alternatives.append(
            {
                "text": candidate["text"],
                "confidence": candidate["confidence"],
                "quality": candidate["quality"],
                "source_stage": candidate["source_stage"],
                "bbox_pixel": candidate["bbox_pixel"],
            }
        )

    for index, candidate in enumerate(kept, start=1):
        candidate["ocr_id"] = f"{candidate['source_map'].split('.')[0]}_rapidocr_{index:04d}"
        if candidate.get("alternatives"):
            texts = []
            for alt in sorted(candidate["alternatives"], key=lambda item: item["quality"], reverse=True):
                if alt["text"] != candidate["text"] and alt["text"] not in texts:
                    texts.append(alt["text"])
            candidate["alternative_texts"] = " | ".join(texts[:8])
            candidate["alternative_count"] = len(candidate["alternatives"])
        else:
            candidate["alternative_texts"] = ""
            candidate["alternative_count"] = 0
    kept.sort(key=lambda item: (item["bbox_pixel"][1], item["bbox_pixel"][0]))
    return kept


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-id", default="1937")
    parser.add_argument("--image", type=Path, default=Path("assets/maps/1937.jpg"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--preprocess-dir", type=Path, default=Path("data/ocr/preprocessed"))
    parser.add_argument(
        "--variants",
        default="original,gray3x_sharp,adaptive3x",
        help="Comma-separated variants: original, gray3x_sharp, adaptive3x, darkmask3x",
    )
    parser.add_argument("--min-conf", type=float, default=0.48)
    parser.add_argument("--dedupe-iou", type=float, default=0.48)
    parser.add_argument("--no-full", action="store_true")
    parser.add_argument("--no-tiles", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output is None:
        args.output = Path("data/ocr") / f"{args.map_id}_rapidocr_text_candidates.json"
    if args.raw_output is None:
        args.raw_output = Path("data/ocr") / f"{args.map_id}_rapidocr_raw_candidates.json"
    image_path = args.image
    if not image_path.exists():
        print(f"missing image: {image_path}", file=sys.stderr)
        return 2

    image = read_image_any(image_path)
    image_height, image_width = image.shape[:2]
    variant_names = [name.strip() for name in args.variants.split(",") if name.strip()]
    variants = build_preprocessed_variants(args.map_id, image, args.preprocess_dir, variant_names)
    print(f"loaded {image_path} ({image_width}x{image_height}), variants={','.join(v.name for v in variants)}", flush=True)

    ocr = RapidOCR()
    raw_candidates: list[dict[str, Any]] = []
    index = 0
    for variant in variants:
        print(f"running RapidOCR: {variant.name}", flush=True)
        variant_candidates, index = run_ocr_variant(
            ocr,
            map_id=args.map_id,
            source_image=image_path,
            image_width=image_width,
            image_height=image_height,
            variant=variant,
            include_full=not args.no_full,
            include_tiles=not args.no_tiles,
            min_conf=args.min_conf,
            start_index=index,
        )
        raw_candidates.extend(variant_candidates)
        print(f"  {variant.name}: kept raw candidates {len(variant_candidates)}", flush=True)

    deduped = dedupe_candidates(raw_candidates, args.dedupe_iou)
    metadata = {
        "map_id": args.map_id,
        "source_map": image_path.as_posix(),
        "image_width": image_width,
        "image_height": image_height,
        "engine": "rapidocr-onnxruntime",
        "coordinate_space": "image_pixel",
        "note": "OCR candidates are in original image pixel coordinates and are not georeferenced.",
        "raw_candidate_count": len(raw_candidates),
        "candidate_count": len(deduped),
        "variants": [variant.name for variant in variants],
    }
    raw_payload = {**metadata, "candidates": raw_candidates}
    payload = {**metadata, "candidates": deduped}
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote raw candidates: {len(raw_candidates)} -> {args.raw_output}")
    print(f"wrote deduped candidates: {len(deduped)} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
