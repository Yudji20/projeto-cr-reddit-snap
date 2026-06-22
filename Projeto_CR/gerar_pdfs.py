from pathlib import Path
import textwrap


ROOT = Path(__file__).resolve().parent
PAGE_W, PAGE_H = 595, 842
LEFT, TOP, BOTTOM = 54, 790, 54
LINE_H = 14


def pdf_escape(text):
    data = text.encode("cp1252", errors="replace")
    out = []
    for byte in data:
        if byte in (40, 41, 92):
            out.append("\\" + chr(byte))
        elif byte < 32 or byte > 126:
            out.append("\\" + format(byte, "03o"))
        else:
            out.append(chr(byte))
    return "".join(out)


def wrap_text(text, width=92):
    if not text:
        return [""]
    return textwrap.wrap(text, width=width, break_long_words=False) or [""]


def markdown_to_lines(markdown):
    lines = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            lines.append(("title", line[2:].strip()))
            lines.append(("space", ""))
        elif line.startswith("## "):
            lines.append(("heading", line[3:].strip()))
        elif line.startswith("- "):
            for idx, wrapped in enumerate(wrap_text(line[2:].strip(), 86)):
                prefix = "- " if idx == 0 else "  "
                lines.append(("body", prefix + wrapped))
        elif line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if all(set(cell) <= {"-", " "} for cell in cells):
                continue
            joined = " | ".join(cells)
            for wrapped in wrap_text(joined, 82):
                lines.append(("body", wrapped))
        elif line.startswith("**") and line.endswith("**"):
            lines.append(("heading", line.strip("*").strip()))
        elif line == "":
            lines.append(("space", ""))
        else:
            cleaned = line.replace("**", "")
            for wrapped in wrap_text(cleaned, 92):
                lines.append(("body", wrapped))
    return lines


def build_pdf(lines, output_path):
    pages = []
    y = TOP
    current = []

    def new_page():
        nonlocal y, current
        if current:
            pages.append(current)
        current = []
        y = TOP

    for style, text in lines:
        if style == "space":
            y -= LINE_H // 2
            if y < BOTTOM:
                new_page()
            continue
        if y < BOTTOM + 18:
            new_page()
        if style == "title":
            size = 16
            font = "F2"
            step = 20
        elif style == "heading":
            size = 13
            font = "F2"
            step = 18
        else:
            size = 10
            font = "F1"
            step = LINE_H
        current.append((font, size, LEFT, y, text))
        y -= step
    if current:
        pages.append(current)

    objects = []

    def add(obj):
        objects.append(obj)
        return len(objects)

    catalog_id = add("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add("")
    font_regular_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>")
    font_bold_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>")
    page_ids = []

    for page in pages:
        commands = []
        for font, size, x, y_pos, text in page:
            commands.append(f"BT /{font} {size} Tf {x} {y_pos} Td ({pdf_escape(text)}) Tj ET")
        stream = "\n".join(commands).encode("latin1")
        content_id = add(f"<< /Length {len(stream)} >>\nstream\n" + stream.decode("latin1") + "\nendstream")
        page_id = add(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{' '.join(str(pid) + ' 0 R' for pid in page_ids)}] /Count {len(page_ids)} >>"

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("latin1"))
        pdf.extend(obj.encode("latin1"))
        pdf.extend(b"\nendobj\n")
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin1"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("latin1")
    )
    output_path.write_bytes(pdf)


def main():
    docs = [
        ("Cronograma_Projeto_Reddit_SNAP.md", "Cronograma_Projeto_Reddit_SNAP.pdf"),
        ("Proposta_Revisada_RedeReddit_SNAP.md", "Proposta_Revisada_RedeReddit_SNAP.pdf"),
    ]
    for source_name, pdf_name in docs:
        markdown = (ROOT / source_name).read_text(encoding="utf-8")
        lines = markdown_to_lines(markdown)
        build_pdf(lines, ROOT / pdf_name)
        print(f"Gerado: {ROOT / pdf_name}")


if __name__ == "__main__":
    main()
