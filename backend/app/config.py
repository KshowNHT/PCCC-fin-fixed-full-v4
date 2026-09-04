"""Application configuration (v2 — PostgreSQL + JWT + OCR).

Mở rộng từ config.py bản v1: thêm DATABASE_URL, JWT_SECRET, và các cờ tính
năng theo kế hoạch 33 ngày (Ke_hoach_Models_Chatbot_PCCC*.md).

=== SECURITY HARDENING (audit \\brutal \\10x) ===
Module này giờ tự kiểm tra và FAIL-FAST khi khởi động nếu phát hiện cấu hình
bảo mật yếu trong môi trường production (JWT_SECRET/mật khẩu admin còn để
giá trị mặc định) — ngăn deploy "quên đổi secret" lên môi trường thật.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.environ.get("PCCC_DATA_DIR", str(BASE_DIR / "data")))
UPLOADS_DIR = DATA_DIR / "uploads"
LEGAL_DB_DIR = DATA_DIR / "legal_db"
DRAWINGS_DIR = DATA_DIR / "drawings"  # bản vẽ upload để OCR

for _d in (DATA_DIR, UPLOADS_DIR, LEGAL_DB_DIR, DRAWINGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

REGULAR_FONT_PATH = DATA_DIR / "Roboto-Regular.ttf"
BOLD_FONT_PATH = DATA_DIR / "Roboto-Medium.ttf"

# --- AI ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# --- Database (PostgreSQL) ---
# Theo kế hoạch Ngày 1: "Khởi tạo FastAPI, kết nối PostgreSQL."
_INSECURE_DATABASE_URL_DEFAULT = "postgresql+asyncpg://pccc_app:pccc_dev_pass@localhost:5432/pccc_db"
DATABASE_URL = os.environ.get("DATABASE_URL", _INSECURE_DATABASE_URL_DEFAULT)

# --- Auth / JWT (Ngày 1: "Viết API Authentication + JWT") ---
_INSECURE_JWT_DEFAULT = "CHANGE_ME_IN_PRODUCTION_pccc_secret_key"
JWT_SECRET = os.environ.get("JWT_SECRET", _INSECURE_JWT_DEFAULT)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "480"))  # 8 giờ ca làm việc

MIN_PASSWORD_LENGTH = 10  # NIST 800-63B khuyến nghị >=8; nâng lên 10 cho an toàn hơn

# Giới hạn 10 tài khoản nhân viên theo hợp đồng (Ngày 1-2 kế hoạch)
MAX_STAFF_ACCOUNTS = int(os.environ.get("MAX_STAFF_ACCOUNTS", "10"))

_INSECURE_ADMIN_PASSWORD_DEFAULT = "admin123"
DEFAULT_ADMIN_USERNAME = os.environ.get("PCCC_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.environ.get("PCCC_ADMIN_PASSWORD", _INSECURE_ADMIN_PASSWORD_DEFAULT)

PORT = int(os.environ.get("PORT", "3000"))
NODE_ENV = os.environ.get("NODE_ENV", "development")
FRONTEND_DIST_DIR = Path(os.environ.get("PCCC_FRONTEND_DIST", str(BASE_DIR.parent / "frontend" / "dist")))

# CORS: cấu hình được qua biến môi trường (danh sách phân tách bởi dấu phẩy).
# Bản trước hardcode 1 domain demo Vercel không liên quan tới khách hàng thật
# — đã bỏ khỏi mặc định, chỉ còn localhost cho dev. Production BẮT BUỘC set
# PCCC_ALLOWED_ORIGINS qua .env (xem compose.yaml).
_default_origins = "http://localhost:3000,http://localhost:5173"
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("PCCC_ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()
]

# --- Upload hardening ---
# Whitelist nghiêm ngặt phần mở rộng file được phép upload làm tài liệu pháp
# lý — chặn .html/.js/.exe/... giả dạng để tránh lưu trữ nội dung có thể bị
# trình duyệt thực thi (stored XSS) nếu URL từng bị lộ ra ngoài.
ALLOWED_DOCUMENT_EXTENSIONS = {".txt", ".docx", ".pdf"}
ALLOWED_DRAWING_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "25"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Giới hạn độ dài tin nhắn chat để chặn lạm dụng chi phí gọi Gemini API
MAX_CHAT_MESSAGE_LENGTH = int(os.environ.get("MAX_CHAT_MESSAGE_LENGTH", "8000"))

REGULAR_FONT_URL = "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.66/fonts/Roboto/Roboto-Regular.ttf"
BOLD_FONT_URL = "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.1.66/fonts/Roboto/Roboto-Medium.ttf"


def assert_production_secrets_are_safe() -> None:
    """FAIL-FAST khi NODE_ENV=production nhưng JWT_SECRET / mật khẩu admin
    khởi tạo vẫn còn là giá trị mặc định không an toàn. Ngăn tình huống
    "quên đổi secret" khi deploy thật — thà app không khởi động được còn
    hơn chạy với JWT có thể bị giả mạo bởi bất kỳ ai đọc được source code
    công khai này."""
    if NODE_ENV != "production":
        return

    problems = []
    if JWT_SECRET == _INSECURE_JWT_DEFAULT or len(JWT_SECRET) < 32:
        problems.append(
            "JWT_SECRET đang để giá trị mặc định hoặc quá ngắn (<32 ký tự). "
            "Tạo secret mới bằng: openssl rand -hex 32"
        )
    if DEFAULT_ADMIN_PASSWORD == _INSECURE_ADMIN_PASSWORD_DEFAULT:
        problems.append("PCCC_ADMIN_PASSWORD đang để giá trị mặc định 'admin123'. Đặt mật khẩu mạnh khác trong .env")
    if len(DEFAULT_ADMIN_PASSWORD) < MIN_PASSWORD_LENGTH:
        problems.append(f"PCCC_ADMIN_PASSWORD phải dài tối thiểu {MIN_PASSWORD_LENGTH} ký tự.")
    # FIX (rà soát chạy online lần 4): DATABASE_URL cũng có fallback mặc định
    # chứa credential yếu (pccc_dev_pass) viết thẳng trong source code công
    # khai — trước đây KHÔNG được đưa vào fail-fast, chỉ JWT_SECRET/mật khẩu
    # admin được kiểm tra. Dùng kiểm tra "chứa chuỗi" (không phải so khớp
    # tuyệt đối) vì compose.yaml thật lại ghép chuỗi này với host khác
    # ("postgres" thay vì "localhost") khi POSTGRES_PASSWORD không được set
    # trong .env — so khớp tuyệt đối sẽ bỏ sót đúng kịch bản thật này.
    if "pccc_dev_pass" in DATABASE_URL:
        problems.append(
            "DATABASE_URL/POSTGRES_PASSWORD đang dùng mật khẩu DB mẫu 'pccc_dev_pass'. "
            "Đặt POSTGRES_PASSWORD (hoặc DATABASE_URL) thật, mạnh hơn trong .env."
        )

    if problems:
        msg = "\n".join(f"  - {p}" for p in problems)
        sys.stderr.write(
            f"\n[SECURITY] Từ chối khởi động ở môi trường production do cấu hình không an toàn:\n{msg}\n"
            "Sửa file .env rồi khởi động lại. (Bỏ qua kiểm tra này bằng cách đặt NODE_ENV != production "
            "CHỈ khi đang chạy dev/test cục bộ.)\n\n"
        )
        raise SystemExit(1)
