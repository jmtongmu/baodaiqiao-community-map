from __future__ import annotations

import argparse
import re
import zlib
from pathlib import Path


STREAM_RE = re.compile(rb"(?<!end)stream\r?\n")
LENGTH_RE = re.compile(rb"/Length\s+(\d+)")
BFCHAR_RE = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
TEXT_BLOCK_RE = re.compile(rb"BT(.*?)ET", re.S)
HEX_TEXT_RE = re.compile(rb"<([0-9A-Fa-f]+)>")
LITERAL_TEXT_RE = re.compile(rb"\((.*?)\)", re.S)


def iter_streams(pdf: bytes):
    for match in STREAM_RE.finditer(pdf):
        start = match.end()
        header = pdf[max(0, match.start() - 800) : match.start()]
        lengths = LENGTH_RE.findall(header)
        if lengths:
            length = int(lengths[-1])
            data = pdf[start : start + length]
        else:
            end = pdf.find(b"endstream", start)
            if end < 0:
                continue
            data = pdf[start:end].strip(b"\r\n")
        if b"/FlateDecode" in header:
            try:
                data = zlib.decompress(data)
            except zlib.error:
                continue
        yield header, data


def is_page_text_stream(header: bytes, data: bytes) -> bool:
    if b"/Subtype /Image" in header or b"/FontFile" in header:
        return False
    if b"BT" not in data or b"ET" not in data:
        return False
    if b"Tj" not in data and b"TJ" not in data:
        return False
    # Image/font streams can contain accidental BT/ET byte sequences.
    if len(data) > 250_000:
        return False
    return True


def parse_cmaps(streams) -> dict[int, str]:
    mapping: dict[int, str] = {}
    for _header, data in streams:
        if b"beginbfchar" not in data:
            continue
        for src, dst in BFCHAR_RE.findall(data):
            try:
                code = int(src, 16)
                chars = bytes.fromhex(dst.decode("ascii")).decode("utf-16-be")
            except Exception:
                continue
            mapping[code] = chars
    return mapping


def decode_hex_text(hex_bytes: bytes, cmap: dict[int, str]) -> str:
    if len(hex_bytes) % 4 == 0:
        width = 4
    elif len(hex_bytes) % 2 == 0:
        width = 2
    else:
        return ""
    out = []
    text = hex_bytes.decode("ascii", errors="ignore")
    for i in range(0, len(text), width):
        part = text[i : i + width]
        try:
            code = int(part, 16)
        except ValueError:
            continue
        if code in cmap:
            out.append(cmap[code])
        elif 32 <= code <= 126:
            out.append(chr(code))
    return "".join(out)


def decode_literal_text(raw: bytes) -> str:
    raw = raw.replace(rb"\(", b"(").replace(rb"\)", b")")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin1", errors="ignore")


def extract_text(streams, cmap: dict[int, str]) -> str:
    pages: list[str] = []
    for header, data in streams:
        if not is_page_text_stream(header, data):
            continue
        chunks: list[str] = []
        for block in TEXT_BLOCK_RE.findall(data):
            block_text: list[str] = []
            for hex_value in HEX_TEXT_RE.findall(block):
                decoded = decode_hex_text(hex_value, cmap)
                if decoded:
                    block_text.append(decoded)
            for literal in LITERAL_TEXT_RE.findall(block):
                decoded = decode_literal_text(literal)
                if decoded:
                    block_text.append(decoded)
            if block_text:
                chunks.append("".join(block_text))
        if chunks:
            pages.append("\n".join(chunks))
    return "\n\n".join(pages)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--text-out", required=True)
    parser.add_argument("--years-out")
    args = parser.parse_args()

    pdf = Path(args.pdf).read_bytes()
    streams = list(iter_streams(pdf))
    cmap = parse_cmaps(streams)
    text = extract_text(streams, cmap)
    Path(args.text_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.text_out).write_text(text, encoding="utf-8")

    if args.years_out:
        year_re = re.compile(r"(?<!\d)(?:1[89]\d{2}|20\d{2})(?!\d)")
        lines = []
        for line in text.splitlines():
            cleaned = re.sub(r"\s+", "", line)
            if year_re.search(cleaned):
                lines.append(cleaned)
        Path(args.years_out).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
