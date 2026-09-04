"""Gemini AI integration layer.

Port of server.ts: getAi(), generateContentWithRetry(), runDeepLLMAppraisal(),
cleanResponseText(). Uses the official `google-genai` Python SDK, which is
the direct counterpart of the `@google/genai` JS SDK used in the original.
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import json_repair
from google import genai
from google.genai import types

from app.rules_engine import (
    get_local_fallback_response,
    get_prior_projects_context,
    get_rag_context_for_project,
)
from app.checklist_data import STANDARDS_CHECKLIST_TEMPLATE
from app.config import GEMINI_API_KEY
from app.models import DeepAppraisalResponse

logger = logging.getLogger("pccc.gemini")

_ai_client: Optional[genai.Client] = None

MODELS_TO_TRY = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]


def get_ai() -> genai.Client:
    global _ai_client
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable")
    if _ai_client is None:
        _ai_client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(headers={"User-Agent": "aistudio-build"}),
        )
    return _ai_client


def clean_response_text(text: str) -> str:
    """Strip markdown code fences and any conversational pre/postamble around JSON."""
    clean = (text or "").strip()

    match = re.search(r"```(?:json)?([\s\S]*?)```", clean, re.IGNORECASE)
    if match:
        clean = match.group(1).strip()

    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)

    first_brace = clean.find("{")
    last_brace = clean.rfind("}")

    if first_brace != -1:
        preamble = clean[:first_brace].strip()
        has_preamble = len(preamble) > 0 and not preamble.startswith("```")

        has_postamble = False
        if last_brace != -1:
            postamble = clean[last_brace + 1:].strip()
            has_postamble = len(postamble) > 0 and not postamble.startswith("```")

        if has_preamble or has_postamble:
            end_limit = last_brace + 1 if last_brace != -1 else len(clean)
            clean = clean[first_brace:end_limit]

    return clean.strip()


async def generate_content_with_retry(contents: Any, config: types.GenerateContentConfig):
    """Robust model caller with exponential backoff & failover model fallback."""
    last_error: Optional[Exception] = None
    client = get_ai()

    for model_name in MODELS_TO_TRY:
        max_retries = 3
        delay = 1.5

        for attempt in range(1, max_retries + 1):
            try:
                logger.info("[Gemini] Calling %s, attempt %d/%d...", model_name, attempt, max_retries)
                # FIX (rà soát "sẵn sàng chạy online" lần 4): trước đây gọi
                # Gemini KHÔNG có timeout — nếu API bên ngoài treo (network
                # hang, server quá tải không trả lỗi mà im lặng), request
                # có thể chờ VÔ THỜI HẠN, chiếm giữ 1 luồng worker mãi mãi.
                # Với nhiều người dùng đồng thời, đây là nguy cơ DoS tài
                # nguyên (worker exhaustion) dù không có kẻ tấn công chủ
                # đích. Giới hạn cứng mỗi lần gọi tối đa 45 giây.
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=model_name,
                        contents=contents,
                        config=config,
                    ),
                    timeout=45.0,
                )
                logger.info("[Gemini] Success using %s on attempt %d", model_name, attempt)
                return response
            except asyncio.TimeoutError as err:
                last_error = err
                logger.error("[Gemini] Timeout (45s) on %s (attempt %d/%d)", model_name, attempt, max_retries)
                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2
            except Exception as err:  # noqa: BLE001 - mirrors JS broad catch
                last_error = err
                msg = str(err)
                status = getattr(err, "status", None) or getattr(err, "status_code", None)
                logger.error("[Gemini] Error on %s (attempt %d/%d): %s", model_name, attempt, max_retries, msg)

                is_retryable = (
                    status is None
                    or status == 503
                    or status == 429
                    or (isinstance(status, int) and status >= 500)
                    or any(k in msg for k in ("503", "429", "high demand", "UNAVAILABLE", "busy"))
                )

                if not is_retryable and attempt == 1:
                    break

                if attempt < max_retries:
                    logger.info("[Gemini] Waiting %sms before retrying...", int(delay * 1000))
                    await asyncio.sleep(delay)
                    delay *= 2

        logger.info("[Gemini] Model %s failed. Trying next model if available...", model_name)

    raise last_error or RuntimeError("Exhausted all available Gemini models and retries.")


def _build_system_instruction(rag_context: str, prior_projects_context: str) -> str:
    # FIX B06 (Bao_Cao_QA_Lan_2.md — nội dung 'note' lệch hạng mục): liệt kê
    # tường minh cả 17 hạng mục kèm đúng STT ngay trong system prompt để neo
    # ngữ cảnh — trước đây model chỉ được mô tả chung chung "17 hạng mục
    # kiểm tra (STT từ 1 đến 17)" mà không thấy rõ hạng mục nào ứng với STT
    # nào, khiến dễ gán nhầm note sang sai STT khi tự sinh JSON tự do.
    checklist_anchor = "\n".join(
        f"  {t['stt']}. {t['criteria']} (căn cứ: {t['reference']})" for t in STANDARDS_CHECKLIST_TEMPLATE
    )

    return f"""Bạn là Chuyên gia AI có 20 năm kinh nghiệm thẩm định thiết kế, kiểm duyệt hồ sơ tư vấn phòng cháy chữa cháy (PCCC) tại Việt Nam. Bạn cẩn trọng, tỉ mỉ, khách quan và am hiểu sâu sắc về luật pháp, tiêu chuẩn Việt Nam hiện hành.

Nhiệm vụ cốt lõi của bạn:
1. Nhận diện các thông số kỹ thuật kiến trúc từ cuộc hội thoại hoặc thanh công cụ nhanh và cập nhật chúng vào 'extractedProjectInfo' (Tên công trình, địa điểm, chủ đầu tư, số tầng nổi, hầm, diện tích sàn, chiều cao, chiều rộng, chiều dài, bậc chịu lửa, tính chất kinh doanh dịch vụ).
2. Kiểm tra thông số kỹ thuật thiếu hụt hoặc mâu thuẫn:
   - CHÚ Ý QUAN TRỌNG: Nếu các thông số kỹ thuật cốt lõi (gồm: Phân loại/công năng công trình 'type', Tổng diện tích sàn 'totalFloorArea', Số tầng nổi 'floors') CHƯA ĐẦY ĐỦ hoặc chưa có thông tin chính thức, bạn PHẢI khéo léo đặt câu hỏi rõ ràng, chi tiết trong 'reply' để thu thập đầy đủ thông tin còn thiếu này.
   - Khi các thông số cốt lõi trên CHƯA đầy đủ, hãy thiết lập kết quả 'result' cho tất cả 17 hạng mục trong checklist thành "Cần xem xét" và phản hồi trong 'note' là "Chưa đủ thông số kỹ thuật kiến trúc để rà soát mục này".
   - Chỉ khi đã có đầy đủ các thông số cốt lõi trên, bạn mới tiến hành thẩm định kỹ thuật chi tiết nhất cho 17 hạng mục kiểm duyệt hồ sơ (chuyển đổi kết quả đạt/không đạt/v.v.) theo quy định pháp luật.
3. Kiểm tra mâu thuẫn dữ liệu kỹ thuật và đưa ra phản hồi:
   - Nếu có mâu thuẫn giữa diện tích sàn, số tầng hay kích thức chiều rộng dài công trình, hãy ghi nhận cảnh báo chi tiết vào 'warnings' để khách hàng xác thực.
   - Nếu công năng chính bị khai báo mâu thuẫn (như lúc nói karaoke lúc nói nhà nghỉ), cảnh báo ngay lập tức.
4. Thẩm duyệt tính pháp lý theo "Nghị định 105/2025/NĐ-CP Phụ lục III":
   - Công trình Nhà hỗn hợp, Nhà ở riêng lẻ kết hợp kinh doanh (nhóm F1.4) bắt buộc thẩm duyệt thiết kế kĩ thuật bởi cơ quan Cảnh sát PCCC khi: CAO TỪ 7 TẦNG TRỞ LÊN hoặc TỔNG DIỆN TÍCH SÀN TỪ 3.000 m² TRỞ LÊN.
   - Nếu dưới ngưỡng trên: "KHÔNG THUỘC DIỆN THẨM DUYỆT THIẾT KẾ PCCC BỞI CƠ QUAN CÔNG AN" nhưng "VẪN PHẢI TUÂN THỦ đầy đủ quy định rà soát an toàn PCCC" (QCVN 06:2022/BXD và QCVN 10:2025/BCA) và trình lưu hồ sơ định kỳ 3 năm/lần tại chính quyền cấp cơ sở.
   - LƯU Ý: giá trị 'isSubjectToAppraisal'/'appraisalReason' bạn trả về CHỈ mang tính tham khảo — hệ thống backend sẽ luôn tính lại bằng công thức cứng ở trên để đảm bảo tính nhất quán tuyệt đối giữa các lần chạy, bạn không cần lo lắng việc "chốt sai" giá trị này.
5. Đánh giá Bảng rà soát ĐÚNG 17 HẠNG MỤC sau đây, PHẢI trả về ĐẦY ĐỦ CẢ 17 hạng mục (không bỏ sót, không thêm, không trùng STT), và STT của mỗi hạng mục PHẢI khớp CHÍNH XÁC với danh sách dưới đây (đây là danh sách cố định, không được tự đổi thứ tự hay nội dung hạng mục):
{checklist_anchor}

   Với mỗi mục 'stt' (bắt buộc dùng đúng số STT ở danh sách trên ứng với ĐÚNG tên hạng mục đó — TUYỆT ĐỐI không viết 'note' của hạng mục này vào STT của hạng mục khác), bạn chỉ cung cấp:
   - 'result': chọn chuẩn xác một giá trị phù hợp nhất ("Đạt", "Không đạt", "Không bắt buộc", "Khuyến nghị mạnh", "Khuyến nghị", "Cần xem xét", "Cần đo đạc"). (Giá trị này cũng chỉ mang tính tham khảo, backend sẽ đối chiếu lại bằng rules engine.)
   - 'note': Viết nhận xét phân tích siêu ngắn gọn và súc tích (tối đa 2 câu), ĐÚNG NGỮ CẢNH của riêng hạng mục có STT này (ví dụ: STT nói về 'Bậc chịu lửa' thì note phải nói về bậc chịu lửa, không được lạc sang nội dung đường giao thông hay bình chữa cháy). Tránh lặp lại văn bản tiêu chuẩn thô kệch.

Hãy đưa ra lời thoại phản hồi 'reply' tiếng Việt thân thiện, lịch thiệp, gợi ý khách quan, hỏi rõ thông tin nếu thiếu. Sau đó trả về JSON đồng nhất theo schema.

Tài nguyên văn bản pháp lý quy định tìm kiếm từ RAG:
{rag_context}

Bối cảnh và lịch sử học tập liên dự án:
- Bạn cũng có quyền truy cập vào Thư viện cơ sở dữ liệu pháp lý chuyên dụng (được tải lên bởi người dùng và lưu trữ tại thư mục /data/legal_db/). Hãy luôn kiểm tra, khai thác nội dung của các tài liệu tự chọn này khi thẩm định và nêu rõ tên tài liệu/mã tài liệu khi tư vấn cho người dùng để tăng tính thuyết phục.

Bối cảnh thông số của các dự án tương tự trước đây (sử dụng để nâng cao tốc độ kiểm duyệt và giữ tính đồng nhất phán quyết):
{prior_projects_context}

HƯỚNG DẪN TĂNG TỐC ĐỘ KIỂM TRA & HỌC HỎI LỊCH SỬ THIẾT KẾ:
Rà soát bối cảnh học tập ở trên nếu có để tìm sự tương đồng. Nếu gặp dự án tương đồng cao, hãy học hỏi các đánh giá về bậc chịu lửa, khoảng cách an toàn, hệ thống báo cháy, và vận dụng ngay các đánh giá hay lý luận từ dự án trước vào đánh giá dự án hiện tại để rút ngắn thời gian tư vấn, duy trì tính chính xác đồng bộ tuyệt đối không tính toán hay đánh giá lệch pha từ đầu."""


async def run_deep_llm_appraisal(
    project: Dict[str, Any],
    messages_history: List[Dict[str, Any]],
    document_database: List[Dict[str, Any]],
    chat_sessions: List[Dict[str, Any]],
    custom_trigger_text: Optional[str] = None,
    current_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    rag_context = get_rag_context_for_project(project, document_database)
    prior_projects_context = get_prior_projects_context(project, chat_sessions, current_session_id)
    system_instruction = _build_system_instruction(rag_context, prior_projects_context)

    trigger_prompt = custom_trigger_text or "Hãy phân tích, tư vấn cụ thể và cập nhật các thông tin."

    user_text = (
        f"Thông tin dự án hiện tại: {json.dumps(project, ensure_ascii=False)}\n"
        f"Nội dung lịch sử trò chuyện trước: {json.dumps(messages_history[-6:], ensure_ascii=False)}\n"
        f'Tin nhắn kích hoạt phân tích mới nhất: "{trigger_prompt}"\n\n'
        "Hãy phân tích, đối chiếu toàn bộ thông số kỹ thuật đã nhập với cơ sở dữ liệu pháp luật."
    )

    try:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            # FIX B10 (Bao_Cao_QA_Lan_2.md): temperature=0.2 trước đây cho
            # phép model trả lời khác nhau ở các lần gọi giống hệt đầu vào —
            # nguồn gốc trực tiếp của "kết quả không tái lập được". Kết luận
            # pháp lý/result giờ đã được override deterministic ở main.py
            # (rules_engine), nhưng vẫn hạ temperature về 0 để phần 'note'/
            # 'reply' cũng ổn định nhất có thể giữa các lần chạy giống nhau.
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=DeepAppraisalResponse,
        )
        response = await generate_content_with_retry(
            contents=[{"role": "user", "parts": [{"text": user_text}]}],
            config=config,
        )

        response_text = getattr(response, "text", "") or ""
        json_string = clean_response_text(response_text)
        try:
            return json_repair.loads(json_string)
        except Exception:
            logger.warning("json_repair failed, fallback direct parse")
            return json.loads(json_string)
    except Exception as err:  # noqa: BLE001 - mirrors JS catch -> local fallback
        logger.error("Lỗi gọi Gemini AI: %s", err)
        return get_local_fallback_response(project)
