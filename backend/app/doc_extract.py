"""Text extraction for uploaded .txt / .docx / .doc / .pdf legal documents.

Port of the extraction branch inside POST /api/documents/upload in server.ts:
- .txt  -> read as-is (utf-8 / TCVN3 conversion)
- .docx -> docx2txt.process
- .doc  -> OLE2 Compound File Binary / piece table extraction (Word 97-2003)
- .pdf  -> pypdf.PdfReader
"""
import logging
from pathlib import Path
import re
import struct
from typing import Dict, List, Optional

import docx2txt
from pypdf import PdfReader

# Tắt cảnh báo ồn ào của pypdf khi thiếu fontTools trong môi trường runtime
logging.getLogger("pypdf").setLevel(logging.ERROR)

logger = logging.getLogger("pccc.doc_extract")

TCVN3_MAP: Dict[int, str] = {
    0x7C: "ư",  # Ký tự | trong font ABC/.VnTime thường dùng cho chữ ư
    0x82: "à", 0x83: "ả", 0x84: "ã", 0x85: "á", 0x86: "ạ",
    0x87: "ầ", 0x88: "ẩ", 0x89: "ẫ", 0x8A: "ấ", 0x8B: "ậ",
    0x8C: "è", 0x8D: "ẻ", 0x8E: "ẽ", 0x8F: "é", 0x90: "ẹ",
    0x91: "ề", 0x92: "ể", 0x93: "ễ", 0x94: "ế", 0x95: "ệ",
    0x96: "ì", 0x97: "ỉ", 0x98: "ĩ", 0x99: "í", 0x9A: "ị",
    0x9B: "ò", 0x9C: "ỏ", 0x9D: "õ", 0x9E: "ó", 0x9F: "ọ",
    0xA1: "ă", 0xA2: "â", 0xA3: "ê", 0xA4: "ô", 0xA5: "ơ",
    0xA6: "ư", 0xA7: "đ", 0xA8: "Ă", 0xA9: "Â", 0xAA: "Ê",
    0xAB: "Ô", 0xAC: "Ơ", 0xAD: "Ư", 0xAE: "Đ",
    0xB5: "à", 0xB6: "ả", 0xB7: "ã", 0xB8: "á", 0xB9: "ạ",
    0xBB: "ằ", 0xBC: "ẳ", 0xBD: "ẵ", 0xBE: "ắ", 0xC6: "ặ",
    0xC7: "ầ", 0xC8: "ẩ", 0xC9: "ẫ", 0xCA: "ấ", 0xCB: "ậ",
    0xCC: "è", 0xCE: "ẻ", 0xCF: "ẽ", 0xD0: "é", 0xD1: "ẹ",
    0xD2: "ề", 0xD3: "ể", 0xD4: "ễ", 0xD5: "ế", 0xD6: "ệ",
    0xD7: "ì", 0xD8: "ỉ", 0xDC: "ĩ", 0xDD: "í", 0xDE: "ị",
    0xDF: "ò", 0xE1: "ỏ", 0xE2: "õ", 0xE3: "ó", 0xE4: "ọ",
    0xE5: "ồ", 0xE6: "ổ", 0xE7: "ỗ", 0xE8: "ố", 0xE9: "ộ",
    0xEA: "ờ", 0xEB: "ở", 0xEC: "ỡ", 0xED: "ớ", 0xEE: "ợ",
    0xEF: "ù", 0xF1: "ủ", 0xF2: "ũ", 0xF3: "ú", 0xF4: "ụ",
    0xF5: "ừ", 0xF6: "ử", 0xF7: "ữ", 0xF8: "ứ", 0xF9: "ự",
    0xFA: "ỳ", 0xFB: "ỷ", 0xFC: "ỹ", 0xFD: "ý", 0xFE: "ỵ",
}


def convert_tcvn3_to_unicode(text: str) -> str:
    """Chuyển đổi văn bản tiếng Việt từ mã TCVN3 (ABC/.VnTime) sang Unicode chuẩn."""
    if not text:
        return ""
    tcvn3_markers = [
        "tiªu", "ch¸y", "c«ng", "nhµ", "ng¨n", "®iÒu", "tiªu chuÈn",
        "yªu cÇu", "thiÕt kÕ", "b¶o vÖ", "ch÷a ch¸y", "tho¸t",
        "phßng", "tr×nh", "chèng",
    ]
    sample = text[:5000].lower()
    has_tcvn3 = any(marker in sample for marker in tcvn3_markers)
    if not has_tcvn3:
        tcvn_count = sum(1 for c in text[:2000] if ord(c) in (0xAA, 0xA3, 0xB8, 0xB5, 0xC8, 0xCA, 0xDF, 0xCC, 0xD0))
        if tcvn_count < 5:
            return text

    chars = []
    n = len(text)
    for i, c in enumerate(text):
        code = ord(c)
        if code in TCVN3_MAP:
            mapped = TCVN3_MAP[code]
            if code in (0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE):
                prev_is_lower = (i > 0 and text[i - 1].isalpha() and text[i - 1].islower())
                next_is_lower = (i + 1 < n and text[i + 1].isalpha() and text[i + 1].islower())
                if prev_is_lower or next_is_lower:
                    mapped = mapped.lower()
            chars.append(mapped)
        else:
            chars.append(c)

    res = "".join(chars)
    # Khắc phục chữ Đ hoa giữa các từ thường trong bảng mã TCVN3 cũ (ví dụ: thẩmĐịnh -> thẩm định, quyĐịnh -> quy định)
    res = re.sub(r"(?<=[a-zà-ỹ])Đ(?=[a-zà-ỹ])", "đ", res)
    return res


def _clean_extracted_text(text: str) -> str:
    """Loại bỏ ngắt dòng vô tình làm gãy từ ngữ trong file scan/PDF cũ."""
    if not text:
        return ""
    # Nối các từ bị gãy dòng: ví dụ "Phòng \ncháy", "Phòn\ng", "thiết k\nế"
    text = re.sub(r"(?<=[A-Za-zÀ-ỹ])\s*\n\s*(?=[a-zà-ỹ])", "", text)
    # Chuẩn hóa khoảng trắng ngang
    text = re.sub(r"[ \t]+", " ", text)
    return text


def extract_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="strict") as f:
        raw = f.read()
    return _clean_extracted_text(convert_tcvn3_to_unicode(raw))


def extract_docx(path: str) -> str:
    raw = docx2txt.process(path) or ""
    return _clean_extracted_text(convert_tcvn3_to_unicode(raw))


def extract_doc(path: str) -> str:
    """Trích xuất nội dung văn bản thuần túy từ file Word 97-2003 (.doc) định dạng nhị phân OLE2.

    Phân tích cấu trúc Piece Table (CLX) trong Table stream và đọc trực tiếp
    văn bản Unicode (UTF-16LE) hoặc CP1252/TCVN3 không phụ thuộc thư viện ngoài.
    """
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        raise ValueError("File .doc không đúng định dạng OLE2 Compound Document.")

    sector_shift = struct.unpack("<H", data[30:32])[0]
    sector_size = 1 << sector_shift
    fat_sectors_count = struct.unpack("<I", data[44:48])[0]
    first_dir_sector = struct.unpack("<I", data[48:52])[0]

    fat_sectors = []
    for i in range(min(109, fat_sectors_count)):
        sec = struct.unpack("<I", data[76 + i * 4 : 80 + i * 4])[0]
        if sec < 0xFFFFFFFA:
            fat_sectors.append(sec)

    fat = []
    for fs in fat_sectors:
        pos = (fs + 1) * sector_size
        entries = struct.unpack(f"<{sector_size // 4}I", data[pos : pos + sector_size])
        fat.extend(entries)

    def get_stream(start_sector: int) -> bytes:
        chain = []
        cur = start_sector
        while cur < 0xFFFFFFFA and cur < len(fat):
            chain.append(cur)
            cur = fat[cur]
        return b"".join(data[(s + 1) * sector_size : (s + 2) * sector_size] for s in chain)

    dir_data = get_stream(first_dir_sector)
    word_doc_stream: Optional[bytes] = None
    table_stream_0: Optional[bytes] = None
    table_stream_1: Optional[bytes] = None

    for i in range(0, len(dir_data), 128):
        entry = dir_data[i : i + 128]
        name_len = struct.unpack("<H", entry[64:66])[0]
        if name_len > 0:
            name = entry[: name_len - 2].decode("utf-16le", errors="ignore")
            start_sec = struct.unpack("<I", entry[116:120])[0]
            size = struct.unpack("<I", entry[120:124])[0]
            if name == "WordDocument":
                word_doc_stream = get_stream(start_sec)[:size]
            elif name == "0Table":
                table_stream_0 = get_stream(start_sec)[:size]
            elif name == "1Table":
                table_stream_1 = get_stream(start_sec)[:size]

    if not word_doc_stream or len(word_doc_stream) < 512:
        raise ValueError("Không tìm thấy dòng dữ liệu WordDocument trong file .doc.")

    flags = struct.unpack("<H", word_doc_stream[10:12])[0]
    f_which_tbl = (flags >> 9) & 1
    table_stream = table_stream_1 if f_which_tbl else table_stream_0
    if not table_stream:
        raise ValueError("Không tìm thấy Table stream trong file .doc.")

    fc_clx = struct.unpack("<I", word_doc_stream[0x01A2:0x01A6])[0]
    lcb_clx = struct.unpack("<I", word_doc_stream[0x01A6:0x01AA])[0]
    clx = table_stream[fc_clx : fc_clx + lcb_clx]

    pos = 0
    pcdt_offset = None
    while pos < len(clx):
        clx_type = clx[pos]
        pos += 1
        if clx_type == 1:
            cb = struct.unpack("<H", clx[pos : pos + 2])[0]
            pos += 2 + cb
        elif clx_type == 2:
            pcdt_offset = pos
            break
        else:
            break

    if pcdt_offset is None:
        raise ValueError("Không tìm thấy Piece Table (CLX) trong file .doc.")

    lcb = struct.unpack("<I", clx[pcdt_offset : pcdt_offset + 4])[0]
    plcfpcd = clx[pcdt_offset + 4 : pcdt_offset + 4 + lcb]
    num_pieces = (lcb - 4) // 12
    cp_list = [struct.unpack("<I", plcfpcd[i * 4 : (i + 1) * 4])[0] for i in range(num_pieces + 1)]
    pcd_offset = (num_pieces + 1) * 4

    text_parts = []
    for i in range(num_pieces):
        char_count = cp_list[i + 1] - cp_list[i]
        pcd = plcfpcd[pcd_offset + i * 8 : pcd_offset + (i + 1) * 8]
        fc = struct.unpack("<I", pcd[2:6])[0]
        is_compressed = bool(fc & 0x40000000)
        actual_fc = fc & ~0x40000000
        if is_compressed:
            byte_offset = actual_fc // 2
            raw_bytes = word_doc_stream[byte_offset : byte_offset + char_count]
            piece = raw_bytes.decode("windows-1252", errors="replace")
        else:
            byte_offset = actual_fc
            raw_bytes = word_doc_stream[byte_offset : byte_offset + char_count * 2]
            piece = raw_bytes.decode("utf-16le", errors="replace")
        text_parts.append(piece)

    raw_text = "".join(text_parts).replace("\r\n", "\n").replace("\r", "\n")
    return _clean_extracted_text(convert_tcvn3_to_unicode(raw_text))


def extract_pdf(path: str, original_filename: str) -> str:
    try:
        reader = PdfReader(path)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        if text.strip():
            return _clean_extracted_text(convert_tcvn3_to_unicode(text))
        raise ValueError("PDF không có lớp văn bản. Cần OCR trước khi nạp thư viện.")
    except Exception:
        logger.exception("Không trích xuất được PDF")
        raise


def sanitize_text(text: str) -> str:
    """Strip control bytes & null terminators, matching the JS regex sanitation."""
    text = (text or "").replace("\u0000", "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    return text.strip()


def detect_document_metadata(original_filename: str, text: str) -> Dict[str, str]:
    """Tự động trích xuất mã hiệu (code), tiêu đề (title) và loại văn bản (type) từ tên file hoặc nội dung."""
    stem = Path(original_filename.replace("\\", "/")).stem
    clean_stem = re.sub(r"[_\-]+", " ", stem).strip()

    doc_code = ""
    doc_title = ""
    doc_type = "Khác"

    # 1. Nhận diện Luật PCCC
    if re.search(r"(?i)\bluật\s+(?:pccc|phòng\s+cháy)\b", stem):
        doc_code = "Luật PCCC & CNCH"
        doc_type = "LUẬT"
        doc_title = "Luật Phòng cháy, chữa cháy và Cứu nạn, cứu hộ"

    # 2. Nhận diện các quy chuẩn, tiêu chuẩn, nghị định, thông tư
    if not doc_code:
        code_pattern = r"(?i)\b(TCVN|QCVN|QC|NĐ|ND|TT)\s*[:\-_/.]?\s*([0-9]+(?:\s*[:\-_/.\s]\s*[0-9]+)*)"
        m = re.search(code_pattern, stem)
        if not m and text:
            m = re.search(code_pattern, text[:1500])

        if m:
            prefix = m.group(1).upper()
            if prefix == "QC":
                prefix = "QCVN"
            num_raw = m.group(2)
            parts = [p.strip() for p in re.split(r"[:\-_/.\s]+", num_raw) if p.strip()]
            if prefix in ("TCVN", "QCVN"):
                doc_type = prefix
                # Tìm phần 4 chữ số biểu thị năm ban hành (ví dụ: 1995, 2020, 2022, 2025...)
                year_idx = -1
                for idx, p in enumerate(parts):
                    if len(p) == 4 and p.isdigit() and 1950 <= int(p) <= 2050:
                        year_idx = idx
                        break

                if year_idx > 0:
                    code_num = "-".join(parts[:year_idx])
                    year = parts[year_idx]
                    doc_code = f"{prefix} {code_num}:{year}"
                elif len(parts) >= 1:
                    doc_code = f"{prefix} {'-'.join(parts)}"
            elif prefix in ("NĐ", "ND"):
                doc_code = f"{num_raw}/NĐ-CP" if "nđ-cp" not in num_raw.lower() else num_raw.upper()
                doc_type = "Nghị định"
            elif prefix == "TT":
                doc_code = f"{num_raw}/TT-BCA" if "tt" not in num_raw.lower() else num_raw.upper()
                doc_type = "Thông tư"

    if not doc_code:
        doc_code = clean_stem.upper()[:64]

    # 3. Bóc tách tiêu đề văn bản từ nội dung
    if not doc_title and text:
        cleaned_head = _clean_extracted_text(text[:2500])
        lines = [ln.strip() for ln in cleaned_head.splitlines() if ln.strip()]
        for i, line in enumerate(lines[:20]):
            line_lower = line.lower()
            if any(h in line_lower for h in [
                "cộng hòa xã hội", "độc lập - tự do", "tiêu chuẩn việt nam",
                "tiêu chuẩn quốc gia", "quy chuẩn kỹ thuật quốc gia",
                "bộ xây dựng", "bộ công an", "xuất bản lần", "ban hành kèm theo"
            ]):
                continue
            if re.match(r"(?i)^(?:TCVN|QCVN|NĐ|TT)\s*[\d\s:/\-]+$", line):
                continue
            if any(k in line_lower for k in [
                "phòng cháy", "chống cháy", "an toàn cháy", "quy định",
                "yêu cầu thiết kế", "hệ thống", "trang bị", "thông gió",
                "chữa cháy", "chiếu sáng", "hút khói", "cứu nạn", "cứu hộ"
            ]):
                cand = line
                # Nối dòng kế tiếp nếu là phụ đề (ví dụ: " - Yêu cầu thiết kế")
                if i + 1 < len(lines):
                    next_l = lines[i + 1]
                    if next_l.startswith("-") or any(sub in next_l.lower() for sub in ["yêu cầu", "thiết kế", "lắp đặt"]):
                        cand += " " + next_l
                cand = re.sub(r"\s+", " ", cand).strip()
                if len(cand) >= 15:
                    doc_title = cand[:500]
                    break

    if not doc_title:
        doc_title = clean_stem[:500]

    return {
        "code": doc_code or clean_stem.upper(),
        "title": doc_title or clean_stem,
        "type": doc_type,
    }


