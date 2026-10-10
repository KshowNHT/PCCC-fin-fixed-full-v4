"""Vision/OCR Extraction Model — Ngày 12-17 kế hoạch:

'Phát triển Vision/OCR Model (GPT-4o) để trích xuất thông tin từ file PDF/PNG
bản vẽ.' + 'Tinh chỉnh pipeline OCR để tự điền dữ liệu bóc tách được vào
ProjectData Model.'

Ghi chú kỹ thuật quan trọng: bản thiết kế gốc trong file kế hoạch đề xuất
GPT-4o Vision (OpenAI). Toàn bộ phần còn lại của hệ thống (chatbot, RAG,
appraisal) đã và đang dùng Gemini (`@google/genai` ở bản Node gốc, rồi
`google-genai` ở bản Python). Để tránh phải tích hợp thêm một nhà cung cấp
AI thứ hai (2 bộ API key, 2 SDK, 2 chi phí vận hành) chỉ cho riêng tính năng
OCR, module này dùng Gemini multimodal (cùng model đã cấu hình trong
gemini_client.py) — về mặt chức năng tương đương (đọc ảnh/bản vẽ kỹ thuật,
trả JSON có cấu trúc), chỉ khác nhà cung cấp. Nếu khách hàng yêu cầu đúng
GPT-4o Vision theo hợp đồng, chỉ cần thay client trong hàm
`_call_vision_model()` bên dưới bằng `openai.chat.completions.create(...,
model="gpt-4o", response_format={"type": "json_object"})` — phần rasterize
PDF và parse kết quả giữ nguyên.
"""
import base64
import io
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

from google.genai import types

from app.gemini_client import clean_response_text, generate_content_with_retry
from app.models import ExtractedProjectInfo

logger = logging.getLogger("pccc.ocr_vision")

_VISION_SYSTEM_PROMPT = """Bạn là kỹ sư PCCC chuyên đọc bản vẽ kiến trúc / mặt bằng / khung tên bản vẽ xây dựng Việt Nam.

Nhiệm vụ: nhìn (các) ảnh bản vẽ được cung cấp (mặt bằng, mặt cắt, khung tên, ghi chú kỹ thuật) và trích xuất chính xác các thông số kỹ thuật của công trình. CHỈ điền giá trị khi bạn thực sự đọc thấy trên bản vẽ với giá trị và đơn vị được ghi rõ; không ước tính kích thước, khối tích, hạng nguy hiểm cháy hoặc bậc chịu lửa. Nếu không đọc được hoặc không chắc chắn, để trống (null) — KHÔNG bịa số liệu.

Trả về JSON đúng theo schema, các trường:
- name: Tên công trình (đọc từ khung tên bản vẽ)
- location: Địa điểm xây dựng
- investor: Chủ đầu tư (đọc từ khung tên)
- designer: Đơn vị thiết kế (đọc từ khung tên)
- type: Loại công trình / công năng (vd: "Nhà ở riêng lẻ kết hợp kinh doanh", "Nhà hỗn hợp")
- length, width: Chiều dài, chiều rộng khu đất/công trình (mét), đọc từ kích thước ghi trên mặt bằng
- height: Chiều cao công trình thực tế (mét)
- pcccHeight: Chiều cao tính toán PCCC (thường bằng chiều cao đến sàn tầng trên cùng có người sử dụng, mét)
- floorArea: Diện tích xây dựng 1 tầng điển hình (m²)
- totalFloorArea: Tổng diện tích sàn toàn công trình (m²) — cộng dồn qua các tầng nếu đọc được bảng thống kê diện tích
- floors: Số tầng nổi (đếm qua mặt cắt đứng hoặc ghi chú)
- basements: Số tầng hầm
- fireRating: Bậc chịu lửa nếu có ghi chú kỹ thuật (vd: "Bậc III")
- commercialDetails: Mô tả công năng kinh doanh nếu bản vẽ có ghi chú (vd: cửa hàng tầng 1, gara ô tô...)
- floorFunctions: Mảng công năng từng tầng theo thứ tự tầng 1 -> tầng cao nhất, nếu bản vẽ có chú thích công năng từng tầng

BẮT BUỘC mọi tài liệu trả TẤT CẢ các nhà trong components, kể cả một nhà cũng là danh sách một phần tử, mỗi nhà là một phần tử có id riêng, name, type, height, pcccHeight, floorArea, totalFloorArea, floors, volume (khối tích m³), hazardClass (A/B/C/D/E), fireRating, industrialSubtype (other chỉ khi ghi rõ sản xuất công nghiệp khác, special chỉ khi ghi rõ loại chuyên ngành), sourcePages (trang nguồn) và sourceText (dòng số liệu đọc được). Thông số chưa đọc được dùng 0 hoặc chuỗi rỗng, không điền từ nhà khác. Dòng “Nhà có quy mô lớn nhất”, “Tổng cộng” là dòng tổng hợp, tuyệt đối không tạo hạng mục. KHÔNG gộp các nhà thành nhà hỗn hợp, không cộng diện tích các nhà để áp ngưỡng một nhà. Không sao chép hạng C của một kho cho nhà xưởng hay văn phòng. Các trường kỹ thuật cấp dự án để null; chỉ metadata tên dự án/chủ đầu tư/địa điểm ở cấp dự án. Không suy ra totalFloorArea từ diện tích xây dựng hoặc pcccHeight từ chiều cao tổng thể.
Chỉ trả JSON, không thêm giải thích, không markdown code fence."""


class OCRInputError(ValueError):
    pass


def _pdf_to_images(pdf_path: str, max_pages: int = 24) -> List[bytes]:
    """Rasterize các trang đầu của PDF bản vẽ thành ảnh PNG bytes (dùng poppler qua pdf2image)."""
    from pdf2image import convert_from_path

    from pypdf import PdfReader
    count = len(PdfReader(pdf_path).pages)
    if count > max_pages:
        raise OCRInputError(f"PDF có {count} trang; giới hạn OCR là {max_pages}. Tách hồ sơ thành các phần, không bỏ qua trang.")
    pages = convert_from_path(pdf_path, dpi=150, first_page=1, last_page=max_pages, size=2400, thread_count=1, timeout=30)
    images: List[bytes] = []
    for page in pages:
        import io

        buf = io.BytesIO()
        page.save(buf, format="PNG")
        images.append(buf.getvalue())
    return images


def _load_images_from_upload(file_path: str, content_type: str) -> List[bytes]:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf" or content_type == "application/pdf":
        return _pdf_to_images(file_path)
    # Ảnh trực tiếp (.png/.jpg/.jpeg/.webp)
    from PIL import Image
    with Image.open(file_path) as image:
        image = image.convert("RGB")
        image.thumbnail((2400, 2400))
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return [buf.getvalue()]


async def _call_vision_model(images: List[bytes]) -> Dict[str, Any]:
    """Gọi Gemini multimodal vision. Xem docstring module để biết cách thay
    bằng GPT-4o Vision nếu cần bám sát 100% brand model trong hợp đồng gốc."""
    parts: List[Dict[str, Any]] = [{"text": _VISION_SYSTEM_PROMPT}]
    for page_number, img_bytes in enumerate(images, 1):
        parts.append({"text": f"Trang nguồn {page_number}"})
        parts.append(
            {
                "inline_data": {
                    "mime_type": "image/png",
                    "data": base64.b64encode(img_bytes).decode("ascii"),
                }
            }
        )

    config = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
        response_schema=ExtractedProjectInfo,
    )
    response = await generate_content_with_retry(
        contents=[{"role": "user", "parts": parts}],
        config=config,
    )

    import json_repair

    text = getattr(response, "text", "") or ""
    cleaned = clean_response_text(text)
    try:
        return json_repair.loads(cleaned)
    except Exception:  # noqa: BLE001
        import json

        return json.loads(cleaned)


async def extract_project_data_from_drawing(file_path: str, content_type: str = "") -> Dict[str, Any]:
    """Pipeline OCR đầy đủ: PDF/ảnh bản vẽ -> ảnh hoá -> Gemini Vision -> ProjectData dict.

    Trả về dict theo đúng field names của ProjectInfo/ProjectData (camelCase)
    để frontend autofill trực tiếp vào form, đúng yêu cầu Ngày 15-17:
    'Cập nhật UI Form để hiển thị dữ liệu do AI tự động bóc tách (Autofill)'.
    """
    images = await asyncio.to_thread(_load_images_from_upload, file_path, content_type)
    if not images:
        raise ValueError("Không đọc được trang nào từ file bản vẽ đã upload.")

    try:
        extracted = await _call_vision_model(images)
    except Exception as err:  # noqa: BLE001
        logger.error("Lỗi trích xuất OCR bản vẽ: %s", err)
        raise

    # Fail closed on an incomplete schema, before returning a preview or writing data.
    from pydantic import ValidationError
    try:
        extracted = ExtractedProjectInfo.model_validate(extracted).model_dump(exclude_none=True)
    except ValidationError as exc:
        raise OCRInputError("OCR chưa tách được danh sách hạng mục hợp lệ. Không áp dụng hồ sơ thiếu; hãy thử lại hoặc nhập tay từng nhà.") from exc
    if not extracted["components"]:
        raise OCRInputError("Không đọc được hạng mục độc lập nào. Không tự gộp công trình hoặc suy đoán số liệu.")
    for building in extracted["components"]:
        if not building["sourcePages"] or not building["sourceText"].strip() or any(page > len(images) for page in building["sourcePages"]):
            raise OCRInputError("Hạng mục OCR thiếu trang nguồn hoặc dòng số liệu để đối chiếu. Không áp dụng dữ liệu chưa rõ nguồn.")

    # Loại bỏ key rỗng/None để không ghi đè dữ liệu đã có bằng giá trị rỗng
    result = {k: v for k, v in extracted.items() if v not in (None, "", [])}
    result["_ocrCoverage"] = {"pagesRead": len(images), "completePageCoverage": True,
                              "notice": "Đã gửi tất cả trang trong giới hạn; người dùng phải đối chiếu số lượng hạng mục và số liệu trước khi kiểm duyệt."}
    return result
