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


def generate_compliance_report_pdf(project: Dict[str, Any], checklist: List[Dict[str, Any]], conclusions: Dict[str, Any]) -> bytes:
    """Paginated report: long Vietnamese input, table rows and reasons must wrap."""
    from html import escape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    font, bold = _ensure_fonts()
    buf = io.BytesIO()
    style = ParagraphStyle("body", fontName=font, fontSize=9, leading=13, wordWrap="CJK", spaceAfter=6)
    heading = ParagraphStyle("heading", parent=style, fontName=bold, fontSize=12, leading=17, textColor=colors.HexColor("#1f4e79"), spaceBefore=10)
    title = ParagraphStyle("title", parent=heading, fontSize=15, leading=20, alignment=1)
    def para(value, selected=style):
        return Paragraph(escape(str(value or "Chưa cập nhật")).replace("\n", "<br/>"), selected)
    story = [para("BÁO CÁO SÀNG LỌC HỒ SƠ PCCC", title), para(project.get("name"), title),
             para("Kết quả sơ bộ cần kỹ sư xác nhận; không thay thế văn bản thẩm định hoặc nghiệm thu."),
             para("I. THÔNG TIN CÔNG TRÌNH", heading)]
    labels = {"name":"Tên công trình", "location":"Địa điểm", "investor":"Chủ đầu tư", "designer":"Đơn vị thiết kế", "stage":"Giai đoạn", "type":"Công năng khai báo", "floors":"Số tầng nổi", "basements":"Số tầng hầm", "pcccHeight":"Chiều cao PCCC (m)", "floorArea":"Diện tích tầng (m²)", "totalFloorArea":"Tổng diện tích sàn (m²)", "fireRating":"Bậc chịu lửa khai báo", "commercialDetails":"Chi tiết công năng"}
    rows = [[para(label), para(project.get(key))] for key, label in labels.items()]
    table = LongTable(rows, colWidths=[145, 365], splitInRow=1)
    table.setStyle(TableStyle([("GRID", (0,0),(-1,-1),0.4,colors.lightgrey),("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f1f5f9"))]))
    if project.get("components"):
        story.append(para("HẠNG MỤC ĐỘC LẬP — KHÔNG GỘP QUY MÔ", heading))
        for c in project["components"]:
            story.append(para(f"{c['name']} — {c.get('type') or 'Chưa rõ công năng'}; {c.get('floors') or '?'} tầng; cao {c.get('height') or '?'} m; tổng sàn {c.get('totalFloorArea') or '?'} m²; khối tích {c.get('volume') or '?'} m³; hạng {c.get('hazardClass') or '?'}; {c.get('fireRating') or '?'}. Nguồn: {c.get('sourceText') or 'Nhập tay'}"))
    story += [table, para("II. KẾT QUẢ SÀNG LỌC QUY MÔ", heading), para(conclusions.get("reason")), para(conclusions.get("basisText"))]
    for warning in conclusions.get("warnings") or []:
        story.append(para("Lưu ý: " + str(warning)))
    story.append(para("III. HẠNG MỤC CẦN KIỂM TRA BẰNG HỒ SƠ", heading))
    rows = [[para(v) for v in ("STT", "Hạng mục", "Nhận xét / căn cứ", "Trạng thái")]]
    for item in checklist:
        rows.append([para(item.get("stt")), para(item.get("criteria")),
            para(str(item.get("note", "")) + "\n" + str(item.get("reference", ""))), para(item.get("result"))])
    table = LongTable(rows, colWidths=[28, 120, 272, 90], repeatRows=1, splitInRow=1)
    table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.lightgrey),("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e2e8f0")),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5)]))
    story += [table, Spacer(1,14), para("IV. XÁC NHẬN CỦA NGƯỜI RÀ SOÁT", heading),
              para("Kỹ sư cần kiểm tra toàn văn, hiệu lực, điều kiện áp dụng và bằng chứng thực tế trước khi ký. Báo cáo do phần mềm tạo không tự xác nhận tuân thủ."), Spacer(1,25), para("Họ tên / chức danh / ngày xác nhận: ............................................")]
    def footer(c, document):
        c.setFont(font,8)
        c.drawRightString(PAGE_W-42,24,f"Trang {document.page}")
    SimpleDocTemplate(buf,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=38,bottomMargin=40,title="Báo cáo sàng lọc PCCC").build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()
