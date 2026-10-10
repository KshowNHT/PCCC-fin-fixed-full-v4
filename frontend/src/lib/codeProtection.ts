/**
 * codeProtection.ts — "Khoá chặn" người dùng tài khoản test truy cập/khai
 * thác mã nguồn phía client qua DevTools trình duyệt, theo yêu cầu bổ sung
 * của khách hàng (không có trong 3 bản báo cáo QA gốc).
 *
 * ============================================================================
 * CẢNH BÁO KỸ THUẬT TRUNG THỰC — ĐỌC KỸ TRƯỚC KHI BẬT TÍNH NĂNG NÀY
 * ============================================================================
 * Đây là các biện pháp "làm khó" (deterrent) ở tầng trình duyệt, KHÔNG PHẢI
 * biện pháp bảo mật thật sự. Về nguyên lý web: trình duyệt BẮT BUỘC phải
 * TẢI VỀ toàn bộ mã HTML/CSS/JS để hiển thị và chạy được trang — nghĩa là
 * mã nguồn phía client LUÔN nằm sẵn trên máy người dùng dưới dạng có thể
 * đọc được. Không có đoạn JavaScript nào (kể cả của module này) có thể
 * ngăn 100% một người dùng đủ kỹ thuật:
 *   - Tắt JavaScript TRƯỚC KHI trang tải (các script chặn ở đây không kịp chạy)
 *   - Mở sẵn DevTools/tab Network TỪ TRƯỚC KHI điều hướng tới trang (nhiều
 *     trình duyệt vẫn ghi lại toàn bộ request nếu tab đã mở sẵn)
 *   - Dùng công cụ chặn NGOÀI trình duyệt (mitmproxy, Burp Suite, Charles...)
 *     để xem toàn bộ traffic HTTP — các công cụ này không hề bị ảnh hưởng
 *     bởi bất kỳ đoạn JS nào chạy TRONG trang
 *   - Tải thẳng mã nguồn bằng `curl`/`wget`/`view-source:` mà không qua
 *     trình duyệt đầy đủ tính năng
 *   - Dùng trình duyệt đã tắt tính năng chặn phím tắt của trang (một số
 *     trình duyệt/extension cho phép ghi đè lại `keydown` của trang)
 *
 * Vì vậy: KHÔNG BAO GIỜ được dùng module này như một lớp bảo vệ dữ liệu/
 * business-logic thật sự. Toàn bộ logic nhạy cảm (thẩm định, tính toán quy
 * định PCCC, xác thực...) đã và phải luôn nằm ở BACKEND (không gửi xuống
 * client) — đây chính là lý do kiến trúc hệ thống này tách biệt rules_engine
 * ở server thay vì tính trên trình duyệt. Module này CHỈ có tác dụng:
 *   1. Ngăn người dùng THÔNG THƯỜNG (không rành kỹ thuật) tò mò/vô tình mở
 *      DevTools khi dùng tài khoản demo/test được cấp.
 *   2. Tăng độ phiền toái cho việc bot/script tự động đơn giản crawl giao
 *      diện (không ảnh hưởng gì tới người dùng cố ý dùng công cụ chuyên dụng).
 *   3. Thể hiện RÕ RÀNG chính sách "không được phép kiểm thử/sao chép mã
 *      nguồn" bằng cảnh báo trực tiếp — có giá trị nhắc nhở/răn đe, có thể
 *      dùng làm căn cứ nếu cần xử lý vi phạm hợp đồng/điều khoản sử dụng.
 * ============================================================================
 */

export interface CodeProtectionOptions {
  /** Vô hiệu hoá chuột phải (menu ngữ cảnh) trên toàn trang. */
  disableRightClick?: boolean;
  /** Chặn các tổ hợp phím mở DevTools phổ biến (F12, Ctrl+Shift+I/J/C, Ctrl+U...). */
  blockDevToolsShortcuts?: boolean;
  /** Bật cơ chế phát hiện DevTools đang mở (dựa trên chênh lệch kích thước cửa sổ). */
  detectDevTools?: boolean;
  /** Callback gọi khi phát hiện DevTools mở (vd: hiện overlay cảnh báo). */
  onDevToolsDetected?: () => void;
  /** Callback gọi khi DevTools được đóng lại sau khi đã mở. */
  onDevToolsClosed?: () => void;
  /** In cảnh báo lớn ra Console khi trang tải xong. */
  printConsoleWarning?: boolean;
}

const DEFAULT_OPTIONS: Required<Omit<CodeProtectionOptions, "onDevToolsDetected" | "onDevToolsClosed">> = {
  disableRightClick: true,
  blockDevToolsShortcuts: true,
  detectDevTools: true,
  printConsoleWarning: true,
};

/** Chặn chuột phải toàn trang. */
function setupDisableRightClick(): () => void {
  const handler = (e: MouseEvent) => e.preventDefault();
  document.addEventListener("contextmenu", handler);
  return () => document.removeEventListener("contextmenu", handler);
}

/** Chặn các tổ hợp phím mở DevTools / xem mã nguồn / lưu trang phổ biến
 * trên cả Windows/Linux (Ctrl+...) và macOS (Cmd+Opt+...). */
function setupBlockDevToolsShortcuts(): () => void {
  const handler = (e: KeyboardEvent) => {
    const key = e.key?.toUpperCase();
    const ctrlOrCmd = e.ctrlKey || e.metaKey;

    // F12: mở DevTools (hầu hết trình duyệt Chromium/Firefox)
    if (key === "F12") {
      e.preventDefault();
      return;
    }
    // Ctrl/Cmd+Shift+I, J, C: DevTools / Console / Chọn phần tử
    if (ctrlOrCmd && e.shiftKey && ["I", "J", "C"].includes(key)) {
      e.preventDefault();
      return;
    }
    // Ctrl/Cmd+U: Xem mã nguồn trang (view-source:)
    if (ctrlOrCmd && key === "U") {
      e.preventDefault();
      return;
    }
    // Ctrl/Cmd+S: Lưu trang về máy (tải toàn bộ HTML/JS/CSS)
    if (ctrlOrCmd && key === "S") {
      e.preventDefault();
      return;
    }
    // macOS: Cmd+Option+I/J/C
    if (e.metaKey && e.altKey && ["I", "J", "C"].includes(key)) {
      e.preventDefault();
      return;
    }
  };
  document.addEventListener("keydown", handler, true);
  return () => document.removeEventListener("keydown", handler, true);
}

/** Phát hiện DevTools đang mở dựa trên chênh lệch kích thước cửa sổ ngoài
 * (outerWidth/outerHeight) so với vùng hiển thị (innerWidth/innerHeight) —
 * khi DevTools mở dạng "docked" (gắn cạnh trình duyệt), chênh lệch này tăng
 * đột biến. Đây là kỹ thuật phổ biến, hoạt động tốt với DevTools dạng gắn
 * cạnh phải/dưới — KHÔNG phát hiện được DevTools mở dạng cửa sổ rời
 * (undocked) hoặc trình duyệt đã có DevTools mở SẴN TỪ TRƯỚC khi trang tải
 * (xem cảnh báo đầu file). Dùng interval (không phải theo dõi liên tục)
 * để tránh hao tốn hiệu năng. */
function setupDetectDevTools(onDetected: () => void, onClosed: () => void): () => void {
  const threshold = 160; // px — ngưỡng chênh lệch hợp lý cho hầu hết DevTools docked
  let wasOpen = false;

  const check = () => {
    const widthDiff = window.outerWidth - window.innerWidth;
    const heightDiff = window.outerHeight - window.innerHeight;
    const isOpen = widthDiff > threshold || heightDiff > threshold;

    if (isOpen && !wasOpen) {
      wasOpen = true;
      onDetected();
    } else if (!isOpen && wasOpen) {
      wasOpen = false;
      onClosed();
    }
  };

  const intervalId = window.setInterval(check, 1000);
  check(); // kiểm tra ngay lần đầu, không đợi 1s
  return () => window.clearInterval(intervalId);
}

function printConsoleWarning() {
  const style = "color: #dc2626; font-size: 20px; font-weight: bold;";
  const styleSmall = "color: #64748b; font-size: 13px;";
  // eslint-disable-next-line no-console
  console.log("%c⚠️ DỪNG LẠI!", style);
  // eslint-disable-next-line no-console
  console.log(
    "%cĐây là hệ thống phần mềm nội bộ. Tài khoản bạn đang dùng chỉ được cấp cho mục đích xem thử/nghiệm thu " +
      "giao diện, KHÔNG được phép sao chép, kiểm thử, hoặc phân tích mã nguồn dưới bất kỳ hình thức nào. " +
      "Mọi truy cập trái phép vào mã nguồn có thể vi phạm điều khoản sử dụng/hợp đồng đã ký kết.",
    styleSmall
  );
}

/**
 * Kích hoạt toàn bộ biện pháp bảo vệ theo cấu hình. Trả về hàm dọn dẹp
 * (cleanup) — LUÔN gọi hàm này khi unmount để gỡ các event listener.
 */
export function activateCodeProtection(options: CodeProtectionOptions = {}): () => void {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const cleanups: Array<() => void> = [];

  if (opts.disableRightClick) cleanups.push(setupDisableRightClick());
  if (opts.blockDevToolsShortcuts) cleanups.push(setupBlockDevToolsShortcuts());
  if (opts.detectDevTools) {
    cleanups.push(
      setupDetectDevTools(
        () => options.onDevToolsDetected?.(),
        () => options.onDevToolsClosed?.()
      )
    );
  }
  if (opts.printConsoleWarning) printConsoleWarning();

  return () => cleanups.forEach((fn) => fn());
}
