interface FastApiValidationErrorItem {
  loc?: unknown[];
  msg?: string;
  type?: string;
}

interface FastApiErrorResponse {
  detail?: string | FastApiValidationErrorItem[];
}

const FIELD_LABELS_VI: Record<string, string> = {
  floors: "Số tầng nổi",
  basements: "Số tầng hầm",
  floorArea: "Diện tích xây dựng",
  totalFloorArea: "Tổng diện tích sàn",
  height: "Chiều cao công trình",
  pcccHeight: "Chiều cao PCCC",
  length: "Chiều dài",
  width: "Chiều rộng",
  fireRating: "Bậc chịu lửa",
  name: "Tên công trình",
  location: "Địa điểm",
  investor: "Chủ đầu tư",
  designer: "Đơn vị thiết kế",
  type: "Loại công trình",
  commercialDetails: "Chi tiết kinh doanh",
};

function translatePydanticMessage(msg: string, fieldLabel: string): string {
  const le = msg.match(/Input should be less than or equal to ([\d.]+)/);
  if (le) return `${fieldLabel}: giá trị phải nhỏ hơn hoặc bằng ${le[1]}.`;
  const ge = msg.match(/Input should be greater than or equal to ([\d.]+)/);
  if (ge) return `${fieldLabel}: giá trị phải lớn hơn hoặc bằng ${ge[1]}.`;
  const lt = msg.match(/Input should be less than ([\d.]+)/);
  if (lt) return `${fieldLabel}: giá trị phải nhỏ hơn ${lt[1]}.`;
  const gt = msg.match(/Input should be greater than ([\d.]+)/);
  if (gt) return `${fieldLabel}: giá trị phải lớn hơn ${gt[1]}.`;
  const maxLen = msg.match(/String should have at most (\d+) character/);
  if (maxLen) return `${fieldLabel}: không được vượt quá ${maxLen[1]} ký tự.`;
  const minLen = msg.match(/String should have at least (\d+) character/);
  if (minLen) return `${fieldLabel}: phải có tối thiểu ${minLen[1]} ký tự.`;
  if (/Field required/i.test(msg)) return `${fieldLabel}: bắt buộc phải nhập.`;
  if (/valid number/i.test(msg)) return `${fieldLabel}: phải là một số hợp lệ.`;
  if (/valid integer/i.test(msg)) return `${fieldLabel}: phải là số nguyên hợp lệ.`;
  return `${fieldLabel}: dữ liệu không hợp lệ.`;
}

function isFastApiErrorResponse(data: unknown): data is FastApiErrorResponse {
  return typeof data === "object" && data !== null && "detail" in data;
}

export async function parseApiErrorMessage(res: Response): Promise<string> {
  try {
    const data: unknown = await res.json();
    if (isFastApiErrorResponse(data)) {
      if (typeof data.detail === "string") {
        return data.detail;
      }
      if (Array.isArray(data.detail)) {
        return data.detail
          .map((item) => {
            const fieldKey =
              Array.isArray(item.loc) && item.loc.length > 0
                ? String(item.loc[item.loc.length - 1])
                : "";
            const fieldLabel = FIELD_LABELS_VI[fieldKey] || "Dữ liệu";
            return translatePydanticMessage(item.msg || "", fieldLabel);
          })
          .join(" ");
      }
    }
  } catch {
    // Không parse được json thì dùng fallback bên dưới
  }
  return "Dữ liệu không hợp lệ hoặc máy chủ đang bận. Vui lòng thử lại.";
}

