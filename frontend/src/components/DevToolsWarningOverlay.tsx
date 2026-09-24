import React from "react";
import { ShieldAlert } from "lucide-react";

/**
 * Overlay toàn màn hình hiển thị khi phát hiện DevTools đang mở (chỉ áp
 * dụng cho tài khoản không phải admin — xem cách gọi trong App.tsx). Che mờ
 * nội dung trang, KHÔNG xoá dữ liệu/đăng xuất người dùng — người dùng chỉ
 * cần đóng DevTools lại là thao tác được tiếp tục bình thường (tránh gây
 * khó chịu quá mức nếu phát hiện nhầm, đồng thời tôn trọng dữ liệu người
 * dùng đang nhập dở).
 *
 * Xem cảnh báo kỹ thuật đầy đủ trong lib/codeProtection.ts — đây là biện
 * pháp răn đe/nhắc nhở, không phải hàng rào bảo mật tuyệt đối.
 */
export function DevToolsWarningOverlay() {
  return (
    <div
      className="fixed inset-0 z-[9999] bg-slate-900/97 backdrop-blur-sm flex items-center justify-center p-6 animate-fade-in"
      style={{ userSelect: "none" }}
    >
      <div className="max-w-md text-center">
        <ShieldAlert className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h2 className="text-white text-xl font-black mb-3">Đã phát hiện công cụ DevTools</h2>
        <p className="text-slate-300 text-sm leading-relaxed">
          Tài khoản bạn đang sử dụng chỉ được cấp cho mục đích xem thử/nghiệm thu giao diện, không được phép sử
          dụng công cụ kiểm tra trình duyệt để xem/khai thác mã nguồn. Vui lòng đóng DevTools để tiếp tục sử dụng
          hệ thống bình thường.
        </p>
        <p className="text-slate-500 text-xs mt-4">
          Dữ liệu bạn đang thao tác không bị mất — chỉ cần đóng DevTools (F12) là có thể tiếp tục.
        </p>
      </div>
    </div>
  );
}
