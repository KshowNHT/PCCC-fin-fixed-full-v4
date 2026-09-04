"""PDF generation, using reportlab as the functional counterpart of PDFKit.

Direct port of the PDF-related sections of server.ts:
- generateDocPDFHelper  -> generate_document_pdf
- drawTableRow          -> _draw_table_row
- POST /api/report/export-pdf -> generate_compliance_report_pdf

reportlab's coordinate system has its origin at the bottom-left with y
increasing upward, the opposite of PDFKit's top-left/y-down convention used
in the original code. All positions below are expressed with a `top_y`
helper that flips the axis so the ported coordinates read the same as the
original PDFKit calls.
"""
import io
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.config import BOLD_FONT_PATH, REGULAR_FONT_PATH

PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pt, matches PDFKit's default A4 size

_FONTS_REGISTERED = False


def _ensure_fonts() -> tuple[str, str]:
    """Register the Vietnamese-capable Roboto fonts if present; fallback to Helvetica."""
    global _FONTS_REGISTERED
    has_regular = REGULAR_FONT_PATH.exists()
    has_bold = BOLD_FONT_PATH.exists()

    if not _FONTS_REGISTERED:
        if has_regular:
            pdfmetrics.registerFont(TTFont("Roboto-Regular", str(REGULAR_FONT_PATH)))
        if has_bold:
            pdfmetrics.registerFont(TTFont("Roboto-Bold", str(BOLD_FONT_PATH)))
        _FONTS_REGISTERED = True

    return (
        "Roboto-Regular" if has_regular else "Helvetica",
        "Roboto-Bold" if has_bold else "Helvetica-Bold",
    )


def _top_y(y: float) -> float:
    """Convert a PDFKit-style top-down y coordinate to reportlab's bottom-up y."""
    return PAGE_H - y


def _wrap_text(c: canvas.Canvas, text: str, font: str, size: float, max_width: float) -> List[str]:
    lines: List[str] = []
    for raw_line in str(text).split("\n"):
        words = raw_line.split(" ")
        cur = ""
        for w in words:
            test = f"{cur} {w}".strip()
            if c.stringWidth(test, font, size) <= max_width or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def _height_of_string(c: canvas.Canvas, text: str, font: str, size: float, width: float) -> float:
    lines = _wrap_text(c, text, font, size, width)
    return len(lines) * size * 1.28


def _draw_text_block(
    c: canvas.Canvas, text: str, x: float, y_top: float, font: str, size: float,
    color: str = "#000000", width: float = 495, align: str = "left",
) -> float:
    """Draw wrapped text with a top-left origin; returns the new top_y after the block."""
    c.setFont(font, size)
    c.setFillColor(color)
    lines = _wrap_text(c, text, font, size, width)
    leading = size * 1.28
    cur_top = y_top
    for line in lines:
        draw_y = _top_y(cur_top + size)
        if align == "center":
            c.drawCentredString(x + width / 2, draw_y, line)
        elif align == "right":
            c.drawRightString(x + width, draw_y, line)
        else:
            c.drawString(x, draw_y, line)
        cur_top += leading
    return cur_top


def _draw_continued_text(c: canvas.Canvas, x: float, y_top: float, parts: List[tuple], width: float = 495) -> float:
    """Draw a sequence of (text, font, size, color) runs on one logical wrapped paragraph,
    mirroring PDFKit's `{ continued: true }` inline-run pattern used for label/value pairs."""
    combined = "".join(p[0] for p in parts)
    font, size, color = parts[-1][1], parts[-1][2], parts[-1][3]
    return _draw_text_block(c, combined, x, y_top, font, size, color, width)


def generate_document_pdf(doc: Dict[str, Any]) -> bytes:
    """Port of generateDocPDFHelper: a beautifully styled vector PDF of a legal document."""
    font_reg, font_bold = _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    c.setTitle(doc.get("title", ""))
    c.setAuthor("Chuyên Gia Compliance AI PCCC")

    c.setFont(font_bold, 10)
    c.setFillColor("#ff5722")
    c.drawString(50, _top_y(45 + 10), "HỆ THỐNG THẨM ĐỊNH COMPLIANCE PCCC AI")

    c.setFont(font_reg, 8)
    c.setFillColor("#64748b")
    c.drawString(50, _top_y(57 + 8), "CHUYÊN GIA TỰ ĐỘNG PHÁP LÝ PHÒNG CHÁY CHỮA CHÁY VIỆT NAM")

    c.setStrokeColor("#ff9800")
    c.setLineWidth(1.5)
    c.line(50, _top_y(72), 545, _top_y(72))

    current_y = 90.0

    c.setFont(font_bold, 14)
    c.setFillColor("#0f172a")
    current_y = _draw_text_block(c, doc.get("title", ""), 50, current_y, font_bold, 14, "#0f172a", 495) + 15

    def kv_line(label: str, value: str, value_color: str = "#0f172a") -> None:
        nonlocal current_y
        c.setFont(font_bold, 9.5)
        c.setFillColor("#475569")
        c.drawString(50, _top_y(current_y + 9.5), label)
        label_w = c.stringWidth(label, font_bold, 9.5)
        c.setFont(font_reg, 9.5)
        c.setFillColor(value_color)
        c.drawString(50 + label_w, _top_y(current_y + 9.5), value)
        current_y += 6 + 9.5

    kv_line("Ký hiệu văn bản: ", doc.get("code", ""))
    kv_line("Phân loại quy quy định: ", doc.get("type") or "Tiêu chuẩn / Quy chuẩn Việt Nam")
    kv_line("Nguồn cơ sở dữ liệu: ", "Hệ thống RAG Thư viện Pháp luật PCCC", "#22c55e")
    current_y += 15 - 9.5

    c.setStrokeColor("#cbd5e1")
    c.setLineWidth(0.5)
    c.line(50, _top_y(current_y), 545, _top_y(current_y))
    current_y += 15

    c.setFont(font_bold, 11)
    c.setFillColor("#ff5722")
    c.drawString(50, _top_y(current_y + 11), "NỘI DUNG QUY ĐỊNH CHI TIẾT")
    current_y += 10 + 11

    _draw_text_block(
        c, doc.get("content") or "Chưa có nội dung rà soát chi tiết.",
        50, current_y, font_reg, 9, "#1e293b", 495,
    )

    c.showPage()
    c.save()
    return buf.getvalue()


def _draw_table_row(
    c: canvas.Canvas, y: float, cols: List[float], texts: List[str],
    font_reg: str, font_bold: str, aligns: List[str], is_header: bool = False,
) -> float:
    """Port of drawTableRow: wraps text per-column, computes row height, draws bg/border/text."""
    padding = 6
    size = 8 if is_header else 7.5
    max_height = 20.0

    col_lines: List[List[str]] = []
    for i, text in enumerate(texts):
        col_width = cols[i]
        lines = _wrap_text(c, text, font_reg if not is_header else font_bold, size, col_width - padding * 2)
        col_lines.append(lines)
        text_height = len(lines) * size * 1.28
        if text_height + padding * 2 > max_height:
            max_height = text_height + padding * 2

    headers = ["STT", "HẠNG MỤC", "YÊU CẦU QUY CHUẨN", "KẾT LUẬN CHI TIẾT", "ĐÁNH GIÁ"]

    if y + max_height > 750:
        c.showPage()
        y = 55.0
        c.setFillColor("#1e3a8a")
        c.rect(50, _top_y(y + 20), 495, 20, fill=1, stroke=0)
        current_x = 50.0
        for i, th in enumerate(headers):
            col_width = cols[i]
            c.setFont(font_bold, 8)
            c.setFillColor("#ffffff")
            c.drawString(current_x + padding, _top_y(y + padding + 8), th)
            current_x += col_width
        y += 20

    if is_header:
        c.setFillColor("#1e3a8a")
    else:
        c.setFillColor("#ffffff" if int(y) % 2 == 0 else "#f8fafc")
    c.rect(50, _top_y(y + max_height), 495, max_height, fill=1, stroke=0)

    c.setStrokeColor("#cbd5e1")
    c.setLineWidth(0.5)
    c.rect(50, _top_y(y + max_height), 495, max_height, fill=0, stroke=1)

    current_x = 50.0
    for i, lines in enumerate(col_lines):
        col_width = cols[i]
        align = aligns[i] if i < len(aligns) else "left"
        text = texts[i]

        font = font_bold if is_header else (font_bold if i in (1, 4) else font_reg)
        color = "#ffffff" if is_header else "#1e293b"
        if not is_header and i == 4:
            color = "#16a34a" if text == "Đạt" else ("#dc2626" if text == "Không đạt" else "#d97706")

        c.setFont(font, size)
        c.setFillColor(color)
        for li, line in enumerate(lines):
            draw_y = _top_y(y + padding + size + li * size * 1.28)
            if align == "center":
                c.drawCentredString(current_x + col_width / 2, draw_y, line)
            else:
                c.drawString(current_x + padding, draw_y, line)
        current_x += col_width

    return y + max_height


def generate_compliance_report_pdf(
    project: Dict[str, Any], checklist: List[Dict[str, Any]], conclusions: Dict[str, Any],
) -> bytes:
    """Port of POST /api/report/export-pdf."""
    font_reg, font_bold = _ensure_fonts()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Báo cáo Thẩm định PCCC - {project.get('name', '')}")
    c.setAuthor("Chuyên Gia Compliance AI PCCC")

    c.setFont(font_bold, 10)
    c.setFillColor("#0f172a")
    c.drawCentredString(PAGE_W / 2, _top_y(45 + 10), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    c.setFont(font_bold, 9)
    c.setFillColor("#334155")
    c.drawCentredString(PAGE_W / 2, _top_y(58 + 9), "Độc lập – Tự do – Hạnh phúc")
    c.setStrokeColor("#64748b")
    c.setLineWidth(0.75)
    c.line(220, _top_y(72), 375, _top_y(72))

    c.setFont(font_bold, 14)
    c.setFillColor("#b91c1c")
    c.drawCentredString(PAGE_W / 2, _top_y(95 + 14), "BẢNG TƯ VẤN AN TOÀN PHÒNG CHÁY CHỮA CHÁY")

    c.setFont(font_bold, 10)
    c.setFillColor("#334155")
    title2 = f"{str(project.get('name', '')).upper()} – {project.get('floors', 0)} TẦNG – {project.get('totalFloorArea', 0)}m² SÀN"
    c.drawCentredString(PAGE_W / 2, _top_y(115 + 10), title2)

    today = date.today()
    creation_date = f"Ngày lập: ngày {today.day} tháng {today.month} năm {today.year}"
    c.setFont(font_reg, 8.5)
    c.setFillColor("#64748b")
    c.drawCentredString(PAGE_W / 2, _top_y(130 + 8.5), creation_date)

    current_y = 155.0

    c.setFont(font_bold, 11)
    c.setFillColor("#1e3a8a")
    c.drawString(50, _top_y(current_y + 11), "I. THÔNG TIN CÔNG TRÌNH ĐẦU VÀO")
    current_y += 10 + 11

    fields = [
        ("Tên công trình", project.get("name", "")),
        ("Chủ đầu tư", project.get("investor") or "Chưa cập nhật"),
        ("Địa điểm xây dựng", project.get("location") or "Chưa cập nhật"),
        ("Đơn vị thiết kế / Giai đoạn", f"{project.get('designer') or 'Chưa cập nhật'} / {project.get('stage') or 'Thiết kế cơ sở'}"),
        ("Loại công trình & Công năng", project.get("type", "")),
        ("Quy mô số tầng", f"{project.get('floors', 0)} tầng nổi, {project.get('basements', 0)} tầng hầm"),
        ("Chiều cao PCCC", f"{project.get('pcccHeight') or project.get('height', 0)} m (Chiều cao thực tế: {project.get('height', 0)} m)"),
        ("Bậc chịu lửa dự kiến", project.get("fireRating") or "Bậc III"),
    ]

    for label, val in fields:
        c.setFont(font_bold, 9)
        l_h = _height_of_string(c, label, font_bold, 9, 151)
        v_h = _height_of_string(c, str(val), font_reg, 9, 334)
        cell_h = max(l_h, v_h) + 10

        if current_y + cell_h > 780:
            c.showPage()
            current_y = 55.0

        c.setFillColor("#f1f5f9")
        c.rect(50, _top_y(current_y + cell_h), 155, cell_h, fill=1, stroke=0)
        c.setFillColor("#ffffff")
        c.rect(205, _top_y(current_y + cell_h), 340, cell_h, fill=1, stroke=0)
        c.setStrokeColor("#cbd5e1")
        c.setLineWidth(0.5)
        c.rect(50, _top_y(current_y + cell_h), 495, cell_h, fill=0, stroke=1)

        c.setFillColor("#334155")
        c.setFont(font_bold, 8.5)
        c.drawString(56, _top_y(current_y + 5 + 8.5), label)
        c.setFillColor("#0f172a")
        c.setFont(font_reg, 8.5)
        c.drawString(211, _top_y(current_y + 5 + 8.5), str(val))

        current_y += cell_h

    current_y += 20

    if current_y + 120 > 780:
        c.showPage()
        current_y = 55.0

    c.setFont(font_bold, 11)
    c.setFillColor("#1e3a8a")
    c.drawString(50, _top_y(current_y + 11), "II. KẾT LUẬN VỀ THẨM DUYỆT THIẾT KẾ PCCC")
    current_y += 8 + 11

    law_text = (
        "Căn cứ pháp lý chính: Bộ luật PCCC, Nghị định số 105/2025/NĐ-CP ngày 15/5/2025 - Phụ lục III "
        "(Danh mục dự án, công trình thuộc diện thẩm định thiết kế về phòng cháy và chữa cháy)."
    )
    current_y = _draw_text_block(c, law_text, 50, current_y, font_reg, 9.5, "#1e293b", 495) + 12

    is_no_appraisal = not conclusions.get("isAppraisalRequired")
    appraisal_status = (
        "✓ CÔNG TRÌNH KHÔNG THUỘC DIỆN THẨM DUYỆT THIẾT KẾ PCCC BỞI CƠ QUAN CÔNG AN"
        if is_no_appraisal
        else "✗ CÔNG TRÌNH THUỘC DIỆN THẨM DUYỆT THIẾT KẾ PCCC BẮT BUỘC BỞI CƠ QUAN CÔNG AN"
    )
    c.setFillColor("#ecfdf5" if is_no_appraisal else "#fef2f2")
    c.rect(50, _top_y(current_y + 30), 495, 30, fill=1, stroke=0)
    c.setStrokeColor("#10b981" if is_no_appraisal else "#ef4444")
    c.setLineWidth(0.75)
    c.rect(50, _top_y(current_y + 30), 495, 30, fill=0, stroke=1)
    c.setFont(font_bold, 9)
    c.setFillColor("#065f46" if is_no_appraisal else "#991b1b")
    c.drawString(60, _top_y(current_y + 10 + 9), appraisal_status)
    current_y += 18 + 12

    reason_text = f"Giải trình lý do cụ thể: {conclusions.get('reason', '')}"
    current_y = _draw_text_block(c, reason_text, 50, current_y, font_reg, 9.5, "#1e293b", 495) + 12

    warnings = conclusions.get("warnings") or []
    if warnings:
        c.setFont(font_bold, 9.5)
        c.setFillColor("#b91c1c")
        c.drawString(50, _top_y(current_y + 9.5), "Cảnh báo / Lưu ý bất thường trong hồ sơ:")
        current_y += 5 + 9.5
        for warn in warnings:
            current_y = _draw_text_block(c, f"• {warn}", 50, current_y, font_reg, 9, "#991b1b", 495) + 3
        current_y += 10

    current_y += 15

    if current_y + 100 > 780:
        c.showPage()
        current_y = 55.0

    c.setFont(font_bold, 11)
    c.setFillColor("#1e3a8a")
    c.drawString(50, _top_y(current_y + 11), "III. CHECKLIST TỔNG HỢP KIỂM TRA RÀ SOÁT CHI TIẾT")
    current_y += 10 + 11

    col_widths = [30, 95, 150, 155, 65]
    col_headers = ["STT", "HẠNG MỤC", "YÊU CẦU QUY CHUẨN", "KẾT LUẬN CHI TIẾT", "ĐÁNH GIÁ"]
    col_aligns = ["center", "left", "left", "left", "center"]

    current_y = _draw_table_row(c, current_y, col_widths, col_headers, font_reg, font_bold, col_aligns, True)

    for item in checklist:
        item_texts = [
            str(item.get("stt", "")),
            f"{item.get('criteria', '')}\n({item.get('reference', '')})",
            item.get("requirement", ""),
            item.get("note", ""),
            item.get("result", ""),
        ]
        current_y = _draw_table_row(c, current_y, col_widths, item_texts, font_reg, font_bold, col_aligns, False)

    current_y += 20

    if current_y + 120 > 780:
        c.showPage()
        current_y = 55.0

    c.setFont(font_bold, 11)
    c.setFillColor("#1e3a8a")
    c.drawString(50, _top_y(current_y + 11), "IV. DANH MỤC CĂN CỨ VÀ KÝ XÁC NHẬN TƯ VẤN")
    current_y += 8 + 11

    citations = (
        "Các văn bản đối chiếu đã áp dụng: Nghị định số 105/2025/NĐ-CP; QCVN 06:2022/BXD Sửa đổi 1:2023; "
        "QCVN 10:2025/BCA; TCVN 13456:2022; TCVN 7435-1:2004; TCVN 7568-14:2025."
    )
    current_y = _draw_text_block(c, citations, 50, current_y, font_reg, 8.5, "#475569", 495) + 20

    c.setFont(font_bold, 9.5)
    c.setFillColor("#0f172a")
    c.drawCentredString(330 + 215 / 2, _top_y(current_y + 9.5), "ĐƠN VỊ TƯ VẤN THẨM ĐỊNH PCCC AI")
    c.setFont(font_reg, 8.5)
    c.setFillColor("#64748b")
    c.drawCentredString(330 + 215 / 2, _top_y(current_y + 3 + 8.5 + 12), "(Ký và ghi rõ họ tên, đóng dấu sản phẩm)")

    c.showPage()
    c.save()
    return buf.getvalue()
