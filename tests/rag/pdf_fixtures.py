"""
Minimal PDF builders for extraction tests.

These construct valid PDFs from raw syntax rather than shipping binary blobs, so
every byte under test is reviewable and no extra dependency is needed to author
fixtures.

RTL note: real PDF generators emit right-to-left runs in *visual* order, and
pypdf reverses them to recover logical order. `build_persian_pdf` therefore
writes glyph codes in visual order so the fixture behaves like a real Persian
PDF rather than a synthetic one.
"""

from __future__ import annotations

PDF_HEADER = b"%PDF-1.4\n"


def _assemble(objects: dict[int, str], *, info_id: int | None = None) -> bytes:
    out = bytearray(PDF_HEADER)
    offsets: dict[int, int] = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(out)
        out += f"{object_id} 0 obj\n{objects[object_id]}\nendobj\n".encode()

    xref_offset = len(out)
    max_id = max(objects)
    out += f"xref\n0 {max_id + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for object_id in range(1, max_id + 1):
        if object_id in offsets:
            out += f"{offsets[object_id]:010d} 00000 n \n".encode()
        else:
            # Object ids need not be contiguous; unused slots are free entries.
            out += b"0000000000 65535 f \n"

    trailer = f"<< /Size {max_id + 1} /Root 1 0 R"
    if info_id is not None:
        trailer += f" /Info {info_id} 0 R"
    trailer += " >>"
    out += f"trailer\n{trailer}\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    return bytes(out)


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")


def _pdf_string(text: str) -> str:
    """
    Encode a PDF text string.

    Literal `(...)` strings are PDFDocEncoded, which cannot represent Persian, so
    non-ASCII values use a UTF-16BE hex string with a BOM as the PDF spec requires.
    """
    if text.isascii():
        return f"({_escape(text)})"
    encoded = text.encode("utf-16-be").hex().upper()
    return f"<FEFF{encoded}>"


def build_pdf(pages: list[str], *, title: str | None = None) -> bytes:
    """Build a Latin-text PDF with one content stream per page."""
    page_ids = [4 + index * 2 for index in range(len(pages))]
    content_ids = [5 + index * 2 for index in range(len(pages))]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)

    objects: dict[int, str] = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>",
        3: "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, text in enumerate(pages):
        objects[page_ids[index]] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_ids[index]} 0 R "
            "/Resources << /Font << /F1 3 0 R >> >> >>"
        )
        stream = f"BT /F1 12 Tf 72 720 Td ({_escape(text)}) Tj ET" if text else ""
        objects[content_ids[index]] = (
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"
        )

    info_id = None
    if title is not None:
        info_id = max(objects) + 1
        objects[info_id] = f"<< /Title {_pdf_string(title)} >>"
    return _assemble(objects, info_id=info_id)


def build_persian_pdf(pages: list[str]) -> bytes:
    """
    Build a PDF carrying Persian text via Identity-H plus a ToUnicode CMap.

    Glyph codes are written in visual order to match real-world RTL PDFs.
    """
    page_ids = [10 + index * 3 for index in range(len(pages))]
    content_ids = [11 + index * 3 for index in range(len(pages))]
    cmap_ids = [12 + index * 3 for index in range(len(pages))]
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)

    objects: dict[int, str] = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>",
    }
    for index, text in enumerate(pages):
        distinct = list(dict.fromkeys(text))
        bfchars = "\n".join(f"<{ord(ch):04X}> <{ord(ch):04X}>" for ch in distinct)
        cmap = (
            "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
            "/CMapName /Custom def\n/CMapType 2 def\n"
            "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
            f"{len(distinct)} beginbfchar\n{bfchars}\nendbfchar\n"
            "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend"
        )
        codes = "".join(f"{ord(ch):04X}" for ch in reversed(text))
        stream = f"BT /F1 12 Tf 72 720 Td <{codes}> Tj ET" if text else ""

        objects[page_ids[index]] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_ids[index]} 0 R "
            "/Resources << /Font << /F1 3 0 R >> >> >>"
        )
        objects[content_ids[index]] = (
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"
        )
        objects[cmap_ids[index]] = (
            f"<< /Length {len(cmap)} >>\nstream\n{cmap}\nendstream"
        )

    first_cmap = cmap_ids[0]
    objects[3] = (
        "<< /Type /Font /Subtype /Type0 /BaseFont /Noto /Encoding /Identity-H "
        f"/DescendantFonts [4 0 R] /ToUnicode {first_cmap} 0 R >>"
    )
    objects[4] = (
        "<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Noto "
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
        "/DW 1000 >>"
    )
    return _assemble(objects)


def build_corrupt_pdf() -> bytes:
    """Correct magic bytes, unparseable body."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 9 0 R\nthis is not a pdf"


def build_encrypted_pdf() -> bytes:
    """A PDF whose trailer declares encryption."""
    objects = {
        1: "<< /Type /Catalog /Pages 2 0 R >>",
        2: "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>",
        4: "<< /Filter /Standard /V 1 /R 2 /O (0000000000000000) "
        "/U (0000000000000000) /P -1 >>",
    }
    out = bytearray(PDF_HEADER)
    offsets: dict[int, int] = {}
    for object_id in sorted(objects):
        offsets[object_id] = len(out)
        out += f"{object_id} 0 obj\n{objects[object_id]}\nendobj\n".encode()
    xref_offset = len(out)
    max_id = max(objects)
    out += f"xref\n0 {max_id + 1}\n".encode() + b"0000000000 65535 f \n"
    for object_id in range(1, max_id + 1):
        out += f"{offsets[object_id]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {max_id + 1} /Root 1 0 R /Encrypt 4 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    return bytes(out)


def build_image_only_pdf() -> bytes:
    """A structurally valid PDF with pages but no text operators."""
    return build_pdf(["", ""])
