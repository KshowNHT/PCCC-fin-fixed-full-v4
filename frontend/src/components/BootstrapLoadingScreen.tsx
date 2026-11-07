import React, { useState, useEffect } from "react";
import { clearAuth } from "../lib/api";

interface BootstrapLoadingScreenProps {
  onRetry?: () => void;
}

export const BootstrapLoadingScreen: React.FC<BootstrapLoadingScreenProps> = ({ onRetry }) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleResetSession = () => {
    clearAuth();
    window.location.reload();
  };

  const handleReload = () => {
    if (onRetry) {
      onRetry();
    } else {
      window.location.reload();
    }
  };

  let statusMessage = "Đang xác thực phiên làm việc an toàn...";
  let subMessage = "Hệ thống đang kiểm tra chữ ký token và thiết lập kết nối mã hóa...";

  if (elapsedSeconds >= 4 && elapsedSeconds < 12) {
    statusMessage = "Đang kết nối tới dịch vụ máy chủ PCCC AI...";
    subMessage = "Đang đồng bộ cơ sở dữ liệu quy chuẩn và trạng thái phiên làm việc...";
  } else if (elapsedSeconds >= 12) {
    statusMessage = "Máy chủ Cloud đang khởi động nguội (Cold Start)...";
    subMessage =
      "Dịch vụ máy chủ (Render/Aiven) tự động ngủ khi không hoạt động để tiết kiệm tài nguyên. Lần đánh thức đầu tiên thường mất khoảng 30 - 50 giây.";
  }

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-slate-900 text-slate-100 p-6 select-none">
      <div className="relative mb-6">
        {/* Vòng sáng xoay hiệu ứng radar */}
        <div className="w-20 h-20 rounded-full border-4 border-amber-500/20 border-t-amber-500 animate-spin" />
        {/* Biểu tượng ngọn lửa PCCC trung tâm */}
        <div className="absolute inset-0 flex items-center justify-center text-amber-500">
          <svg className="w-8 h-8 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2c1.1 0 2 .9 2 2 0 .74-.4 1.38-1 1.72v2.34C16.89 8.54 20 11.91 20 16c0 4.41-3.59 8-8 8s-8-3.59-8-8c0-4.09 3.11-7.46 7-7.94V5.72C10.4 5.38 10 4.74 10 4c0-1.1.9-2 2-2zm0 8c-3.31 0-6 2.69-6 6 0 3.31 2.69 6 6 6s6-2.69 6-6c0-3.31-2.69-6-6-6zm0 2c2.21 0 4 1.79 4 4 0 2.21-1.79 4-4 4s-4-1.79-4-4c0-2.21 1.79-4 4-4z" />
          </svg>
        </div>
      </div>

      <h2 className="text-lg font-bold text-slate-100 mb-1 text-center tracking-tight">
        {statusMessage}
      </h2>
      <p className="text-xs text-slate-400 text-center max-w-md mb-6 leading-relaxed">
        {subMessage}
      </p>

      {/* Thanh tiến trình mô phỏng */}
      <div className="w-64 h-1.5 bg-slate-800 rounded-full overflow-hidden mb-6 relative">
        <div
          className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all duration-300"
          style={{ width: `${Math.min(95, elapsedSeconds * 4 + 10)}%` }}
        />
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400 mb-6">
        <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-ping" />
        <span>Thời gian chờ: {elapsedSeconds} giây</span>
      </div>

      {elapsedSeconds >= 15 && (
        <div className="flex flex-col sm:flex-row items-center gap-3 animate-fade-in">
          <button
            type="button"
            onClick={handleReload}
            className="px-4 py-2 text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 active:bg-slate-600 rounded-lg border border-slate-700 transition"
          >
            Thử tải lại ngay
          </button>
          <button
            type="button"
            onClick={handleResetSession}
            className="px-4 py-2 text-xs font-medium text-amber-400 bg-amber-950/40 hover:bg-amber-950/70 active:bg-amber-900 rounded-lg border border-amber-600/30 transition"
          >
            Về màn hình đăng nhập
          </button>
        </div>
      )}
    </div>
  );
};

