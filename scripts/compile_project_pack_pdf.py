#!/usr/bin/env python3
"""
Compile docs/01-06 markdown pack into a single PDF.
Output: docs/OpenJobs_Project_Pack.pdf
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT_FILE = DOCS / "OpenJobs_Project_Pack.pdf"

PACK_FILES = [
    ("01", "Product requirements", "01-product-requirements.md"),
    ("02", "Technical requirements", "02-technical-requirements.md"),
    ("03", "Application flow", "03-app-flow.md"),
    ("04", "Design brief", "04-design-brief.md"),
    ("05", "Backend schema", "05-backend-schema.md"),
    ("06", "Implementation plan", "06-implementation-plan.md"),
]

BRAND_PRIMARY = (15, 76, 129)
BRAND_ACCENT = (0, 150, 136)
TEXT_MUTED = (90, 90, 90)


def _ascii(text: str) -> str:
    """FPDF 1.x pages are latin-1; normalize punctuation and drop unsupported chars."""
    text = (
        text.replace("\u2014", " - ")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2192", "->")
        .replace("\u2265", ">=")
        .replace("\u2264", "<=")
        .replace("\u2713", "[x]")
        .replace("\u2610", "[ ]")
    )
    return text.encode("latin-1", errors="replace").decode("latin-1")


class PackPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self._section = ""

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(95, 8, "OpenJobs Project Pack", align="L")
        self.cell(95, 8, _ascii(self._section)[:50], align="R", ln=True)
        self.line(10, 14, 200, 14)
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def cover(self):
        self.add_page()
        self.set_fill_color(*BRAND_PRIMARY)
        self.rect(0, 0, 210, 95, style="F")
        self.set_y(30)
        self.set_font("Helvetica", "B", 30)
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, "OpenJobs", align="C", ln=True)
        self.set_font("Helvetica", "", 14)
        self.cell(0, 8, "Six-document project pack", align="C", ln=True)
        self.ln(48)
        self.set_text_color(30, 30, 30)
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 10, "Product, technical, flow, design, schema, plan", align="C", ln=True)
        self.ln(6)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 6, f"Compiled {date.today().isoformat()}", align="C", ln=True)
        self.ln(12)
        for num, title, _ in PACK_FILES:
            self.cell(0, 7, f"  {num}. {title}", align="C", ln=True)

    def doc_start(self, num: str, title: str):
        self.add_page()
        self._section = title
        self.set_fill_color(*BRAND_ACCENT)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 10, f"  {num}. {title}", ln=True, fill=True)
        self.ln(4)
        self.set_text_color(30, 30, 30)

    def h2(self, text: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*BRAND_PRIMARY)
        self.multi_cell(0, 6, _ascii(text))
        self.set_text_color(30, 30, 30)
        self.ln(1)

    def h3(self, text: str):
        self.set_font("Helvetica", "B", 10)
        self.multi_cell(0, 5.5, _ascii(text))
        self.ln(1)

    def body(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 4.5, _ascii(text))
        self.ln(1)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 4.5, _ascii("  - " + text))


def _parse_markdown_lines(lines: list[str], pdf: PackPDF):
    in_code = False
    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line.strip():
            pdf.ln(2)
            continue
        if line.startswith("# "):
            continue  # doc title skipped (on cover section)
        if line.startswith("## "):
            pdf.h2(line[3:].strip())
        elif line.startswith("### "):
            pdf.h3(line[4:].strip())
        elif line.startswith("|") and "---" not in line:
            pdf.body(line.replace("|", " ").strip())
        elif line.startswith("- ") or line.startswith("* "):
            pdf.bullet(line[2:].strip())
        elif re.match(r"^\d+\.\s", line):
            pdf.bullet(line.strip())
        elif line.startswith("---"):
            pdf.ln(2)
        else:
            pdf.body(line.strip())


def build_pdf() -> Path:
    pdf = PackPDF()
    pdf.cover()
    for num, title, filename in PACK_FILES:
        path = DOCS / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        pdf.doc_start(num, title)
        content = path.read_text(encoding="utf-8")
        _parse_markdown_lines(content.splitlines(), pdf)
    DOCS.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT_FILE))
    return OUT_FILE


def main():
    path = build_pdf()
    print(f"Wrote {path} ({path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
