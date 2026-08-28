#!/usr/bin/env python3
"""Render a reproducible PDF evidence crop and write a provenance manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import sys


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def unit_float(value: str) -> float:
    parsed = float(value)
    if not 0.0 < parsed < 1.0:
        raise argparse.ArgumentTypeError("must be greater than 0 and less than 1")
    return parsed


def hex_color(value: str) -> str:
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) is None:
        raise argparse.ArgumentTypeError("must be a color in #RRGGBB form")
    return value.upper()


def rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )


def tool_version(executable: str) -> str:
    result = run_checked([executable, "-v"])
    text = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    return text.splitlines()[0] if text else "unknown"


def pdf_page_count(pdfinfo: str, pdf: Path) -> int:
    result = run_checked([pdfinfo, str(pdf)])
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    if match is None:
        raise RuntimeError("pdfinfo output did not contain a Pages field")
    return int(match.group(1))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="input PDF")
    parser.add_argument("--page", type=positive_int, required=True, help="one-based PDF page")
    parser.add_argument("--output", type=Path, required=True, help="output PNG path")
    parser.add_argument("--dpi", type=positive_int, default=220, help="render resolution")
    parser.add_argument(
        "--crop",
        nargs=4,
        type=nonnegative_int,
        metavar=("X", "Y", "WIDTH", "HEIGHT"),
        help="pixel crop at the requested DPI; width and height must be positive",
    )
    parser.add_argument(
        "--highlight",
        nargs=4,
        action="append",
        type=nonnegative_int,
        metavar=("X", "Y", "WIDTH", "HEIGHT"),
        help="repeatable highlight rectangle in output-image pixel coordinates",
    )
    parser.add_argument(
        "--highlight-fill",
        type=hex_color,
        default="#C4B5FD",
        help="highlight fill color; default: #C4B5FD",
    )
    parser.add_argument(
        "--highlight-alpha",
        type=unit_float,
        default=0.28,
        help="highlight fill opacity; default: 0.28",
    )
    parser.add_argument(
        "--highlight-border",
        type=hex_color,
        default="#8B5CF6",
        help="highlight border color; default: #8B5CF6",
    )
    parser.add_argument(
        "--highlight-border-width",
        type=positive_int,
        default=4,
        help="highlight border width in pixels; default: 4",
    )
    parser.add_argument("--paper-id", required=True, help="versioned arXiv ID or DOI")
    parser.add_argument("--source-url", required=True, help="URL used to obtain the PDF")
    parser.add_argument("--retrieved-date", required=True, help="retrieval date in YYYY-MM-DD")
    parser.add_argument("--manifest", type=Path, help="JSON path; defaults beside output")
    parser.add_argument("--overwrite", action="store_true", help="replace existing outputs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf = args.pdf.expanduser().resolve()
    output = args.output.expanduser().resolve()
    manifest = (
        args.manifest.expanduser().resolve()
        if args.manifest
        else output.with_suffix(".json")
    )

    if not pdf.is_file():
        raise FileNotFoundError(f"PDF does not exist: {pdf}")
    if output.suffix.lower() != ".png":
        raise ValueError("--output must end in .png")
    if output == manifest:
        raise ValueError("image and manifest paths must differ")
    datetime.strptime(args.retrieved_date, "%Y-%m-%d")

    if args.crop and (args.crop[2] <= 0 or args.crop[3] <= 0):
        raise ValueError("crop width and height must be positive")
    if args.highlight:
        for rectangle in args.highlight:
            if rectangle[2] <= 0 or rectangle[3] <= 0:
                raise ValueError("highlight width and height must be positive")

    raw_output = (
        output.with_name(f"{output.stem}.raw.png") if args.highlight else output
    )

    candidate_outputs = {output, manifest, raw_output}
    existing = [path for path in candidate_outputs if path.exists()]
    if existing and not args.overwrite:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"refusing to overwrite existing output: {joined}")

    pdfinfo = shutil.which("pdfinfo")
    pdftoppm = shutil.which("pdftoppm")
    if pdfinfo is None or pdftoppm is None:
        missing = [
            name
            for name, executable in (("pdfinfo", pdfinfo), ("pdftoppm", pdftoppm))
            if executable is None
        ]
        raise RuntimeError(f"required Poppler tool(s) missing: {', '.join(missing)}")

    pages = pdf_page_count(pdfinfo, pdf)
    if args.page > pages:
        raise ValueError(f"page {args.page} exceeds PDF page count {pages}")

    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    prefix = raw_output.with_suffix("")
    command = [
        pdftoppm,
        "-f",
        str(args.page),
        "-l",
        str(args.page),
        "-singlefile",
        "-r",
        str(args.dpi),
    ]
    if args.crop:
        x, y, width, height = args.crop
        command.extend(
            ["-x", str(x), "-y", str(y), "-W", str(width), "-H", str(height)]
        )
    command.extend(["-png", str(pdf), str(prefix)])
    run_checked(command)

    if not raw_output.is_file() or raw_output.stat().st_size == 0:
        raise RuntimeError(f"renderer did not create a non-empty image: {raw_output}")

    if args.highlight:
        try:
            from PIL import Image, ImageDraw
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "Pillow is required when --highlight is used; install it in the "
                "active project environment"
            ) from error

        with Image.open(raw_output) as source_image:
            annotated = source_image.convert("RGB")
        image_width, image_height = annotated.size
        drawing = ImageDraw.Draw(annotated, "RGBA")
        fill = (*rgb(args.highlight_fill), round(255 * args.highlight_alpha))
        border = (*rgb(args.highlight_border), 255)
        for x, y, width, height in args.highlight:
            if x + width > image_width or y + height > image_height:
                raise ValueError(
                    "highlight rectangle exceeds rendered image bounds: "
                    f"{[x, y, width, height]} vs {[image_width, image_height]}"
                )
            drawing.rectangle(
                (x, y, x + width - 1, y + height - 1),
                fill=fill,
                outline=border,
                width=args.highlight_border_width,
            )
        annotated.save(output, format="PNG")

    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"no non-empty final evidence image was created: {output}")

    record = {
        "schema_version": 2,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "paper": {
            "identifier": args.paper_id,
            "pdf_url": args.source_url,
            "retrieved_date": args.retrieved_date,
            "pdf_filename": pdf.name,
            "pdf_sha256": sha256(pdf),
            "pdf_pages": pages,
        },
        "render": {
            "renderer": tool_version(pdftoppm),
            "page_one_based": args.page,
            "dpi": args.dpi,
            "crop_xywh_pixels": list(args.crop) if args.crop else None,
            "output_filename": output.name,
            "output_sha256": sha256(output),
            "raw_output_filename": raw_output.name if args.highlight else None,
            "raw_output_sha256": sha256(raw_output) if args.highlight else None,
            "annotation": {
                "rectangles_xywh_pixels": args.highlight,
                "fill_hex": args.highlight_fill,
                "fill_alpha": args.highlight_alpha,
                "border_hex": args.highlight_border,
                "border_width_pixels": args.highlight_border_width,
            }
            if args.highlight
            else None,
        },
    }
    manifest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(output)
    print(manifest)
    if args.highlight:
        print(f"unannotated crop: {raw_output}")
    print(f"![Highlighted PDF evidence: {args.paper_id}, page {args.page}]({output})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
