import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  errorMessage: string;
}

/**
 * ErrorBoundary — FIX (rà soát cuối cùng trước bàn giao khách hàng): trước
 * đây TOÀN BỘ ứng dụng KHÔNG có bất kỳ Error Boundary nào. Hành vi mặc định
 * của React khi 1 component bất kỳ ném lỗi trong lúc render (vd: truy cập
 * field null trên dữ liệu bất ngờ từ API, lỗi logic chưa lường trước) là
 * UNMOUNT TOÀN BỘ CÂY COMPONENT — để lại màn hình TRẮNG HOÀN TOÀN, không có
 * bất kỳ thông báo nào cho người dùng, không có cách nào tự khôi phục ngoài
 * F5. Đây là 1 trong những gap dễ bị bỏ sót nhất trước khi bàn giao khách
 * hàng — mọi thứ "chạy tốt" lúc test kỹ vẫn có thể sập trắng ngay khi gặp 1
 * tình huống dữ liệu chưa lường trước trong môi trường thật.
 *
 * Bọc `<App />` bằng component này (xem main.tsx) — khi có lỗi render ở bất
 * kỳ đâu trong cây, hiển thị màn hình lỗi thân thiện thay vì trắng trơn,
 * kèm nút "Tải lại trang" và nút "Về trang chủ" (xoá session lỗi, thử lại
 * từ đầu). Lỗi được log ra console để dev/admin còn truy vết được nguyên
 * nhân qua log trình duyệt của người dùng (nếu họ báo lại).
 */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error?.message || "Lỗi không xác định" };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] Lỗi runtime chưa được xử lý:", error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    // Xoá state lỗi + điều hướng về gốc — hữu ích khi lỗi bắt nguồn từ 1
    // session/dữ liệu cụ thể đang mở (vd session bị hỏng), không phải lỗi
    // toàn cục — tải lại từ URL gốc tránh lặp lại đúng lỗi đó ngay lập tức.
    window.location.href = "/";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen w-full flex items-center justify-center bg-slate-50 p-6">
          <div className="max-w-md text-center">
            <AlertTriangle className="w-14 h-14 text-amber-500 mx-auto mb-4" />
            <h1 className="text-lg font-black text-slate-900 mb-2">Đã xảy ra lỗi ngoài dự kiến</h1>
            <p className="text-sm text-slate-500 mb-1">
              Hệ thống gặp sự cố khi hiển thị trang. Dữ liệu của bạn không bị mất — vui lòng thử tải lại trang.
            </p>
            <p className="text-xs text-slate-400 mb-6 font-mono break-words">{this.state.errorMessage}</p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={this.handleReload}
                className="flex items-center gap-2 px-4 py-2 bg-brand-orange text-white text-sm font-bold rounded-lg hover:opacity-90 transition-opacity"
              >
                <RefreshCw className="w-4 h-4" />
                Tải lại trang
              </button>
              <button
                onClick={this.handleGoHome}
                className="px-4 py-2 bg-white border border-slate-300 text-slate-700 text-sm font-bold rounded-lg hover:bg-slate-50 transition-colors"
              >
                Về trang chủ
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
